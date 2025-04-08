# LangGraph グラフ構築・接続スクリプト
from langgraph.checkpoint.sqlite import SqliteSaver

# チェックポイント保存用のSQLite構成
checkpoint = SqliteSaver.from_path("./checkpoints.db")



from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from nodes import (
    GraphState,
    augment_query_node,
    specific_node,
    association_node,
    generate_response_node,
    register_pair_node,
    update_history_node,
    summarize_history_node,
    save_trigger_node,
    save_node
)

# ---- グラフ初期化 ----
builder = StateGraph(GraphState)

# ---- ノード登録 ----
builder.add_node("augment_query_node", RunnableLambda(augment_query_node))
builder.add_node("specific_node", RunnableLambda(specific_node))
builder.add_node("association_node", RunnableLambda(association_node))
builder.add_node("generate_response_node", RunnableLambda(generate_response_node))
builder.add_node("register_pair_node", RunnableLambda(register_pair_node))
builder.add_node("update_history_node", RunnableLambda(update_history_node))
builder.add_node("summarize_history_node", RunnableLambda(summarize_history_node))
builder.add_node("save_trigger_node", RunnableLambda(save_trigger_node))
builder.add_node("save_node", RunnableLambda(save_node))

# ---- フロー構築 ----
builder.set_entry_point("augment_query_node")
builder.add_edge("augment_query_node", "specific_node")
builder.add_edge("augment_query_node", "association_node")
builder.add_edge("specific_node", "generate_response_node")
builder.add_edge("association_node", "generate_response_node")
builder.add_edge("generate_response_node", "register_pair_node")
builder.add_edge("register_pair_node", "update_history_node")

# summarize_turn? 条件付き分岐
def should_summarize(state: GraphState) -> str | None:
    if len(state["history"]) > 6:
        return "summarize_history_node"
    else:
        return "save_trigger_node"

builder.add_conditional_edges(
    "update_history_node",
    path=should_summarize,
    path_map={
        "履歴が多いので要約" : "summarize_history_node",
        "履歴が短いのでスキップ" : "save_trigger_node"
    }
)

builder.add_edge("summarize_history_node", "save_trigger_node")

# save_trigger? 条件付き分岐
def should_save(state: GraphState) -> str | None:
    return "save_node" if state.get("save_flag", False) else END

builder.add_conditional_edges(
    "save_trigger_node",
    path=should_save,
    path_map={
        "保存する" : "save_node",
        "保存しない" : END
    }
)

builder.add_edge("save_node", END)

# ---- グラフをコンパイル ----
app = builder.compile(memory=checkpoint)

# ---- テスト実行 ----
if __name__ == "__main__":
# ---- グラフ構造を表示 ----
    print("\n=== LangGraph ASCII ===")
    app.get_graph().print_ascii()

    print("\n=== LangGraph Mermaid (for Markdown/Notebook) ===")
    print(app.get_graph().draw_mermaid())