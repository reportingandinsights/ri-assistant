# Knowledge Transfer for 💬 RIA

This guide will give a walkthrough of services and important codebase snippets used to power RIA for future maintenance.

## ⌨️ Development
This section will walk through how to get the code and install software dependencies from the Github repository.

**Required**
1) Visual Studio Code (or another code editor)
2) Python
3) Pip

**Download**
1) Open Visual Studio Code and open a terminal
2) Clone the repository by running the below in the terminal
   
   ```
   $ git clone https://github.com/reportingandinsights/ri-assistant
   ```

3) Create a virtual environment to download the dependencies

   ```
   $ python -m venv /path/to/new/virtual/environment
   ```

4) Install all dependencies - ensure you're in the same directory as the `requirements.txt` file 

   ```
   $ pip install -r requirements.txt
   ```

3. Run the app locally to debug
   ```
   $ streamlit run streamlit_app.py
   ```

Additionally, the "Manage app" sidebar on the right side of the cloud deployment contains helpful print statements to help future debugging.

## 🍽️ Services
1) 🚀 Deployment: Streamlit
2) 🤖 AI: Groq
3) 🗃️ Vector Storage: Pinecone
4) 📝 Document Storage: Github

Each service except Streamlit requires some sort of key to access the resources.

### 🚀 Streamlit
[Streamlit](https://streamlit.io/) is a web service to publish apps, where this chatbot is hosted on. This is where a user asks a natural language question using the dialog box.

Login through the Streamlit-Github SSO using the reporting and insights email.

Streamlit will automatically update the app when new changes are pushed to this project's Github repository main branch.

Note that while this Github repo and Streamlit app is public, Streamlit app usage is restricted to certain users. 

**Changing User Access**
1) Go to the [Streamlit app dashboard](https://share.streamlit.io/)
2) Click the three vertical dots on the right
3) Go to Settings > Sharing
4) Set "Who can view this app" to "Only specific people can view this app"
5) Add or delete user emails as necessary

**Updating Documents**

To update the chatbot on the latest (and greatest) documentation follow these steps:
1) Upload updated code to the common-code repository or upload Google Drive documentation to the google-drive-docs repository
2) Open the Streamlit app
3) Click the relevant "Update Google Drive Documents" or "Update Common-Code Documents button"
As long as the file structure hasn't changed (ie: folders or files have moved), this operation should overwrite the old document in the Pinecone database.

**Deleting Documents**

It might be necessary to delete all documents in the Pinecone database because the file paths might have changed (ie: moving folders and files around). Simply click "Delete Pinecone Database" and the app will delete all documents and recreate an empty database for you.

To double-check that the database has been deleted, go to [Pinecone](https://pinecone.io/) and check the number of documents are in the ri-assistant index.  

Note that you will have to reupload all documents after this operation!

### 🤖 Groq
[Groq](https://groq.com/) is a free large language model provider that this chat app uses to understand and respond to the user's questions.

[Privacy](https://groq.com/privacy-policy/): No data given to Groq's LLMs are stored or used to train their models.

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

[Privacy](https://www.pinecone.io/privacy/): Pinecone protects its customer's privacy and does not sell database data. It does collect usage data on how its services are being leveraged.

Pinecone also uses an API key to access the database, with a near identical process to Groq. Remember to copy the key because after you close the window there is no option to access it again.
1) Click "Create API Key"
2) Submit a name (you can change the name later) and copy the key
3) Replace the old key with the new key in two places: the Streamlit website and locally in the `secrets.toml` folder with

   ```
   PINECONE_API_KEY = "replace-with-token"
   ```

### 📝 Document Storage: Github
The [Common Code repo](https://github.com/reportingandinsights/common-code) stores unorganized code snippets from various reports that are helpful to reuse. The folder documents in the [Google Drive Docs repo](https://github.com/reportingandinsights/google-drive-docs) stores all of the Google Drive documentation. These two repositories are private so no information is exposed.

Login using the reporting and insights email.

**Document Disclaimer**
Because I was not able to get a Google Drive API token to read the documentation in the Google Drive directly, I had to upload the documents to Github. This allows the chatbot to clone the repository and read all the files to send them to Pinecone. **Note images are not loaded to Pinecone due to extra installations and Excel documents are hard for the chatbot to understand as loaded text does not keep its cell format.**

The chatbot needs a [Fine-grained access token](https://github.com/settings/personal-access-tokens) to read and clone the Github folders in both repositories. 

This token:
- does not expire (as of 01/09/25)
- can only access the ri-assistant and common-code repository to read metadata and file contents

If the lack of expiration is a security concern, you can regenerate the token to add an expiration date using the following steps. Note that if you do you will also need to replace the token.

**Regenerating the Token**
1) Click on Regenerate Token and choose an expiration date
2) Under Repository Access, give access to reportingandinsights/common-code and reportingandinsights/ri-assistant
3) Add Read-only access to Contents (metadata access is automatically enabled)
4) Save and replace the old token with the new token in two places: the Streamlit website and locally in the `secrets.toml` folder with

   ```
   GITHUB_PERSONAL_ACCESS_TOKEN = "replace-with-token"
   ```
