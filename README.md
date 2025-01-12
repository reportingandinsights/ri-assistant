# 💬 R&I Assistant Chatbot (RIA)

## Why RIA?

❓Other chatbots (like 🤖 ChatGPT) are not able to give assistance about Saddleback-specific questions such as how we say our scrum status, details on report standards and guidelines, or information on the data dictionary.

❗This is where **RIA** (*R*&*I* *A*ssistant) comes in - armed with knowledge about Saddleback-specific standards, designs, and Github code, RIA provides volunteers and interns with support, guidance, and answers for common tasks and problems.

## How to use RIA?

1) Login to the reportingandinsights Github account or
2) be one of the special users in Streamlit's User Access List (see [Knowledge Transfer](./knowledge_transfer.md) under Streamlit > Changing User Access)

☁️ Then, open in Streamlit cloud: [![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ri-assist-demov1.streamlit.app/)

## RIA's Technical Specs

RIA is a Python Streamlit app that uses Groq's llama-3.1-70b-versatile model, Pinecone for vector databasing and storage, langchain for RAG document parsing, and sentence-transformers for query construction.

Go to [Knowledge Transfer](./knowledge_transfer.md)
