import json
from pathlib import Path

from prefilter import prefilter_jobs
from llm_score import score_job_with_groq


def latest_jobs_file():
    data_dir = Path("data")
    files = sorted(data_dir.glob("jobs_*.json"))
    if not files:
        raise FileNotFoundError("No jobs_YYYY-MM-DD.json found in data/")
    return files[-1]


def save_scored_jobs(scored_jobs, jobs_filename):
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    date_part = jobs_filename.replace("jobs_", "").replace(".json", "")
    out_path = data_dir / f"scored_{date_part}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scored_jobs, f, indent=2, ensure_ascii=False)

    return out_path


def main():
    path = latest_jobs_file()

    with open(path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    kept, rejected = prefilter_jobs(jobs)

    print("Total jobs:", len(jobs))
    print("Rejected (prefilter):", len(rejected))
    print("Sending to LLM:", len(kept))
    print()

    scored = []

    for job in rejected:
        scored.append({
            **job,
            "match": False,
            "score": 0,
            "reason": f"Prefilter removed ({job.get('reject_reason')})"
        })

    for i, job in enumerate(kept, start=1):
        result = score_job_with_groq(job)
        scored.append({**job, **result})

        print(
            f"[{i}/{len(kept)}] score={result['score']} "
            f"match={result['match']} | {job.get('title')} | {result['reason']}"
        )

    scored.sort(key=lambda x: x.get("score", 0), reverse=True)

    out_path = save_scored_jobs(scored, path.name)
    print("\nSaved scored jobs to:", out_path)


if __name__ == "__main__":
    main()