# AI Workflow for Job Search

# Overview

This project is a AI system that helps the candidate find relevant jobs easily.

The system begins by fetching related (AI in my case) job postings, filters out irrelevant roles, evaluates the remaining jobs using a local AI model, and sends the best matches by email.

My goal of working with this project is to:

- learn how AI systems can automate tasks

- practice building AI workflow

- help with my own job search

- build a practical portfolio project

# How the System Works

The system runs once per day (6:30 pm) using windows task scheduler and follows these steps:

1. Fetch jobS related to from the Arbetsförmedlingen (Swedish Employement Service) using API.

2. Save the job data locally.

3. Apply a simple rule-based filter to remove irrelevant roles.

4. Send each remaining job to a local LLM (phi3:mini) for evaluation.

5. Score the job based on relevance to my profile.

6. Send the best job matches by email.

# Architecture

To better understand the working of this project, refer the diagram below:



docs/architecture.png
# Example Email Output

The system sends a daily email with the summary of the analysed jobs and the jobs that are matched to the candidate.



Screenshot:

docs/email_example.png


# Project Structure
JobSearch-Agent
│
├── data/                # stored job data
├── fetch_jobs.py        # fetch jobs from API
├── prefilter.py         # rule-based filtering
├── llm_score.py         # LLM evaluation logic
├── score_today.py       # scoring pipeline
├── send_email.py        # email notification
├── main.py              # run full workflow
├── requirements.txt
└── README.md

# Technologies Used

Python

Ollama

Phi-3 Mini (local LLM)

Gmail SMTP

JobTech API (Arbetsförmedlingen)

# Setup

To Install dependencies:

pip install -r requirements.txt

# Environment Variables

Create a .env file:

GMAIL_SENDER=your_email@gmail.com
GMAIL_RECEIVER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password

# Runnig the System

To Run the full workflow, run the script
- python main.py

This will:

1. fetch jobs

2. filter jobs

3. evaluate jobs using the LLM

4. send email with job matches


# Possible Future Improvements

Some ideas for future versions:

- Convert the workflow into a true AI agent using LangGraph

- Add a web dashboard

- Add job application tracking

- Add support for multiple job sites 

