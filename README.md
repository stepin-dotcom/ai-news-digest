# AI News Digest

Daily text with the most important AWS AI, ChatGPT/OpenAI, Anthropic, and AI-agents news.

Runs on GitHub Actions (free), summarizes with Claude, delivers via your carrier's free email-to-SMS gateway (AT&T / T-Mobile).

## Setup

### 1. Gmail app password (~3 min)
1. Turn on 2-Step Verification: [myaccount.google.com/security](https://myaccount.google.com/security).
2. Create an app password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) → name it `ai-news-digest` → copy the 16-character password.

### 2. Gemini API key (free)
Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — sign in with your Google account, click **Create API key**, copy it. Free tier covers ~1,500 requests/day on Gemini 2.5 Flash; this script uses 1 request/day.

### 3. Figure out your carrier gateway addresses
- **AT&T**: `<10-digit-number>@mms.att.net` (MMS, allows longer messages)
- **T-Mobile**: `<10-digit-number>@tmomail.net` (handles both SMS and MMS)

Example for both phones: `5551234567@mms.att.net,5559876543@tmomail.net`

### 4. Push to GitHub
```bash
cd ai-news-digest
git init
git add .
git commit -m "Initial commit"
gh repo create ai-news-digest --private --source=. --push
```

### 5. Add secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:
- `GEMINI_API_KEY` — from step 2
- `GMAIL_USER` — your Gmail address
- `GMAIL_APP_PASSWORD` — the 16-char app password from step 1
- `SMS_GATEWAYS` — comma-separated gateway addresses from step 3

### 6. Enable GitHub Pages
Repo → **Settings → Pages** → under **Build and deployment** set **Source = Deploy from a branch**, **Branch = main**, **Folder = / (root)**. Save. Your archive will live at `https://<your-username>.github.io/ai-news-digest/digests/`.

(The workflow needs write permission, which is already set in [daily-digest.yml](.github/workflows/daily-digest.yml). If your repo blocks Actions from pushing, also visit **Settings → Actions → General → Workflow permissions** → "Read and write permissions".)

### 7. Test it
Actions tab → **Daily AI Digest** → **Run workflow**. Within a minute you'll get:
- A **text message** with the 4-6 top headlines plus a link to the full styled HTML page on your phone (sent to every number in `SMS_GATEWAYS`).
- A **richer HTML email** to `GMAIL_USER` with the same content as a backup.
- A new file in `digests/YYYY-MM-DD.html` committed to the repo and published via Pages.

> **First-deploy delay:** GitHub Pages takes ~30-60 seconds to publish after the first push, so if you tap the link in the SMS immediately and see a 404, refresh in a minute. Subsequent days deploy faster.

The scheduled run fires daily at 13:00 UTC (8am ET) — edit the cron in [.github/workflows/daily-digest.yml](.github/workflows/daily-digest.yml).

## Customizing

- **Sources**: edit `SOURCES` in [digest.py](digest.py). Any RSS feed works; for sites without one use `https://news.google.com/rss/search?q=...`.
- **Topics**: AWS What's New is keyword-filtered to AI items. Tweak the keyword list.
- **Time of day**: change the `cron` line in the workflow (it's UTC).
- **Length**: bump the 900-char cap in `digest.py`. MMS gateways handle 1500+ chars.
- **Cadence**: change cron to e.g. `0 13 * * 1-5` for weekdays only.
- **Add a phone**: append another gateway address to the `SMS_GATEWAYS` secret.

## Cost
- GitHub Actions: free
- Gemini API: free (well within Google's 1,500 req/day free tier)
- Gmail SMTP + carrier gateways: free

## Notes
- Carrier email-to-SMS gateways are best-effort. AT&T and T-Mobile both work as of 2026; Verizon shut theirs down in 2024.
- If a message arrives blank, your carrier may be stripping the empty subject line — add a short subject in `send_sms` if so.
