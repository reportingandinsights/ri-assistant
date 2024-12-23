# 💬 R&I Assistant Chatbot (RIA)

## Why RIA?

❓Other chatbots (like 🤖 ChatGPT) are not able to give assistance about Saddleback-specific questions such as how we say our scrum status, details on report standards and guidelines, or information on the data dictionary.

❗This is where **RIA** (**R**&**I** **A**ssistant) comes in - armed with knowledge about Saddleback-specific standards, designs, and Github code, RIA provides volunteers and interns with support, guidance, and answers for common tasks and problems.

## How to use RIA?

1. ☁️ Open in Streamlit cloud (recommended): [![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

2. 🖥️ Run locally (details in dev section)

## RIA's Technical Specs

RIA is a Python Streamlit app that uses Groq's llama-3.1-70b-versatile model, Pinecone for vector databasing and storage, langchain for RAG document parsing, and sentence-transformers for query construction.

## Local Development

1. Clone the repository
   ```
   $ git clone https://github.com/Awnder/RI-assist-demov1.git
   ```

2. Install the requirements
   ```
   $ pip install -r requirements.txt
   ```

3. Run the app locally to debug
   ```
   $ streamlit run streamlit_app.py
   ```

Groq, Pinecone, and Streamlit accounts are registered under the reportingandinsights user.
API keys are stored in the 1Password database.