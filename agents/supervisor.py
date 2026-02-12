"""
Supervisor Agent – orchestrates NBCU, CBS, and Fox agents using LangGraph
and AWS Bedrock Amazon Nova Pro as the decision-making LLM.

Architecture:
    1. The supervisor uses Nova Pro to analyse incoming source files and
       determine which provider agents to invoke.
    2. Each provider agent runs its parsing/conversion pipeline and uses
       Nova Lite to produce per-provider analysis.
    3. The supervisor collects all results and uses Nova Pro to produce
       a final executive summary across all providers.

    LangGraph flow:
        START → supervisor_plan → nbcu_agent → cbs_agent → fox_agent
              → aggregate → supervisor_summarize → END

When Bedrock credentials are missing, all LLM steps gracefully degrade
to deterministic logic so the app still works without an API key.
"""

import json
import os
from typing import Dict, Any, TypedDict

from agents.nbcu_agent import NBCUAgent
from agents.cbs_agent import CBSAgent
from agents.fox_agent import FoxAgent
from agents.bedrock_llm import get_supervisor_llm

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


PLAN_PROMPT = """You are a supervisor agent managing media schedule conversion for
three networks: NBCU, CBS, and FOX.

The following source files have been detected in the input directory:
{file_list}

For each file determine:
1. Which provider agent should handle it (NBCU for .json, CBS for .csv, FOX for .txt)
2. What kind of data you expect it to contain

Respond with a brief execution plan (3-5 sentences) describing the order
of operations and any observations about the files."""


SUMMARY_PROMPT = """You are a supervisor agent that has just completed a multi-agent
SCTE-224 conversion pipeline. Here are the results from each provider agent:

{agent_summaries}

Provide an executive summary covering:
1. Overall conversion status and total events processed
2. Key highlights or concerns from each provider
3. Blackout/viewing-policy observations across all networks
4. Any recommendations for the operations team

Keep the response concise (5-8 sentences)."""


class AgentState(TypedDict):
    source_dir: str
    target_dir: str
    supervisor_plan: str
    nbcu_result: Dict[str, Any]
    cbs_result: Dict[str, Any]
    fox_result: Dict[str, Any]
    combined: Dict[str, Any]
    supervisor_summary: str


class SupervisorAgent:
    """Coordinates the three provider agents using Nova Pro and LangGraph."""

    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.llm = get_supervisor_llm()

    # -- LLM helpers -----------------------------------------------------------

    def _llm_plan(self, file_list: list) -> str:
        """Use Nova Pro to create an execution plan."""
        if self.llm is None:
            return "Running in deterministic mode (no LLM credentials configured)."
        try:
            prompt = PLAN_PROMPT.format(
                file_list="\n".join(f"  - {f}" for f in file_list)
            )
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"[Supervisor LLM planning unavailable: {e}]"

    def _llm_summarize(self, agent_results: list) -> str:
        """Use Nova Pro to produce a final executive summary."""
        if self.llm is None:
            return ""
        try:
            summaries = []
            for r in agent_results:
                summaries.append(
                    f"**{r.get('agent', 'Unknown')}**: "
                    f"{r.get('events_count', 0)} events, "
                    f"status={r.get('status', 'N/A')}, "
                    f"analysis: {r.get('llm_analysis', 'N/A')}"
                )
            prompt = SUMMARY_PROMPT.format(
                agent_summaries="\n\n".join(summaries)
            )
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"[Supervisor LLM summary unavailable: {e}]"

    # -- node functions for LangGraph ------------------------------------------

    def _node_plan(self, state: AgentState) -> dict:
        files = []
        if os.path.isdir(state["source_dir"]):
            files = sorted(os.listdir(state["source_dir"]))
        plan = self._llm_plan(files)
        return {"supervisor_plan": plan}

    @staticmethod
    def _node_nbcu(state: AgentState) -> dict:
        agent = NBCUAgent(state["source_dir"], state["target_dir"])
        return {"nbcu_result": agent.process()}

    @staticmethod
    def _node_cbs(state: AgentState) -> dict:
        agent = CBSAgent(state["source_dir"], state["target_dir"])
        return {"cbs_result": agent.process()}

    @staticmethod
    def _node_fox(state: AgentState) -> dict:
        agent = FoxAgent(state["source_dir"], state["target_dir"])
        return {"fox_result": agent.process()}

    @staticmethod
    def _node_aggregate(state: AgentState) -> dict:
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

    def _node_summarize(self, state: AgentState) -> dict:
        agent_results = state["combined"].get("agent_results", [])
        summary = self._llm_summarize(agent_results)
        updated = dict(state["combined"])
        updated["supervisor_summary"] = summary
        updated["supervisor_plan"] = state.get("supervisor_plan", "")
        return {"combined": updated, "supervisor_summary": summary}

    # -- public API ------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """Execute the full agent pipeline and return aggregated results."""
        if LANGGRAPH_AVAILABLE:
            return self._run_with_langgraph()
        return self._run_direct()

    def _run_with_langgraph(self) -> Dict[str, Any]:
        graph = StateGraph(AgentState)

        graph.add_node("supervisor_plan", self._node_plan)
        graph.add_node("nbcu_agent", self._node_nbcu)
        graph.add_node("cbs_agent", self._node_cbs)
        graph.add_node("fox_agent", self._node_fox)
        graph.add_node("aggregate", self._node_aggregate)
        graph.add_node("supervisor_summarize", self._node_summarize)

        graph.set_entry_point("supervisor_plan")
        graph.add_edge("supervisor_plan", "nbcu_agent")
        graph.add_edge("nbcu_agent", "cbs_agent")
        graph.add_edge("cbs_agent", "fox_agent")
        graph.add_edge("fox_agent", "aggregate")
        graph.add_edge("aggregate", "supervisor_summarize")
        graph.add_edge("supervisor_summarize", END)

        app = graph.compile()

        initial_state: AgentState = {
            "source_dir": self.source_dir,
            "target_dir": self.target_dir,
            "supervisor_plan": "",
            "nbcu_result": {},
            "cbs_result": {},
            "fox_result": {},
            "combined": {},
            "supervisor_summary": "",
        }

        final = app.invoke(initial_state)
        return final["combined"]

    def _run_direct(self) -> Dict[str, Any]:
        """Fallback when LangGraph is not available."""
        state: AgentState = {
            "source_dir": self.source_dir,
            "target_dir": self.target_dir,
            "supervisor_plan": "",
            "nbcu_result": {},
            "cbs_result": {},
            "fox_result": {},
            "combined": {},
            "supervisor_summary": "",
        }
        state.update(self._node_plan(state))
        state.update(self._node_nbcu(state))
        state.update(self._node_cbs(state))
        state.update(self._node_fox(state))
        state.update(self._node_aggregate(state))
        state.update(self._node_summarize(state))
        return state["combined"]
