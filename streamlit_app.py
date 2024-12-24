from langchain_community.document_loaders import UnstructuredImageLoader, GithubFileLoader, PyPDFLoader, UnstructuredExcelLoader, UnstructuredMarkdownLoader, Docx2txtLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
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

system_prompt = f'''
SYSTEM PROMPT: You are an expert at understanding and explaining business technology and Power BI development to interns. Let's take this step-by-step:
First, answer any questions based on the data provided and always consider the context of the question, providing the most accurate and relevant information when forming a response.
Second, if unsure of anything, mention it in the response and provide a web search suggestion or other documents for further research. 
Third, if you are listing instructions, always attempt to break them down into simple steps, and provide examples where necessary.
Fourth, use emojis sparingly to highlight key points.
Finally, cite your sources using bullet-points below your response only.'''

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

    with st.sidebar:
        with st.spinner("Updating documents..."):
            directory_path = "./r&i_assistant_docs"

            dir_docs_ids, dir_docs = _process_directory(directory_path)
            vectorstore.add_documents(documents=dir_docs, ids=dir_docs_ids)
            print('upserting docs:', dir_docs_ids)

            github_docs_ids, github_docs = _process_github()
            vectorstore.add_documents(documents=github_docs, ids=github_docs_ids)
            print('upserting docs:', github_docs_ids[len(github_docs_ids)//2:])

            print('completed upserting all docs')


        success = st.success("Documents updated successfully!")
        time.sleep(2.5)
        success.empty()

# from sys import getsizeof
# too_big = []
# for text in df['text'].tolist():
#     if getsizeof(text) > 5000:
#         too_big.append((text, getsizeof(text)))
# print(f"{len(too_big)} / {len(df)} records are too big")

def _process_directory(directory_path) -> tuple:
    ''' resursively processes all files in a directory returns a tuple of ids and data '''
    ids = []
    data = []

    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            
            loader = None
            if file.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            elif file.endswith(".docx"):
                loader = Docx2txtLoader(file_path)
            elif file.endswith(".xlsx"):
                loader = UnstructuredExcelLoader(file_path)
            elif file.endswith(".csv"):
                loader = CSVLoader(file_path)
            elif file.endswith(".md"):
                loader = UnstructuredMarkdownLoader(file_path)
            # elif files.endswith(".png"):
            #   loader = UnstructuredImageLoader(file_path)

            if loader != None:
                built_dir_doc = _build_directory_document(file_path, loader)
                ids.append(built_dir_doc.id)
                data.append(built_dir_doc)

            print('loading:', file_path)

    return (ids, data)
    
def _process_github() -> tuple:
    ''' creates Documents for all files in reportingandinsights common-code github repo, returns a tuple of ids and data '''
    ids = []
    data = []

    loader = GithubFileLoader(
        repo="reportingandinsights/common-code",
        branch="main",
        access_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        file_filter=lambda file_path: file_path.endswith(".md") or file_path.endswith(".txt") or file_path.endswith(".xml"),
    )
    
    for gitdoc in loader.load():
        built_gitdoc = _build_github_doc("https://github.com/reportingandinsights/common-code/", gitdoc)
        ids.append(built_gitdoc.id)
        data.append(built_gitdoc)

        print('uploading:', gitdoc.metadata['path'])

    return (ids, data)

def _build_directory_document(file_path: str, loader: object) -> Document:
    ''' create a Document object with id, metadata, and page content '''
    return Document(
        id=file_path,
        metadata={
            "source": file_path
        },
        page_content=f"Source: {file_path}\n{loader.load()[0].page_content}"
    )

# have to add /blob/main/folder to the url, and %20 to replace spaces in url

def _build_github_doc(repo_name: str, gitdoc: list) -> Document:
    ''' create a Document object with id, metadata, and page content. github loader loads all documents so requires a different function '''
    return Document(
        id=f"{repo_name}{gitdoc.metadata['path']}",
        metadata={
            "source": f"{repo_name}{gitdoc.metadata['path']}"
        },
        page_content=f"Source: {repo_name}{gitdoc.metadata['path']}\n{[gitdoc][0].page_content}" # convert the doc to a 1-element list to access the page_content
    )


### Streamlit App ###

st.title("💬 R&I Assistant (RIA) Chatbot")

# Create a session state variable to store the chat messages. This ensures that the messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": system_prompt}, 
        {"role": "assistant", "content": ":wave: Hi I'm RIA! I'm here to help you with any questions. Feel free to ask me anything!"},
    ]

# if "augmented_queries" not in st.session_state:
#     st.session_state.augmented_queries = []

# Display the existing chat messages via `st.chat_message`.
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         if "SYSTEM PROMPT" not in message["content"]:
#             st.markdown(message["content"])

# Displaying initial message and not the system prompt
for i in range(1, len(st.session_state.messages)):
    with st.chat_message(st.session_state.messages[i]["role"]):
        st.markdown(st.session_state.messages[i]["content"])

# Create a chat input field to allow the user to enter a message at bottom of page
if query := st.chat_input("How can I help?"):

    # Store and display the current prompt.
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Store the augmented query
    # st.session_state.augmented_queries.append({"role": "user", "content": augmented_query})

    # embed the prompt, query the pinecone database, and create a llm query that contains the context
    with st.spinner("Thinking..."):
        query_embed = sentence_transformers.SentenceTransformer("sentence-transformers/all-mpnet-base-v2").encode(query)
        pinecone_matches = pinecone_index.query(vector=query_embed.tolist(), top_k=5, include_metadata=True, namespace=pinecone_namespace)
        contexts = [match['metadata']['text'] for match in pinecone_matches['matches']]
        augmented_query = "<CONTEXT>\n" + "\n-------\n".join(contexts[:10]) + "\n-------\n</CONTEXT>\n\nMY QUESTION:\n" + query
        
    # Generate a response.
    stream = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            # note that the groq llama model has a 6000 token/minute limit 
            # this restricts message history when I try to send history larger than 6000 tokens (which is like 1 question)
            # therefore I have to make do with no conversation history
            # {"role": m["role"], "content": m["content"]}
            # for m in st.session_state.messages
            {"role": "assistant", "content": system_prompt},
            {"role": "user", "content": augmented_query},
        ],
        stream=True,
    )

    # Stream the response to the chat using `st.write_stream`, then store it in session
    with st.chat_message("assistant"):
        response = st.write_stream(parse_groq_stream(stream))
    st.session_state.messages.append({"role": "assistant", "content": response})
    
with st.sidebar:
    st.button("Update documents", on_click=lambda: rag_documents())
    st.button("Clear chat", on_click=lambda: st.session_state.pop("messages", None))