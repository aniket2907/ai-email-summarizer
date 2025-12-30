# api/cron.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv
import os

# Load .env locally (Vercel uses dashboard env vars)
load_dotenv(override=True)

from utils.summarizer import summarize_threads, render_html
from utils.gmail import (
    get_access_token,
    list_recent_unread_message_ids,
    get_message_snippet,
    mark_as_read,
)

app = FastAPI()

@app.get("/", response_class=PlainTextResponse)
def home():
    return "AI Email Summarizer running. Try /health or /api/cron"

@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"

@app.get("/api/cron")
def run_digest():
    """
    Main cron endpoint.

    Behavior:
    - DEMO_MODE=true  -> uses mock emails
    - DEMO_MODE=false -> pulls real unread Gmail emails (last 24h)

    Delivery:
    - SKIP_DELIVERY=true -> no sending (safe)
    """
    demo = os.getenv("DEMO_MODE", "false").lower() == "true"
    skip_delivery = os.getenv("SKIP_DELIVERY", "false").lower() == "true"
    mark_read = os.getenv("MARK_AS_READ", "false").lower() == "true"

    # 1) Collect threads (mock or Gmail)
    if demo:
        threads = [
            {"from": "Alice <alice@example.com>", "subject": "Standup notes", "snippet": "We shipped auth; next sprint on analytics."},
            {"from": "Recruiter <jobs@company.com>", "subject": "Interview Loop", "snippet": "Wed/Thu for the technical screen?"},
            {"from": "Billing <billing@service.com>", "subject": "Invoice Due", "snippet": "Invoice #123 is due on 31 Oct."},
        ]
        ids = []
    else:
        access = get_access_token()
        ids = list_recent_unread_message_ids(access, max_results=15)
        threads = [get_message_snippet(access, mid) for mid in ids]

    # 2) Summarize with OpenAI
    summary = summarize_threads(threads)

    # 3) Render HTML preview (used later for email)
    html = render_html(summary["subject"], summary["bullets"])

    # 4) Optional: mark as read (OFF by default)
    if (not demo) and mark_read and ids:
        # only mark read if you explicitly enable MARK_AS_READ=true
        access = get_access_token()
        mark_as_read(access, ids)

    # 5) Delivery still skipped for now
    if not skip_delivery:
        # Resend/Slack sending will be added later
        pass

    return JSONResponse({
        "ok": True,
        "demo": demo,
        "skipped_delivery": skip_delivery,
        "gmail_unread_count": (0 if demo else len(ids)),
        "subject": summary["subject"],
        "bullets": summary["bullets"],
        "html_preview": html
    })
