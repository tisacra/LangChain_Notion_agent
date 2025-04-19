from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
import sys

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")

# === LLMの初期化 ===
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORGANIZATION_ID,
    model_name="gpt-4o-mini"
)
llm.invoke("Hello, world!")
