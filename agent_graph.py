from __future__ import annotations

import re
import time
import ollama
import json
from datetime import date, timedelta
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Literal, Optional

from langgraph.graph import StateGraph, START, END


# ---------- 1) Define the shared State ----------
class AgentState(TypedDict, total=False):
    run_date: str
    profile: Dict[str, Any]
    jobs: List[Dict[str, Any]]          # jobs to evaluate
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

def _safe_json_loads(text: str):
    """
    Try to parse JSON even if the model returns extra text.
    Extract the first {...} block and parse it.
    """
    text = text.strip()

    # Fast path: already clean JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try extracting JSON object from messy output
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return json.loads(m.group(0))


def _estimate_required_years(job_text: str) -> int | None:
    """
    Very simple heuristic: look for patterns like '3+ years', '5 years of experience'.
    We'll use this only as a soft pre-filter.
    """
    patterns = [
        r"(\d+)\s*\+\s*years",
        r"(\d+)\s*years\s+of\s+experience",
        r"minimum\s+(\d+)\s*years"
    ]
    for p in patterns:
        m = re.search(p, job_text.lower())
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None


def llm_match_job_ollama(job: dict, profile: dict, model: str = "llama3.2:1b") -> dict:
    """
    Ask llama (via Ollama) to decide whether this job matches the profile.
    Return strict JSON dict with: match, score, reasons, red_flags.
    """
    jd = job.get("description") or ""
    title = job.get("title") or ""
    company = job.get("company") or ""
    location = job.get("location") or ""
    url = job.get("url") or ""

    system = (
        "You are an AI job-matching assistant. "
        "You must output ONLY valid JSON and nothing else."
    )

    # We keep the output schema very small and stable (easy to parse).
    schema_instructions = """
Return ONLY JSON with exactly these keys:
{
  "match": "yes" or "no",
  "score": integer from 0 to 100,
  "reasons": [string, ...],
  "red_flags": [string, ...]
}
Rules:
- Prefer technical skill match, relevant experience match, and role/title alignment.
- Reject if the role is clearly senior/lead or requires high years of experience for an early-career profile.
- Be concise: 2-5 reasons max, 0-5 red_flags max.
"""

    user = f"""
CANDIDATE PROFILE (JSON):
{json.dumps(profile, ensure_ascii=False)}

JOB:
Title: {title}
Company: {company}
Location: {location}
URL: {url}

JOB DESCRIPTION:
{jd}

{schema_instructions}
""".strip()

    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # If your ollama version supports structured output, you can try:
        # format="json"
    )

    content = resp["message"]["content"]
    return _safe_json_loads(content)

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
    For each job in state['jobs'], call llama (Ollama) and decide match/no-match.
    Adds results into state['matches'] and state['rejected'].
    """
    profile = state.get("profile", {})
    jobs = state.get("jobs", [])

    matches = []
    rejected = []

    # Read the experience threshold from profile rules (default 2 if missing)
    exp_threshold = 2
    try:
        exp_threshold = int(profile["targeting"]["seniority_preferences"]["exclude_if_min_years_experience_greater_than"])
    except Exception:
        exp_threshold = 2

    # Senior keyword filter (fast reject without LLM)
    senior_keywords = ("senior", "lead", "principal", "staff", "head of")

    for idx, job in enumerate(jobs, start=1):
        title = (job.get("title") or "").lower()
        jd = (job.get("description") or "")
        combined_text = f"{job.get('title','')}\n{jd}"

        # 1) quick rule-based skip for obvious senior titles
        if any(k in title for k in senior_keywords):
            rejected.append({
                **job,
                "decision": {"match": "no", "score": 0,
                             "reasons": ["Role appears senior-level based on title."],
                             "red_flags": ["Senior/Lead title"]}
            })
            continue

        # 2) quick heuristic on years of experience
        years = _estimate_required_years(combined_text)
        if years is not None and years > exp_threshold:
            rejected.append({
                **job,
                "decision": {"match": "no", "score": 0,
                             "reasons": [f"Role appears to require {years}+ years of experience (threshold {exp_threshold})."],
                             "red_flags": [f"Experience requirement: {years}+ years"]}
            })
            continue

        # 3) LLM decision
        try:
            decision = llm_match_job_ollama(job, profile, model="llama3.2:1b")
        except Exception as e:
            # If parsing/model fails, reject safely but record error
            decision = {"match": "no", "score": 0, "reasons": ["LLM evaluation failed."], "red_flags": [str(e)]}

        record = {**job, "decision": decision}

        if str(decision.get("match", "")).lower() == "yes":
            matches.append(record)
        else:
            rejected.append(record)

        # small delay so you don't hammer your local model
        time.sleep(0.1)

        # Optional: progress print
        print(f"[match] {idx}/{len(jobs)} -> {decision.get('match')} (score={decision.get('score')})")

    return {
        **state,
        "matches": matches,
        "rejected": rejected,
        "stats": {
            **state.get("stats", {}),
            "matching_ran": True,
            "matches_count": len(matches),
            "rejected_count": len(rejected),
            "exp_threshold": exp_threshold,
        }
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
