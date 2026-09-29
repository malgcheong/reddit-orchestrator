from langgraph.graph import END, START, StateGraph

from .nodes import (approve_node, collect_node, execute_node, gate_node,
                    judge_node, plan_node, publish_node, title_node)
from .state import OrchestratorState


def _after_collect(state) -> str:
    return "plan" if state.get("posts") else "empty"


def _after_gate(state) -> str:
    # Deterministic gate is the guard: fail closed (reject) before spending the judge.
    return "judge" if state["gate"]["passed"] else "rejected"


def _after_approve(state) -> str:
    return "publish" if state.get("approval", {}).get("approved") else "rejected"


def build_graph(checkpointer=None):
    g = StateGraph(OrchestratorState)
    g.add_node("collect", collect_node)
    g.add_node("plan", plan_node)
    g.add_node("execute", execute_node)
    g.add_node("title", title_node)
    g.add_node("gate", gate_node)
    g.add_node("judge", judge_node)
    g.add_node("approve", approve_node)
    g.add_node("publish", publish_node)

    g.add_edge(START, "collect")
    g.add_conditional_edges("collect", _after_collect, {"plan": "plan", "empty": END})
    g.add_edge("plan", "execute")
    g.add_edge("execute", "title")
    g.add_edge("title", "gate")
    g.add_conditional_edges("gate", _after_gate, {"judge": "judge", "rejected": END})
    g.add_edge("judge", "approve")
    g.add_conditional_edges("approve", _after_approve, {"publish": "publish", "rejected": END})
    g.add_edge("publish", END)

    return g.compile(checkpointer=checkpointer)
