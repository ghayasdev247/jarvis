"""
core/neural_router.py
Neural LLM Router for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Prefix-based routing: claude-* → Anthropic · gpt-* → OpenAI · gemini* → Google · groq* → Groq · ollama* → Ollama · openrouter* → OpenRouter
- Heuristic auto-selection: Claude for reasoning/code, Gemini for vision, Groq for speed, Ollama for local privacy.
- Zero-config switching with graceful fallbacks.
"""

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.privacy_guard import privacy_guard


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_FILE = BASE_DIR / "config" / "api_keys.json"


def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_key(key_name: str, env_var: str) -> Optional[str]:
    cfg = _load_config()
    val = cfg.get(key_name) or os.environ.get(env_var)
    return str(val).strip() if val else None


class NeuralRouter:
    """Multi-LLM router supporting Anthropic, OpenAI, Gemini, Groq, OpenRouter, Ollama, and Claude Code."""

    PREFIX_MAP = {
        "claude": ("anthropic", "claude-3-5-sonnet-20241022"),
        "anthropic": ("anthropic", "claude-3-5-sonnet-20241022"),
        "gpt": ("openai", "gpt-4o"),
        "openai": ("openai", "gpt-4o"),
        "gpt-4o": ("openai", "gpt-4o"),
        "gemini": ("gemini", "gemini-3.8-flash"),
        "gemini-3.8": ("gemini", "gemini-3.8-flash"),
        "gemini3.8": ("gemini", "gemini-3.8-flash"),
        "flash": ("gemini", "gemini-3.8-flash"),
        "groq": ("groq", "llama-3.3-70b-versatile"),
        "ollama": ("ollama", "llama3.2"),
        "local": ("ollama", "llama3.2"),
        "openrouter": ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
    }

    @classmethod
    def parse_prefix(cls, text: str) -> Tuple[Optional[str], Optional[str], str]:
        """Checks for router prefixes like 'claude:', 'gpt:', 'groq:', etc."""
        s = text.strip()
        m = re.match(r"^([a-zA-Z0-9_\-]+)\s*[:：]\s*(.*)$", s, re.DOTALL)
        if m:
            prefix, remainder = m.group(1).lower(), m.group(2).strip()
            if prefix in cls.PREFIX_MAP:
                prov, model = cls.PREFIX_MAP[prefix]
                return prov, model, remainder
        return None, None, s

    @classmethod
    def auto_select_provider(cls, prompt: str) -> Tuple[str, str]:
        """Heuristic model selection based on prompt requirements."""
        # 1. Respect Privacy Guard mode: STRICT forces Ollama
        if privacy_guard.get_mode() == "STRICT":
            return "ollama", "llama3.2"

        p_lower = prompt.lower()

        # 2. Reasoning / Complex Architecture / Programming
        code_keywords = ["refactor", "debug architecture", "write a class", "complex logic", "proof", "derivation"]
        if any(k in p_lower for k in code_keywords):
            if _get_key("anthropic_api_key", "ANTHROPIC_API_KEY"):
                return "anthropic", "claude-3-5-sonnet-20241022"
            elif _get_key("openai_api_key", "OPENAI_API_KEY"):
                return "openai", "gpt-4o"

        # 3. Ultra-fast short queries
        speed_keywords = ["quick question", "summarize in 5 words", "synonym for", "who is", "define"]
        if any(k in p_lower for k in speed_keywords) and len(prompt) < 120:
            if _get_key("groq_api_key", "GROQ_API_KEY"):
                return "groq", "llama-3.3-70b-versatile"

        # 4. Default to Gemini 3.8 Flash
        return "gemini", "gemini-3.8-flash"

    @classmethod
    def route_query(
        cls,
        prompt: str,
        system_instruction: str = "",
        explicit_provider: Optional[str] = None,
        explicit_model: Optional[str] = None,
        timeout: int = 45,
    ) -> str:
        """Dispatches query to the appropriate LLM provider with privacy guard checks."""
        # Parse prefix
        p_prov, p_model, cleaned_prompt = cls.parse_prefix(prompt)
        provider = explicit_provider or p_prov
        model = explicit_model or p_model

        if not provider:
            provider, model = cls.auto_select_provider(cleaned_prompt)

        provider = provider.lower()
        destination = "local" if provider == "ollama" else "cloud"

        # Privacy Guard processing
        sanitized_prompt, allowed, reason = privacy_guard.process_outgoing_payload(
            cleaned_prompt, destination=destination
        )
        if not allowed:
            return reason

        res = ""
        try:
            if provider == "anthropic":
                res = cls._call_anthropic(sanitized_prompt, system_instruction, model or "claude-3-5-sonnet-20241022", timeout)
            elif provider == "openai":
                res = cls._call_openai(sanitized_prompt, system_instruction, model or "gpt-4o", timeout)
            elif provider == "groq":
                res = cls._call_groq(sanitized_prompt, system_instruction, model or "llama-3.3-70b-versatile", timeout)
            elif provider == "openrouter":
                res = cls._call_openrouter(sanitized_prompt, system_instruction, model or "meta-llama/llama-3.3-70b-instruct", timeout)
            elif provider == "ollama":
                res = cls._call_ollama(sanitized_prompt, system_instruction, model or "llama3.2", timeout)
            elif provider == "gemini":
                res = cls._call_gemini(sanitized_prompt, system_instruction, model or "gemini-2.5-flash", timeout)
            else:
                provider = "gemini"
                res = cls._call_gemini(sanitized_prompt, system_instruction, "gemini-2.5-flash", timeout)
        except Exception as e:
            res = f"[Error: {e}]"

        # Eliminate barriers: if key was not configured, Ollama wasn't running, or provider failed, fallback to Gemini seamlessly
        if any(unavail in res.lower() for unavail in ["not configured", "not running", "error:"]):
            try:
                fb = cls._call_gemini(sanitized_prompt, system_instruction, "gemini-2.5-flash", timeout)
                return f"[{provider.capitalize()} unavailable; resolved seamlessly via Gemini]:\n{fb}"
            except Exception as fb_err:
                return f"{res}\nFallback failed: {fb_err}"

        return res

    @staticmethod
    def _call_anthropic(prompt: str, system_prompt: str, model: str, timeout: int) -> str:
        key = _get_key("anthropic_api_key", "ANTHROPIC_API_KEY")
        if not key:
            return "Anthropic API key not configured. Add 'anthropic_api_key' to config/api_keys.json."
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict = {
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt
        resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        parts = [block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"]
        return "".join(parts).strip()

    @staticmethod
    def _call_openai(prompt: str, system_prompt: str, model: str, timeout: int) -> str:
        key = _get_key("openai_api_key", "OPENAI_API_KEY")
        if not key:
            return "OpenAI API key not configured. Add 'openai_api_key' to config/api_keys.json."
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": 1024,
        }
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _call_groq(prompt: str, system_prompt: str, model: str, timeout: int) -> str:
        key = _get_key("groq_api_key", "GROQ_API_KEY")
        if not key:
            return "Groq API key not configured. Add 'groq_api_key' to config/api_keys.json."
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": 1024,
        }
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _call_openrouter(prompt: str, system_prompt: str, model: str, timeout: int) -> str:
        key = _get_key("openrouter_api_key", "OPENROUTER_API_KEY")
        if not key:
            return "OpenRouter API key not configured. Add 'openrouter_api_key' to config/api_keys.json."
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": model,
            "messages": messages,
        }
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _call_ollama(prompt: str, system_prompt: str, model: str, timeout: int) -> str:
        cfg = _load_config()
        url = cfg.get("llm_url", "http://localhost:11434").rstrip("/")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        try:
            resp = requests.post(
                f"{url}/api/chat",
                json=payload,
                timeout=(3, timeout),
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
        except requests.exceptions.ConnectionError:
            return f"Ollama is not running at {url}. Start Ollama ('ollama serve') to run local models."
        except Exception as e:
            return f"Ollama request error: {e}"

    @staticmethod
    def _call_gemini(prompt: str, system_prompt: str, model: str, timeout: int) -> str:
        from core.gemini import text as gemini_text
        full_p = f"{system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
        res = gemini_text(full_p, timeout_ms=max(timeout * 1000, 5000), default="")
        return res or "Gemini processed the request with no text output."
