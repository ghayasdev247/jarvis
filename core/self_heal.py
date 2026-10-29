"""
core/self_heal.py — Autonomous Self-Correction and Code Healing Engine for JARVIS.

Enables JARVIS and H.O.M.E.R (Engineering Specialist) to autonomously diagnose,
patch, verify, and repair errors in the codebase at runtime.
"""
from __future__ import annotations

import ast
import os
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

_RECENT_FAILURES: List[Dict[str, Any]] = []
_REPAIR_HISTORY: List[Dict[str, Any]] = []


def record_failure(source: str, error: str, tb: str = "") -> None:
    """Record a runtime failure or tool crash for autonomous analysis."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "error": str(error),
        "traceback": tb or traceback.format_exc(),
    }
    _RECENT_FAILURES.append(entry)
    if len(_RECENT_FAILURES) > 25:
        _RECENT_FAILURES.pop(0)


def get_recent_failures() -> List[Dict[str, Any]]:
    return list(_RECENT_FAILURES)


def get_repair_history() -> List[Dict[str, Any]]:
    return list(_REPAIR_HISTORY)


def _resolve_file_path(filename_or_path: str) -> Optional[Path]:
    """Safely resolve target file within the project directory."""
    raw = filename_or_path.strip().strip("'\"")
    p = Path(raw)
    if p.is_absolute() and p.exists():
        return p

    # Try relative to BASE_DIR
    cand = BASE_DIR / raw
    if cand.exists():
        return cand

    # Try inside actions/
    cand_actions = BASE_DIR / "actions" / raw
    if cand_actions.exists():
        return cand_actions

    # Try inside core/
    cand_core = BASE_DIR / "core" / raw
    if cand_core.exists():
        return cand_core

    # Search by filename
    matches = list(BASE_DIR.glob(f"**/{Path(raw).name}"))
    if matches:
        return matches[0]

    return None


def diagnose_and_repair(
    target_file: str,
    issue_description: str,
    error_traceback: str = "",
    player=None
) -> Dict[str, Any]:
    """
    Autonomously analyzes code, generates a fix via Gemini SMART tier,
    verifies syntax with ast.parse(), creates a backup, and safely applies the patch.
    """
    file_path = _resolve_file_path(target_file)
    if not file_path or not file_path.exists():
        return {
            "status": "ERROR",
            "message": f"Target file '{target_file}' could not be located in project workspace."
        }

    try:
        current_code = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Failed to read '{file_path.name}': {e}"
        }

    if player and hasattr(player, "write_log"):
        player.write_log(f"[Self-Heal] H.O.M.E.R analyzing '{file_path.name}' for autonomous repair...")

    # Formulate prompt for Gemini SMART
    system_prompt = (
        "You are H.O.M.E.R, Chief Code Architect and Self-Repair Engine for JARVIS (MARK LV).\n"
        "Your task is to fix a bug, error, or defect in a Python file autonomously.\n"
        "RULES:\n"
        "1. Output the COMPLETE, FULL working Python code inside a single ```python ``` code block.\n"
        "2. Do NOT truncate, do NOT use placeholders like '# ... rest of code'. The code must be completely executable.\n"
        "3. Ensure 100% valid Python 3.12 syntax.\n"
        "4. Fix the specific issue described while preserving all existing functions, tools, and UI logic.\n"
        "5. Explain what was fixed briefly before the code block."
    )

    user_prompt = f"""
TARGET FILE: {file_path.name} (Full path: {file_path})
ISSUE DESCRIPTION: {issue_description}
ERROR TRACEBACK:
{error_traceback or 'No traceback provided. Diagnose from issue description and code logic.'}

CURRENT FILE CONTENTS:
```python
{current_code}
```

Analyze the issue, determine the root cause, and provide the complete fixed Python code.
"""

    try:
        from core import gemini
        config = {"system_instruction": system_prompt}
        resp = gemini.call(user_prompt, tier=gemini.SMART, config=config, timeout_ms=30000)
        resp_text = resp.text if hasattr(resp, "text") and resp.text else str(resp or "")
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Gemini code repair model call failed: {e}"
        }

    if not resp_text:
        return {
            "status": "ERROR",
            "message": "AI self-repair model returned an empty response."
        }

    # Extract code block
    fixed_code = ""
    if "```python" in resp_text:
        fixed_code = resp_text.split("```python", 1)[1].split("```", 1)[0].strip()
    elif "```" in resp_text:
        fixed_code = resp_text.split("```", 1)[1].split("```", 1)[0].strip()
    else:
        # Check if the whole text looks like python code
        if "import " in resp_text or "def " in resp_text:
            fixed_code = resp_text.strip()

    if not fixed_code or len(fixed_code) < 30:
        return {
            "status": "ERROR",
            "message": "Could not isolate valid replacement code from AI repair response.",
            "raw_response": resp_text[:300]
        }

    # Strict Syntax Verification via ast.parse
    try:
        ast.parse(fixed_code, filename=str(file_path))
    except SyntaxError as syn_err:
        return {
            "status": "REJECTED",
            "message": f"Syntax verification failed: {syn_err}. Code patch discarded to prevent corruption.",
            "error_line": syn_err.lineno,
            "error_text": syn_err.text,
        }

    # Compile check
    try:
        compile(fixed_code, str(file_path), "exec")
    except Exception as comp_err:
        return {
            "status": "REJECTED",
            "message": f"Code compilation check failed: {comp_err}. Patch rejected."
        }

    # Create safety backup (.bak)
    backup_path = file_path.with_suffix(file_path.suffix + f".bak_{int(time.time())}")
    try:
        shutil.copy2(file_path, backup_path)
    except Exception as e:
        pass  # Proceed even if backup fails

    # Apply the fix safely
    try:
        file_path.write_text(fixed_code, encoding="utf-8")
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Failed to write patched code to '{file_path.name}': {e}"
        }

    repair_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file": str(file_path),
        "issue": issue_description,
        "backup": str(backup_path),
        "status": "APPLIED"
    }
    _REPAIR_HISTORY.append(repair_entry)

    if player and hasattr(player, "write_log"):
        player.write_log(f"[Self-Heal] ✓ Autonomous repair applied to '{file_path.name}' and syntax verified.")

    return {
        "status": "SUCCESS",
        "file": str(file_path.name),
        "full_path": str(file_path),
        "message": f"File '{file_path.name}' successfully patched and syntax verified by H.O.M.E.R.",
        "backup_created": str(backup_path.name) if backup_path.exists() else "None",
    }
