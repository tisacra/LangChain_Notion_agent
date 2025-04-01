# === LangChain + Notion保存特化版 (ページ検索 & ブロック追記版, langchain_openai適用) ===
from langchain_openai import ChatOpenAI
from notion_client import Client
import os
from dotenv import load_dotenv
import difflib
import datetime

# === 環境変数読み込み ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# 環境変数の確認
if not NOTION_DATABASE_ID:
    raise ValueError("NOTION_DATABASE_ID is not set in .env file")

notion = Client(auth=NOTION_TOKEN)
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORGANIZATION_ID,
    model_name="gpt-3.5-turbo"
)

# === 既存ページタイトル取得 ===
def fetch_page_titles_and_ids():
    results = notion.databases.query(database_id=NOTION_DATABASE_ID)
    title_id_pairs = []
    for page in results["results"]:
        title = page["properties"]["Topic"]["title"][0]["text"]["content"]
        page_id = page["id"]
        title_id_pairs.append((title, page_id))
    return title_id_pairs

# === 類似タイトル検索 ===
def search_similar_title(query, title_id_pairs):
    titles = [t[0] for t in title_id_pairs]
    matches = difflib.get_close_matches(query, titles, n=1, cutoff=0.6)
    if matches:
        matched_title = matches[0]
        matched_id = [t[1] for t in title_id_pairs if t[0] == matched_title][0]
        return matched_title, matched_id
    return None, None

# === ブロックとして追記 ===
def append_to_page(page_id, content):
    print(f"📝 ページに追記します: {content}")
    notion.blocks.children.append(
        block_id=page_id,
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
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
    以下のユーザー発話は、AIとの議論内容を議事録としてNotionに保存するように依頼している意図がありますか？
    「はい」または「いいえ」で答えてください。

    発話: "{user_input}"
    """
    decision = llm.invoke(prompt).content
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
                title_id_pairs = fetch_page_titles_and_ids()
                matched_title, matched_id = search_similar_title(keyword, title_id_pairs)

                if matched_title:
                    print(f"📄 既存ページ『{matched_title}』が見つかりました。そこに追記します。")
                    append_to_page(matched_id, user_input)
                else:
                    print(f"❓ 指定されたページ '{keyword}' は存在しません。新規作成しますか？ (yes/no)")
                    confirm = input("> ")
                    if confirm.lower() == "yes":
                        new_page = notion.pages.create(
                            parent={"database_id": NOTION_DATABASE_ID},
                            properties={
                                "Topic": {"title": [{"text": {"content": keyword}}]},
                                "Timestamp": {"date": {"start": os.popen('date -Iseconds').read().strip()}},
                                "Summary": {"rich_text": [{"text": {"content": f"{keyword}についての議論"}}]},
                                "Messages": {"rich_text": [{"text": {"content": user_input}}]},
                            }
                        )
                        append_to_page(new_page["id"], user_input)
                    else:
                        print("❌ 保存をキャンセルしました。")
            else:
                # 議題名が無い場合 → 新規作成案内
                print("❓ 議題名が指定されていません。新規議題名を入力してください:")
                topic = input("> ")
                if not topic.strip():
                    print("❌ 議題名が入力されませんでした。")
                    continue
                
                try:
                    new_page = notion.pages.create(
                        parent={"database_id": NOTION_DATABASE_ID},
                        properties={
                            "Topic": {"title": [{"text": {"content": topic}}]},
                            "Timestamp": {"date": {"start": datetime.datetime.now().isoformat()}},
                            "Summary": {"rich_text": [{"text": {"content": f"{topic}についての議論"}}]},
                            "Messages": {"rich_text": [{"text": {"content": user_input}}]},
                        }
                    )
                    print(f"✅ 新規ページ『{topic}』を作成しました。")
                    append_to_page(new_page["id"], user_input)
                except Exception as e:
                    print(f"❌ ページの作成に失敗しました: {e}")
        else:
            result = llm.invoke(user_input)
            print(result)
