import streamlit as st
from groq import Groq

# Show title and description.
# st.title("💬 Chatbot")
# st.write(
#     "A simple chatbot for R&I Volunteer and Intern Assistance."
# )

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
# openai_api_key = st.text_input("OpenAI API Key", type="password")
# if not openai_api_key:
#     st.info("Please add your OpenAI API key to continue.", icon="🗝️")
# else:

groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
pinecone_client = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])
pinecone_index = pinecone_client.Index("ri-assist")
pinecone_namespace = ""

# Create a session state variable to store the chat messages. This ensures that the messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the existing chat messages via `st.chat_message`.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field to allow the user to enter a message at bottom of page
if prompt := st.chat_input("How can I help?"):

    # embed the prompt, query the pinecone database, and create a llm-friendly query 
    prompt_embed = SentenceTransformer("sentence-transformers/all-mpnet-base-v2").encode(prompt)
    pinecone_matches = pinecone_index.query(vector=query_embed.tolist(), top_k=5, include_metadata=True, namespace=pinecone_namespace)
    contexts = [match['metadata']['text'] for match in pinecone_matches['matches']]
    augmented_prompt = "<CONTEXT>\n" + "\n-------\n".join(contexts[:10]) + "\n-------\n</CONTEXT>\n\nMY QUESTION:\n" + query

    # Store and display the current prompt.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate a response.
    stream = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ],
        stream=True,
    )

    # Stream the response to the chat using `st.write_stream`, then store it in session
    with st.chat_message("assistant"):
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})