import json
from datetime import datetime, timedelta
from pathlib import Path


def load_jobs(file_path):
    """Load jobs from JSON file. Return empty list if file does not exist."""
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jobs(file_path, jobs):
    """Save jobs to a JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


def deduplicate_jobs():
    data_dir = Path("data")
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    today_file = data_dir / f"jobs_{today}.json"
    yesterday_file = data_dir / f"jobs_{yesterday}.json"
    new_jobs_file = data_dir / f"new_jobs_{today}.json"

    # Load jobs
    today_jobs = load_jobs(today_file)
    yesterday_jobs = load_jobs(yesterday_file)

    # Create set of yesterday job IDs
    yesterday_ids = {job.get("id") for job in yesterday_jobs if job.get("id")}

    # Filter new jobs
    new_jobs = [
        job for job in today_jobs
        if job.get("id") not in yesterday_ids
    ]

    # Save new jobs
    save_jobs(new_jobs_file, new_jobs)

    # Print summary
    print(f"Total jobs today       : {len(today_jobs)}")
    print(f"New jobs               : {len(new_jobs)}")
    print(f"Duplicates skipped     : {len(today_jobs) - len(new_jobs)}")
    print(f"New jobs saved to      : {new_jobs_file}")


if __name__ == "__main__":
    deduplicate_jobs()
