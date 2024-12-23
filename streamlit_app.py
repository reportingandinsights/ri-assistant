import torch
import sentence_transformers
import os
import dotenv
import groq
from pinecone.grpc import PineconeGRPC as Pinecone
# from langchain.document_loaders import PyPDFLoader, UnstructuredExcelLoader, Docx2txtLoader
# from langchain_community.document_loaders import UnstructuredImageLoader, GithubFileLoader
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain.schema import Document
import streamlit as st

groq_client = groq.Groq(api_key=st.secrets["GROQ_API_KEY"])
pinecone_client = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])
pinecone_index = pinecone_client.Index("ri-assist")
pinecone_namespace = ""

system_prompt = f'''
SYSTEM PROMPT: You are a confident expert at understanding and explaining business technology and development to interns and volunteers. Let's take this step-by-step:
First, answer any questions based on the data provided and always consider the context of the question, providing the most accurate and relevant information when forming a response.
Second, if unsure of anything, mention it in the response and provide a web search suggestion or other documents for further research. 
Finally, cite your sources below your response only.'''

def parse_groq_stream(stream):
    ''' parse groq content stream to feed to streamlit '''
    for chunk in stream:
        if chunk.choices:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content


st.title("💬 R&I Intern & Volunteer Chatbot")

# Create a session state variable to store the chat messages. This ensures that the messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": system_prompt}, 
        {"role": "assistant", "content": "Hello! I'm here to help you with any questions. Feel free to ask me anything!"},
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

    # embed the prompt, query the pinecone database, and create a llm-friendly query 
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