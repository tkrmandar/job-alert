# 🔔 Red Hat Job Alert

Checks Red Hat's careers page every 10 minutes and emails you when new jobs matching your keywords are posted. No browser/Playwright needed — uses Workday's internal JSON API directly.

## How it works

1. Calls the Workday CXS API (`POST /wday/cxs/redhat/jobs/jobs`) — same endpoint the careers page itself uses
2. Filters jobs by your keywords (title or location match)
3. Compares against previously-seen job IDs stored in `data/seen_jobs.json`
4. Sends an HTML email for any new matches
5. GitHub Actions runs this on a cron every 10 minutes for free

---

## Setup

### 1. Clone & configure locally (optional test)

```bash
git clone https://github.com/YOUR_USERNAME/job-alert.git
cd job-alert
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your email credentials
python src/checker.py
```

### 2. Push to GitHub

```bash
git init   # if not already
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/job-alert.git
git push -u origin main
```

### 3. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret       | Value                                   |
|--------------|-----------------------------------------|
| `WD_TENANT`  | `redhat`                                |
| `WD_SERVER`  | `wd5`                                   |
| `WD_SITE`    | `jobs`                                  |
| `KEYWORDS`   | `devops,platform engineer,sre`          |
| `EMAIL_FROM` | `you@gmail.com`                         |
| `EMAIL_TO`   | `you@gmail.com`                         |
| `SMTP_HOST`  | `smtp.gmail.com`                        |
| `SMTP_PORT`  | `587`                                   |
| `SMTP_USER`  | `you@gmail.com`                         |
| `SMTP_PASS`  | Your Gmail App Password (see below)     |

### 4. Gmail App Password (required if using Gmail)

1. Enable 2-Factor Authentication on your Google account
2. Go to: [Google Account → Security → App Passwords](https://myaccount.google.com/apppasswords)
3. Create an app password (name it "job-alert")
4. Paste the 16-character password as `SMTP_PASS`

> **Other email providers:**
> - Outlook: `smtp-mail.outlook.com`, port `587`
> - Yahoo: `smtp.mail.yahoo.com`, port `587`
> - Any SMTP provider (Mailgun, SendGrid, etc.) works

### 5. Enable GitHub Actions

The workflow file is already at `.github/workflows/job_alert.yml`.

After pushing, go to your repo → **Actions** tab → you should see "Job Alert".

Click **Run workflow** to test it manually before waiting for the cron.

> **Note:** GitHub's minimum cron interval is 5 minutes. The `*/10` cron is respected, but GitHub may delay runs by a few minutes during high-traffic periods.

---

## Customise

### Change keywords
Edit the `KEYWORDS` secret (or `.env` for local) — comma-separated, case-insensitive:
```
KEYWORDS=devops,kubernetes,openshift,sre,platform
```

### Change the target company
Any company on Workday — just update these three values:

| Company      | `WD_TENANT` | `WD_SERVER` | `WD_SITE`          |
|--------------|-------------|-------------|---------------------|
| Red Hat      | `redhat`    | `wd5`       | `jobs`              |
| Mastercard   | `mastercard`| `wd1`       | `CorporateCareers`  |
| Kainos       | `kainos`    | `wd3`       | `kainos`            |

To find values for any company: open their Workday careers URL and extract:
`https://{TENANT}.{WD_SERVER}.myworkdayjobs.com/en-US/{SITE}`

---

## Project structure

```
job-alert/
├── src/
│   └── checker.py          # main script
├── data/
│   └── seen_jobs.json      # auto-created; tracks alerted jobs
├── .github/
│   └── workflows/
│       └── job_alert.yml   # GitHub Actions cron
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Sample email

The email shows job title (linked), location, and posting date in a clean HTML table.

---

## Local cron alternative (if you don't want GitHub Actions)

```bash
# Add to crontab -e
*/10 * * * * cd /path/to/job-alert && python src/checker.py >> logs/cron.log 2>&1
```
