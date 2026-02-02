import requests
from datetime import datetime, timezone

def fetch_ai_jobs():
    BASE_URL = "https://jobsearch.api.jobtechdev.se/search"

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
    
    return today_jobs

if __name__ == "__main__":
    jobs = fetch_ai_jobs()
    print(f"Total jobs found today: {len(jobs)}")
    ##Printing Job Details

    
