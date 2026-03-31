# api/ingest.py

import os
import base64
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from utils.gmail import get_access_token, list_recent_unread_message_ids, get_full_message, fetch_attachment
from utils.attachment_parser import parse_attachment
from utils.chunker import chunk_email, chunk_attachment
from utils.embedder import upsert_documents

router = APIRouter()

DEMO_EMAILS = [
    {"id": "demo-1", "from": "Alice <alice@example.com>", "subject": "Standup notes", "date": "Mon, 31 Mar 2026", "body": "We shipped the auth feature last week. Next sprint will focus on the analytics dashboard. Please review the PR before Thursday.", "attachments": []},
    {"id": "demo-2", "from": "Recruiter <jobs@company.com>", "subject": "Interview Loop", "date": "Mon, 31 Mar 2026", "body": "Hi, we'd love to schedule your technical screen for Wednesday or Thursday. Please confirm your availability and we'll send a calendar invite.", "attachments": []},
    {"id": "demo-3", "from": "Billing <billing@service.com>", "subject": "Invoice #123 Due", "date": "Mon, 31 Mar 2026", "body": "Your invoice #123 for $450.00 is due on October 31st. Please make payment via the link in this email to avoid a late fee.", "attachments": []},
]


@router.post("/api/ingest")
def ingest():
    """
    Fetch recent unread emails, chunk bodies + attachments, embed, and store in Qdrant.
    Set DEMO_MODE=true to use mock emails instead of Gmail.
    """
    demo = os.getenv("DEMO_MODE", "false").lower() == "true"

    all_docs = []
    attachments_processed = 0

    if demo:
        emails = DEMO_EMAILS
    else:
        access = get_access_token()
        ids = list_recent_unread_message_ids(access, max_results=15)
        emails = [get_full_message(access, mid) for mid in ids]

    for email in emails:

        # Chunk and store email body
        all_docs.extend(chunk_email(email))

        # Parse and chunk attachments (PDF / DOCX only, skipped in demo mode)
        for att in email.get("attachments", []):
            if att.get("attachment_id") and not demo:
                data = fetch_attachment(access, email["id"], att["attachment_id"])
            elif att.get("inline_data"):
                data = base64.urlsafe_b64decode(att["inline_data"] + "==")
            else:
                continue

            text = parse_attachment(att["mime_type"], data)
            if text:
                all_docs.extend(chunk_attachment(email, att["name"], text))
                attachments_processed += 1

    if all_docs:
        upsert_documents(all_docs)

    return JSONResponse({
        "ok": True,
        "demo": demo,
        "emails_processed": len(emails),
        "attachments_processed": attachments_processed,
        "chunks_stored": len(all_docs),
    })
