"""Daily SMS digest of AWS AI, ChatGPT/OpenAI, and AI-agents news.

Delivery via carrier email-to-SMS gateways (free) sent through Gmail SMTP.
"""

import html
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
from google import genai

# (display_name, feed_url, optional keyword filter)
SOURCES = [
    (
        "AWS What's New",
        "https://aws.amazon.com/about-aws/whats-new/recent/feed/",
        ["ai", "ml", "bedrock", "sagemaker", "anthropic", "claude", "agent", "amazon q", "nova", "titan"],
    ),
    (
        "AWS ML Blog",
        "https://aws.amazon.com/blogs/machine-learning/feed/",
        None,
    ),
    (
        "OpenAI / ChatGPT",
        "https://news.google.com/rss/search?q=OpenAI+OR+ChatGPT&hl=en-US&gl=US&ceid=US:en",
        None,
    ),
    (
        "Anthropic / Claude",
        "https://news.google.com/rss/search?q=Anthropic+OR+%22Claude+AI%22&hl=en-US&gl=US&ceid=US:en",
        None,
    ),
    (
        "AI Agents",
        "https://news.google.com/rss/search?q=%22AI+agents%22+OR+%22agentic+AI%22&hl=en-US&gl=US&ceid=US:en",
        None,
    ),
    (
        "Google AI",
        "https://news.google.com/rss/search?q=%22Google+AI%22+OR+Gemini+OR+DeepMind&hl=en-US&gl=US&ceid=US:en",
        None,
    ),
]

LOOKBACK_HOURS = 24
SITE_DIR = "digests"


def site_base_url():
    """https://<owner>.github.io/<repo> — computed from GitHub Actions env, override with SITE_BASE_URL."""
    override = os.environ.get("SITE_BASE_URL")
    if override:
        return override.rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")  # "owner/repo"
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}"
    return ""


def fetch_recent():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items = []
    for name, url, keywords in SOURCES:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if not published:
                continue
            pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue
            if keywords:
                text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
                if not any(k in text for k in keywords):
                    continue
            items.append(
                {
                    "source": name,
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:400],
                }
            )
    return items


def summarize(items):
    today = datetime.now().strftime("%-m/%-d")
    if not items:
        return f"AI Digest {today}: nothing notable in the last 24h."

    bundle = "\n\n".join(
        f"[{i['source']}] {i['title']}\n{i['link']}\n{i['summary']}" for i in items
    )

    prompt = f"""You write a daily SMS digest of AWS AI, ChatGPT/OpenAI, AI agents, and adjacent AI news for a builder who works with AWS and AI agents.

From the items below, pick the 4-6 most genuinely important stories. Skip marketing fluff, listicles, opinion pieces, and obvious duplicates across sources. Merge duplicates.

Output format (and nothing else):
AI Digest {today}
1. <punchy one-line headline>
   <url>
2. ...

Hard rules:
- Total output under 900 characters.
- One blank line between items.
- Plain text only (this is an SMS).
- Lead each headline with the most relevant topic tag in brackets when useful: [AWS], [OpenAI], [Anthropic], [Agents], [Google].
- If nothing is genuinely newsworthy, say so in one line.

Items:
{bundle}"""

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return (response.text or "").strip()


