import streamlit as st
from main7 import (
    DATABASE_ID,
    Notion_func, input_flow, save_summary
)

st.title("📚 AI議事録くん")

pages = dict(Notion_func.get_pages(DATABASE_ID))
pages_name = [name for _, name in pages.items()]
#print(pages_name)
st.session_state.page_name = st.selectbox("保存先ページ", pages_name)
page_id = [k for k, v in pages.items() if v == st.session_state.page_name][0]

if "history" not in st.session_state:
    st.session_state.history = []

# 会話履歴の表示
with st.container(height=300, border=True):
    st.write("会話履歴:")

    # 会話履歴の表示
    for role, msg in st.session_state.history:
        st.markdown(f"**{role}**: {msg}")


user_input = st.text_input("あなたの質問は？")

col1, col2 = st.columns(2)

with col1:
    if col1.button("送信"):
        # ユーザー入力を記録
        input_flow(user_input)

with col2:
    if col2.button("メモ保存"):
        save_summary()
