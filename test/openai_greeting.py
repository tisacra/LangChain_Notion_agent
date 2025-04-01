from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
from pathlib import Path

# .envファイルの絶対パスを取得
env_path = Path(__file__).parent.parent / '.env'
# .envファイルを明示的に指定して読み込み
load_dotenv(dotenv_path=env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")

print(f"ENV Path: {env_path}")
print(f"API Key: {OPENAI_API_KEY}")
print(f"Organization ID: {OPENAI_ORGANIZATION_ID}")

if OPENAI_API_KEY:
    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        organization=OPENAI_ORGANIZATION_ID,
        model="gpt-3.5-turbo"  # モデルを明示的に指定
    )
    result = llm.invoke("こんにちは！")
    print(result)
else:
    print("API key not found. Please check .env file.")