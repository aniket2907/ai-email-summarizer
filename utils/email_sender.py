# utils/email_sender.py

import os
import requests


def send_email(subject: str, html: str):
    """
    Send an email using Resend.

    Requires:
      - RESEND_API_KEY
      - EMAIL_FROM
      - EMAIL_TO
    """
    api_key = os.environ["RESEND_API_KEY"]
    email_from = os.environ["EMAIL_FROM"]
    email_to = os.environ["EMAIL_TO"]

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": email_from,
            "to": email_to,
            "subject": subject,
            "html": html,
        },
        timeout=20,
    )

    response.raise_for_status()
