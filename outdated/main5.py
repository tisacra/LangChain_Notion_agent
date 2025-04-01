# === LangChain + Notion ブロック追記版 (固定ページIDで運用) ===
from langchain_openai import ChatOpenAI
from notion_client import Client
import os
from dotenv import load_dotenv

# === 環境変数読み込み ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")  # ← 固定ページIDを環境変数から取得

# === 環境変数の確認 ===
if not PAGE_ID:
    raise ValueError("PAGE_ID is not set in .env file")

# === NotionとLLMの初期化 ===
notion = Client(auth=NOTION_TOKEN)
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORGANIZATION_ID,
    model_name="gpt-3.5-turbo"
)

# === ブロックとして追記 ===
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
    while True:
        user_input = input("> ")
        if user_input.lower() in ["exit", "quit"]:
            break

        if is_valid_save_command(user_input):
            print("💾 保存指示が検出されました。指定ページに追記します。")
            prompt = f"""
            先ほどの議論をNotionブロックとして保存するのに適した形でまとめてください。
            """
            content = llm.invoke(prompt).content
            append_to_page(PAGE_ID, content)
        else:
            result = llm.invoke(user_input)
            print(result)
