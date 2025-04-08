from main7 import (
    DATABASE_ID, update_page_id, get_page_id,
    Notion_func, input_flow, save_summary, save_memory, save_vectorstore, load_memory, load_vectorstore
)
import streamlit as st

DEBUG = True

# ==============================

st.title("📚 AI議事録くん")

if "session_updated" not in st.session_state:
    st.session_state.session_updated = False

if "page_name" not in st.session_state:
    st.session_state.page_name = None

pages = dict(Notion_func.get_pages(DATABASE_ID))
pages_name = [name for _, name in pages.items()]
#print(pages_name)

st.session_state.page_name = st.selectbox("保存先ページ", pages_name)
current_PAGE_ID = [k for k, v in pages.items() if v == st.session_state.page_name][0].replace("-", "")

if "page_id" not in st.session_state:
    st.session_state.page_id = get_page_id()

# ページ変更検出とメモリなど保存・読み込み
if st.session_state.page_id != current_PAGE_ID:
    if st.session_state.session_updated:
        save_memory()
        save_vectorstore()
        st.session_state.session_updated = False
    
    print(f"🔄 ページ変更検出: {current_PAGE_ID}")
    st.session_state.page_id = current_PAGE_ID
    update_page_id(current_PAGE_ID)
    load_memory()
    load_vectorstore()

if "history" not in st.session_state:
    st.session_state.history = []

# === 会話履歴表示部 ===
st.write("会話履歴:")
with st.container(height=300, border=True):
    resume = st.empty()
    
# === 質問入力 ===
user_input = st.text_input("あなたの質問は？")

col1, col2 = st.columns(2)

with col1:
    if col1.button("送信"):
        st.session_state.history.append(("user", user_input))
        # ユーザー入力を記録
        response = input_flow(user_input)
        if response is "refresh":
            st.session_state.history.append(("🤖", "会話履歴をリフレッシュしました"))
            st.session_state.history = []

        else:
            st.session_state.history.append(("🤖", response))
            st.session_state.session_updated = True

with col2:
    if col2.button("メモ保存"):
        save_summary()

# 会話履歴の表示
with resume.container():
    for role, msg in st.session_state.history:
        st.markdown(f"**{role}**: {msg}")