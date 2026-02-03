import requests
import json
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://jobsearch.api.jobtechdev.se/search"


def fetch_ai_jobs_today():
    params = {
        "q": "AI",
        "limit": 100,
        "offset": 0
    }

    today = datetime.now(timezone.utc).date()
    today_jobs = []

    while True:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        hits = data.get("hits", [])
        if not hits:
            break

        for job in hits:
            pub_date_str = job.get("publication_date")
            if not pub_date_str:
                continue

            pub_date = datetime.fromisoformat(pub_date_str).date()

            if pub_date == today:
                today_jobs.append({
                    "id": job.get("id"),
                    "title": job.get("headline"),
                    "company": job.get("employer", {}).get("name"),
                    "description": job.get("description", {}).get("text"),
                    "location": job.get("workplace_address", {}).get("municipality"),
                    "url": job.get("webpage_url"),
                    "published_at": pub_date_str
                })

        params["offset"] += params["limit"]

    return today_jobs, today


def save_jobs_to_file(jobs, date):
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    file_path = data_dir / f"jobs_{date}.json"


    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

    return file_path


if __name__ == "__main__":
    jobs, today = fetch_ai_jobs_today()

    print(f"\nTotal jobs found today: {len(jobs)}")

    if jobs:
        file_path = save_jobs_to_file(jobs, today)
        print(f"Jobs saved to: {file_path}")
    else:
        print("No AI-related jobs found today.")
