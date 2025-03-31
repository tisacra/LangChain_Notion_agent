from langmanus import Manus
from notion_client import Client
import datetime
import json

# === 設定 ===
with open("secret.json", "r") as f:
    secrets = json.load(f)

# === Notion設定 ===
NOTION_TOKEN = secrets["NOTION_TOKEN"]
DATABASE_ID = secrets["NOTION_DATABASE_ID"]
notion = Client(auth=NOTION_TOKEN)

# === Notion保存関数 ===
def save_to_notion(topic, summary, messages):
    notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Timestamp": {
                "date": {"start": datetime.datetime.now().isoformat()}
            },
            "Topic": {"title": [{"text": {"content": topic}}]},
            "Summary": {"rich_text": [{"text": {"content": summary}}]},
            "Messages": {"rich_text": [{"text": {"content": json.dumps(messages, ensure_ascii=False)}}]}
        }
    )
    print(f"✅ Notionに保存しました: {topic}")

# === 議題名と要約の抽出 (簡略版) ===
def extract_topic_and_summary(result):
    # 仮の抽出処理（実運用ではプロンプト解析 or NLUモデルを推奨）
    user_msgs = [m["content"] for m in result["trace"]["messages"] if m["role"] == "user"]
    topic = "保存された議論"
    if user_msgs:
        last = user_msgs[-1]
        if "議題名" in last:
            topic = last.split("議題名")[-1].replace("「", "").replace("」", "").strip()
    summary = f"{topic}についての議論"
    return topic, summary

# === Hook関数 ===
def after_step_hook(result):
    try:
        topic, summary = extract_topic_and_summary(result)
        messages = result["trace"]["messages"]
        # 保存条件 (例: "保存" という言葉が含まれている場合のみ)
        if any("保存" in m["content"] for m in messages if m["role"] == "user"):
            save_to_notion(topic, summary, messages)
    except Exception as e:
        print(f"❗️保存時エラー: {e}")

# === LangManus初期化とHook登録 ===
manus = Manus()
manus.add_hook("after_step", after_step_hook)

# === 実行例 ===
if __name__ == "__main__":
    # 通常のプロンプト実行 (ダミー)
    user_input = input("> ")
    result = manus.run(prompt=user_input)
    print(result["output"])
