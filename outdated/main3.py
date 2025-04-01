# === LangChain + Notion保存特化版 (保存指示の文脈判定版) ===

from langchain_openai import ChatOpenAI
from notion_client import Client
import os
import json
from dotenv import load_dotenv
import difflib
import datetime

# === 環境変数読み込み ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# 環境変数の確認
if not NOTION_DATABASE_ID:
    raise ValueError("NOTION_DATABASE_ID is not set in .env file")

notion = Client(auth=NOTION_TOKEN)
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model_name="gpt-3.5-turbo"
)

# === Notion保存関数 ===
def save_to_notion(topic, summary, messages):
    notion.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties={
            "Timestamp": {"date": {"start": datetime.datetime.now().isoformat()}},
            "Topic": {"title": [{"text": {"content": topic}}]},
            "Summary": {"rich_text": [{"text": {"content": summary}}]},
            "Messages": {"rich_text": [{"text": {"content": json.dumps(messages, ensure_ascii=False)}}]},
        }
    )
    print(f"✅ Notionに保存しました: {topic}")

# === 既存ページタイトル取得 ===
def fetch_page_titles():
    results = notion.databases.query(database_id=NOTION_DATABASE_ID)
    titles = [
        page["properties"]["Topic"]["title"][0]["text"]["content"]
        for page in results["results"]
    ]
    return titles

# === 類似タイトル検索 ===
def search_similar_title(query, titles):
    matches = difflib.get_close_matches(query, titles, n=1, cutoff=0.6)
    return matches[0] if matches else None

# === 保存指示判定 ===
def is_valid_save_command(user_input):
    if "保存" not in user_input:
        return False

    prompt = f"""
    先ほどのユーザー発話は、AIとの議論内容を議事録としてNotionに保存するように依頼している意図がありますか？
    「はい」または「いいえ」だけで答えてください。

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
            print("💾 保存指示が検出されました。")
            keyword = "議題名"
            if keyword in user_input:
                keyword = user_input.split("議題名")[-1].replace("「", "").replace("」", "").strip()
                titles = fetch_page_titles()
                matched = search_similar_title(keyword, titles)

                if matched:
                    print(f"📄 既存ページ『{matched}』が見つかりました。そこに記録します。")
                    summary = f"{matched}についての議論"
                    save_to_notion(matched, summary, [user_input])
                else:
                    print(f"❓ 指定されたページ '{keyword}' は存在しません。新規作成しますか？ (yes/no)")
                    confirm = input("> ")
                    if confirm.lower() == "yes":
                        summary = f"{keyword}についての議論"
                        save_to_notion(keyword, summary, [user_input])
                    else:
                        print("❌ 保存をキャンセルしました。")
            else:
                # 議題名が無い場合 → 新規作成案内
                print("❓ 議題名が指定されていません。新規議題名を入力してください:")
                topic = input("> ")
                summary = f"{topic}についての議論"
                save_to_notion(topic, summary, [user_input])
        else:
            result = llm.invoke(user_input)
            print(result)
