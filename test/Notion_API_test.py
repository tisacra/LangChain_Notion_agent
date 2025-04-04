from notion_client import Client
from dotenv import load_dotenv
import os

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
DATABASE_ID = os.getenv("DATABASE_ID")

notion = Client(auth=NOTION_TOKEN)

# === 内容を読み出し ===
def get_page_content(page_id):
    result = notion.blocks.children.list(block_id=page_id)
    return result

# === データベース内にある子ページを読み出し ===
def get_database_content(database_id):
    # page名とpageIDを取得
    result = [(page['id'], page['properties']['名前']['title'][0]['text']['content']) for page in notion.databases.query(database_id=database_id)['results']]
    return result

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

# === 実行例 ===
if __name__ == "__main__":
    #print(get_page_content(PAGE_ID))
    #append_to_page(PAGE_ID, "Test content")
    print(get_database_content(DATABASE_ID))
    append_to_page(get_database_content(DATABASE_ID)[0][0], "Test content")