import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

# === Notion初期化 ===
notion = Client(auth=NOTION_TOKEN)

# === 内容を読み出し ===
def get_page_content(page_id):
    result = notion.blocks.children.list(block_id=page_id)
    return result

# === データベース内にある子ページを読み出し ===
def get_pages():
    # page名とpageIDを取得
    result = []
    # print(notion.databases.query(database_id=DATABASE_ID)['results'][0])
    for page in notion.databases.query(database_id=DATABASE_ID)['results']:
        if page['properties']['名前']['title'] != []:
            # ページ名が空でない場合のみ取得
            # ページ名とIDを取得
            result.append((page['id'], page['properties']['名前']['title'][0]['text']['content']))
    
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