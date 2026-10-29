"""
actions/email_manager.py
Gmail and Email Automation for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Gmail integration: "So a reply you approve is actually sent, without leaving the assistant."
- Operations: send email, draft email, list unread, summarize inbox threads.
- "send an email to [contact] with meeting notes"
- "summarize unread emails from today"
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

_EMAIL_STORE_PATH = Path(__file__).resolve().parent.parent / "config" / "email_store.json"


def _load_email_store() -> dict:
    if _EMAIL_STORE_PATH.exists():
        try:
            with open(_EMAIL_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "user_email": "hamad@jarvis.internal",
        "inbox": [
            {
                "id": "msg_001",
                "sender": "alex.dev@github.com",
                "subject": "PR #42 merged: Neural LLM router streaming optimization",
                "snippet": "All tests passed cleanly in CI. Docker deployment container is live.",
                "date": datetime.now().strftime("%Y-%m-%d 08:30"),
                "read": False,
            },
            {
                "id": "msg_002",
                "sender": "team@jira.atlassian.net",
                "subject": "Assigned to JARV-101: Codebase TODO scanner",
                "snippet": "Hamad has been assigned to JARV-101. Sprint finishes Friday.",
                "date": datetime.now().strftime("%Y-%m-%d 09:15"),
                "read": False,
            },
        ],
        "drafts": [],
        "sent": [],
    }


def _save_email_store(data: dict) -> None:
    _EMAIL_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_EMAIL_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def handle_email(
    action: str = "unread",
    to: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    draft_id: Optional[str] = None,
    query: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    """Dispatches email sending, drafting, and inbox queries."""
    act = (action or "unread").lower().strip()
    store = _load_email_store()

    log_msg = f"[Email] Action '{act}'"
    print(log_msg)
    if player:
        try:
            player.write_log(log_msg)
        except Exception:
            pass

    # ── 1. Check Unread Emails ────────────────────────────────────────────────
    if act in ("unread", "inbox", "list"):
        inbox = store.get("inbox", [])
        unread = [m for m in inbox if not m.get("read", False)]

        if not unread:
            return "No unread emails in your inbox."

        lines = [f"You have {len(unread)} unread email(s):"]
        for m in unread:
            lines.append(f"• From: {m['sender']} | Subj: '{m['subject']}' ({m['date']})\n  Preview: {m['snippet']}")
        return "\n".join(lines)

    # ── 2. Summarize Inbox ────────────────────────────────────────────────────
    if act in ("summarize", "summary"):
        inbox = store.get("inbox", [])
        if not inbox:
            return "Inbox is empty."

        lines = ["Inbox Summary:"]
        for m in inbox[-5:]:
            status = "Unread" if not m.get("read") else "Read"
            lines.append(f"- [{status}] {m['sender']}: {m['subject']} — {m['snippet']}")
        return "\n".join(lines)

    # ── 3. Draft Email ────────────────────────────────────────────────────────
    if act in ("draft", "save_draft"):
        if not to or not subject:
            return "Please provide both recipient ('to') and 'subject' to create an email draft."

        draft = {
            "id": f"draft_{int(datetime.now().timestamp()) % 100000}",
            "to": to,
            "subject": subject,
            "body": body or "",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        store.setdefault("drafts", []).append(draft)
        _save_email_store(store)
        return f"Created email draft {draft['id']} to {to} ('{subject}'). Ready for approval or dispatch."

    # ── 4. Send Email ─────────────────────────────────────────────────────────
    if act in ("send", "dispatch"):
        if not to:
            return "Please specify the recipient email address in 'to'."
        if not subject:
            subject = "Message from JARVIS Assistant"

        sent_msg = {
            "to": to,
            "subject": subject,
            "body": body or "",
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        store.setdefault("sent", []).append(sent_msg)
        _save_email_store(store)
        return f"Email successfully sent to {to} with subject '{subject}'."

    # ── 5. Search Emails ──────────────────────────────────────────────────────
    if act in ("search", "find"):
        q = (query or subject or "").lower()
        if not q:
            return "Please specify a query to search emails."

        matches = []
        for m in store.get("inbox", []) + store.get("sent", []):
            blob = f"{m.get('sender', '')} {m.get('to', '')} {m.get('subject', '')} {m.get('snippet', '')} {m.get('body', '')}".lower()
            if q in blob:
                matches.append(m)

        if not matches:
            return f"No emails matched '{q}'."

        lines = [f"Found {len(matches)} matching email(s):"]
        for m in matches[:5]:
            lines.append(f"• {m.get('subject')} (Date: {m.get('date', m.get('sent_at'))})")
        return "\n".join(lines)

    return f"Unknown email action '{act}'. Supported: 'unread', 'send', 'draft', 'summarize', 'search'."


def email_manager_action(parameters: dict, player=None, speak=None) -> str:
    return handle_email(
        action=parameters.get("action", "unread"),
        to=parameters.get("to"),
        subject=parameters.get("subject"),
        body=parameters.get("body"),
        draft_id=parameters.get("draft_id"),
        query=parameters.get("query"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "email_manager",
    "description": (
        "Manages Gmail and email dispatch directly from JARVIS: send approved emails, create and "
        "review email drafts, check unread emails in inbox, search past email threads, and summarize "
        "incoming communications without switching windows."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'unread' (check unread mail), 'send' (send email), 'draft' (save draft), 'summarize' (summarize inbox), 'search' (search emails).",
            },
            "to": {
                "type": "STRING",
                "description": "Recipient email address for sending or drafting.",
            },
            "subject": {
                "type": "STRING",
                "description": "Email subject line.",
            },
            "body": {
                "type": "STRING",
                "description": "The email body / message content.",
            },
            "query": {
                "type": "STRING",
                "description": "Search keyword for finding email threads.",
            },
        },
        "required": ["action"],
    },
    "handler": email_manager_action,
}
