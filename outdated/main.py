# === LangChain + Notion 保存テンプレート ===

from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.callbacks.base import BaseCallbackHandler
from dotenv import load_dotenv
from notion_client import Client
import datetime
import json
import os

# === .env読み込み ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

# === Notion保存関数 ===
notion = Client(auth=NOTION_TOKEN)

def save_to_notion(topic, summary, messages):
    notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Timestamp": {"date": {"start": datetime.datetime.now().isoformat()}},
            "Topic": {"title": [{"text": {"content": topic}}]},
            "Summary": {"rich_text": [{"text": {"content": summary}}]},
            "Messages": {"rich_text": [{"text": {"content": json.dumps(messages, ensure_ascii=False)}}]},
        }
    )
    print(f"✅ Notionに保存しました: {topic}")

# === CallbackHandler ===
class SaveToNotionHandler(BaseCallbackHandler):
    def on_chain_end(self, outputs, **kwargs):
        inputs = kwargs.get('inputs', {})
        user_input = inputs.get('prompt', '')
        if "保存" in user_input and "議題名" in user_input:
            topic = "保存された議論"
            if "議題名" in user_input:
                topic = user_input.split("議題名")[-1].replace("「", "").replace("」", "").strip()
            summary = f"{topic}についての議論"
            save_to_notion(topic, summary, [user_input, outputs])

# === LangChainセットアップ ===
llm = ChatOpenAI()
prompt = PromptTemplate.from_template("あなたの質問: {prompt}")

chain = LLMChain(
    llm=llm,
    prompt=prompt,
    callbacks=[SaveToNotionHandler()]
)

# === 実行例 ===
if __name__ == "__main__":
    while True:
        user_input = input("> ")
        if user_input.lower() in ["exit", "quit"]:
            break
        result = chain.run(prompt=user_input)
        print(result)
