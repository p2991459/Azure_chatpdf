from langchain.document_loaders import PyPDFLoader
import openai, os, requests
from azure.storage.blob import BlobServiceClient
openai.api_type = os.getenv("AZURE_API_TYPE")

# Azure OpenAI on your own data is only supported by the 2023-08-01-preview API version
openai.api_version = os.getenv("AZURE_API_VERSION")
# Azure OpenAI setup
openai.api_base = os.getenv("AZURE_API_BASE")  # Add your endpoint here
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")  # Add your OpenAI API key here

storage_account_key = os.getenv("storage_account_key")
storage_account_name = os.getenv("storage_account_name")
connection_string = os.getenv("connection_string")
container_name = os.getenv("container_name")

class Agent:
    def __init__(self, openai_api_key: str | None = None) -> None:
        self.deployment_id = os.getenv("deployment_id")  # Add your deployment ID here
        # Azure Cognitive Search setup
        self.search_endpoint = os.getenv("search_endpoint") # Add your Azure Cognitive Search endpoint here
        self.search_key = os.getenv("search_key")  # Add your Azure Cognitive Search admin key here
        self.search_index_name = os.getenv("search_index_name")  # Add your Azure Cognitive Search index name here
        self.chat_history = []
        self.chain = None
        self.db = None

    def ask(self, question: str) -> str:
        if False:
            response = "Please, add a document."
        else:
            response = self.create_response({"question": question, "chat_history": self.chat_history})
            response = response["answer"].strip()
            self.chat_history.append((question, response))
        return response


    def create_response(self,question):
        def setup_byod(deployment_id: str) -> None:
            """Sets up the OpenAI Python SDK to use your own data for the chat endpoint.

            :param deployment_id: The deployment ID for the model to use with your own data.

            To remove this configuration, simply set openai.requestssession to None.
            """

            class BringYourOwnDataAdapter(requests.adapters.HTTPAdapter):

                def send(self, request, **kwargs):
                    request.url = f"{openai.api_base}/openai/deployments/{deployment_id}/extensions/chat/completions?api-version={openai.api_version}"
                    print(request.url)
                    return super().send(request, **kwargs)

            session = requests.Session()

            # Mount a custom adapter which will use the extensions endpoint for any call using the given `deployment_id`
            session.mount(
                prefix=f"{openai.api_base}/openai/deployments/{deployment_id}",
                adapter=BringYourOwnDataAdapter()
            )

            openai.requestssession = session

        setup_byod(self.deployment_id)
        completion = openai.ChatCompletion.create(
            messages=[{"role": "user",
                       "content": question['question']}],
            deployment_id=self.deployment_id,
            dataSources=[  # camelCase is intentional, as this is the format the API expects
                {
                    "type": "AzureCognitiveSearch",
                    "parameters": {
                        "endpoint": self.search_endpoint,
                        "key": self.search_key,
                        "indexName": self.search_index_name,
                    }
                }
            ]
        )
        # print(completion)
        response = completion["choices"][0]["message"]["content"].strip()
        question["answer"] = response
        return question

    def uploadToBlobStorage(self,file_path,file_name):
        print(f"This is file path:{file_path}")
        print(f"This is file name for blob")
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
        with open(file_path,"rb") as data:
            blob_client.upload_blob(data)
            print(f"Uploaded {file_name}")
    def forget(self) -> None:
        self.db = None
        self.chain = None
        self.chat_history = []
