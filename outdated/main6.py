# === LangChain + Notion ブロック追記版 (ConversationBufferMemory 永続化対応) ===

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from notion_client import Client
import os
from dotenv import load_dotenv
import pickle

# === 環境変数読み込み ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
MEMORY_PATH = "memory.pkl"

if not PAGE_ID:
    raise ValueError("PAGE_ID is not set in .env file")

# === NotionとLLMの初期化 ===
notion = Client(auth=NOTION_TOKEN)
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORGANIZATION_ID,
    model_name="gpt-3.5-turbo"
)

# === Memoryの初期化 ===
def load_memory():
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "rb") as f:
            return pickle.load(f)
    return ConversationBufferMemory(return_messages=True)

def save_memory(memory):
    with open(MEMORY_PATH, "wb") as f:
        pickle.dump(memory, f)

memory = load_memory()

# === ブロック追記関数 ===
def append_to_page(page_id, content):
    notion.blocks.children.append(
        block_id=page_id,
        children=[
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": content}}
                    ]
                }
            }
        ]
    )
    print(f"📝 ページに追記しました: {content}")

# === 保存指示判定 ===
def is_valid_save_command(user_input):
    if "保存" not in user_input:
        return False

    prompt = f"""
    以下のユーザー発話は、AIとの議論内容をNotionに保存するように依頼している意図がありますか？
    「はい」または「いいえ」で答えてください。

    発話: "{user_input}"
    """
    decision = llm.invoke(prompt).content
    print(f"判断結果: {decision}")
    return "はい" in decision

# === 実行例 ===
if __name__ == "__main__":
    try:
        while True:
            user_input = input("> ")
            if user_input.lower() in ["exit", "quit"]:
                break

            memory.chat_memory.add_user_message(user_input)

            if is_valid_save_command(user_input):
                print("💾 保存指示が検出されました。指定ページに追記します。")
                summary_prompt = "これまでの議論内容をNotionに保存するのに適した形でまとめてください。"
                messages = memory.load_memory_variables({})["history"] + f"\n{summary_prompt}"
                content = llm.invoke(messages).content
                append_to_page(PAGE_ID, content)
                memory.chat_memory.add_ai_message(content)
            else:
                messages = memory.load_memory_variables({})["history"] + f"\nユーザー: {user_input}"
                result = llm.invoke(messages).content
                print(result)
                memory.chat_memory.add_ai_message(result)

    finally:
        save_memory(memory)
        print("📝 会話履歴を保存しました。")
