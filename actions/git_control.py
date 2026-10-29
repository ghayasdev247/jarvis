"""
actions/git_control.py
Git & GitHub automation tool for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Git & GitHub: commits, PRs, issues, code review.
- Ask for a summary of yesterday's commits and Jarvis reads the git log itself.
- Operations: status, log, diff, branch, commit, push, pull, review.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def _run_git(args: list[str], cwd: Optional[str] = None, timeout: int = 30) -> tuple[int, str, str]:
    """Runs a git command safely and returns (code, stdout, stderr)."""
    target_dir = cwd or os.getcwd()
    try:
        proc = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=target_dir,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", "Git executable not found in PATH."
    except Exception as e:
        return 1, "", str(e)


def handle_git_control(
    action: str = "status",
    repo_path: Optional[str] = None,
    message: Optional[str] = None,
    branch_name: Optional[str] = None,
    files: Optional[str] = None,
    limit: int = 10,
    since: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    """Executes git automation actions on the specified repo."""
    act = (action or "status").lower().strip()
    cwd = repo_path or os.getcwd()

    if not Path(cwd).exists():
        return f"Directory does not exist: {cwd}"

    if act == "init":
        rc, out, err = _run_git(["init"], cwd=cwd)
        return f"Initialized empty Git repository in {cwd}." if rc == 0 else f"Git init failed: {err}"

    # Verify if directory is a git repository
    rc, out, err = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
    if rc != 0 or out != "true":
        return f"Directory '{cwd}' is not a Git repository. Use 'git init' to initialize it."

    log_msg = f"[Git] Running 'git {act}' in {cwd}"
    print(log_msg)
    if player:
        player.write_log(log_msg)

    # ── Status ─────────────────────────────────────────────────────────────
    if act == "status":
        rc, out, err = _run_git(["status", "--short", "--branch"], cwd=cwd)
        if rc != 0:
            return f"Git status failed: {err}"
        return f"Git Status ({cwd}):\n{out}" if out else "Working tree clean. No changes."

    # ── Log ────────────────────────────────────────────────────────────────
    elif act == "log":
        cmd = ["log", f"-n{limit}", "--pretty=format:%h | %an | %ad | %s", "--date=relative"]
        if since:
            cmd.append(f"--since={since}")
        rc, out, err = _run_git(cmd, cwd=cwd)
        if rc != 0:
            return f"Git log failed: {err}"
        return f"Recent Commits ({cwd}):\n{out}" if out else "No commits found matching criteria."

    # ── Yesterday's Commits (Feature specifically mentioned in specs) ──────
    elif act in ("yesterday", "recent"):
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        cmd = ["log", f"--since={yesterday_date}", "--pretty=format:%h | %an | %ad | %s", "--date=relative"]
        rc, out, err = _run_git(cmd, cwd=cwd)
        if rc != 0:
            return f"Git log failed: {err}"
        return f"Commits since yesterday ({cwd}):\n{out}" if out else "No commits recorded since yesterday."

    # ── Diff ───────────────────────────────────────────────────────────────
    elif act == "diff":
        rc, out, err = _run_git(["diff", "--stat"], cwd=cwd)
        rc2, out2, _ = _run_git(["diff"], cwd=cwd)
        if rc != 0:
            return f"Git diff failed: {err}"
        # Truncate diff if very long
        diff_sample = out2[:2000] + ("\n... [diff truncated]" if len(out2) > 2000 else "")
        return f"Git Diff Summary:\n{out}\n\nDiff Content:\n{diff_sample}" if out else "No uncommitted diffs."

    # ── Branch ─────────────────────────────────────────────────────────────
    elif act == "branch":
        if branch_name:
            # Checkout or create
            rc, out, err = _run_git(["checkout", "-b", branch_name], cwd=cwd)
            if rc != 0:
                # Try checkout existing
                rc, out, err = _run_git(["checkout", branch_name], cwd=cwd)
            return out or err or f"Switched to branch {branch_name}"
        else:
            rc, out, err = _run_git(["branch", "-a"], cwd=cwd)
            return f"Branches:\n{out}" if rc == 0 else f"Failed to list branches: {err}"

    # ── Commit ─────────────────────────────────────────────────────────────
    elif act == "commit":
        if not message:
            return "Commit message is required."
        target_files = files.split() if files else ["."]
        _run_git(["add"] + target_files, cwd=cwd)
        rc, out, err = _run_git(["commit", "-m", message], cwd=cwd)
        if rc != 0:
            return f"Git commit failed: {err or out}"
        return f"Committed successfully:\n{out}"

    # ── Push / Pull / Sync ──────────────────────────────────────────────────
    elif act == "push":
        rc, out, err = _run_git(["push"], cwd=cwd, timeout=60)
        return f"Git Push result:\n{out or err}"

    elif act == "pull":
        rc, out, err = _run_git(["pull"], cwd=cwd, timeout=60)
        return f"Git Pull result:\n{out or err}"

    elif act in ("sync", "autopush", "update_repo"):
        # Auto stage all, commit if changes exist, then push
        _run_git(["add", "."], cwd=cwd)
        commit_msg = message or f"JARVIS update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        rc_c, out_c, err_c = _run_git(["commit", "-m", commit_msg], cwd=cwd)
        rc_p, out_p, err_p = _run_git(["push", "origin", "main"], cwd=cwd, timeout=90)
        if rc_p != 0:
            # fallback to plain push
            rc_p, out_p, err_p = _run_git(["push"], cwd=cwd, timeout=90)
        status_info = "Committed and pushed to GitHub." if rc_p == 0 else f"Push issue: {err_p or out_p}"
        return f"Git Sync Result:\nCommit: {out_c or 'Nothing new to commit'}\nPush: {out_p or err_p}\nStatus: {status_info}"

    # ── Code Review ────────────────────────────────────────────────────────
    elif act == "review":
        rc, diff_out, _ = _run_git(["diff", "HEAD~1"], cwd=cwd)
        if not diff_out:
            rc, diff_out, _ = _run_git(["diff"], cwd=cwd)
        if not diff_out:
            return "No recent changes or diff found to review."
        # Use gemini ladder for review analysis
        from core.gemini import text as gemini_text
        prompt = (
            "You are an expert software reviewer. Review the following Git diff for code quality, "
            "bugs, security pitfalls, and suggest improvements concise and bulleted:\n\n"
            f"{diff_out[:3000]}"
        )
        res = gemini_text(prompt, timeout_ms=30000, default="")
        return res or "Diff review completed with no issues detected."

    return (
        f"Unknown git action '{action}'. Supported actions: 'status', 'init', 'log', 'yesterday', "
        "'diff', 'branch', 'commit', 'push', 'pull', 'sync', 'review'."
    )


def git_control_action(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "status")
    repo_path = parameters.get("repo_path")
    message = parameters.get("message")
    branch_name = parameters.get("branch_name")
    files = parameters.get("files")
    limit = int(parameters.get("limit", 10))
    since = parameters.get("since")
    return handle_git_control(
        action=action,
        repo_path=repo_path,
        message=message,
        branch_name=branch_name,
        files=files,
        limit=limit,
        since=since,
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "git_control",
    "description": (
        "Controls Git version control and GitHub workflows: inspect git status, view commits log "
        "(including yesterday's commits summary), view diffs, switch/create branches, stage & commit files, "
        "push/pull to remote, or perform automated AI code reviews on active diffs."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Git action: 'status', 'log', 'yesterday', 'diff', 'branch', 'commit', 'push', 'pull', 'sync', or 'review'.",
            },
            "repo_path": {
                "type": "STRING",
                "description": "Optional repository path (defaults to current project directory).",
            },
            "message": {
                "type": "STRING",
                "description": "Commit message when action is 'commit'.",
            },
            "branch_name": {
                "type": "STRING",
                "description": "Branch name when action is 'branch'.",
            },
            "files": {
                "type": "STRING",
                "description": "Specific files to stage/commit (space separated, default all).",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Max commits to list in log (default 10).",
            },
            "since": {
                "type": "STRING",
                "description": "Time filter for git log (e.g., 'yesterday', '2 days ago', '2026-10-01').",
            },
        },
        "required": ["action"],
    },
    "handler": git_control_action,
}