def _render_digest_html(items, sms_text, pretty_date):
    by_source = {}
    for item in items:
        by_source.setdefault(item["source"], []).append(item)

    sections = []
    for source, group in by_source.items():
        rows = "".join(
            f'<li><a href="{html.escape(i["link"])}">{html.escape(i["title"])}</a>'
            + (f'<p>{html.escape(i["summary"][:300])}</p>' if i.get("summary") else "")
            + "</li>"
            for i in group
        )
        sections.append(f"<h3>{html.escape(source)}</h3><ul>{rows}</ul>")

    body = "".join(sections) if sections else "<p><em>No items in the last 24h.</em></p>"

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Digest — {html.escape(pretty_date)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; line-height: 1.5; }}
  h1 {{ margin-bottom: 0; }}
  h3 {{ margin-top: 2rem; border-bottom: 1px solid #eee; padding-bottom: 4px; }}
  ul {{ padding-left: 1.2rem; }}
  li {{ margin-bottom: 0.75rem; }}
  li p {{ margin: 4px 0 0; color: #555; font-size: 0.9rem; }}
  pre {{ background: #f6f8fa; padding: 12px; border-radius: 6px; white-space: pre-wrap; font-family: ui-monospace, monospace; }}
  a {{ color: #0969da; }}
  nav a {{ font-size: 0.85rem; }}
</style>
</head><body>
<nav><a href="./">← all digests</a></nav>
<h1>AI Digest</h1>
<p style="color:#666;margin-top:0">{html.escape(pretty_date)}</p>
<pre>{html.escape(sms_text)}</pre>
<h2>All items ({len(items)})</h2>
{body}
</body></html>"""


def _render_index_html(dates):
    items = "".join(
        f'<li><a href="./{d}.html">{d}</a></li>' for d in dates
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Digest Archive</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }}
  a {{ color: #0969da; }}
</style>
</head><body>
<h1>AI Digest</h1>
<p>Daily digest of AWS AI, OpenAI/ChatGPT, Anthropic, and AI-agents news.</p>
<ul>{items}</ul>
</body></html>"""


def write_pages(items, sms_text):
    """Write digests/YYYY-MM-DD.html and refresh digests/index.html. Return the public URL."""
    today = datetime.now().strftime("%Y-%m-%d")
    pretty = datetime.now().strftime("%a %b %-d, %Y")

    os.makedirs(SITE_DIR, exist_ok=True)
    page_path = os.path.join(SITE_DIR, f"{today}.html")
    with open(page_path, "w") as f:
        f.write(_render_digest_html(items, sms_text, pretty))

    # Rebuild index from whatever YYYY-MM-DD.html files exist (newest first)
    dates = sorted(
        (f[:-5] for f in os.listdir(SITE_DIR) if f.endswith(".html") and f != "index.html"),
        reverse=True,
    )
    with open(os.path.join(SITE_DIR, "index.html"), "w") as f:
        f.write(_render_index_html(dates))

    base = site_base_url()
    return f"{base}/{SITE_DIR}/{today}.html" if base else page_path


def _smtp_send(from_addr, password, to_list, msg):
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(from_addr, password)
        server.sendmail(from_addr, to_list, msg.as_string())


def send_sms(message):
    """Send via Gmail SMTP to one or more carrier email-to-SMS gateways.

    SMS_GATEWAYS: comma-separated, e.g. "5551234567@mms.att.net,5559876543@tmomail.net"
        AT&T:     <number>@mms.att.net  (MMS, longer messages)
        T-Mobile: <number>@tmomail.net  (handles both)
    """
    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    recipients = [g.strip() for g in os.environ["SMS_GATEWAYS"].split(",") if g.strip()]

    msg = MIMEText(message)
    msg["Subject"] = ""
    msg["From"] = gmail_user
    msg["To"] = ", ".join(recipients)

    _smtp_send(gmail_user, gmail_app_password, recipients, msg)


def send_email_digest(items, sms_text):
    """Send a richer HTML email to GMAIL_USER with the SMS digest + every fetched item."""
    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    today = datetime.now().strftime("%a %b %-d")

    # Group items by source for the long version
    by_source = {}
    for item in items:
        by_source.setdefault(item["source"], []).append(item)

    sections_html = []
    for source, group in by_source.items():
        rows = "".join(
            f'<li><a href="{html.escape(i["link"])}">{html.escape(i["title"])}</a></li>'
            for i in group
        )
        sections_html.append(
            f"<h3 style='margin-bottom:4px'>{html.escape(source)}</h3><ul>{rows}</ul>"
        )

    html_body = f"""<html><body style="font-family:-apple-system,sans-serif;max-width:640px">
<h2>AI Digest — {today}</h2>
<pre style="background:#f6f8fa;padding:12px;border-radius:6px;white-space:pre-wrap;font-family:ui-monospace,monospace">{html.escape(sms_text)}</pre>
<h3 style="margin-top:24px">All items ({len(items)})</h3>
{''.join(sections_html) if sections_html else '<p><em>No items in the last 24h.</em></p>'}
</body></html>"""

    text_body = f"AI Digest — {today}\n\n{sms_text}\n\n--- All items ---\n" + "\n".join(
        f"[{i['source']}] {i['title']}\n{i['link']}" for i in items
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI Digest — {today}"
    msg["From"] = gmail_user
    msg["To"] = gmail_user
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    _smtp_send(gmail_user, gmail_app_password, [gmail_user], msg)


def main():
    items = fetch_recent()
    print(f"Fetched {len(items)} recent items")
    digest = summarize(items)
    print("---DIGEST---")
    print(digest)
    print("---END---")

    url = write_pages(items, digest)
    print(f"Wrote page: {url}")

    sms_with_link = f"{digest}\n\nFull: {url}" if url.startswith("http") else digest
    send_sms(sms_with_link)
    print("SMS sent.")

    send_email_digest(items, digest)
    print("Email sent.")


if __name__ == "__main__":
    main()
