# LangGraph ノード実装：新しいフローチャート構成に対応
from langchain.memory import ConversationBufferMemory
import os
import pickle

from langchain.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.documents import Document
from langgraph.types import Command
from typing import TypedDict, List, Annotated
import getpass
import os
from dotenv import load_dotenv
import sys




def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")


# サブシステムのインポート - 絶対パスを追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from subsystem import Notion_func


DEBUG = True
if DEBUG:
    print("Debug mode is enabled.")

SUMMARIZE_LENGTH = 6  # 要約の閾値

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

_set_env("OPENAI_API_KEY")
_set_env("OPENAI_ORGANIZATION_ID")

# === LLMの初期化 ===
llm = ChatOpenAI(
    model_name="gpt-4o-mini"
)


SUMMARY_INTERVAL = 3  # 3ターンごとに要約

MEMORY_PATH = "./memory/"
VECTORSTORE_PATH = "./vectorstore/"

# ---- State 型定義 ----

from typing_extensions import Annotated
import operator


class message(TypedDict):
    role: str  # "user" or "assistant"
    content: str

class state(TypedDict):
    history: List[message]
    augmented_query: str = ""
    specific_docs: Annotated[List[Document], operator.add]  # 複数のノードからの更新を許可
    association_docs: Annotated[List[Document], operator.add]  # 複数のノードからの更新を許可
    input: dict = {}
    response: str = ""
    summary: str = ""
    user_id: str = ""
    page_id: str = ""
    save_flag: bool = False
    vectorstore: FAISS = None

def const_state(history : List[message] = [], 
                augmented_query: str = "", 
                specific_docs: List[Document] = [], 
                association_docs: List[Document] = [], 
                input: dict = {},
                response: str = "", 
                summary: str = "", 
                user_id: str = "", 
                page_id: str = "", 
                save_flag: bool = False,
                vectorstore: FAISS = None) -> state:
    return {
        "history": history,
        "augmented_query": augmented_query,
        "specific_docs": specific_docs,
        "association_docs": association_docs,
        "input": input,
        "response": response,
        "summary": summary,
        "user_id": user_id,
        "page_id": page_id,
        "save_flag": save_flag,
        "vectorstore": vectorstore
    }

class InitiateOutput(TypedDict):
    user_id: str
    history: List[message]
    vectorstore: FAISS

embeddings = OpenAIEmbeddings()

# ---- ノード実装 ----

def load_memory_node(state: state) -> Annotated[InitiateOutput, ("user_id", "history", "vectorstore")]:
    # ユーザーIDを取得
    user_id = input("ユーザーIDを入力してください(デフォルト=default) : ")
    if not user_id:
        user_id = "default"
    
    # memory
    m_path = MEMORY_PATH + user_id + ".pkl"
    if os.path.exists(m_path):
        with open(m_path, "rb") as f:
            if DEBUG:
                print(f"💾 会話履歴をロードしました : {user_id}")
            memory = pickle.load(f)
    else:
        print(f"はじめまして {user_id}さん！")
        memory = ConversationBufferMemory(return_messages=True)
    context = memory.load_memory_variables({})["history"]
    if DEBUG:
        print("💬 会話履歴をロードしました : ", context)
    
    # vectorstore
    vs_path = VECTORSTORE_PATH + "/" + user_id
    """VectorStoreをロード、なければ新規作成"""
    if os.path.exists(vs_path):
        if DEBUG:
            print(f"💾 VectorStoreをロードしました : {vs_path}")
        vectorstore = FAISS.load_local(vs_path, embeddings, allow_dangerous_deserialization=True)
    else:
        # 初期化時は最低1つのテキストが必要
        vectorstore = FAISS.from_texts(
            ["初期化用のダミーテキストです。このテキストは検索には使用されません。"],
            embeddings
        )
        vectorstore.save_local(vs_path)
        if DEBUG:
            print(f"💾 VectorStoreを初期化しました : {vs_path}")
    context.append(state["input"])
    return {
        "user_id" : user_id, "history" : context, "vectorstore" : vectorstore}


def augment_query_node(state: state) -> Annotated[str, "augmented_query"]:
    print("💬 ユーザークエリ : ", state["history"])
    if len(state["history"]) == 1:
        context =  state["history"][0]["role"] + ": " + state["history"][0]["content"]
        print("test1")
    elif len(state["history"]) <= SUMMARIZE_LENGTH:
        context = "\n".join([h["role"] + ": " + h["content"] for h in state["history"][-(len(state)-1):-1]])
        print("test2")
    else:
        context = "\n".join([h["role"] + ": " + h["content"] for h in state["history"][-(SUMMARIZE_LENGTH+1):-1]])
        print("test3")
    print("💬 コンテキスト : ", context)
    return {"augmented_query" : context}


