import streamlit as st
import os
from main7 import (
    DATABASE_ID,
    refresh_memory, llm, memory,
    Notion_func,
    summary_memory, SUMMARY_INTERVAL, summarize_memory
)

st.title("📚 AI議事録くん")

pages = dict(Notion_func.get_pages(DATABASE_ID))
pages_name = [name for _, name in pages.items()]
#print(pages_name)
st.session_state.page_name = st.selectbox("保存先ページ", pages_name)
page_id = [k for k, v in pages.items() if v == st.session_state.page_name][0]

if "history" not in st.session_state:
    print("🔄 会話履歴をリフレッシュします")
    st.session_state.history = []
    refresh_memory()

user_input = st.text_input("あなたの質問は？")

col1, col2 = st.columns(2)


if col1.button("送信"):
    # ユーザー入力を記録
    memory.chat_memory.add_user_message(user_input)
    st.session_state.history.append(("user :", user_input))
    if user_input is None or user_input == "":
        pass
    else:
        # 通常の応答生成
        context = summary_memory + "\n".join([msg.content for msg in memory.load_memory_variables({})["history"]])
        reply = llm.invoke(context + f"\nユーザー: {user_input}").content
        st.session_state.history.append(("🤖", reply))
        memory.chat_memory.add_ai_message(reply)

        # 定期的な要約
        if len(st.session_state.history) % SUMMARY_INTERVAL == 0:
            summarize_memory()

if col2.button("保存"):
    summary = llm.invoke(summary_memory + "\n".join([msg.content for msg in memory.load_memory_variables({})["history"]]) + "\n保存要約して").content
    Notion_func.append_to_page(page_id, summary)
    st.session_state.history.append(("📝 要約保存", summary))
    memory.chat_memory.add_ai_message(summary)

# 会話履歴の表示
for role, msg in st.session_state.history:
    st.markdown(f"**{role}**: {msg}")
