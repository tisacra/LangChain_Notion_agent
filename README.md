# LangChain_Notion_Agent

## 概要
LLMとの議論中に気に入った小話を、任意のタイミングでNotionに書き込むワークフローを構築する。

```mermaid
graph TD
    A[ユーザー入力] --> B{保存指示ありか}
    B -->|あり| C[ConversationBufferMemory から履歴取得]
    C --> D[履歴を要約 #40;LLM#41;]
    D --> E[Notion 固定ページにブロック追記]
    D --> F[要約内容を VectorStore に追加]
    B -->|なし| G[VectorStore で類似履歴検索]
    G --> H[ConversationBufferMemory の履歴と検索結果をプロンプトに挿入]
    H --> I[LLM 応答生成]
    I --> J[ユーザーに回答表示]
    A --> K[ConversationBufferMemory に発話追加]
    I --> K
```

## 設定
1. 仮想環境を構築する
```bash
python -m venv venv
```
2. 仮想環境を有効にする
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```
3. 必要なパッケージをインストールする
```bash
pip install -r requirements.txt
```
4. 「.env」ファイルを作成し、その中にLLMのAPIキーとNotionのトークンを設定する。

例：
```
OPENAI_API_KEY = "your_openai_api_key"
OPENAI_ORGANIZATION_ID = "your_openai_org_id" # organizationで運用する場合
NOTION_TOKEN = "your_notion_token"
PAGE_ID = "your_notion_page_id"
```
