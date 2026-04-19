# 🔔 Siemens Job Alert Bot

Automatically scrapes the [Siemens Careers page](https://jobs.siemens.com/en_US/externaljobs) every 10 minutes and emails you when new jobs matching your keyword appear.

---

## How It Works

1. **GitHub Actions** runs the scraper on a cron schedule (every 10 min)
2. **Playwright** launches a headless Chromium, searches for your keyword on Siemens careers
3. **New jobs** are compared against `data/seen_jobs.json` (committed back to repo)
4. **Nodemailer** sends a formatted HTML email with all new matches
5. Seen jobs are saved so you **never get duplicate emails**

---

## Setup Guide

### Step 1 — Fork / Clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/siemens-job-alert.git
cd siemens-job-alert
```

### Step 2 — Set up Gmail App Password

1. Go to your Google Account → **Security** → **2-Step Verification** (enable it)
2. Then go to **App passwords** → Create one for "Mail"
3. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)

### Step 3 — Add GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

| Secret Name   | Value                                              |
|---------------|----------------------------------------------------|
| `JOB_KEYWORD` | e.g. `software engineer` or `data scientist`       |
| `EMAIL_TO`    | Your email address (where to receive alerts)       |
| `EMAIL_FROM`  | Your Gmail address (used to send)                  |
| `EMAIL_PASS`  | Your Gmail App Password (16 chars, no spaces)      |

### Step 4 — Push to GitHub

```bash
git add .
git commit -m "init: siemens job alert bot"
git push origin main
```

### Step 5 — Enable GitHub Actions

- Go to your repo → **Actions** tab
- If prompted, click **"I understand my workflows, go ahead and enable them"**
- The cron will fire automatically every 10 minutes
- You can also click **"Run workflow"** to test it immediately

---

## Local Testing

```bash
npm install
npx playwright install chromium

# Set env vars
export JOB_KEYWORD="software engineer"
export EMAIL_TO="you@gmail.com"
export EMAIL_FROM="you@gmail.com"
export EMAIL_PASS="your-app-password"

node scraper.js
```

---

## Customization

- **Change keyword**: Update the `JOB_KEYWORD` secret in GitHub
- **Change schedule**: Edit `cron: '*/10 * * * *'` in `.github/workflows/job-alert.yml`
  - Every 5 min: `'*/5 * * * *'`
  - Every hour: `'0 * * * *'`
  - 9am IST daily: `'30 3 * * *'` (UTC+5:30 offset)
- **Multiple keywords**: Duplicate the job in the workflow with different `JOB_KEYWORD` values

---

## ⚠️ Notes

- GitHub Actions free tier allows **2,000 minutes/month** — running every 10 min uses ~4,320 min/month on a private repo. Use a **public repo** to get unlimited free minutes for public repos, or adjust the cron interval.
- Gmail App Passwords require 2FA to be enabled on your Google account.
