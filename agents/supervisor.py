"""
Supervisor Agent – orchestrates NBCU, CBS, and Fox agents using LangChain / LangGraph.

The supervisor delegates to each provider agent, collects results, and returns
a combined summary. It uses a LangGraph StateGraph to model the workflow:

    START → nbcu_agent → cbs_agent → fox_agent → aggregate → END

If LangChain/LangGraph are not installed the supervisor falls back to a
direct-execution mode so the app still works without an LLM key.
"""

from typing import Dict, Any, List, TypedDict
import os

from agents.nbcu_agent import NBCUAgent
from agents.cbs_agent import CBSAgent
from agents.fox_agent import FoxAgent

# ---------------------------------------------------------------------------
# LangGraph integration (gracefully degrades when packages unavailable)
# ---------------------------------------------------------------------------
try:
    from langgraph.graph import StateGraph, END

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


class AgentState(TypedDict):
    source_dir: str
    target_dir: str
    nbcu_result: Dict[str, Any]
    cbs_result: Dict[str, Any]
    fox_result: Dict[str, Any]
    combined: Dict[str, Any]


class SupervisorAgent:
    """Coordinates the three provider agents and merges results."""

    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = source_dir
        self.target_dir = target_dir

    # -- node functions for LangGraph ------------------------------------------

    @staticmethod
    def _run_nbcu(state: AgentState) -> dict:
        agent = NBCUAgent(state["source_dir"], state["target_dir"])
        return {"nbcu_result": agent.process()}

    @staticmethod
    def _run_cbs(state: AgentState) -> dict:
        agent = CBSAgent(state["source_dir"], state["target_dir"])
        return {"cbs_result": agent.process()}

    @staticmethod
    def _run_fox(state: AgentState) -> dict:
        agent = FoxAgent(state["source_dir"], state["target_dir"])
        return {"fox_result": agent.process()}

    @staticmethod
    def _aggregate(state: AgentState) -> dict:
        results = [state["nbcu_result"], state["cbs_result"], state["fox_result"]]
        total_events = sum(r.get("events_count", 0) for r in results)
        total_files = sum(r.get("files_processed", 0) for r in results)
        all_output = []
        all_errors = []
        for r in results:
            all_output.extend(r.get("output_files", []))
            all_errors.extend(r.get("errors", []))

        combined = {
            "total_files_processed": total_files,
            "total_events": total_events,
            "total_output_files": len(all_output),
            "output_files": all_output,
            "all_errors": all_errors,
            "status": "success" if not all_errors else "partial_success",
            "agent_results": results,
        }
        return {"combined": combined}

    # -- public API ------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """Execute the full agent pipeline and return aggregated results."""
        if LANGGRAPH_AVAILABLE:
            return self._run_with_langgraph()
        return self._run_direct()

    def _run_with_langgraph(self) -> Dict[str, Any]:
        graph = StateGraph(AgentState)

        graph.add_node("nbcu_agent", self._run_nbcu)
        graph.add_node("cbs_agent", self._run_cbs)
        graph.add_node("fox_agent", self._run_fox)
        graph.add_node("aggregate", self._aggregate)

        graph.set_entry_point("nbcu_agent")
        graph.add_edge("nbcu_agent", "cbs_agent")
        graph.add_edge("cbs_agent", "fox_agent")
        graph.add_edge("fox_agent", "aggregate")
        graph.add_edge("aggregate", END)

        app = graph.compile()

        initial_state: AgentState = {
            "source_dir": self.source_dir,
            "target_dir": self.target_dir,
            "nbcu_result": {},
            "cbs_result": {},
            "fox_result": {},
            "combined": {},
        }

        final = app.invoke(initial_state)
        return final["combined"]

    def _run_direct(self) -> Dict[str, Any]:
        """Fallback when LangGraph is not available."""
        state: AgentState = {
            "source_dir": self.source_dir,
            "target_dir": self.target_dir,
            "nbcu_result": {},
            "cbs_result": {},
            "fox_result": {},
            "combined": {},
        }
        state.update(self._run_nbcu(state))
        state.update(self._run_cbs(state))
        state.update(self._run_fox(state))
        state.update(self._aggregate(state))
        return state["combined"]
