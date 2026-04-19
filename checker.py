"""
Red Hat Job Alert - Checks for new job postings matching keywords
and sends email notifications.
"""

import json
import os
import hashlib
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
TENANT    = os.getenv("WD_TENANT", "redhat")
WD_SERVER = os.getenv("WD_SERVER", "wd5")
SITE      = os.getenv("WD_SITE",   "jobs")
KEYWORDS  = [k.strip().lower() for k in os.getenv("KEYWORDS", "devops").split(",")]
DATA_FILE = Path(os.getenv("DATA_FILE", "data/seen_jobs.json"))
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "50"))

EMAIL_FROM   = os.getenv("EMAIL_FROM")
EMAIL_TO     = os.getenv("EMAIL_TO")
SMTP_HOST    = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT    = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER    = os.getenv("SMTP_USER")
SMTP_PASS    = os.getenv("SMTP_PASS")

BASE_URL  = f"https://{TENANT}.{WD_SERVER}.myworkdayjobs.com"
API_URL   = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}/jobs"
HEADERS   = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Accept-Language": "en-US",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120",
    "Referer": f"{BASE_URL}/en-US/{SITE}",
}

# ── Workday API ──────────────────────────────────────────────────────────────
def fetch_all_jobs() -> list[dict]:
    """Paginate through the Workday CXS API and return all job postings."""
    jobs, offset = [], 0
    while True:
        payload = {
            "appliedFacets": {},
            "limit": PAGE_SIZE,
            "offset": offset,
            "searchText": "",
        }
        resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("jobPostings", [])
        jobs.extend(batch)
        log.info("Fetched %d jobs (offset %d / total %d)", len(batch), offset, data.get("total", 0))
        if not batch or offset + PAGE_SIZE >= data.get("total", 0):
            break
        offset += PAGE_SIZE
    return jobs

# ── Keyword matching ─────────────────────────────────────────────────────────
def matches_keywords(job: dict) -> bool:
    """Return True if ANY keyword appears in the job title or location."""
    haystack = " ".join([
        job.get("title", ""),
        job.get("locationsText", ""),
    ]).lower()
    return any(kw in haystack for kw in KEYWORDS)

# ── Seen-jobs store (simple JSON file) ──────────────────────────────────────
def load_seen() -> set:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        return set(json.loads(DATA_FILE.read_text()))
    return set()

def save_seen(seen: set):
    DATA_FILE.write_text(json.dumps(list(seen)))

def job_id(job: dict) -> str:
    return hashlib.md5(job.get("externalPath", job.get("title", "")).encode()).hexdigest()

# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(new_jobs: list[dict]):
    if not all([EMAIL_FROM, EMAIL_TO, SMTP_USER, SMTP_PASS]):
        log.warning("Email not configured – printing to stdout instead.")
        for j in new_jobs:
            print(f"  NEW: {j['title']} | {j.get('locationsText','?')} | {BASE_URL}{j['externalPath']}")
        return

    subject = f"🚀 {len(new_jobs)} New Red Hat Job(s) Matching: {', '.join(KEYWORDS)}"

    rows = ""
    for j in new_jobs:
        url  = f"{BASE_URL}{j['externalPath']}"
        loc  = j.get("locationsText", "—")
        date = j.get("postedOn", "—")
        rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <a href="{url}" style="color:#c0392b;font-weight:bold;text-decoration:none;">{j['title']}</a>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#555;">{loc}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#888;">{date}</td>
        </tr>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
      <h2 style="color:#c0392b;">🔔 New Red Hat Jobs Alert</h2>
      <p>Found <strong>{len(new_jobs)}</strong> new posting(s) matching <strong>{', '.join(KEYWORDS)}</strong></p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#c0392b;color:#fff;">
            <th style="padding:10px;text-align:left;">Title</th>
            <th style="padding:10px;text-align:left;">Location</th>
            <th style="padding:10px;text-align:left;">Posted</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="color:#aaa;font-size:12px;margin-top:20px;">
        Checked at {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC · 
        <a href="{BASE_URL}/en-US/{SITE}?q={'%20'.join(KEYWORDS)}">View all on Red Hat Careers</a>
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    log.info("Email sent to %s", EMAIL_TO)

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    log.info("Starting job check | keywords=%s", KEYWORDS)
    seen = load_seen()

    try:
        all_jobs = fetch_all_jobs()
    except requests.RequestException as e:
        log.error("Failed to fetch jobs: %s", e)
        return

    matching   = [j for j in all_jobs if matches_keywords(j)]
    new_jobs   = [j for j in matching if job_id(j) not in seen]

    log.info("Total=%d | Matching=%d | New=%d", len(all_jobs), len(matching), len(new_jobs))

    if new_jobs:
        send_email(new_jobs)
        seen.update(job_id(j) for j in new_jobs)
        save_seen(seen)
        log.info("Saved %d new job IDs", len(new_jobs))
    else:
        log.info("No new matching jobs found.")

if __name__ == "__main__":
    main()
