"""
actions/self_correction.py — Autonomous Self-Correction, Health Audit & Problem Solver Action (Khud-Mukhtar).

Enables JARVIS and H.O.M.E.R to inspect errors, modify source code, install missing
packages, verify syntax, and heal defects autonomously without requiring human intervention.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from typing import Optional

from core.self_heal import (
    diagnose_and_repair,
    get_recent_failures,
    get_repair_history,
    auto_install_missing_dependency,
    BASE_DIR,
)


def run_system_health_audit(player=None) -> str:
    """Audits all action modules, checks for syntax errors or broken imports, and auto-repairs them."""
    actions_dir = BASE_DIR / "actions"
    issues_found = []
    repaired = []

    for py_file in sorted(actions_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            code = py_file.read_text(encoding="utf-8")
            ast.parse(code, filename=str(py_file))
        except SyntaxError as e:
            issues_found.append(f"{py_file.name}: SyntaxError at line {e.lineno}")
            rep = diagnose_and_repair(
                target_file=str(py_file),
                issue_description=f"SyntaxError at line {e.lineno}: {e.msg}",
                player=player
            )
            if rep.get("status") == "SUCCESS":
                repaired.append(py_file.name)
        except Exception as e:
            issues_found.append(f"{py_file.name}: {e}")

    failures = get_recent_failures()
    summary = [
        "JARVIS Autonomous System Audit (H.O.M.E.R):",
        f"• Files Scanned: {len(list(actions_dir.glob('*.py')))}",
        f"• Recent Runtime Failures Logged: {len(failures)}",
    ]
    if issues_found:
        summary.append(f"• Issues Detected: {', '.join(issues_found)}")
    else:
        summary.append("• Code Health: 100% Valid Syntax & Clean Tree.")

    if repaired:
        summary.append(f"• Autonomously Repaired: {', '.join(repaired)}")

    return "\n".join(summary)


def self_correct_code(
    parameters: dict = None,
    target_file: str = "",
    issue_description: str = "",
    error_traceback: str = "",
    package_name: str = "",
    player=None,
    speak=None,
    **kwargs
) -> str:
    """Diagnose, install packages, and autonomously patch files in the JARVIS codebase."""
    params = parameters or {}
    act = (params.get("action") or "auto").strip().lower()
    t_file = params.get("target_file") or target_file or ""
    issue = params.get("issue_description") or issue_description or ""
    tb = params.get("error_traceback") or error_traceback or ""
    pkg = params.get("package_name") or package_name or ""

    # Mode 1: Audit all systems
    if act in ("audit", "scan", "check_all", "system_audit"):
        return run_system_health_audit(player=player)

    # Mode 2: Auto-install package
    if pkg or act in ("install", "install_package", "install_dep"):
        target_pkg = pkg or issue
        ok, msg = auto_install_missing_dependency(target_pkg, player=player)
        return msg

    # Mode 3: Target file repair or Recent failure healing
    if not t_file:
        failures = get_recent_failures()
        if failures:
            last_fail = failures[-1]
            t_file = last_fail.get("source", "")
            if not issue:
                issue = last_fail.get("error", "Runtime crash or exception")
            if not tb:
                tb = last_fail.get("traceback", "")
        else:
            # If nothing logged, run health audit
            return run_system_health_audit(player=player)

    if not issue:
        issue = "Fix runtime error, ensure robust exception handling, and verify 100% valid Python syntax."

    # Check if issue is a missing dependency
    if any(k in issue.lower() for k in ("modulenotfounderror", "no module named", "importerror")):
        dep_ok, dep_msg = auto_install_missing_dependency(issue, player=player)
        if dep_ok:
            return f"Autonomous Self-Healing: {dep_msg}"

    result = diagnose_and_repair(
        target_file=t_file,
        issue_description=issue,
        error_traceback=tb,
        player=player
    )

    if result.get("status") == "SUCCESS":
        msg = (
            f"Autonomous Self-Correction Completed by H.O.M.E.R (Khud-Mukhtar):\n"
            f"• Target File: {result.get('file')}\n"
            f"• Result: Verified and hot-reloaded successfully.\n"
            f"• Safety Backup: {result.get('backup_created')}\n"
            f"The defect has been resolved autonomously and the system is operating normally."
        )
    else:
        msg = (
            f"Self-Correction Alert: {result.get('status')}\n"
            f"Details: {result.get('message', 'Unknown failure')}\n"
            f"No unsafe code was applied."
        )

    return msg


TOOL = {
    "name": "self_correct_code",
    "description": (
        "JARVIS's Autonomous Self-Correction and Problem Solver engine, managed by H.O.M.E.R. "
        "Use this tool whenever an action fails, an exception occurs, a script breaks, a package is missing, "
        "or code needs to be modified/repaired autonomously ('apnay maslay khud hul karo', 'fix error', 'audit'). "
        "JARVIS analyzes root causes, installs dependencies, patches code, validates syntax, and heals itself."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Optional action: 'auto' (default), 'audit' (scan all files & heal), or 'install_package'.",
                "enum": ["auto", "audit", "install_package"]
            },
            "target_file": {
                "type": "STRING",
                "description": "Path or filename to repair (e.g. 'actions/dev_agent.py', 'ui.py', or 'actions/web_downloader.py')."
            },
            "issue_description": {
                "type": "STRING",
                "description": "Detailed description of the bug, defect, or missing logic that needs fixing."
            },
            "error_traceback": {
                "type": "STRING",
                "description": "Optional error traceback or exception log."
            },
            "package_name": {
                "type": "STRING",
                "description": "Optional package name to auto-install via pip."
            }
        },
    },
    "handler": self_correct_code,
}
