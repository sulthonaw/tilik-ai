"""LangGraph StateGraph assembly and compiled runnable workflow for Tilik AI."""

import logging
from typing import Optional

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    concurrent_fetch_node,
    evaluator_node,
    intent_node,
    ner_slang_node,
    synthesizer_node,
)
from app.models.schemas import VerificationResponse
from app.models.state import AgentState

logger = logging.getLogger("agent_graph")


def build_verification_graph():
    """Builds and compiles the LangGraph StateGraph workflow."""
    workflow = StateGraph(AgentState)

    # Register all nodes
    workflow.add_node("ner_slang", ner_slang_node)
    workflow.add_node("intent", intent_node)
    workflow.add_node("concurrent_fetch", concurrent_fetch_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Define sequential edges
    workflow.add_edge(START, "ner_slang")
    workflow.add_edge("ner_slang", "intent")
    workflow.add_edge("intent", "concurrent_fetch")
    workflow.add_edge("concurrent_fetch", "evaluator")
    workflow.add_edge("evaluator", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()


# Compiled runnable graph singleton
verification_graph = build_verification_graph()


async def run_verification(
    text: str,
    source_platform: Optional[str] = "x",
    user_role: Optional[str] = "PEMULA",
) -> VerificationResponse:
    """Executes the verification graph for input social media text."""
    initial_state: AgentState = {
        "raw_text": text,
        "source_platform": source_platform or "x",
        "user_role": user_role or "PEMULA",
    }
    final_state = await verification_graph.ainvoke(initial_state)
    return final_state["response"]
