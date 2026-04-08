from groq import Groq
import json
import re
from dotenv import load_dotenv
import os

load_dotenv() 

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

MODEL_NAME = os.environ.get("MODEL_NAME")


def score_job_with_groq(job):
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

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_completion_tokens=300,
            stream=False  # IMPORTANT: disable streaming
        )



        text = completion.choices[0].message.content.strip()

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

        score = max(0, min(100, score))
        if not reason:
            reason = "No reason given."

        return {"match": match, "score": score, "reason": reason}

    except Exception as e:
        return {"match": False, "score": 0, "reason": f"Groq error: {e}"}