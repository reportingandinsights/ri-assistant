### R&I Assistant Chatbot ###
# created by Andrew Shiroma to accelerate intern and volunteer onboarding
# uses Langchain and Pinecone to vectorize documents and uses Groq's Llama model to generate responses to user questions 


### Imports ###

# langchain document loaders
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader, UnstructuredMarkdownLoader, UnstructuredXMLLoader
from langchain_community.document_loaders.csv_loader import CSVLoader

# langchain document manipulation - embeddings, text splitters 
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document

# pinecone and vector storing
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
import sentence_transformers

# operations
import os
import time
import subprocess
import tempfile

# web app
import streamlit as st

# AI model
import groq

### Initializing Groq ###

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
1) Always ensure your explanations are clear, concise, and easy to understand for both beginner and advanced users.
2) If the answer involves company-specific processes or documents, refer to the most up-to-date and accurate resources available.
3) Cite the file source as a github hyperlink url for documents you used as sources using bullet-points below your response ONLY. Do not include citations within the response text.

Example scenarios:
1) A user asks, “How do I create a DAX measure to calculate year-over-year growth in Power BI?” You should walk them through the DAX formula and explain how it works in the context of their dataset.
2) A user asks, “Where can I find the internal guidelines for creating Power BI reports?” You should direct them to the relevant company documentation or provide a summary based on company-specific standards.

