from langchain_community.chat_models import ChatOllama

llm = ChatOllama(model="mistral")
response = llm.invoke("人工知能とは？")
print(response)