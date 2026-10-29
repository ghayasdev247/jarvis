"""
actions/docker_control.py
Docker Management and Container Control for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Docker control: containers, images, logs, compose status via natural language.
- "Ask what is eating memory and it queries the running containers rather than guessing."
- Operations: ps/list, logs, stats, start, stop, restart, images, compose.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _run_docker(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Runs a docker CLI command safely."""
    try:
        proc = subprocess.run(
            ["docker"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        stderr_text = proc.stderr.strip()
        if proc.returncode != 0 and ("error during connect" in stderr_text.lower() or "pipe" in stderr_text.lower()):
            stderr_text = "Docker Desktop daemon is not running. Launch Docker Desktop to use container features."
        return proc.returncode, proc.stdout.strip(), stderr_text
    except FileNotFoundError:
        return 127, "", "Docker executable not found on system. Ensure Docker Desktop is installed and in PATH."
    except Exception as e:
        return 1, "", str(e)


def handle_docker_control(
    action: str = "ps",
    container: Optional[str] = None,
    tail: int = 50,
    all_containers: bool = False,
    player=None,
    speak=None,
) -> str:
    """Dispatches Docker queries and controls."""
    act = (action or "ps").lower().strip()

    log_msg = f"[Docker] Running 'docker {act}'"
    print(log_msg)
    if player:
        player.write_log(log_msg)

    # ── List Containers (ps) ────────────────────────────────────────────────
    if act in ("ps", "list", "containers"):
        cmd = ["ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}"]
        if all_containers:
            cmd.insert(1, "-a")
        rc, out, err = _run_docker(cmd)
        if rc != 0:
            return f"Docker ps failed: {err}"
        return f"Docker Containers:\n{out}" if out else "No containers found."

    # ── Memory and CPU stats ────────────────────────────────────────────────
    elif act in ("stats", "memory", "top", "resource"):
        # docker stats --no-stream shows current memory and CPU snapshot
        cmd = ["stats", "--no-stream", "--format", "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}"]
        if container:
            cmd.append(container)
        rc, out, err = _run_docker(cmd, timeout=35)
        if rc != 0:
            return f"Docker stats failed: {err}"
        return f"Docker Resource Utilization (Memory & CPU):\n{out}" if out else "No running containers found to inspect stats."

    # ── Logs ────────────────────────────────────────────────────────────────
    elif act == "logs":
        if not container:
            return "Please specify container name or ID to view logs."
        cmd = ["logs", f"--tail={tail}", container]
        rc, out, err = _run_docker(cmd, timeout=30)
        output = out or err
        if not output:
            return f"No logs found for container '{container}'."
        # Truncate if long
        log_sample = output[-2500:] if len(output) > 2500 else output
        return f"Logs for {container} (tail {tail}):\n{log_sample}"

    # ── Start / Stop / Restart ─────────────────────────────────────────────
    elif act == "start":
        if not container:
            return "Please specify container to start."
        rc, out, err = _run_docker(["start", container])
        return f"Started container: {out or container}" if rc == 0 else f"Failed to start: {err}"

    elif act == "stop":
        if not container:
            return "Please specify container to stop."
        rc, out, err = _run_docker(["stop", container])
        return f"Stopped container: {out or container}" if rc == 0 else f"Failed to stop: {err}"

    elif act == "restart":
        if not container:
            return "Please specify container to restart."
        rc, out, err = _run_docker(["restart", container])
        return f"Restarted container: {out or container}" if rc == 0 else f"Failed to restart: {err}"

    # ── Images ─────────────────────────────────────────────────────────────
    elif act == "images":
        rc, out, err = _run_docker(["images", "--format", "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"])
        return f"Docker Images:\n{out}" if rc == 0 else f"Failed to list images: {err}"

    # ── Compose ────────────────────────────────────────────────────────────
    elif act == "compose":
        rc, out, err = _run_docker(["compose", "ps"])
        return f"Docker Compose Services:\n{out}" if rc == 0 else f"Compose check error: {err}"

    return (
        f"Unknown docker action '{action}'. Choose from: 'ps', 'stats' (check memory/cpu), "
        "'logs', 'start', 'stop', 'restart', 'images', 'compose'."
    )


def docker_control_action(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "ps")
    container = parameters.get("container")
    tail = int(parameters.get("tail", 50))
    all_containers = bool(parameters.get("all_containers", False))
    return handle_docker_control(
        action=action,
        container=container,
        tail=tail,
        all_containers=all_containers,
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "docker_control",
    "description": (
        "Controls Docker containers, images, and resource telemetry: list running/all containers (ps), "
        "check memory and CPU usage per container (stats), view container logs, start/stop/restart containers, "
        "list images, and check docker-compose status."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Docker action: 'ps' (list containers), 'stats' (inspect memory/CPU load), 'logs', 'start', 'stop', 'restart', 'images', or 'compose'.",
            },
            "container": {
                "type": "STRING",
                "description": "Container name or ID for logs, stats, start, stop, or restart.",
            },
            "tail": {
                "type": "INTEGER",
                "description": "Number of recent log lines to retrieve (default 50).",
            },
            "all_containers": {
                "type": "BOOLEAN",
                "description": "Whether to list all containers including stopped ones (default false).",
            },
        },
        "required": ["action"],
    },
    "handler": docker_control_action,
}