Your goal is to make the user feel confident in using Power BI and navigating company documentation, while providing practical and actionable solutions.
'''

groq_client = groq.Groq(api_key=st.secrets["GROQ_API_KEY"])

def parse_groq_stream(stream: object) -> None:
    ''' parse groq content stream to feed to streamlit chat write '''
    for chunk in stream:
        try:
            if chunk.choices:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Sorry, there's been an error: {e}. Please try again."})
            print(f"Error: {e}")

### Initializing Pinecone ###

# this embedding generates a 768-dimension vector describing the semantic meaning of the text
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
pinecone_client = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])

index_name = "ri-assistant"
pinecone_namespace = ""

# every time streamlit reruns, creates pinecone index if inecessary
existing_indexes = [index_info["name"] for index_info in pinecone_client.list_indexes()]
if index_name not in existing_indexes:
    print('creating new pinecone index')
    pinecone_client.create_index(
        name=index_name,
        dimension=768, # index dimensions must match embeddings
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"), # these are the free pinecone options
    )
    while not pinecone_client.describe_index(index_name).status["ready"]:
        time.sleep(1)

pinecone_index = pinecone_client.Index(index_name)
st.session_state.vectorstore = PineconeVectorStore(index=pinecone_index, embedding=embeddings)


### RAG Document Loading to Pinecone ###
        
def rag_documents(repo_name: str) -> None:
    ''' 
    repo_name (str): name of the github repo
    loads github documents and uploads them to the pinecone database 
    '''
    github_url = f'https://github.com/reportingandinsights/{repo_name}'

    # personal access token (PAC) is needed query the github API to clone repos 
    github_PAC_url = f'https://{st.secrets["GITHUB_PERSONAL_ACCESS_TOKEN"]}@github.com/reportingandinsights/{repo_name}'

    with st.sidebar:
        try:
            with st.spinner('Updating documents...'):
                # creating a temporary directory from the cloned github in order to load all documents
                with tempfile.TemporaryDirectory() as temp_path:
                    if _clone_github_repo(github_PAC_url, temp_path):
                        ids, docs = _load_github_files(github_url, temp_path)
                        st.session_state.vectorstore.add_documents(documents=docs, ids=ids)

            success = st.success('Documents updated successfully!')
            time.sleep(2)
            success.empty()
        except Exception as e:
            error = st.error(e)
            time.sleep(2)
            error.empty()

def _clone_github_repo(github_url: str, temp_path: str) -> bool:
    ''' 
    clones a gitub repository to a temporary folder and returns the temp path
    temp folder inspiration from https://github.com/cmooredev/RepoReader/tree/main/RepoReader 
    '''
    try:
        subprocess.run(['git', 'clone', github_url, temp_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")
        return False
    
def _load_github_files(github_url: str, temp_path: str) -> tuple:
    ''' iterates over the cloned github repo and loads all files into a list of documents, returns a tuple of ids and docs '''
    ids = []
    docs = []
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=200)

    for root, _, files in os.walk(temp_path):
        # get path from root and remove the temp folders from the path
        # this is used to build the github url
        github_path = '/'.join(root.split(os.sep)[3:])
        github_path = github_path.replace(' ', '%20') # replacing spaces with %20 to make the https url valid

        # iterate over all files and extract text
        for file in files:
            file_path = os.path.join(root, file)
            try:
                loader = None
                if file_path.endswith('.txt'):
                    loader = TextLoader(file_path)
                elif file_path.endswith('.md'):
                    loader = UnstructuredMarkdownLoader(file_path)
                elif file_path.endswith('.xml'):
                    loader = UnstructuredXMLLoader(file_path)
                elif file_path.endswith('.csv'):
                    loader = CSVLoader(file_path)
                elif file_path.endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                elif file_path.endswith(('docx', 'doc')):
                    loader = Docx2txtLoader(file_path)
                elif file_path.endswith(('xlsx', 'xls')):
                    loader = UnstructuredExcelLoader(file_path)

                if loader:
                    # loader.load() returns a list, but this list only has one document because os.walk only gives it one element
                    text = loader.load()[0].page_content

                    # some text is too large to give to Groq, so need to split text into chunks 
                    for index, t in enumerate(text_splitter.split_text(text)):
                        file = file.replace(' ', '%20')

                        if github_path == '': # if the file is in the root directory
                            github_complete_path = f'{github_url}/blob/main/{file}'
                        else: # if the file is in a subdirectory
                            github_complete_path = f'{github_url}/blob/main/{github_path}/{file}'

                        built_doc = _build_document(github_complete_path, t, index)
                        ids.append(github_complete_path)
                        docs.append(built_doc)
                        print('loading:', github_complete_path)

            except Exception as e:
                print(f'error loading {file_path}, error: {e}')

    return (ids, docs)

def _build_document(file_path: str, text: str, index: int) -> Document:
    ''' create a Document object with id, metadata, and page content '''
    return Document(
        id=f'{file_path}-chunk-{str(index)}',
        metadata={
            "source": file_path
        },
        page_content=f'Source: {file_path}\n{text}'
    )

def delete_database() -> None:
    ''' delete and recreate an empty pinecone index '''
    print('deleting index')
    with st.spinner('Deleting database...'):
        pinecone_client.delete_index(index_name)

    success = st.success('Database deleted successfully!')
    time.sleep(2)
    success.empty()


### Confirmation Modals

@st.dialog('Delete Database')
def confirm_delete_database() -> None:
    st.warning('Are you sure you want to delete all the documents in the Pinecone database?', icon='⚠️')
    st.write('You will have to update all documents again! This action is irreversible.')
    if st.button('Yes'):
        delete_database()
        st.rerun()


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
        model="llama-3.3-70b-versatile",
        messages=[
            # note that the groq llama model has a 6000 token/minute limit 
            # this restricts messages larger than 6000 tokens (which is basically 1 1/2 questions)
            # therefore I have to make do with no conversation history
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
    st.subheader('Update Document Options')
    st.button('Update Google Drive Documents', on_click=lambda: rag_documents('google-drive-docs'))
    st.button('Update Common-Code Documents', on_click=lambda: rag_documents('common-code'))

    st.subheader('Delete Options')
    st.button('Delete Pinecone Database', on_click=lambda: confirm_delete_database())
    st.button('Clear Chat History', on_click=lambda: st.session_state.pop('messages', None))