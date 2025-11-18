# utils/summarizer.py

import os
import requests
import json
from datetime import datetime

def summarize_threads(threads):
    """
    Takes a list of email threads and returns a structured summary using OpenAI.
    Each thread looks like:
      { "from": "...", "subject": "...", "snippet": "..." }
    """

    if not threads:
        return {
            "subject": "Email Digest — No new mail",
            "bullets": []
        }

    # Build readable input for the AI
    items = "\n".join(
        [
            f"{i+1}. From: {t['from']}\nSubject: {t['subject']}\nSnippet: {t['snippet']}"
            for i, t in enumerate(threads)
        ]
    )

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    prompt = f"""
You are an assistant that writes clear, helpful daily email digests.

Summarize the following emails in 6–10 bullets.
Each bullet should be:
- one sentence
- mention sender or subject
- state the main point or request
- optionally include what action the user should take

Return valid JSON with this structure:
{{
  "bullets": [
    {{"title": "", "detail": ""}}
  ]
}}

Emails:
{items}
"""

    # Call OpenAI API
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You summarize emails clearly and professionally."},
                {"role": "user", "content": prompt}
            ],
        },
        timeout=30
    )

    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]

    # Parse JSON response
    try:
        parsed = json.loads(content)
        bullets = parsed.get("bullets", [])
    except Exception:
        bullets = []

    subject = f"Email Digest — {datetime.now().strftime('%Y-%m-%d')}"

    return {
        "subject": subject,
        "bullets": bullets
    }


def escape(s: str) -> str:
    """Escape HTML characters."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )


def render_html(subject: str, bullets: list):
    """Create the HTML version of the email digest."""
    if not bullets:
        body = "<p>No unread messages today.</p>"
    else:
        body = "<ol>" + "".join(
            [
                f"<li><b>{escape(b.get('title', ''))}</b><br>{escape(b.get('detail', ''))}</li>"
                for b in bullets
            ]
        ) + "</ol>"

    return f"""
    <div style="font-family: -apple-system, Segoe UI, Roboto, sans-serif;">
      <h2>{escape(subject)}</h2>
      {body}
      <p style="color:#777;">Generated automatically by your AI Email Summarizer.</p>
    </div>
    """
