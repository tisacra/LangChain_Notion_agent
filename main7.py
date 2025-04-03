# === LangChain + Notion ブロック追記版 (ConversationBufferMemory + VectorStore統合) ===
'''
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
    J --> K[ConversationBufferMemory に発話追加
            +
            質問・回答ペアを VectorStore に追加]
    K --> A
'''

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv
import pickle
import shutil

import subsystem.Notion_func as Notion_func

SUMMARIZE_LOCAL = False
VALID_SAVE_LOCAL = False

# === 動的要約設定 ===
from langchain_ollama import ChatOllama

# 要約専用パイプライン
local_summarizer = ChatOllama(model="gemma3:4b", verbose=True)

turn_counter = 0
SUMMARY_INTERVAL = 3  # 3ターンごとに要約
summary_memory = ""  # 要約蓄積用

# === 環境変数読み込み ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")
DATABASE_ID = os.getenv("DATABASE_ID")
PAGE_ID = os.getenv("PAGE_ID")

MEMORY_PATH = "memory/"
VECTORSTORE_PATH = "vectorstore/"

if not PAGE_ID:
    raise ValueError("PAGE_ID is not set in .env file")

if not DATABASE_ID:
    raise ValueError("DATABASE_ID is not set in .env file")

# === LLMの初期化 ===
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORGANIZATION_ID,
    model_name="gpt-4o-mini"
)

embeddings = OpenAIEmbeddings()


# === Memoryの初期化 ===
def load_memory():
    if os.path.exists(MEMORY_PATH + PAGE_ID + ".pkl"):
        with open(MEMORY_PATH + PAGE_ID + ".pkl", "rb") as f:
            return pickle.load(f)
    return ConversationBufferMemory(return_messages=True)

def save_memory(memory):
    with open(MEMORY_PATH + PAGE_ID + ".pkl", "wb") as f:
        pickle.dump(memory, f)

def refresh_memory():
    """会話履歴をリフレッシュする"""
    global memory
    memory = ConversationBufferMemory(return_messages=True)
    if os.path.exists(MEMORY_PATH + PAGE_ID + ".pkl"):
        os.remove(MEMORY_PATH + PAGE_ID + ".pkl")
    print("🔄 会話履歴をリフレッシュしました")

memory = load_memory()

# === VectorStoreの初期化 ===
def load_vectorstore():
    """VectorStoreをロード、なければ新規作成"""
    if os.path.exists(VECTORSTORE_PATH + PAGE_ID):
        return FAISS.load_local(VECTORSTORE_PATH + PAGE_ID, embeddings, allow_dangerous_deserialization=True)
    
    # 初期化時は最低1つのテキストが必要
    vectorstore = FAISS.from_texts(
        ["初期化用のダミーテキストです。このテキストは検索には使用されません。"],
        embeddings
    )
    vectorstore.save_local(VECTORSTORE_PATH + PAGE_ID)
    return vectorstore

def save_vectorstore(vectorstore):
    """VectorStoreを保存"""
    vectorstore.save_local(VECTORSTORE_PATH + PAGE_ID)

def refresh_vectorstore():
    """VectorStoreをリフレッシュする"""
    global vectorstore
    # 初期化時は最低1つのテキストが必要
    vectorstore = FAISS.from_texts(
        ["初期化用のダミーテキストです。このテキストは検索には使用されません。"],
        embeddings
    )
    if os.path.exists(VECTORSTORE_PATH):
        try:
            shutil.rmtree(VECTORSTORE_PATH)
        except Exception as e:
            print(f"⚠️ VectorStoreの削除中にエラーが発生しました: {e}")
            return
    print("🔄 VectorStoreをリフレッシュしました")

def refresh_all():
    """会話履歴とVectorStore両方をリフレッシュする"""
    refresh_memory()
    refresh_vectorstore()
    print("✨ 全てのデータをリフレッシュしました")

vectorstore = load_vectorstore()


# === 保存指示判定 ===
def is_valid_save_command(user_input):
    prompt = f"""
    以下のユーザー発話は、AIとの議論内容をNotionに保存するように依頼している意図がありますか？
    「はい」または「いいえ」だけで答えてください。

    発話: "{user_input}"
    """
    if not VALID_SAVE_LOCAL:
        decision = llm.invoke(prompt).content
    else:
        decision = local_summarizer.invoke(prompt).content
    #print(f"判断結果: {decision}")
    return "はい" in decision

def is_new_topic(input):
    prompt = f"""
    以下のやり取りの流れは、「異なる新しいトピックの開始」だと思われますか？
    「はい」または「いいえ」だけで答えてください。

    発話: "{input}"
    """
    decision = llm.invoke(prompt).content
    print(f"判断結果: {decision}")
    return "はい" in decision

# === 要約関数 ===
def summarize_memory():
    global summary_memory
    current_history = "\n".join([msg.content for msg in memory.load_memory_variables({})["history"]])
    prompt = f"""
    以下の議論履歴を要約してください。
    特に、質疑応答を重視して、[質問]→[回答]の形式で示すようにしてください。

    {current_history}
    """
    if not SUMMARIZE_LOCAL:
        summary = llm.invoke(prompt).content
    else:
        summary = local_summarizer.invoke(prompt).content
    summary_memory += f"\n{summary}"
    print(f"📝 要約追加: {summary}")
    memory.chat_memory.clear()
    print(memory.load_memory_variables({}))
    return summary

def save_summary():
    print("💾 保存指示が検出されました。指定ページに追記します。")
    # Notion保存
    Notion_func.append_to_page(PAGE_ID, summarize_memory())

def input_flow(user_input):
    global turn_counter
    
    if user_input is None or user_input == "":
        return ""    
    
    if user_input.lower() in ["refresh", "clear"]:
        refresh_all()
        return "refresh"
    elif user_input.lower() == "refresh memory":
        refresh_memory()
        return "refresh memory"
    elif user_input.lower() == "refresh vectorstore":
        refresh_vectorstore()
        return "refresh vectorstore"
    
    if is_valid_save_command(user_input):
        save_summary()
        try:
            save_vectorstore(vectorstore)
        except Exception as e:
            print(f"⚠️ VectorStoreの保存に失敗しました: {e}")

    else:
        # 類似履歴検索
        docs = vectorstore.similarity_search(user_input, k=2)
        retrieved = "\n".join([d.page_content for d in docs])

        # Memory履歴取得
        history = "".join([msg.content for msg in memory.load_memory_variables({})["history"]])

        # LLM応答生成
        prompt = f"過去の議論: {retrieved}\n直近の会話: {history}\n\nユーザー: {user_input}"

        # 新しいトピックの検出
        if is_new_topic(prompt):
            print("🔄 新しいトピックの開始を検出しました。会話履歴をリフレッシュします。")
            refresh_memory()

        result = llm.invoke(prompt).content
        print(result)
        # 通常発話もペアで保存
        pair_text = f"[質問] {user_input}\n[回答] {result}"
        vectorstore.add_texts([pair_text])
        save_vectorstore(vectorstore)

        # Memoryにも追加
        memory.chat_memory.add_user_message(user_input)
        memory.chat_memory.add_ai_message(result)
        turn_counter += 1
    
        # 動的要約
        if turn_counter % SUMMARY_INTERVAL == 0:
            summarize_memory()
            print(f"🔄 動的要約: {summary_memory}")


# === 実行例 ===
if __name__ == "__main__":
    turn_counter = 0
    try:
        while True:
            user_input = input("> ")
            if user_input.lower() in ["exit", "quit"]:
                break
            input_flow(user_input)
            
    finally:
        save_memory(memory)
        print("✅ 会話履歴を保存しました。")
