from notion_client import Client
from dotenv import load_dotenv
import os

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

notion = Client(auth=NOTION_TOKEN)

response = notion.search(filter={"property": "object", "value": "database"})
for result in response["results"]:
    print(result["id"], result["title"])

database_id = response["results"][0]["id"]

response = notion.databases.query(database_id=database_id)
for page in response["results"]:
    print(page["properties"])
