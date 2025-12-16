# utils/gmail.py

import os
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
    response.raise_for_status()
    return response.json()["access_token"]


def list_recent_unread_message_ids(access_token, max_results=20):
    """
    Return message IDs for unread emails from the last 24 hours.
    """
    params = {
        "q": "newer_than:1d is:unread in:inbox",
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
