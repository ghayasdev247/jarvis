"""
core/self_heal.py — Autonomous Self-Correction, Code Healing & Khud-Mukhtar Problem Solver for JARVIS.

Enables JARVIS and H.O.M.E.R (Engineering Specialist) to autonomously diagnose,
patch, verify, auto-install missing dependencies, and repair errors in the codebase at runtime.
"""
from __future__ import annotations

import ast
import importlib
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

_RECENT_FAILURES: List[Dict[str, Any]] = []
_REPAIR_HISTORY: List[Dict[str, Any]] = []

# Common Python module names mapped to their canonical pip distribution packages
KNOWN_PKG_MAP = {
    "cv2": "opencv-python",
    "PIL": "pillow",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "google.genai": "google-genai",
    "genai": "google-genai",
    "serial": "pyserial",
    "fitz": "pymupdf",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "openwakeword": "openwakeword",
    "sounddevice": "sounddevice",
    "psutil": "psutil",
    "pytube": "pytube",
    "yt_dlp": "yt-dlp",
    "requests": "requests",
    "aiohttp": "aiohttp",
    "numpy": "numpy",
}


def record_failure(source: str, error: str, tb: str = "") -> None:
    """Record a runtime failure or tool crash for autonomous analysis."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "error": str(error),
        "traceback": tb or traceback.format_exc(),
    }
    _RECENT_FAILURES.append(entry)
    if len(_RECENT_FAILURES) > 30:
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
    if (BASE_DIR / "actions" / f"{raw}.py").exists():
        return BASE_DIR / "actions" / f"{raw}.py"

    # Try inside core/
    cand_core = BASE_DIR / "core" / raw
    if cand_core.exists():
        return cand_core
    if (BASE_DIR / "core" / f"{raw}.py").exists():
        return BASE_DIR / "core" / f"{raw}.py"

    # Search by filename
    matches = list(BASE_DIR.glob(f"**/{Path(raw).name}"))
    if matches:
        return matches[0]

    return None


def auto_install_missing_dependency(error_text: str, player=None) -> tuple[bool, str]:
    """
    Detects missing Python package from error message and installs it automatically via pip.
    """
    patterns = [
        r"No module named ['\"]([a-zA-Z0-9_\-\.]+)['\"]",
        r"ModuleNotFoundError:\s+No module named\s+['\"]([a-zA-Z0-9_\-\.]+)['\"]",
        r"cannot import name ['\"]?[a-zA-Z0-9_]+['\"]? from ['\"]([a-zA-Z0-9_\-\.]+)['\"]",
    ]
    pkg_candidate = None
    for pat in patterns:
        m = re.search(pat, error_text, re.IGNORECASE)
        if m:
            pkg_candidate = m.group(1).split(".")[0].strip()
            break

    if not pkg_candidate:
        return False, "No missing module identified from error text."

    pkg_name = KNOWN_PKG_MAP.get(pkg_candidate.lower(), pkg_candidate.replace("_", "-"))

    log_msg = f"[Autonomous Self-Heal] Auto-installing missing dependency: '{pkg_name}'..."
    print(log_msg)
    if player and hasattr(player, "write_log"):
        player.write_log(log_msg)

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg_name, "--default-timeout=120"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        if proc.returncode == 0:
            success_msg = f"Successfully installed dependency '{pkg_name}' via pip."
            print(f"[Autonomous Self-Heal] ✓ {success_msg}")
            if player and hasattr(player, "write_log"):
                player.write_log(f"[Autonomous Self-Heal] ✓ {success_msg}")
            return True, success_msg
        else:
            err = proc.stderr.strip() or proc.stdout.strip()
            return False, f"Failed to install '{pkg_name}': {err[:200]}"
    except Exception as e:
        return False, f"Exception while auto-installing '{pkg_name}': {e}"


def reload_action_module(file_path: Path) -> Optional[Any]:
    """Hot-reloads a patched Python file in sys.modules so the changes take effect immediately."""
    stem = file_path.stem
    # Check by absolute file path
    for mod_name, mod in list(sys.modules.items()):
        if getattr(mod, "__file__", None):
            try:
                if Path(mod.__file__).resolve() == file_path.resolve():
                    importlib.reload(mod)
                    return mod
            except Exception:
                pass

    # Check common module names
    for mod_name in (f"actions.{stem}", f"core.{stem}", stem):
        if mod_name in sys.modules:
            try:
                return importlib.reload(sys.modules[mod_name])
            except Exception:
                pass

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
        player.write_log(f"[Khud-Mukhtar Self-Heal] H.O.M.E.R analyzing '{file_path.name}' for autonomous repair...")

    # Formulate prompt for Gemini SMART
    system_prompt = (
        "You are H.O.M.E.R, Chief Code Architect and Autonomous Self-Repair Engine for JARVIS (MARK LV).\n"
        "Your mission is to autonomously resolve any defect, bug, or execution problem in a Python file.\n"
        "RULES:\n"
        "1. Output the COMPLETE, FULL working Python code inside a single ```python ``` code block.\n"
        "2. Do NOT truncate, do NOT use placeholders like '# ... rest of code'. The code must be completely executable.\n"
        "3. Ensure 100% valid Python 3.12 syntax.\n"
        "4. Fix the specific issue described while preserving all existing functions, tools, and UI logic.\n"
        "5. If the issue is Windows executable lookup (WinError 2), use sys.executable, check PATH, or use shell=True safely.\n"
        "6. Explain what was fixed briefly before the code block."
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
        resp = gemini.call(user_prompt, tier=gemini.SMART, config=config, timeout_ms=35000)
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

    # Create safety backup (.bak) in config/backups/ or alongside file
    backup_dir = BASE_DIR / "config" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{file_path.stem}_{int(time.time())}{file_path.suffix}.bak"
    try:
        shutil.copy2(file_path, backup_path)
    except Exception:
        pass

    # Apply the fix safely
    try:
        file_path.write_text(fixed_code, encoding="utf-8")
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Failed to write patched code to '{file_path.name}': {e}"
        }

    # Hot reload module in running runtime
    reloaded_mod = reload_action_module(file_path)

    repair_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file": str(file_path),
        "issue": issue_description,
        "backup": str(backup_path),
        "status": "APPLIED",
        "reloaded": bool(reloaded_mod),
    }
    _REPAIR_HISTORY.append(repair_entry)

    if player and hasattr(player, "write_log"):
        player.write_log(f"[Khud-Mukhtar Self-Heal] ✓ Autonomous repair applied to '{file_path.name}' & hot-reloaded.")

    return {
        "status": "SUCCESS",
        "file": str(file_path.name),
        "full_path": str(file_path),
        "message": f"File '{file_path.name}' successfully patched, verified, and hot-reloaded by H.O.M.E.R.",
        "backup_created": str(backup_path.name) if backup_path.exists() else "None",
        "module": reloaded_mod,
    }


def is_critical_failure(output_or_error: Any) -> bool:
    """Detects if a return value or exception signifies a critical runtime failure that requires healing."""
    if not output_or_error:
        return False
    text = str(output_or_error).lower()
    critical_signals = [
        "winerror",
        "command not found",
        "command execution failed",
        "traceback (most recent call last)",
        "modulenotfounderror",
        "cannot find the file specified",
        "importerror: no module named",
        "syntaxerror: invalid syntax",
        "fatal error:",
        "exception: ",
    ]
    return any(sig in text for sig in critical_signals)


def autonomous_heal_and_execute(
    action_name: str,
    action_record: Any,
    call_fn: Callable[[], str],
    parameters: dict,
    ctx: dict,
    logger: Callable[[str], None] = print,
) -> str:
    """
    Autonomous Execution Engine (Khud-Mukhtar):
    Executes an action, intercepts any failure, automatically analyzes and patches
    the defect (missing package or code bug), hot-reloads, and re-executes seamlessly.
    """
    player = ctx.get("player")
    target_file = getattr(action_record, "file", "") or f"{action_name}.py"

    # Step 1: Initial Attempt
    initial_error = ""
    try:
        result = call_fn()
        if not is_critical_failure(result):
            return result
        initial_error = str(result)
    except Exception as e:
        initial_error = f"{e}\n{traceback.format_exc()}"

    # Step 2: Critical failure detected -> Engage Autonomous Self-Healing
    record_failure(target_file or action_name, initial_error)
    notice = f"[Khud-Mukhtar] Masla detect hua '{action_name}' main. H.O.M.E.R khud hul kar raha hai..."
    logger(notice)
    if player and hasattr(player, "write_log"):
        player.write_log(notice)

    healed = False
    heal_summary = ""

    # Phase A: Check for missing dependencies
    if any(k in initial_error.lower() for k in ("modulenotfounderror", "no module named", "importerror")):
        dep_ok, dep_msg = auto_install_missing_dependency(initial_error, player=player)
        if dep_ok:
            healed = True
            heal_summary = dep_msg

    # Phase B: If not dependency, perform Autonomous Code Diagnosis & Patch
    if not healed:
        repair_res = diagnose_and_repair(
            target_file=target_file,
            issue_description=f"Runtime failure in action '{action_name}': {initial_error[:500]}",
            error_traceback=initial_error,
            player=player,
        )
        if repair_res.get("status") == "SUCCESS":
            healed = True
            heal_summary = repair_res.get("message", "Code repaired successfully.")
            # Update action_record handler with reloaded module handler if available
            reloaded_mod = repair_res.get("module")
            if reloaded_mod:
                new_tool = getattr(reloaded_mod, "TOOL", {})
                new_handler = new_tool.get("handler")
                if callable(new_handler):
                    action_record.handler = new_handler

    # Step 3: Re-Execution after healing
    if healed:
        re_notice = f"[Khud-Mukhtar] Masla kamiyabi say hul hogaya ({heal_summary}). Task dobara execute ho raha hai..."
        logger(re_notice)
        if player and hasattr(player, "write_log"):
            player.write_log(re_notice)

        try:
            retry_result = call_fn()
            if not is_critical_failure(retry_result):
                return (
                    f"✓ [Autonomous Resolution Succeeded] JARVIS encountered an initial defect in '{action_name}', "
                    f"but H.O.M.E.R autonomously repaired it ({heal_summary}) and completed the task:\n\n{retry_result}"
                )
            else:
                return f"[Self-Heal Applied, Retry Output]:\n{retry_result}"
        except Exception as retry_exc:
            return f"[Self-Heal Applied, but Re-execution failed]: {retry_exc}"

    # If could not heal autonomously, return informative error
    return f"Action '{action_name}' failed: {initial_error[:400]}. Failure recorded in self-healing ledger."
