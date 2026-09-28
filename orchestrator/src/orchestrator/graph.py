from langgraph.graph import END, START, StateGraph

from .nodes import collect_node, execute_node, gate_node, judge_node, plan_node
from .state import OrchestratorState


def _after_collect(state) -> str:
    return "plan" if state.get("posts") else "empty"


def _after_gate(state) -> str:
    # Deterministic gate is the guard: fail closed (reject) before spending the judge.
    return "judge" if state["gate"]["passed"] else "rejected"


def build_graph(checkpointer=None):
    g = StateGraph(OrchestratorState)
    g.add_node("collect", collect_node)
    g.add_node("plan", plan_node)
    g.add_node("execute", execute_node)
    g.add_node("gate", gate_node)
    g.add_node("judge", judge_node)

    g.add_edge(START, "collect")
    g.add_conditional_edges("collect", _after_collect, {"plan": "plan", "empty": END})
    g.add_edge("plan", "execute")
    g.add_edge("execute", "gate")
    g.add_conditional_edges("gate", _after_gate, {"judge": "judge", "rejected": END})
    g.add_edge("judge", END)

    return g.compile(checkpointer=checkpointer)
