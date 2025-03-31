from langchain_community.chat_models import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key loaded: {'Yes' if api_key else 'No'}")

if api_key:
    llm = ChatOpenAI()
    result = llm.invoke("こんにちは！")
    print(result)
else:
    print("API key not found. Please set the OPENAI_API_KEY environment variable.")
