from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Literal, Optional

from langgraph.graph import StateGraph, START, END


# ---------- 1) Define the shared State ----------
class AgentState(TypedDict, total=False):
    run_date: str
    profile: Dict[str, Any]
    jobs: List[Dict[str, Any]]          # jobs to evaluate (usually new_jobs)
    matches: List[Dict[str, Any]]       # filled later by LLM
    rejected: List[Dict[str, Any]]      # filled later by LLM
    stats: Dict[str, Any]


# ---------- 2) Helper functions ----------
def _today_str() -> str:
    return date.today().isoformat()


def _yesterday_str() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------- 3) Nodes ----------
def load_profile_node(state: AgentState) -> AgentState:
    profile_path = Path("profiles") / "me.json"
    profile = _read_json(profile_path)

    return {
        **state,
        "run_date": state.get("run_date") or _today_str(),
        "profile": profile,
        "stats": {**state.get("stats", {}), "profile_loaded": True},
    }


def load_jobs_node(state: AgentState) -> AgentState:
    run_date = state.get("run_date") or _today_str()
    data_dir = Path("data")

    # Prefer new_jobs; fallback to jobs
    new_jobs_path = data_dir / f"new_jobs_{run_date}.json"
    jobs_path = data_dir / f"jobs_{run_date}.json"

    if new_jobs_path.exists():
        jobs = _read_json(new_jobs_path)
        source = str(new_jobs_path)
    elif jobs_path.exists():
        jobs = _read_json(jobs_path)
        source = str(jobs_path)
    else:
        jobs = []
        source = "NONE"

    return {
        **state,
        "jobs": jobs,
        "matches": state.get("matches", []),
        "rejected": state.get("rejected", []),
        "stats": {
            **state.get("stats", {}),
            "jobs_source": source,
            "jobs_loaded": len(jobs),
        },
    }


def route_if_no_jobs(state: AgentState) -> Literal["match_jobs_node", "save_results_node"]:
    # Conditional routing: if nothing to evaluate, skip matching
    jobs = state.get("jobs", [])
    return "save_results_node" if len(jobs) == 0 else "match_jobs_node"


def match_jobs_node(state: AgentState) -> AgentState:
    """
    Placeholder for tomorrow's LLM matching.
    For now, just pass through and record that matching was skipped/placeholder.
    """
    return {
        **state,
        "stats": {**state.get("stats", {}), "matching_ran": False, "note": "LLM matching not implemented yet"},
    }


def save_results_node(state: AgentState) -> AgentState:
    run_date = state.get("run_date") or _today_str()
    out_path = Path("data") / f"matches_{run_date}.json"

    payload = {
        "run_date": run_date,
        "stats": state.get("stats", {}),
        "matches": state.get("matches", []),
        "rejected": state.get("rejected", []),
    }

    _write_json(out_path, payload)

    print("\n[LangGraph Agent] Run complete")
    print(f"  Date: {run_date}")
    print(f"  Jobs loaded: {state.get('stats', {}).get('jobs_loaded', 0)}")
    print(f"  Output: {out_path}")

    return state


# ---------- 4) Build the graph ----------
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("load_profile_node", load_profile_node)
    graph.add_node("load_jobs_node", load_jobs_node)
    graph.add_node("match_jobs_node", match_jobs_node)
    graph.add_node("save_results_node", save_results_node)

    graph.add_edge(START, "load_profile_node")
    graph.add_edge("load_profile_node", "load_jobs_node")

    # Conditional edge: after loading jobs, decide next step
    graph.add_conditional_edges(
        "load_jobs_node",
        route_if_no_jobs,
        {
            "match_jobs_node": "match_jobs_node",
            "save_results_node": "save_results_node",
        },
    )

    graph.add_edge("match_jobs_node", "save_results_node")
    graph.add_edge("save_results_node", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    app.invoke({"run_date": _today_str()})
