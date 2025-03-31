from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")

print(f"API Key loaded: {'Yes' if OPENAI_API_KEY else 'No'}")
if OPENAI_API_KEY:
    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        organization=OPENAI_ORGANIZATION_ID,
        model="gpt-4o-mini"
    )
    result = llm.invoke("こんにちは！")
    print(result)