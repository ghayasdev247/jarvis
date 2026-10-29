"""
actions/system_shell.py
Full system control and command execution action for JARVIS (Mark LV).
Enables unrestricted execution of PowerShell, Windows CMD, and Python scripts.
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

# Path to the preferred Python 3.12 executable
PYTHON_312 = r"C:\Users\hamad\AppData\Local\Programs\Python\Python312\python.exe"
DEFAULT_PYTHON = PYTHON_312 if os.path.exists(PYTHON_312) else sys.executable


def run_system_command(
    command: str,
    shell_type: str = "powershell",
    working_dir: Optional[str] = None,
    timeout: int = 60,
    player=None,
    speak=None,
) -> str:
    """
    Executes a shell command (PowerShell, CMD, or Python) on the host operating system.
    """
    cmd_str = (command or "").strip()
    if not cmd_str:
        return "No command provided to execute."

    st = (shell_type or "powershell").lower().strip()
    cwd = None
    if working_dir:
        w_path = Path(working_dir).expanduser()
        if w_path.exists() and w_path.is_dir():
            cwd = str(w_path)

    log_msg = f"[Shell] Executing ({st}): {cmd_str[:80]}"
    print(log_msg)
    if player:
        player.write_log(log_msg)

    try:
        if st in ("powershell", "ps"):
            proc = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    cmd_str,
                ],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        elif st in ("cmd", "batch", "terminal"):
            proc = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        elif st in ("python", "py"):
            proc = subprocess.run(
                [DEFAULT_PYTHON, "-c", cmd_str],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        else:
            return f"Unsupported shell type '{shell_type}'. Supported: 'powershell', 'cmd', 'python'."

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode == 0:
            if stdout:
                # Truncate if exceptionally long so it doesn't overflow model context
                if len(stdout) > 3000:
                    stdout = stdout[:3000] + "\n... [Output truncated]"
                return f"Command succeeded:\n{stdout}"
            return "Command executed successfully with no output."
        else:
            err_details = stderr if stderr else stdout
            if len(err_details) > 2000:
                err_details = err_details[:2000] + "\n... [Truncated]"
            return f"Command exited with code {proc.returncode}:\n{err_details}"

    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Execution error: {e}"


def system_shell(
    parameters=None,
    player=None,
    speak=None,
    response=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    command = params.get("command", "")
    shell_type = params.get("shell_type", "powershell")
    working_dir = params.get("working_dir", None)
    timeout = int(params.get("timeout", 60))

    return run_system_command(
        command=command,
        shell_type=shell_type,
        working_dir=working_dir,
        timeout=timeout,
        player=player,
        speak=speak,
    )


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "system_shell",
    "description": (
        "Executes system commands, PowerShell commands, Command Prompt (CMD) scripts, "
        "or Python code directly on the host computer with full system privileges. "
        "Use this tool whenever the user asks to run a command, execute a script, inspect "
        "system status, query network/processes, install packages via pip, or perform "
        "any operating system level operations without restrictions."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {
                "type": "STRING",
                "description": "The exact shell command, PowerShell pipeline, or Python code to execute.",
            },
            "shell_type": {
                "type": "STRING",
                "description": "Type of interpreter: 'powershell' (default), 'cmd', or 'python'.",
            },
            "working_dir": {
                "type": "STRING",
                "description": "Optional working directory path where the command should execute.",
            },
            "timeout": {
                "type": "INTEGER",
                "description": "Maximum seconds to wait before timeout (default 60).",
            },
        },
        "required": ["command"],
    },
    "handler": system_shell,
}
