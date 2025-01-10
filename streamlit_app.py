from langchain_community.document_loaders import UnstructuredImageLoader, GithubFileLoader, PyPDFLoader, UnstructuredExcelLoader, UnstructuredMarkdownLoader, Docx2txtLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_googledrive.document_loaders import GoogleDriveLoader
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
import sentence_transformers
import os
import groq
import streamlit as st
import time


### Initializing Pinecone, Groq system prompt, and response streaming ###

groq_client = groq.Groq(api_key=st.secrets["GROQ_API_KEY"])
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
pinecone_client = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])

index_name = "ri-assist"
existing_indexes = [index_info["name"] for index_info in pinecone_client.list_indexes()]

if index_name not in existing_indexes:
    pinecone_client.create_index(
        name=index_name,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    while not pinecone_client.describe_index(index_name).status["ready"]:
        time.sleep(1)

pinecone_index = pinecone_client.Index(index_name)
pinecone_namespace = ""
vectorstore = PineconeVectorStore(index=pinecone_index, embedding=embeddings)

# system_prompt = f'''
# You are an expert at understanding and explaining Saddleback Reporting and Insights documentation and Power BI. Let's take this step-by-step:
# First: answer any questions based on the data provided and always consider the context of the question, providing the most accurate information when forming a complete, but succinct response.
# Second: if unsure of anything, mention it in the response and offer web search suggestions or file suggestions where appropriate. 
# Third: if you are listing instructions, always attempt to break them down into simple steps, and provide examples where necessary.
# Finally: cite your sources using bullet-points below your response only.'''

system_prompt = f'''
You are an expert chatbot specialized in understanding and explaining Power BI concepts, as well as company-specific documentation. Let's think step-by-step:

Your tasks include:

Power BI Expertise:
Explain core Power BI concepts such as data modeling, DAX (Data Analysis Expressions), Power Query, and visualization techniques.
Guide users through building and sharing reports and dashboards, troubleshooting issues, and optimizing performance.
Offer best practices on data governance, security, and compliance within Power BI.
Provide step-by-step solutions to common Power BI challenges like data transformations, report design, and embedding.

Company-Specific Documentation:
Interpret and clarify internal documents related to business processes, tools, data governance, and reporting standards.
Provide guidance on how Power BI integrates with company-specific data sources, systems, and workflows.
Answer questions related to company policies on data usage, reporting standards, and any custom Power BI templates or resources the company has created.

When responding:
Always ensure your explanations are clear, concise, and easy to understand for both beginner and advanced users.
If the answer involves company-specific processes or documents, refer to the most up-to-date and accurate resources available.
Cite your documents you used as sources using bullet-points below your response only.

Example scenarios:
1) A user asks, “How do I create a DAX measure to calculate year-over-year growth in Power BI?” You should walk them through the DAX formula and explain how it works in the context of their dataset.
2) A user asks, “Where can I find the internal guidelines for creating Power BI reports?” You should direct them to the relevant company documentation or provide a summary based on company-specific standards.

Your goal is to make the user feel confident in using Power BI and navigating company documentation, while providing practical and actionable solutions.
'''

def parse_groq_stream(stream):
    ''' parse groq content stream to feed to streamlit '''
    for chunk in stream:
        try:
            if chunk.choices:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Sorry, there's been an error: {e}. Please try again."})
            print(f"Error: {e}")

### RAG Document Loading to Pinecone ###

def rag_documents() -> None:
    ''' loads documents and uploads them to the pinecone database '''

    # chosen arbitrarily - chunk size is how many characters to split the document into. some documents are too big to send to the AI all at once
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100)

    with st.sidebar:
        with st.spinner('Updating documents...'):
            directory_path = './r&i_assistant_docs'

            dir_docs_ids, dir_docs = _process_directory(directory_path, text_splitter)
            vectorstore.add_documents(documents=dir_docs, ids=dir_docs_ids)
            print('upserting docs:', dir_docs_ids)

            github_docs_ids, github_docs = _process_github(text_splitter)
            vectorstore.add_documents(documents=github_docs, ids=github_docs_ids)
            print('upserting docs:', github_docs_ids)

            print('completed upserting all docs')

        success = st.success('Documents updated successfully!')
        time.sleep(2.5)
        success.empty()

