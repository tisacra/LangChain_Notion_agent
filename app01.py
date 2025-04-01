import streamlit as st
import os
from main7 import refresh_memory, llm, append_to_page, memory

st.title("📚 AI議事録くん")

if "history" not in st.session_state:
    print("🔄 会話履歴をリフレッシュします")
    st.session_state.history = []
    refresh_memory()

user_input = st.text_input("あなたの質問は？")

if st.button("送信"):
    memory.chat_memory.add_user_message(user_input)
    st.session_state.history.append(("user :", user_input))
    if None:
        pass
    else:
        reply = llm.invoke("".join([msg.content for msg in memory.load_memory_variables({})["history"]]) + f"\nユーザー: {user_input}").content
        st.session_state.history.append(("🤖", reply))
        memory.chat_memory.add_ai_message(reply)

if st.button("保存"):
    summary = llm.invoke("".join([msg.content for msg in memory.load_memory_variables({})["history"]]) + "\n保存要約して").content
    append_to_page(os.getenv("PAGE_ID"), summary)
    st.session_state.history.append(("📝 要約保存", summary))
    memory.chat_memory.add_ai_message(summary)

for role, msg in st.session_state.history:
    st.markdown(f"**{role}**: {msg}")