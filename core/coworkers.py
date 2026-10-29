"""
core/coworkers.py — Multi-Agent Co-Worker System for JARVIS.

Defines 4 autonomous AI co-workers who serve under JARVIS's command:
1. FRIDAY  — Operations & Web Specialist (Downloads, Scraping, Browser, System Monitoring)
2. EDITH   — Security & Tactical Control (Defense, Camera, Permissions, Alerts)
3. HOMER   — Architecture & Code Specialist (Programming, Scripts, File Processing, Bug Fixing)
4. JOCASTA — Intelligence & Knowledge Analyst (Research, Flight, Weather, News, Deep Analysis)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class CoWorker:
    id: str
    name: str
    title: str
    specialty: str
    color_hex: str
    voice_name: str = "Aoede"
    status: str = "IDLE"  # IDLE, ACTIVE, WORKING, STANDBY
    current_task: str = "Standing by for JARVIS"
    completed_tasks: int = 0
    activity_log: List[str] = field(default_factory=list)

    def set_status(self, status: str, task: str = ""):
        self.status = status
        if task:
            self.current_task = task
            self.activity_log.append(f"[{time.strftime('%H:%M:%S')}] {task}")
            if len(self.activity_log) > 20:
                self.activity_log.pop(0)

    def finish_task(self, summary: str = "Task completed"):
        self.status = "IDLE"
        self.completed_tasks += 1
        self.current_task = f"Completed: {summary[:35]}"
        self.activity_log.append(f"[{time.strftime('%H:%M:%S')}] ✓ {summary}")
        if len(self.activity_log) > 20:
            self.activity_log.pop(0)


# Initialize the 4 Co-Workers under JARVIS
from memory.config_manager import get_coworker_voice, save_coworker_voice

COWORKERS: Dict[str, CoWorker] = {
    "friday": CoWorker(
        id="friday",
        name="F.R.I.D.A.Y",
        title="Operations & Web Division",
        specialty="Web Automation, Browser, Downloads & Sys-Ops",
        color_hex="#00d4ff",  # Cyan Blue
        voice_name=get_coworker_voice("friday"),
        status="IDLE",
        current_task="Monitoring networks and download queues",
    ),
    "edith": CoWorker(
        id="edith",
        name="E.D.I.T.H",
        title="Tactical Security & Vision",
        specialty="Hardware Control, Vision, Camera & Defense",
        color_hex="#ff4455",  # Crimson Red
        voice_name=get_coworker_voice("edith"),
        status="IDLE",
        current_task="Perimeter cameras & system integrity secure",
    ),
    "homer": CoWorker(
        id="homer",
        name="H.O.M.E.R",
        title="Engineering & Code Architecture",
        specialty="Software Dev, File Operations, Scripts & Automation",
        color_hex="#00ffaa",  # Cyber Emerald Green
        voice_name=get_coworker_voice("homer"),
        status="IDLE",
        current_task="Code compiler & script engine standby",
    ),
    "jocasta": CoWorker(
        id="jocasta",
        name="J.O.C.A.S.T.A",
        title="Intelligence & Data Analytics",
        specialty="Research, Information Synthesis, Web Intel & Reports",
        color_hex="#ffaa00",  # Amber Gold
        voice_name=get_coworker_voice("jocasta"),
        status="IDLE",
        current_task="Knowledge base synchronized",
    ),
}


class CoWorkerManager:
    """Singleton manager for JARVIS's subordinates."""
    _instance: Optional[CoWorkerManager] = None
    _callbacks: List[Any] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._coworkers = COWORKERS
        return cls._instance

    @property
    def coworkers(self) -> Dict[str, CoWorker]:
        return self._coworkers

    def get_coworker(self, name_or_id: str) -> Optional[CoWorker]:
        key = name_or_id.lower().replace(".", "").strip()
        for k, cw in self._coworkers.items():
            if k == key or cw.name.lower().replace(".", "") == key or key in cw.name.lower():
                return cw
        return None

    def register_listener(self, cb):
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def notify(self):
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass

    def set_coworker_voice(self, worker_id: str, voice_name: str) -> bool:
        cw = self.get_coworker(worker_id)
        if not cw:
            return False
        cw.voice_name = voice_name
        save_coworker_voice(cw.id, voice_name)
        self.notify()
        return True

    def assign_task(self, worker_id: str, task: str) -> str:
        cw = self.get_coworker(worker_id)
        if not cw:
            return f"Error: Co-worker '{worker_id}' not found."
        cw.set_status("ACTIVE", task)
        self.notify()
        return f"{cw.name} acknowledged JARVIS's order: '{task}' (Status: ACTIVE)."

    def complete_task(self, worker_id: str, result: str) -> str:
        cw = self.get_coworker(worker_id)
        if not cw:
            return f"Error: Co-worker '{worker_id}' not found."
        cw.finish_task(result)
        self.notify()
        return f"{cw.name} reported task complete to JARVIS: '{result}'."


def get_manager() -> CoWorkerManager:
    return CoWorkerManager()

