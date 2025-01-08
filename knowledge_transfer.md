# Knowledge Transfer for 💬 RIA

This guide will give a top-down walkthrough of services and codebase used to power RIA for future maintenance, starting from the services that the client would see down to the actual code.

## Development
This section will walk through how to get the code from the Github repository.
1) Open Visual Studio Code and open a terminal
2) Clone the repository by running the below in the terminal
   
    ```
    git clone https://github.com/reportingandinsights/ri-assistant
    ```

## Services
1) 🚀 Deployment: Streamlit
2) 🤖 AI: Groq
3) 🗃️ Vector Storage: Pinecone
4) 📝 Code Storage: Github Common Code Repository
5) 📝 Document Storage: Google Drive API (in progress)

Each service except Streamlit requires some sort of key to access the resources.

### 🚀 Streamlit
Streamlit is a web service to publish apps, where this chatbot is hosted on. This is where a user asks a natural language question using the dialog box.

Login through the Github SSO using the reporting and insights email.

Streamlit will automatically update the app when new changes are pushed to this project's Github repository.

### 🤖 Groq
Groq is a free large language model that this chat app uses to understand and respond to the user's questions. 

Login through the Github SSO using the reporting and insights email.

The chat app uses a free [API key](https://console.groq.com/keys) named ri-assistant to access the model. This API key is secure and cannot be accessed after creation. To create a new key and make the chatbot use the new key:
1) Click "Create API Key"
2) Submit a name (you can change the name later) and copy the key
3) Replace the old key with the new key in two places: Streamlit for public use and locally on your computer for development

**Streamlit for Public Use**
1) Go to [Streamlit Cloud](https://share.streamlit.io/) and log in
2) Click the three vertical dots on the right and open Settings
3) Go to Secrets and enter the new API key on a new line in the following format, keeping the quotes around the key:

   ```
   GROQ_API_KEY = "replace-with-token"
   ```

**Locally for Development**
1) If it does not exist, create a `.streamlit` folder inside the ri-assistant folder using Visual Studio Code
2) If it does not exist, create a `secrets.toml` file inside the `.streamlit` folder 
3) Enter the new API key in `secrets.toml` on a new line using the following format, keeping the quotes around the key:

   ```
   GROQ_API_KEY = "replace-with-token"
   ```
   
You can go to [this page](https://console.groq.com/metrics) to see metrics on request frequency. 

R&I is currently on Groq's [Free Tier](https://console.groq.com/settings/billing). This means there are built-in [request limits](https://console.groq.com/settings/limits) (as of 1/7/2025) so you do not need to worry about going over and paying money.

### 🗃️ Pinecone
Pinecone is a vector database that stores math vectors representing document texts. The Groq AI requests these vectors and uses the information to inform its answers.


**Todo:** explain github and gdrive, and code snippets 
