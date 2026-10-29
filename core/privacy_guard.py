"""
core/privacy_guard.py
Privacy Guard Core for JARVIS.

Inspired by Jarvis Institute feature specifications:
- STRICT mode: Keeps data strictly local, blocks external cloud transmission, redirects to local Ollama.
- GUARDED mode: Automatically detects and redacts secrets (API keys, passwords, bearer tokens, AWS keys, etc.) before sending to external APIs.
- Audit ledger: Full audit trail recording every external API call, redaction count, and timestamps.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"
AUDIT_LOG_FILE = BASE_DIR / "memory" / "audit_ledger.jsonl"

# Common credential and secret patterns
REDACTION_PATTERNS = [
    # OpenAI & generic API keys
    (re.compile(r"\b(sk-[a-zA-Z0-9_\-]{20,})\b"), "[REDACTED_OPENAI_KEY]"),
    # Google API keys (AIza...)
    (re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b"), "[REDACTED_GEMINI_KEY]"),
    # Anthropic API keys (sk-ant-...)
    (re.compile(r"\b(sk-ant-[a-zA-Z0-9_\-]{20,})\b"), "[REDACTED_ANTHROPIC_KEY]"),
    # GitHub personal access tokens
    (re.compile(r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b"), "[REDACTED_GITHUB_TOKEN]"),
    # AWS access key IDs
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
    # JWT tokens
    (re.compile(r"\b(ey[a-zA-Z0-9_\-]{15,}\.ey[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,})\b"), "[REDACTED_JWT_TOKEN]"),
    # Bearer tokens in headers
    (re.compile(r"(?i)\bBearer\s+([a-zA-Z0-9\-\._~\+\/]+=*)"), "Bearer [REDACTED_BEARER_TOKEN]"),
    # Passwords or secrets in key-value pairs (password=..., secret=...)
    (
        re.compile(r"(?i)\b(password|passwd|secret|api_key|apikey|private_key)\s*[:=]\s*([\'\"][^\'\"]+[\'\"]|\S+)"),
        r"\1=[REDACTED_SECRET]",
    ),
    # Private Key blocks
    (
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?-----END (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY_BLOCK]",
    ),
]


class PrivacyGuard:
    _instance: Optional[PrivacyGuard] = None

    def __init__(self):
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> PrivacyGuard:
        if cls._instance is None:
            cls._instance = PrivacyGuard()
        return cls._instance

    @staticmethod
    def get_mode() -> str:
        """Returns active privacy mode: 'STRICT', 'GUARDED', or 'OFF'. Default is 'GUARDED'."""
        try:
            if CONFIG_FILE.exists():
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                mode = data.get("privacy_mode", "GUARDED").upper().strip()
                if mode in ("STRICT", "GUARDED", "OFF"):
                    return mode
        except Exception:
            pass
        return "GUARDED"

    @staticmethod
    def set_mode(mode: str) -> str:
        """Sets privacy mode to STRICT, GUARDED, or OFF."""
        mode_clean = mode.upper().strip()
        if mode_clean not in ("STRICT", "GUARDED", "OFF"):
            return f"Invalid privacy mode '{mode}'. Choose from STRICT, GUARDED, or OFF."

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {}
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["privacy_mode"] = mode_clean
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return f"Privacy mode successfully set to {mode_clean}."

    def redact_text(self, text: str) -> Tuple[str, int]:
        """Redacts sensitive credentials from the text. Returns (sanitized_text, redactions_count)."""
        if not text or not isinstance(text, str):
            return text, 0

        redacted_count = 0
        cleaned = text
        for pattern, replacement in REDACTION_PATTERNS:
            matches = pattern.findall(cleaned)
            if matches:
                redacted_count += len(matches)
                cleaned = pattern.sub(replacement, cleaned)
        return cleaned, redacted_count

    def process_outgoing_payload(self, payload: Any, destination: str = "cloud") -> Tuple[Any, bool, str]:
        """
        Validates and processes payload before sending externally.
        Returns:
            (sanitized_payload, allowed, message)
        """
        mode = self.get_mode()

        if mode == "STRICT" and destination.lower() != "local":
            msg = "[Privacy Guard: STRICT] Cloud transmission blocked. Operating in offline/local-only mode."
            self.log_audit("BLOCKED", destination, payload, redactions=0, notes="Blocked by STRICT mode")
            return payload, False, msg

        if mode == "OFF":
            self.log_audit("ALLOWED", destination, payload, redactions=0, notes="Privacy mode OFF")
            return payload, True, "Allowed"

        # GUARDED mode: Redact secrets
        redactions = 0
        if isinstance(payload, str):
            sanitized, count = self.redact_text(payload)
            redactions += count
            payload_to_send = sanitized
        elif isinstance(payload, dict):
            payload_str = json.dumps(payload)
            sanitized_str, count = self.redact_text(payload_str)
            redactions += count
            try:
                payload_to_send = json.loads(sanitized_str)
            except Exception:
                payload_to_send = payload
        else:
            payload_to_send = payload

        self.log_audit("SANITIZED", destination, payload_to_send, redactions=redactions, notes=f"Guarded (Redacted {redactions})")
        return payload_to_send, True, f"Sanitized with {redactions} redactions"

    def log_audit(self, action: str, destination: str, payload: Any, redactions: int = 0, notes: str = "") -> None:
        """Appends audit event to audit_ledger.jsonl."""
        try:
            sample = str(payload)[:120] if payload is not None else ""
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "destination": destination,
                "redactions": redactions,
                "sample": sample,
                "notes": notes,
            }
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[Privacy Guard] Audit log error: {e}")

    def get_audit_summary(self, limit: int = 10) -> str:
        """Returns recent audit ledger records."""
        if not AUDIT_LOG_FILE.exists():
            return "No audit logs recorded yet."

        try:
            lines = AUDIT_LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
            if not lines:
                return "Audit ledger is empty."

            recent = lines[-limit:]
            entries = []
            for line in reversed(recent):
                try:
                    item = json.loads(line)
                    entries.append(
                        f"[{item.get('timestamp', '')[:19]}] {item.get('action')} -> {item.get('destination')} "
                        f"(Redactions: {item.get('redactions', 0)}) | {item.get('notes', '')}"
                    )
                except Exception:
                    continue

            mode = self.get_mode()
            header = f"=== Privacy Guard Audit Ledger (Mode: {mode}, Total Events: {len(lines)}) ===\n"
            return header + "\n".join(entries)
        except Exception as e:
            return f"Error reading audit ledger: {e}"


# Singleton instance helper
privacy_guard = PrivacyGuard.get_instance()