def _process_directory(directory_path: str, text_splitter: object) -> tuple:
    ''' resursively processes all files in a directory returns a tuple of ids and data '''
    ids = []
    data = []

    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            
            loader = None
            if file.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file.endswith('.docx'):
                loader = Docx2txtLoader(file_path)
            elif file.endswith('.xlsx'):
                loader = UnstructuredExcelLoader(file_path)
            elif file.endswith('.csv'):
                loader = CSVLoader(file_path)
            elif file.endswith('.md'):
                loader = UnstructuredMarkdownLoader(file_path)
            # elif files.endswith('.png'):
            #   loader = UnstructuredImageLoader(file_path)

            if loader != None:
                # directory loads documents one at a time
                text = loader.load()[0].page_content # gets a string of text from the file
                split_text = text_splitter.split_text(text)

                for index, t in enumerate(split_text):
                    built_dir_doc = _build_document(file_path, t, index)
                    ids.append(built_dir_doc.id)
                    data.append(built_dir_doc)
                    print('loading:', file_path)

    return (ids, data)
    
def _process_github(text_splitter: object) -> tuple:
    ''' creates Documents for all files in reportingandinsights common-code github repo, returns a tuple of ids and data '''
    ids = []
    data = []

    loader = GithubFileLoader(
        repo='reportingandinsights/common-code',
        branch='main',
        access_token=os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN'),
        file_filter=lambda file_path: file_path.endswith('.md') or file_path.endswith('.txt') or file_path.endswith('.xml'),
    )

    # github loads all documents as a list, so need to iterate through each document
    for gitdoc in loader.load():
        file_path = 'https://github.com/reportingandinsights/common-code/blob/main/' + gitdoc.metadata['path']
        split_text = text_splitter.split_text(gitdoc.page_content)

        for index, text in enumerate(split_text):
            built_gitdoc = _build_document(file_path, text, index)
            ids.append(built_gitdoc.id)
            data.append(built_gitdoc) 
            print('loading:', file_path)

    return (ids, data)

def _build_document(file_path: str, text: str, index: int) -> Document:
    ''' create a Document object with id, metadata, and page content '''
    return Document(
        id=f'{file_path}-chunk-{str(index)}',
        metadata={
            "source": file_path
        },
        page_content=f'Source: {file_path}\n{text}'
    )

### Streamlit App ###

st.title('💬 R&I Assistant (RIA) Chatbot')

# Create a session state variable to store the chat messages
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": system_prompt}, 
        {"role": "assistant", "content": ":wave: Hi I'm RIA! I'm here to help you with any questions. Feel free to ask me anything!"},
    ]

# Displaying messages (except system prompt)
for i in range(1, len(st.session_state.messages)):
    with st.chat_message(st.session_state.messages[i]["role"]):
        st.markdown(st.session_state.messages[i]["content"])

# Create a chat input field to allow the user to enter a message at bottom of page
if query := st.chat_input('How can I help?'):

    # Store and display the current prompt.
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message('user'):
        st.markdown(query)

    # embed the prompt, query the pinecone database, and create a llm query that contains the context
    with st.spinner('Thinking...'):
        query_embed = sentence_transformers.SentenceTransformer('sentence-transformers/all-mpnet-base-v2').encode(query)
        pinecone_matches = pinecone_index.query(vector=query_embed.tolist(), top_k=10, include_metadata=True, namespace=pinecone_namespace)
        contexts = [match['metadata']['text'] for match in pinecone_matches['matches']]
        augmented_query = '<CONTEXT>\n\n-------\n' + '\n'.join(contexts[:10]) + '\n-------\n</CONTEXT>\n\nMY QUESTION:\n' + query

    # Generate a response.
    stream = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            # note that the groq llama model has a 6000 token/minute limit 
            # this restricts message history when I try to send history larger than 6000 tokens (which is basically 1 1/2 questions)
            # therefore I have to make do with no conversation history
            # {"role": m["role"], "content": m["content"]}
            # for m in st.session_state.augmented_messages
            {"role": "assistant", "content": system_prompt},
            {"role": "user", "content": augmented_query},
        ],
        stream=True,
    )

    # Stream the response to the chat using `st.write_stream`, then store it in session
    with st.chat_message('assistant'):
        response = st.write_stream(parse_groq_stream(stream))
    st.session_state.messages.append({"role": "assistant", "content": response})
    
with st.sidebar:
    st.button('Update documents', on_click=lambda: rag_documents())
    st.button('Clear chat', on_click=lambda: st.session_state.pop('messages', None))