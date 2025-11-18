# api/cron.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv
from datetime import datetime
import os

# Load .env locally (Vercel uses dashboard env vars)
load_dotenv(override=False)

# NEW: import our summarizer
from utils.summarizer import summarize_threads, render_html

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
    For now:
    - Uses mock data
    - Summarizes with OpenAI (gpt-4.1-mini)
    - Delivery is skipped (SKIP_DELIVERY=true)
    """
    demo = os.getenv("DEMO_MODE", "false").lower() == "true"
    skip_delivery = os.getenv("SKIP_DELIVERY", "false").lower() == "true"

    # STEP 1: Use mock messages (Gmail comes later)
    threads = [
        {
            "from": "Alice <alice@example.com>",
            "subject": "Standup notes",
            "snippet": "We shipped auth; next sprint on analytics."
        },
        {
            "from": "Recruiter <jobs@company.com>",
            "subject": "Interview Loop",
            "snippet": "Wed/Thu for the technical screen?"
        },
        {
            "from": "Billing <billing@service.com>",
            "subject": "Invoice Due",
            "snippet": "Invoice #123 is due on 31 Oct."
        },
    ]

    # STEP 2: Summarize with OpenAI
    summary = summarize_threads(threads)

    # STEP 3: Render clean HTML version for emails (delivery later)
    html = render_html(summary["subject"], summary["bullets"])

    # STEP 4: Delivery skipped for now (safe dev mode)
    if not skip_delivery:
        # Email or Slack sending will go here in a later step
        pass

    return JSONResponse({
        "ok": True,
        "demo": demo,
        "skipped_delivery": skip_delivery,
        "subject": summary["subject"],
        "bullets": summary["bullets"],
        "html_preview": html
    })
