require('dotenv').config();

const { chromium } = require('playwright');
const nodemailer = require('nodemailer');
const fs = require('fs');
const path = require('path');

// ─── CONFIG ───────────────────────────────────────────────────────────────────
const KEYWORD = 'devops';

const BASE_URL =
  'https://jobs.siemens.com/en_US/externaljobs/SearchJobs/' +
  KEYWORD +
  '/?listFilterMode=1&folderRecordsPerPage=6&folderOffset=';

const EMAIL_TO = process.env.EMAIL_TO;
const EMAIL_FROM = process.env.EMAIL_FROM;
const EMAIL_PASS = process.env.EMAIL_PASS;

const SEEN_JOBS_FILE = path.join(__dirname, 'data', 'seen_jobs.json');

// ─── SEEN JOBS ────────────────────────────────────────────────────────────────
function loadSeenJobs() {
  try {
    if (fs.existsSync(SEEN_JOBS_FILE)) {
      return new Set(JSON.parse(fs.readFileSync(SEEN_JOBS_FILE, 'utf8')));
    }
  } catch {}
  return new Set();
}

function saveSeenJobs(seenJobs) {
  fs.mkdirSync(path.dirname(SEEN_JOBS_FILE), { recursive: true });
  fs.writeFileSync(SEEN_JOBS_FILE, JSON.stringify([...seenJobs], null, 2));
}

// ─── EMAIL ────────────────────────────────────────────────────────────────────
async function sendEmail(newJobs, totalJobs) {
  if (!EMAIL_TO || !EMAIL_FROM || !EMAIL_PASS) {
    console.log('⚠️ Email not configured, skipping...');
    return;
  }

  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: EMAIL_FROM,
      pass: EMAIL_PASS,
    },
    tls: {
      rejectUnauthorized: false,
    },
  });

  let html = '';

  if (newJobs.length === 0) {
    html = `
      <h3>✅ No new DevOps jobs</h3>
      <p>Total jobs checked: ${totalJobs}</p>
    `;
  } else {
    html =
      `<h3>🚨 ${newJobs.length} New DevOps Jobs Found</h3>` +
      newJobs
        .map(
          (j) =>
            `<p><b>${j.title}</b><br>${j.location}<br><a href="${j.url}">Apply</a></p>`
        )
        .join('');
  }

  await transporter.sendMail({
    from: EMAIL_FROM,
    to: EMAIL_TO,
    subject:
      newJobs.length === 0
        ? `✅ No New DevOps Jobs`
        : `🚨 ${newJobs.length} New DevOps Jobs`,
    html,
  });

  console.log('✅ Email sent');
}

// ─── SCRAPER ──────────────────────────────────────────────────────────────────
async function scrapeJobs() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const jobs = [];
  let pageNum = 0;

  while (true) {
    const offset = pageNum * 6;
    const url = `${BASE_URL}${offset}`;

    console.log(`\n📄 Fetching: ${url}`);

    await page.goto(url, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    // 🍪 Cookies
    try {
      const btn = await page.$('#onetrust-accept-btn-handler');
      if (btn) {
        await btn.click();
        await page.waitForTimeout(2000);
      }
    } catch {}

    await page.waitForTimeout(3000);

    const jobData = await page.evaluate((keyword) => {
      const results = [];
      const kw = keyword.toLowerCase();

      const articles = document.querySelectorAll('article.article--result');

      articles.forEach((article) => {
        const titleEl = article.querySelector('h3 a');
        const locationEl = article.querySelector('.list-item-location');

        const title = titleEl?.textContent?.trim() || '';
        const url = titleEl?.href || '';
        const location = locationEl?.textContent?.trim() || '';

        if (!title || !url) return;

        if (title.toLowerCase().includes(kw)) {
          results.push({ title, url, location });
        }
      });

      return results;
    }, KEYWORD);

    console.log(`📋 Found ${jobData.length} jobs`);

    if (jobData.length === 0) {
      console.log('🚫 No more pages');
      break;
    }

    jobs.push(...jobData);
    pageNum++;
  }

  await browser.close();

  // 🧹 Deduplicate
  const unique = [];
  const seen = new Set();

  for (const j of jobs) {
    if (!seen.has(j.url)) {
      seen.add(j.url);
      unique.push(j);
    }
  }

  console.log(`\n📊 Total unique jobs: ${unique.length}`);

  return unique;
}

// ─── MAIN ─────────────────────────────────────────────────────────────────────
(async () => {
  const allJobs = await scrapeJobs();
  const seenJobs = loadSeenJobs();

  // ✅ robust filtering (by URL, not title)
  const newJobs = allJobs.filter((j) => !seenJobs.has(j.url));

  console.log(`🆕 New jobs: ${newJobs.length}`);

  newJobs.forEach((j, i) => {
    console.log(`${i + 1}. ${j.title}`);
  });

  // 📧 Always send email (even if 0 new jobs)
  await sendEmail(newJobs, allJobs.length);

  // 💾 Save ALL jobs as seen (important)
  allJobs.forEach((j) => seenJobs.add(j.url));
  saveSeenJobs(seenJobs);

  console.log('💾 Seen jobs updated');
})();