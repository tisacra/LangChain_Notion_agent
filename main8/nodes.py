# LangGraph ノード実装：新しいフローチャート構成に対応

from langchain.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from typing import TypedDict, List
import os

from urllib3 import response



DEBUG = True
if DEBUG:
    print("Debug mode is enabled.")

CHAT_LOCAL = False
ABSTRACTION_LOCAL = False
SUMMARIZE_LOCAL = False
VALID_SAVE_LOCAL = False

USE_LOCAL_LLM = CHAT_LOCAL or ABSTRACTION_LOCAL or SUMMARIZE_LOCAL or VALID_SAVE_LOCAL
if USE_LOCAL_LLM:
    print("Local LLM is enabled.")
    # === 動的要約設定 ===
    from langchain_ollama import ChatOllama

    # 要約専用パイプライン
    local_summarizer = ChatOllama(model="gemma3:4b", verbose=True)

# === 環境変数読み込み ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION_ID = os.getenv("OPENAI_ORGANIZATION_ID")
DATABASE_ID = os.getenv("DATABASE_ID")
PAGE_ID = os.getenv("PAGE_ID")
VECTORSTORE_PATH = "vectorstore/"

# === LLMの初期化 ===
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORGANIZATION_ID,
    model_name="gpt-4o-mini"
)


SUMMARY_INTERVAL = 3  # 3ターンごとに要約

# ---- State 型定義 ----

class GraphState(TypedDict):
    history: List[dict]  # raw履歴
    augmented_query: str
    specific_docs: List[Document]
    association_docs: List[Document]
    response: str
    summary: str
    page_id: str
    save_flag: bool
    
# === 動的要約設定 ===
embeddings = OpenAIEmbeddings()

# ---- 初期化 ----
def load_vectorstore():
    """VectorStoreをロード、なければ新規作成"""
    if os.path.exists(VECTORSTORE_PATH + PAGE_ID):
        if DEBUG:
            print(f"💾 VectorStoreをロードしました : {PAGE_ID}")
        return FAISS.load_local(VECTORSTORE_PATH + PAGE_ID, embeddings, allow_dangerous_deserialization=True)
    
    # 初期化時は最低1つのテキストが必要
    vectorstore = FAISS.from_texts(
        ["初期化用のダミーテキストです。このテキストは検索には使用されません。"],
        embeddings
    )
    vectorstore.save_local(VECTORSTORE_PATH + PAGE_ID)
    if DEBUG:
        print(f"💾 VectorStoreを初期化しました : {PAGE_ID}")
    return vectorstore

vectorstore = load_vectorstore()

# ---- ノード実装 ----

def augment_query_node(state: GraphState) -> GraphState:
    user_input = state["history"][-1]["content"]
    context = " ".join([h["content"] for h in state["history"][-3:-1]])
    state["augmented_query"] = f"{context} {user_input}"
    return state


def specific_node(state: GraphState) -> GraphState:
    results = vectorstore.similarity_search(state["augmented_query"], k=3, filter={"type": "specific"})
    state["specific_docs"] = results
    return state


def association_node(state: GraphState) -> GraphState:
    # 入力テキストの抽象化
    prompt = f"以下のやり取りを抽象化してください：\n{state['augmented_query']}"

    if ABSTRACTION_LOCAL:
        response = local_summarizer.invoke(prompt).content
    else:
        response = llm.invoke(prompt).content
    
    abstract_query = f"[ABSTRACT] {response}"
    results = vectorstore.similarity_search(abstract_query, k=3, filter={"type": "abstract"})
    state["association_docs"] = results
    return state


def generate_response_node(state: GraphState) -> GraphState:
    specific = [doc.page_content for doc in state["specific_docs"]]
    association = [doc.page_content for doc in state["association_docs"]]
    context = "\n".join(["具体的文脈 : " + specific, "抽象的文脈" + association])
    user_input = state["history"][-1]["content"]
    response = ""
    if CHAT_LOCAL:
        response = local_summarizer.invoke(f"{user_input}\n参考: {context}").content
    else:
        response = llm.invoke(f"{user_input}\n参考: {context}").content
    state["response"] = f"{response}"
    return state


def register_pair_node(state: GraphState) -> GraphState:
    pair = f"Q: {state['history'][-1]['content']}\nA: {state['response']}"
    vectorstore.add_documents([
        Document(page_content=f"[ABSTRACT] {pair}", metadata={"type": "abstract"})
    ])
    return state


def update_history_node(state: GraphState) -> GraphState:
    state["history"].append({"role": "assistant", "content": state["response"]})
    return state


def summarize_history_node(state: GraphState) -> GraphState:
    if len(state["history"]) <= 1:
        state["summary"] = "[SUMMARY]（履歴が短いため要約なし）"
    else:
        full_text = "\n".join([f"{h['role']}: {h['content']}" for h in state["history"]])
        state["summary"] = f"[SUMMARY] {full_text[:1000]}..."
    return state


def save_trigger_node(state: GraphState) -> GraphState:
    # 条件分岐のみ行うプレースホルダ、実処理なし
    if state["history"][-1]["content"] == "save":
        state["save_flug"] = True
    else:
        state["save_flug"] = False
    return state


def save_node(state: GraphState) -> GraphState:
    # Notion保存処理（省略）
    summary_doc = Document(
        page_content=state["summary"],
        metadata={"type": "summary", "page_id": state.get("page_id", "unknown")}
    )
    vectorstore.add_documents([summary_doc])
    state["history"] = []  # 履歴リセット
    return state