def specific_node(state: state) -> Annotated[List[Document], "specific_docs"]:
    print("💬 具体的文脈 : ", state["augmented_query"])
    return {"specific_docs" : state["vectorstore"].similarity_search(state["augmented_query"], k=3, filter={"type": "specific"})}


def association_node(state: state) -> Annotated[List[Document], "association_docs"]:
    prompt = f"以下のやり取りを抽象化してください：{state['augmented_query']}"

    if ABSTRACTION_LOCAL:
        response = local_summarizer.invoke(prompt).content
    else:
        response = llm.invoke(prompt).content
    print("💬 抽象化 : ", response)
    abstract_query = f"[ABSTRACT] {response}"
    return {"association_docs" : state["vectorstore"].similarity_search(abstract_query, k=3, filter={"type": "abstract"})}


def generate_response_node(state: state) -> Annotated[str, "response"]:
    history = "\n".join([f"{h['role']}: {h['content']}" for h in state["history"]])
    specific = "\n".join([doc.page_content for doc in state["specific_docs"]])
    association = "\n".join([doc.page_content for doc in state["association_docs"]])
    if DEBUG:
        print("💬 履歴 : ", history)
        print("💬 関連する具体的文脈 : ", specific)
        print("💬 関連する抽象的文脈 : ", association)
    context = "履歴 : " + history + "\n"+ "関連する具体的文脈 : " + specific + "\n" + "類似する抽象的文脈" + association
    user_input = state["input"]["content"]
    if CHAT_LOCAL:
        return local_summarizer.invoke(f"{user_input}\n参考: {context}").content
    else:
        return {"response" : llm.invoke(f"{user_input}\n参考: {context}").content}


def register_pair_node(state: state) -> None:
    pair = f"Q: {state['history'][-1]['content']}\nA: {state['response']}"
    state["vectorstore"].add_documents([
        Document(page_content=f"[ABSTRACT] {pair}", metadata={"type": "abstract"})
    ])
    state["vectorstore"].add_documents([
        Document(page_content=f"[SPECIFIC] {pair}", metadata={"type": "specific"})
    ])


def update_history_node(state: state) -> Annotated[List[dict], "history"]:
    history_old = state["history"].copy()
    print("💬 履歴 : ", history_old)
    update = [{"role": "assistant", "content": state["response"]}]
    updated = history_old + update
    if DEBUG:
        print("💬 履歴更新 : ", updated)
    return {"history" : updated}


def summarize_history_node(state: state) -> dict:
    if len(state["history"]) <= SUMMARIZE_LENGTH:
        summary =  ""
    else:
        full_text = "\n".join([f"{h['role']}: {h['content']}" for h in state["history"]])
        prompt = f"以下の議論履歴を要約してください。\n{full_text}"
        if SUMMARIZE_LOCAL:
            summary = local_summarizer.invoke(prompt).content
        else:
            summary = llm.invoke(prompt).content
        return {"history" : [{"role" : "summary", "content" : summary}],"summary" : summary}


def note_trigger_node(state: state) -> Annotated[bool, "save_flag"]:
    print(state)
    return {"save_flag" : state["input"]["content"] == "save"}


def note_node(state: state) -> None:
    summary_doc = Document(
        page_content=state["summary"],
        metadata={"type": "summary", "page_id": state["page_id"]}
    )
    state["vectorstore"].add_documents([summary_doc])
    print("💾 保存指示が検出されました。指定ページに追記します。")
    pages = Notion_func.get_pages()
    print("💾 保存先ページ候補一覧\n")
    for page_id, page_name in pages:
        print(f"No.{pages.index((page_id, page_name)) + 1} ページ名: {page_name}, ID: {page_id}")
    print("\n💾 保存先ページを選択してください。-> ")
    while True:
        try:
            page_number = int(input())
            if 1 <= page_number <= len(pages):
                break
            else:
                print("💾 無効な番号です。再度入力してください。")
        except ValueError:
            print("💾 数字を入力してください。")
    page_id = pages[page_number - 1][0]
    prompt = f"""
以下の議論履歴を要約してください。
特に、質疑応答を重視して、[文脈]、[質問]→[回答]の形式で示すようにしてください。

{"\n".join([f"{h['role']}: {h['content']}\n" for h in state["history"]])}
"""
    summary = (
        local_summarizer.invoke(prompt).content
        if SUMMARIZE_LOCAL else llm.invoke(prompt).content
    )
    Notion_func.append_to_page(page_id, summary)

def save_node(state: state) -> None:
    print("💾 議論履歴を保存します。")
    memory = ConversationBufferMemory(return_messages=True)
    for msg in state["history"]:
        memory.chat_memory.add_message(msg)
    m_path = MEMORY_PATH + state["user_id"] + ".pkl"
    with open(m_path, "wb") as f:
        if DEBUG:
            print(f"💾 会話履歴を保存しました : {state["user_id"]}")
        pickle.dump(memory, f)