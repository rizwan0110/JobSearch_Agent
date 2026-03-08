# title-based prefilter
# filters senior roles and non-AI roles

SENIOR_WORDS = [
    "senior", "lead", "principal", "staff", "head",
    "director", "manager", "architect",
    "ledande", "chef", "ansvarig", "arkitekt"
]

NON_TARGET_WORDS = [
    "customer support", "support", "customer service",
    "sales", "sälj", "försälj",
    "recruiter", "rekryter",
    "kundtjänst", "kundservice",
    "account manager", "business development"
]


def has_keyword(title, words):
    title = title.lower()
    for w in words:
        if w in title:
            return True
    return False


def prefilter_jobs(jobs):
    kept = []
    rejected = []

    for job in jobs:
        title = job.get("title", "")

        if has_keyword(title, SENIOR_WORDS):
            job["reject_reason"] = "senior_role"
            rejected.append(job)
            continue

        if has_keyword(title, NON_TARGET_WORDS):
            job["reject_reason"] = "non_target_role"
            rejected.append(job)
            continue

        # all remaining job titles go to LLM for analysis
        kept.append(job)

    return kept, rejected