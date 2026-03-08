import json
import smtplib
import os
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def latest_scored_file():
    data_dir = Path("data")
    files = sorted(data_dir.glob("scored_*.json"))
    if not files:
        raise FileNotFoundError("No scored_YYYY-MM-DD.json found in data/")
    return files[-1]


def build_email_body(scored, matches, date_str):
    total_jobs = len(scored)

    prefilter_rejected = sum(
        1 for j in scored if str(j.get("reason", "")).startswith("Prefilter removed")
    )

    sent_to_llm = total_jobs - prefilter_rejected
    final_matches = len(matches)

    lines = []
    lines.append(f"AI Job Matches for {date_str}")
    lines.append("")

    lines.append("Summary")
    lines.append(f"- Total jobs fetched: {total_jobs}")
    lines.append(f"- Rejected by prefilter: {prefilter_rejected}")
    lines.append(f"- Sent to LLM: {sent_to_llm}")
    lines.append(f"- Final matches: {final_matches}")
    lines.append("")

    if not matches:
        lines.append("No matching jobs found today.")
        return "\n".join(lines)

    for i, job in enumerate(matches, start=1):
        lines.append(f"{i}. {job.get('title')} — {job.get('company')}")
        lines.append(f"   Score: {job.get('score')}")
        lines.append(f"   Reason: {job.get('reason')}")
        lines.append(f"   Link: {job.get('url')}")
        lines.append("")

    return "\n".join(lines)


def send_email_gmail(subject, body, sender_email, receiver_email, app_password):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())


def main():
    sender_email = os.getenv("GMAIL_SENDER")
    receiver_email = os.getenv("GMAIL_RECEIVER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not receiver_email or not app_password:
        print("Missing env vars. Set: GMAIL_SENDER, GMAIL_RECEIVER, GMAIL_APP_PASSWORD")
        return

    path = latest_scored_file()
    date_str = path.stem.replace("scored_", "")

    with open(path, "r", encoding="utf-8") as f:
        scored = json.load(f)

    matches = [j for j in scored if j.get("match") is True]

    matches.sort(key=lambda x: x.get("score", 0), reverse=True)
    matches = matches[:10]

    subject = f"AI Job Matches — {date_str}"
    body = build_email_body(scored, matches, date_str)

    send_email_gmail(subject, body, sender_email, receiver_email, app_password)

    print("Email sent.")


if __name__ == "__main__":
    main()