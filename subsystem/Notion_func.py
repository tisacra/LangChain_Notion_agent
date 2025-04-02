import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

# === Notion初期化 ===
notion = Client(auth=NOTION_TOKEN)

# === 内容を読み出し ===
def get_page_content(page_id):
    result = notion.blocks.children.list(block_id=page_id)
    return result

# === データベース内にある子ページを読み出し ===
def get_pages(database_id):
    # page名とpageIDを取得
    result = [(page['id'], page['properties']['名前']['title'][0]['text']['content']) for page in notion.databases.query(database_id=database_id)['results']]
    return result

# === Notionブロック追記関数 ===
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