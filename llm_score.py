import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "phi3:mini"


def score_job_with_ollama(job):
    title = job.get("title", "")
    company = job.get("company", "")
    description = job.get("description", "") or ""

    description = description[:1200]

    prompt = f"""
You are filtering job ads for a junior AI/ML candidate.

Candidate profile:
- MSc AI Engineering
- Python, SQL, ML/DL, RAG, LLM projects
- Looking for junior AI/ML/NLP/Data Science roles and internships

Hard reject rules:
1) If the job requires more than 2 years of AI/ML experience -> match=false
2) If Swedish fluency is required -> match=false
3) If the job requires a work permit -> match=false

Important:
- The title may not say "junior"
- Infer seniority from requirements
- If years are not clearly stated, do not reject for experience
- Focus on whether the role is mainly AI/ML

Return only one JSON object:
{{"match": true/false, "score": 0-100, "reason": "short reason"}}

Job title: {title}
Company: {company}
Job description: {description}
""".strip()

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=780)
        r.raise_for_status()

        data = r.json()
        text = (data.get("response") or "").strip()

        match_json = re.search(r"\{.*?\}", text, re.DOTALL)

        if not match_json:
            return {"match": False, "score": 0, "reason": "LLM returned no JSON."}

        json_text = match_json.group()

        try:
            result = json.loads(json_text)
        except Exception:
            return {"match": False, "score": 0, "reason": "Invalid JSON from LLM."}

        match = bool(result.get("match", False))
        score = int(result.get("score", 0))
        reason = str(result.get("reason", "")).strip()

        if score < 0:
            score = 0
        if score > 100:
            score = 100
        if not reason:
            reason = "No reason given."

        return {"match": match, "score": score, "reason": reason}

    except Exception as e:
        return {"match": False, "score": 0, "reason": f"Ollama error: {e}"}