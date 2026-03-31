# utils/gmail.py

import os
import base64
import requests

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


def get_access_token():
    """
    Exchange a long-lived refresh token for a short-lived access token.

    Requires these env vars:
    - GOOGLE_CLIENT_ID
    - GOOGLE_CLIENT_SECRET
    - GOOGLE_REFRESH_TOKEN
    """
    data = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data=data,
        timeout=20,
    )
    if response.status_code != 200:
        # Print Google’s exact reason (super important for fixing)
        raise RuntimeError(f"Token endpoint error {response.status_code}: {response.text}")

    return response.json()["access_token"]


def list_recent_unread_message_ids(access_token, max_results=20):
    """
    Return message IDs for unread emails from the last 24 hours.
    """
    params = {
        "q": "newer_than:1d is:unread in:inbox category:primary",
        "maxResults": max_results,
    }

    response = requests.get(
        f"{GMAIL_API_BASE}/users/me/messages",
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
        timeout=20,
    )

    data = response.json()

    if "messages" not in data:
        return []

    return [m["id"] for m in data["messages"]]


def get_message_snippet(access_token, message_id):
    """
    Fetch basic info for a single Gmail message.
    """
    response = requests.get(
        f"{GMAIL_API_BASE}/users/me/messages/{message_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"format": "full"},
        timeout=20,
    )
    response.raise_for_status()
    msg = response.json()

    headers = {
        h["name"]: h["value"]
        for h in msg["payload"].get("headers", [])
    }

    return {
        "id": message_id,
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "snippet": msg.get("snippet", ""),
    }


def get_full_message(access_token, message_id):
    """
    Fetch full message: headers, decoded body text, and attachment metadata.
    """
    response = requests.get(
        f"{GMAIL_API_BASE}/users/me/messages/{message_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"format": "full"},
        timeout=20,
    )
    response.raise_for_status()
    msg = response.json()

    headers = {
        h["name"]: h["value"]
        for h in msg["payload"].get("headers", [])
    }

    return {
        "id": message_id,
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "date": headers.get("Date", ""),
        "body": _extract_body(msg["payload"]),
        "attachments": _extract_attachment_metadata(msg["payload"]),
    }


def _extract_body(payload: dict) -> str:
    """Recursively extract plain-text body from a message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text

    return ""


def _extract_attachment_metadata(payload: dict) -> list[dict]:
    """Walk payload parts and collect attachment descriptors."""
    attachments = []
    for part in payload.get("parts", []):
        filename = part.get("filename", "")
        if filename:
            body = part.get("body", {})
            attachments.append({
                "name": filename,
                "mime_type": part.get("mimeType", ""),
                "attachment_id": body.get("attachmentId", ""),
                "inline_data": body.get("data", ""),  # set for small attachments
            })
        else:
            attachments.extend(_extract_attachment_metadata(part))
    return attachments


def fetch_attachment(access_token, message_id, attachment_id) -> bytes:
    """Download and decode a Gmail attachment by its attachment ID."""
    response = requests.get(
        f"{GMAIL_API_BASE}/users/me/messages/{message_id}/attachments/{attachment_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return base64.urlsafe_b64decode(response.json()["data"] + "==")


def mark_as_read(access_token, message_ids):
    """
    Remove the UNREAD label from messages.
    """
    if not message_ids:
        return

    response = requests.post(
        f"{GMAIL_API_BASE}/users/me/messages/batchModify",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "ids": message_ids,
            "removeLabelIds": ["UNREAD"],
        },
        timeout=20,
    )
    response.raise_for_status()
