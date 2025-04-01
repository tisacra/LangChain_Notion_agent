# === LangChain + Notion保存先自動検索 RAG統合版 ===

from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from notion_client import Client
import difflib
import requests
import os
import json
from dotenv import load_dotenv

# === 環境変数読み込み ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
FASTAPI_ENDPOINT = "http://localhost:8000/history"

notion = Client(auth=NOTION_TOKEN)

# === Notion保存関数 ===
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

# === 既存タイトル取得 ===
def fetch_page_titles():
    results = notion.databases.query(database_id=DATABASE_ID)
    titles = [
        page["properties"]["Topic"]["title"][0]["text"]["content"]
        for page in results["results"]
    ]
    return titles

# === タイトル類似検索 ===
def search_similar_title(query, titles):
    matches = difflib.get_close_matches(query, titles, n=1, cutoff=0.6)
    return matches[0] if matches else None

# === 過去履歴検索 ===
def fetch_history(topic_keyword):
    try:
        response = requests.get(FASTAPI_ENDPOINT)
        if response.status_code == 200:
            histories = response.json()
            related = [h for h in histories if topic_keyword in h["topic"]]
            if related:
                latest = related[-1]
                return latest["summary"] + "\n" + "\n".join([str(m) for m in latest["messages"]])
        return ""
    except Exception as e:
        print(f"❗️履歴取得失敗: {e}")
        return ""

# === RAGプロンプト ===
prompt = PromptTemplate.from_template(
    """
    以下は過去の議論履歴です：
    {history}

    ユーザーからの質問:
    {prompt}

    上記履歴を参考に、できるだけ具体的に回答してください。
    """
)

# === LangChainセットアップ ===
llm = ChatOpenAI()

def rag_chat_with_title_search(user_input):
    # 記録指示か判定
    if "保存" in user_input and "議題名" in user_input:
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
        # 通常RAG応答
        keyword = "LangChain" if "LangChain" in user_input else ""
        history = fetch_history(keyword) if keyword else ""
        chain = LLMChain(llm=llm, prompt=prompt)
        result = chain.run(prompt=user_input, history=history)
        print(result)

# === 実行例 ===
if __name__ == "__main__":
    while True:
        user_input = input("> ")
        if user_input.lower() in ["exit", "quit"]:
            break
        rag_chat_with_title_search(user_input)
