# LangGraph グラフ構築・接続スクリプト

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from nodes import (
    state,
    const_state,
    load_memory_node,
    augment_query_node,
    specific_node,
    association_node,
    generate_response_node,
    register_pair_node,
    update_history_node,
    summarize_history_node,
    note_trigger_node,
    note_node,
    save_node
)
load_dotenv()

LG_DEBUG = True  # デバッグモードのフラグ
LG_DEBUG_STREAM = False  # ストリーミングデバッグモードのフラグ




# ---- グラフ初期化 ----
builder = StateGraph(state)

# ---- ノード登録 ----
builder.add_node("load_memory_node", load_memory_node)
builder.add_node("note_trigger_node", note_trigger_node)
builder.add_node("note_node", note_node)
builder.add_node("augment_query_node", augment_query_node)
builder.add_node("specific_node", specific_node)
builder.add_node("association_node", association_node)
builder.add_node("generate_response_node", generate_response_node)
builder.add_node("register_pair_node", register_pair_node)
builder.add_node("update_history_node", update_history_node)
builder.add_node("summarize_history_node", summarize_history_node)
builder.add_node("save_node", save_node)

# ---- フロー構築 ----
builder.set_entry_point("load_memory_node")
builder.add_edge("load_memory_node", "note_trigger_node")
# save_trigger? 条件付き分岐
def should_save(state: state) -> str | None:
    return "note" if state.get("save_flag", False) else "continue"

builder.add_conditional_edges(
    "note_trigger_node",
    path=should_save,
    path_map={
        "note" : "note_node",
        "continue" : "augment_query_node"
    }
)

builder.add_edge("note_node", END)

builder.add_edge("augment_query_node", "specific_node")
builder.add_edge("augment_query_node", "association_node")
builder.add_edge("specific_node", "generate_response_node")
builder.add_edge("association_node", "generate_response_node")
builder.add_edge("generate_response_node", "register_pair_node")
builder.add_edge("register_pair_node", "update_history_node")

# summarize_turn? 条件付き分岐
def should_summarize(state: state) -> str | None:
    print(state["history"])
    if len(state["history"]) > 6:
        return "summarize_history_node"
    else:
        return "save"

builder.add_conditional_edges(
    "update_history_node",
    path=should_summarize,
    path_map={
        "summarize_history_node" : "summarize_history_node",
        "save" : "save_node"
    }
)

builder.add_edge("summarize_history_node", "save_node")
builder.add_edge("save_node", END)


# ---- グラフをコンパイル ----
app = builder.compile()

# ---- テスト実行 ----
if __name__ == "__main__":
    test_input = input("テスト入力を入力してください: ")
    if LG_DEBUG:
        print("LangGraph Debug Mode")
        # ---- グラフ構造を表示 ----
        print("\n=== LangGraph ASCII ===")
        app.get_graph().print_ascii()

    # ---- テスト実行 ----
    test_state = const_state(input = {"role": "user", "content":test_input})
    print(test_state)
    
    if LG_DEBUG_STREAM:
        for event in app.stream(test_state, stream_mode="values"):
            print(event)
    else:
        result = app.invoke(test_state, debug=LG_DEBUG)