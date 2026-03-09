import os

print("\n--- Fetching jobs ---")
os.system("python fetch_jobs.py")

print("\n--- Scoring jobs ---")
os.system("python score_today.py")

print("\n--- Sending email ---")
os.system("python send_email.py")

print("\nDONE.")