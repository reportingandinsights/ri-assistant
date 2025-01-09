# Knowledge Transfer for 💬 RIA

This guide will give a top-down walkthrough of services and important codebase snippets used to power RIA for future maintenance, starting from the services that the client would see down to the actual code.

## ⌨️ Development
This section will walk through how to get the code and install software dependencies from the Github repository.

**Required**
1) Visual Studio Code (or another code editor)
2) Python
3) Pip

**Installation**
1) Open Visual Studio Code and open a terminal
2) Clone the repository by running the below in the terminal
   
    ```
    git clone https://github.com/reportingandinsights/ri-assistant
    ```

3) Create a virtual environment to download the dependencies

   ```
   python -m venv /path/to/new/virtual/environment
   ```

4) Install all dependencies - ensure you're in the same directory as the `requirements.txt` file 

   ```
   pip install -r "requirements.txt"
   ```

## 🍽️ Services
1) 🚀 Deployment: Streamlit
2) 🤖 AI: Groq
3) 🗃️ Vector Storage: Pinecone
4) 📝 Code Storage: Github Common Code Repository
5) 📝 Document Storage: Google Drive API (in progress)

Each service except Streamlit requires some sort of key to access the resources.

### 🚀 Streamlit
[Streamlit](https://streamlit.io/) is a web service to publish apps, where this chatbot is hosted on. This is where a user asks a natural language question using the dialog box.

Login through the Streamlit-Github SSO using the reporting and insights email.

Streamlit will automatically update the app when new changes are pushed to this project's Github repository.

### 🤖 Groq
[Groq](https://groq.com/) is a free large language model provider that this chat app uses to understand and respond to the user's questions. 

Login through the Groq-Github SSO using the reporting and insights email.

The chat app uses a free [API key](https://console.groq.com/keys) named ri-assistant to access the model. This API key is secure and cannot be accessed after creation. To create a new key and make the chatbot use the new key:
1) Click "Create API Key"
2) Submit a name (you can change the name later) and copy the key
3) Replace the old key with the new key in two places: Streamlit and locally in the file folders
   
**Streamlit**
1) Go to [Streamlit Cloud](https://share.streamlit.io/) and log in
2) Click the three vertical dots on the right and open Settings
3) Go to Secrets and enter the new API key on a new line in the following format, keeping the quotes around the key:

   ```
   GROQ_API_KEY = "replace-with-token"
   ```

**Locally**
1) If it does not exist, create a `.streamlit` folder inside the ri-assistant folder
2) If it does not exist, create a `secrets.toml` file inside the `.streamlit` folder 
3) Enter the new API key in `secrets.toml` on a new line using the following format, keeping the quotes around the key:

   ```
   GROQ_API_KEY = "replace-with-token"
   ```
   
You can go to [this page](https://console.groq.com/metrics) to see metrics on request frequency. 

R&I is currently on Groq's [Free Tier](https://console.groq.com/settings/billing). This means there are built-in [request limits](https://console.groq.com/settings/limits) (as of 1/7/2025) so you do not need to worry about going over and paying money.

### 🗃️ Pinecone
[Pinecone](https://www.pinecone.io/) is a vector database that stores math vectors representing document texts. The Groq AI requests these vectors and uses the information to inform its answers.

Login through the Pinecone-Github SSO using the reporting and insights email.

Pinecone also uses an API key to access the database, with a near identical process to Groq. Remember to copy the key because after you close the window there is no option to access it again.
1) Click "Create API Key"
2) Submit a name (you can change the name later) and copy the key
3) Replace the old key with the new key in two places: the Streamlit website and locally in the `secrets.toml` folder with

   ```
   PINECONE_API_KEY = "replace-with-token"
   ```

### 📝 Code Storage: Github Common Code Repository
This [Github repo](https://github.com/reportingandinsights/common-code) stores unorganized code snippets from various reports that are helpful to reuse. The chatbot uses all the files in this repository for its data.

The chatbot needs a [Fine-grained access token](https://github.com/settings/personal-access-tokens) to read the Github folders in this repository. 

This token:
- does not expire (as of 01/09/25)
- can only access the common-code repository to read metadata and file contents

If the lack of expiration is a security concern, you can regenerate the token to add an expiration date using the following steps. Note that if you do you will also need to replace the token.

**Regenerating the Token**
1) Click on Regenerate Token and choose an expiration date
2) Under Repository Access, only give access to reportingandinsights/common-code
3) Add Read-only access to Contents (metadata access is automatically enabled)
4) Save and replace the old token with the new token in two places: the Streamlit website and locally in the `secrets.toml` folder with

   ```
   GITHUB_PERSONAL_ACCESS_TOKEN = "replace-with-token"
   ```
   
