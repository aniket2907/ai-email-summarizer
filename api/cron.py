# api/cron.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv
from datetime import datetime
import os

# Load .env locally (Vercel uses project env settings in the dashboard)
# This does nothing in production, but helps locally.
load_dotenv(override=False)

app = FastAPI()

@app.get("/", response_class=PlainTextResponse)
def home():
    """
    Simple landing message so visiting http://127.0.0.1:8000/ doesn't 404.
    """
    return "AI Email Summarizer running. Try /health or /api/cron"

@app.get("/health", response_class=PlainTextResponse)
def health():
    """
    Minimal health check for uptime probes.
    """
    return "ok"

@app.get("/api/cron")
def run_digest():
    """
    This endpoint will be called by Vercel Cron in production.
    For now, it returns a mock digest (safe: no external APIs called).
    We'll wire Gmail + OpenAI + delivery in later steps.
    """
    # Safe local-testing flags (optional)
    demo = os.getenv("DEMO_MODE", "false").lower() == "true"
    skip_delivery = os.getenv("SKIP_DELIVERY", "false").lower() == "true"

    # Mock messages so you can see a "digest" structure immediately.
    threads = [
        {"from":"Alice <alice@example.com>", "subject":"Standup notes", "snippet":"We shipped auth; next sprint on analytics."},
        {"from":"Recruiter <jobs@company.com>", "subject":"Interview Loop", "snippet":"Wed/Thu for the technical screen?"},
        {"from":"Billing <billing@service.com>", "subject":"Invoice Due", "snippet":"Invoice #123 is due on 31 Oct."},
    ]

    # Minimal digest: later we’ll replace with OpenAI summarization.
    subject = f"Email Digest — {datetime.now().strftime('%d-%m-%Y')}"
    bullets = [
        {"title": t["subject"], "detail": t["snippet"]} for t in threads
    ]

    # skip_delivery is honored.
    # will add: Resend (email) or Slack webhook here onced local testing is complete.

    return JSONResponse({
        "ok": True,
        "subject": subject,
        "count": len(bullets),
        "bullets": bullets,
        "demo": demo,
        "skipped_delivery": skip_delivery
    })
