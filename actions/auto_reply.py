"""
actions/auto_reply.py
Auto-Reply Engine for WhatsApp, Messenger, and messaging apps in JARVIS.

Inspired by Jarvis Institute feature specifications:
- Auto-Reply Engine: WhatsApp · Messenger · custom rule engine.
- Automated intelligent replies with schedules, custom templates, and autonomous handling.
- Operations: status, enable/disable, list_rules, add_rule, add_template, list_templates, generate_reply.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
RULES_FILE = CONFIG_DIR / "auto_reply_rules.json"


def _default_config() -> Dict[str, Any]:
    return {
        "enabled": False,
        "ai_smart_reply": True,
        "platforms": ["whatsapp", "messenger", "telegram"],
        "schedule": {
            "mode": "manual",  # "manual", "after_hours", "meetings", "all_day"
            "after_hours_start": "18:00",
            "after_hours_end": "09:00",
        },
        "templates": {
            "busy": "Hello! I am currently focused in a meeting and will get back to you shortly.",
            "away": "Hi there! I am currently away from my desk. I will review your message as soon as I return.",
            "urgent": "Thank you for reaching out. If this is critical, please call me directly.",
        },
        "rules": [
            {
                "trigger_keywords": ["pricing", "cost", "rates"],
                "reply_template": "Thanks for asking about pricing! I'll share our project estimate shortly.",
            },
            {
                "trigger_keywords": ["meeting", "schedule", "call"],
                "reply_template": "I'm available later today. Let me check my calendar and confirm a slot.",
            },
        ],
        "history": [],
    }


def _load_rules() -> Dict[str, Any]:
    if not RULES_FILE.exists():
        cfg = _default_config()
        _save_rules(cfg)
        return cfg
    try:
        data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_config()
        return data
    except Exception:
        return _default_config()


def _save_rules(data: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        RULES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[AutoReply] Error saving rules: {e}")


def handle_auto_reply(
    action: str = "status",
    enabled: Optional[bool] = None,
    template_name: Optional[str] = None,
    template_text: Optional[str] = None,
    keywords: Optional[str] = None,
    incoming_message: Optional[str] = None,
    platform: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    """Dispatches auto-reply operations."""
    act = (action or "status").lower().strip()
    data = _load_rules()

    if act == "status":
        state = "ENABLED (Active)" if data.get("enabled") else "DISABLED (Idle)"
        mode = data.get("schedule", {}).get("mode", "manual")
        rule_count = len(data.get("rules", []))
        tmpl_count = len(data.get("templates", {}))
        platforms = ", ".join(data.get("platforms", []))
        return (
            f"=== Auto-Reply Engine Status ===\n"
            f"State: {state}\n"
            f"Schedule Mode: {mode}\n"
            f"Supported Platforms: {platforms}\n"
            f"Active Templates: {tmpl_count}\n"
            f"Configured Rules: {rule_count}\n"
            f"AI Smart Reply: {'Yes' if data.get('ai_smart_reply') else 'No'}"
        )

    elif act in ("enable", "turn_on", "start"):
        data["enabled"] = True
        _save_rules(data)
        if player:
            player.write_log("SYS: Auto-Reply Engine activated")
        return "Auto-Reply Engine is now ENABLED. JARVIS will manage incoming messages."

    elif act in ("disable", "turn_off", "stop"):
        data["enabled"] = False
        _save_rules(data)
        if player:
            player.write_log("SYS: Auto-Reply Engine deactivated")
        return "Auto-Reply Engine is now DISABLED."

    elif act in ("templates", "list_templates"):
        tmpls = data.get("templates", {})
        if not tmpls:
            return "No templates defined."
        lines = ["=== Auto-Reply Templates ==="]
        for k, v in tmpls.items():
            lines.append(f"• [{k}]: \"{v}\"")
        return "\n".join(lines)

    elif act in ("add_template", "set_template"):
        if not template_name or not template_text:
            return "Provide both template_name and template_text."
        data.setdefault("templates", {})[template_name] = template_text
        _save_rules(data)
        return f"Template '{template_name}' saved."

    elif act in ("rules", "list_rules"):
        rules = data.get("rules", [])
        if not rules:
            return "No custom auto-reply rules configured."
        lines = ["=== Auto-Reply Rules ==="]
        for i, r in enumerate(rules, 1):
            kw = ", ".join(r.get("trigger_keywords", []))
            reply = r.get("reply_template", "")
            lines.append(f"{i}. Keywords [{kw}] -> \"{reply}\"")
        return "\n".join(lines)

    elif act == "add_rule":
        if not keywords or not template_text:
            return "Provide keywords (comma separated) and template_text (or reply text)."
        kw_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        data.setdefault("rules", []).append({
            "trigger_keywords": kw_list,
            "reply_template": template_text,
        })
        _save_rules(data)
        return f"Rule added for keywords: {kw_list}"

    elif act in ("generate_reply", "draft_reply", "test"):
        if not incoming_message:
            return "Please provide incoming_message to generate an auto-reply draft."

        msg_lower = incoming_message.lower()

        # 1. Check matching keyword rules
        for rule in data.get("rules", []):
            if any(kw in msg_lower for kw in rule.get("trigger_keywords", [])):
                return f"[Matched Rule Reply]:\n{rule.get('reply_template')}"

        # 2. If AI Smart Reply enabled, synthesize intelligent response
        if data.get("ai_smart_reply", True):
            from core.gemini import text as gemini_text
            prompt = (
                "You are JARVIS replying autonomously on behalf of the user to an incoming chat message. "
                "Draft a polite, professional, and helpful response. Be brief (1-2 sentences max). "
                f"Incoming message: \"{incoming_message}\""
            )
            reply = gemini_text(prompt, timeout_ms=25000, default="")
            if not reply:
                reply = data.get("templates", {}).get("away", "I will get back to you shortly.")
            return f"[AI Synthesized Auto-Reply]:\n{reply}"

        # 3. Fallback to default away template
        return f"[Default Away Reply]:\n{data.get('templates', {}).get('away')}"

    return (
        f"Unknown auto-reply action '{action}'. Choose from: 'status', 'enable', 'disable', "
        "'list_templates', 'add_template', 'list_rules', 'add_rule', 'generate_reply'."
    )


def auto_reply_action(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "status")
    enabled = parameters.get("enabled")
    template_name = parameters.get("template_name")
    template_text = parameters.get("template_text")
    keywords = parameters.get("keywords")
    incoming_message = parameters.get("incoming_message")
    platform = parameters.get("platform")
    return handle_auto_reply(
        action=action,
        enabled=enabled,
        template_name=template_name,
        template_text=template_text,
        keywords=keywords,
        incoming_message=incoming_message,
        platform=platform,
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "auto_reply",
    "description": (
        "Controls JARVIS Auto-Reply Engine for WhatsApp, Facebook Messenger, and messaging apps: "
        "inspect status, enable/disable automated replies, manage scheduled templates (busy, away, meeting), "
        "configure keyword matching rules, or generate AI-synthesized contextual auto-replies for incoming messages."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'status', 'enable', 'disable', 'list_templates', 'add_template', 'list_rules', 'add_rule', or 'generate_reply'.",
            },
            "enabled": {
                "type": "BOOLEAN",
                "description": "True to activate, False to deactivate auto-reply engine.",
            },
            "template_name": {
                "type": "STRING",
                "description": "Template identifier (e.g. 'busy', 'meeting', 'out_of_office').",
            },
            "template_text": {
                "type": "STRING",
                "description": "The reply message body to send.",
            },
            "keywords": {
                "type": "STRING",
                "description": "Comma-separated keywords for rule triggering (e.g. 'urgent, quote, help').",
            },
            "incoming_message": {
                "type": "STRING",
                "description": "Text of the incoming message to generate an auto-reply draft for.",
            },
            "platform": {
                "type": "STRING",
                "description": "Messaging platform (e.g. 'whatsapp', 'messenger', 'telegram').",
            },
        },
        "required": ["action"],
    },
    "handler": auto_reply_action,
}
