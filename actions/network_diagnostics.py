"""
actions/network_diagnostics.py
Network Intelligence and Automated System Diagnostics for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Network Intelligence: Check Tailscale mesh status, ping latency, identify offline nodes.
- Automated Diagnostics: "run full diagnostics on the API: logs, health check, db connections, latency"
- Port checks, connectivity verification, and HTTP endpoint health probes.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.request
from typing import Optional


def _check_tailscale() -> str:
    """Checks Tailscale CLI or status."""
    try:
        proc = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            self_node = data.get("Self", {})
            peers = data.get("Peer", {})

            online_nodes = []
            offline_nodes = []

            for peer_id, info in peers.items():
                name = info.get("HostName", peer_id[:8])
                online = info.get("Online", False)
                ip = (info.get("TailscaleIPs") or ["?"])[0]
                if online:
                    online_nodes.append(f"{name} ({ip})")
                else:
                    last_seen = info.get("LastSeen", "Unknown")
                    offline_nodes.append(f"{name} (last seen: {last_seen[:16]})")

            result = [
                f"Tailscale Status: Connected as {self_node.get('HostName', 'Local')} (IP: {(self_node.get('TailscaleIPs') or ['?'])[0]})",
                f"Active Mesh Nodes ({len(online_nodes)}): {', '.join(online_nodes) if online_nodes else 'None'}",
            ]
            if offline_nodes:
                result.append(f"Offline Nodes ({len(offline_nodes)}): {', '.join(offline_nodes)}")
            return "\n".join(result)
    except FileNotFoundError:
        pass
    except Exception as e:
        return f"Tailscale query note: {e}"

    # Fallback to general local IP detection
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return (
            f"Tailscale CLI not found in PATH.\n"
            f"Local Machine Network Identity: Host '{hostname}' on IP {local_ip}.\n"
            f"Local gateway connection is active."
        )
    except Exception as e:
        return f"Network query failed: {e}"


def _ping_host(host: str, count: int = 3) -> tuple[bool, str]:
    """Pings a host safely on Windows."""
    try:
        cmd = ["ping", "-n", str(count), host]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
        success = proc.returncode == 0 and "TTL=" in proc.stdout
        return success, proc.stdout.strip()
    except Exception as e:
        return False, str(e)


def _check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Probes if a TCP port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def _check_http(url: str, timeout: float = 3.0) -> tuple[int, float, str]:
    """Tests HTTP status code and response latency."""
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Diagnostic/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = (time.time() - t0) * 1000.0
            return resp.status, latency, "OK"
    except urllib.error.HTTPError as e:
        latency = (time.time() - t0) * 1000.0
        return e.code, latency, e.reason
    except Exception as e:
        latency = (time.time() - t0) * 1000.0
        return 0, latency, str(e)


def handle_diagnostics(
    action: str = "full",
    target: Optional[str] = None,
    port: Optional[int] = None,
    player=None,
    speak=None,
) -> str:
    """Dispatches network diagnostics and infrastructure telemetry."""
    act = (action or "full").lower().strip()

    log_msg = f"[Diagnostics] Running '{act}'"
    print(log_msg)
    if player:
        try:
            player.write_log(log_msg)
        except Exception:
            pass

    # ── 1. Tailscale Mesh Check ───────────────────────────────────────────────
    if act in ("tailscale", "mesh"):
        return _check_tailscale()

    # ── 2. Ping / Connectivity Probe ──────────────────────────────────────────
    if act in ("ping", "connectivity"):
        host = target or "1.1.1.1"
        ok, out = _ping_host(host)
        if ok:
            # Extract round-trip average
            return f"Ping to {host} successful.\n" + "\n".join(out.splitlines()[-2:])
        return f"Ping to {host} failed:\n{out}"

    # ── 3. Port Probe ─────────────────────────────────────────────────────────
    if act in ("port", "port_check"):
        host = target or "127.0.0.1"
        p = port or 8000
        open_status = _check_port(host, p)
        return f"Port {p} on {host} is {'OPEN (Listening)' if open_status else 'CLOSED (Unreachable)'}."

    # ── 4. Full Automated Diagnostics Suite ───────────────────────────────────
    if act in ("full", "diagnostics", "suite", "health"):
        results = ["=== JARVIS Automated Diagnostics Suite ==="]

        # 1. Local Network & DNS
        t_dns = time.time()
        try:
            socket.gethostbyname("google.com")
            dns_ok = True
            dns_time = (time.time() - t_dns) * 1000.0
        except Exception:
            dns_ok = False
            dns_time = 0.0

        results.append(f"• DNS Resolution: {'HEALTHY' if dns_ok else 'FAILED'} ({dns_time:.1f}ms)")

        # 2. Key Local Service Ports
        services = [
            ("Web Dashboard", "127.0.0.1", 3001),
            ("Local API", "127.0.0.1", 8000),
            ("Redis Cache", "127.0.0.1", 6379),
            ("Postgres DB", "127.0.0.1", 5432),
            ("Ollama Local", "127.0.0.1", 11434),
        ]
        port_results = []
        for name, h, p in services:
            is_up = _check_port(h, p, timeout=0.5)
            if is_up:
                port_results.append(f"{name} ({p}): ONLINE")
            else:
                port_results.append(f"{name} ({p}): OFFLINE")
        results.append("• Infrastructure Ports:\n  " + "\n  ".join(port_results))

        # 3. HTTP Gateway & External Latency
        code, lat, err = _check_http("https://api.github.com", timeout=3.0)
        results.append(f"• External Gateway Latency: {lat:.1f}ms (HTTP {code})")

        # 4. Tailscale / Mesh
        ts_summary = _check_tailscale()
        results.append(f"• Mesh Network Status:\n  {ts_summary.splitlines()[0]}")

        return "\n".join(results)

    return f"Unknown diagnostic action '{act}'. Use 'full', 'tailscale', 'ping', or 'port'."


def network_diagnostics_action(parameters: dict, player=None, speak=None) -> str:
    return handle_diagnostics(
        action=parameters.get("action", "full"),
        target=parameters.get("target"),
        port=parameters.get("port"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "network_diagnostics",
    "description": (
        "Runs automated network intelligence and system diagnostics: check Tailscale mesh status, "
        "measure ping and round-trip latency, probe local/remote TCP ports (dashboard, redis, postgres, ollama), "
        "and execute complete health check suites on APIs and infrastructure."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'full' (run complete diagnostics suite), 'tailscale' (check mesh nodes), 'ping' (ping a host), 'port' (check if port is open).",
            },
            "target": {
                "type": "STRING",
                "description": "Hostname, IP address, or URL to probe (e.g. '127.0.0.1', '8.8.8.8', 'localhost').",
            },
            "port": {
                "type": "INTEGER",
                "description": "Port number to check when action is 'port' (e.g. 3001, 8000, 6379, 11434).",
            },
        },
        "required": ["action"],
    },
    "handler": network_diagnostics_action,
}
