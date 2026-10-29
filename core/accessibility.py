"""
core/accessibility.py
WCAG 2.2 AAA Accessibility System and Screen Reader Integration for J.A.R.V.I.S.

Provides complete accessibility for blind and visually impaired users:
- Toggled globally and in-app via Ctrl+F2.
- Screen reader-ready accessible roles, names, and descriptions for all UI elements:
  * Command prompt input box
  * Response & activity log
  * Briefing & document display
  * Holographic HUD & screen status indicators
  * System monitor and action controls
- Ultra-high contrast WCAG AAA compliant visual theme (>7:1 to 21:1 contrast ratio).
- Real-time NVDA screen reader auditory feedback and tactile braille support.
- Full keyboard-first navigation with clear focus outlines, Tab ordering, and hotkeys:
  * Ctrl+F2: Toggle Accessibility AAA Mode
  * Ctrl+L: Jump immediately to Prompt Box
  * Ctrl+R: Read latest JARVIS response aloud
  * Ctrl+H: Read full screen and system status aloud
  * Escape: Interrupt JARVIS speech & dismiss overlays
  * F4: Mute / unmute microphone
"""

from __future__ import annotations

import re
import sys
import threading
from typing import Optional

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QTextEdit, QPushButton,
    QLabel, QSplitter, QScrollBar
)

from memory.config_manager import (
    get_accessibility_mode, save_accessibility_mode,
    get_language_preference,
)


_URDU_RANGE_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")


def is_urdu(text: str) -> bool:
    return bool(_URDU_RANGE_RE.search(text)) if text else False


class AccessibilityManager(QObject):
    """Coordinates WCAG AAA Accessibility Mode and Screen Reader Integration."""

    mode_changed = pyqtSignal(bool)

    # WCAG 2.2 AAA Ultra-High Contrast Stylesheet
    AAA_STYLESHEET = """
        QWidget {
            font-family: 'Segoe UI', 'Consolas', 'Courier New', sans-serif;
            font-size: 13pt;
        }
        QMainWindow, QWidget#centralWidget {
            background-color: #000000 !important;
            color: #FFFFFF !important;
        }
        QLineEdit {
            background-color: #000000 !important;
            color: #FFFFFF !important;
            font-size: 14pt !important;
            font-weight: bold !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 4px !important;
            padding: 6px 10px !important;
        }
        QLineEdit:focus {
            border: 3px solid #FFFF00 !important;
            background-color: #0d0d00 !important;
            color: #FFFFFF !important;
        }
        QTextEdit {
            background-color: #000000 !important;
            color: #FFFFFF !important;
            font-size: 13pt !important;
            line-height: 1.5 !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 4px !important;
            padding: 8px !important;
            selection-background-color: #FFFF00 !important;
            selection-color: #000000 !important;
        }
        QTextEdit:focus {
            border: 3px solid #FFFF00 !important;
        }
        QPushButton {
            background-color: #1a1a1a !important;
            color: #FFFFFF !important;
            font-size: 13pt !important;
            font-weight: bold !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 4px !important;
            padding: 6px 14px !important;
            min-height: 34px !important;
        }
        QPushButton:hover {
            background-color: #333333 !important;
            border-color: #FFFF00 !important;
        }
        QPushButton:focus {
            border: 3px solid #FFFF00 !important;
            background-color: #FFFF00 !important;
            color: #000000 !important;
        }
        QLabel {
            color: #FFFFFF !important;
            background-color: transparent !important;
            font-size: 12pt !important;
        }
        QScrollBar:vertical {
            background: #000000 !important;
            width: 14px !important;
            border: 1px solid #FFFFFF !important;
        }
        QScrollBar::handle:vertical {
            background: #FFFF00 !important;
            border-radius: 3px !important;
            min-height: 30px !important;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px !important;
        }
    """

    def __init__(self):
        super().__init__()
        self._active: bool = get_accessibility_mode()
        self._last_response_text: str = ""
        self._last_announced_text: str = ""
        self._mw = None
        self._last_toggle_time: float = 0.0

        # NVDA Screen Reader Controller Client initialization
        self._nvda_client = None
        self._accessible_output = None
        self._init_screen_reader_drivers()

    def _init_screen_reader_drivers(self):
        """Initializes NVDA Controller Client DLL and accessible_output2 unified driver."""
        if sys.platform != "win32":
            return
        # 1. Try accessible-output2 NVDA / Auto driver
        try:
            import accessible_output2.outputs.nvda as ao_nvda
            self._ao_nvda = ao_nvda.NVDA()
        except Exception:
            self._ao_nvda = None

        try:
            import accessible_output2.outputs.auto as ao_auto
            self._accessible_output = ao_auto.Auto()
        except Exception:
            self._accessible_output = None

        # 2. Try direct NVDA Controller Client DLL
        from pathlib import Path
        dll_candidates = [
            Path(__file__).resolve().parent / "lib" / "nvdaControllerClient64.dll",
            Path(__file__).resolve().parent / "lib" / "nvdaControllerClient32.dll",
            Path(r"C:\Program Files\NVDA\nvdaControllerClient64.dll"),
        ]
        for dll_path in dll_candidates:
            if dll_path.is_file():
                try:
                    import ctypes
                    lib = ctypes.windll.LoadLibrary(str(dll_path))
                    lib.nvdaController_testIfRunning.restype = ctypes.c_long
                    lib.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                    lib.nvdaController_speakText.restype = ctypes.c_long
                    lib.nvdaController_brailleMessage.argtypes = [ctypes.c_wchar_p]
                    lib.nvdaController_brailleMessage.restype = ctypes.c_long
                    self._nvda_client = lib
                    break
                except Exception:
                    pass

    @property
    def is_active(self) -> bool:
        return self._active

    def is_nvda_active(self) -> bool:
        """Check if NVDA screen reader is running and accepting controller calls."""
        if self._ao_nvda:
            try:
                if self._ao_nvda.is_active():
                    return True
            except Exception:
                pass
        if self._nvda_client:
            try:
                if self._nvda_client.nvdaController_testIfRunning() == 0:
                    return True
            except Exception:
                pass
        return False

    def announce(self, text: str, interrupt: bool = False) -> None:
        """Audibly announce text via NVDA screen reader and tactile Braille displays.
        Runs asynchronously in a background worker to keep UI 100% responsive.
        SAPI 5 is completely removed from accessibility mode as requested.
        """
        if not text or not text.strip():
            return

        clean_text = re.sub(r"[*_`#~\[\]\(\)>]", " ", text)
        clean_text = re.sub(r"https?://\S+", "link", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if not clean_text:
            return

        self._last_announced_text = clean_text

        def _speak_worker():
            # 1. Dispatch to NVDA Screen Reader via Controller Client API & Braille
            nvda_spoke = False
            if self._nvda_client:
                try:
                    if self._nvda_client.nvdaController_testIfRunning() == 0:
                        if interrupt:
                            try:
                                self._nvda_client.nvdaController_cancelSpeech()
                            except Exception:
                                pass
                        res = self._nvda_client.nvdaController_speakText(clean_text)
                        if res == 0:
                            nvda_spoke = True
                        self._nvda_client.nvdaController_brailleMessage(clean_text[:120])
                except Exception:
                    pass

            if not nvda_spoke and self._ao_nvda:
                try:
                    if self._ao_nvda.is_active():
                        self._ao_nvda.speak(clean_text, interrupt=interrupt)
                        self._ao_nvda.braille(clean_text[:120])
                        nvda_spoke = True
                except Exception:
                    pass

            # 2. Fire Windows Accessibility System Alert for screen readers (NVDA, Narrator, JAWS)
            try:
                import ctypes
                user32 = ctypes.windll.user32
                # EVENT_SYSTEM_ALERT = 0x0002, EVENT_OBJECT_NAMECHANGE = 0x800C
                user32.NotifyWinEvent(0x800C, 0, 0xFFFFFFFC, 0)
            except Exception:
                pass

        threading.Thread(target=_speak_worker, daemon=True, name="A11yAnnounce").start()

    def set_last_response(self, text: str) -> None:
        self._last_response_text = text
        if self._active:
            # Clean and announce response to screen reader
            clean = re.sub(r"^(JARVIS|AI|System)\s*:\s*", "", text, flags=re.IGNORECASE)
            self.announce(f"JARVIS: {clean}")

    def read_last_response(self) -> None:
        """Reads the most recent JARVIS response aloud."""
        if self._last_response_text:
            self.announce(f"Latest response: {self._last_response_text}", interrupt=True)
        else:
            self.announce("No previous response recorded yet.", interrupt=True)

    def read_screen_status(self, mw=None) -> None:
        """Summarizes the current screen and system state for a blind user (Stonic AI / Jarvis Desktop)."""
        target = mw or self._mw
        status_parts = ["Screen and System Status:"]
        if target:
            hud_state = getattr(target.hud, "state", "READY")
            is_muted = getattr(target, "_muted", False)
            asst_name = getattr(target, "_assistant_name", "JARVIS")
            status_parts.append(f"{asst_name} is currently {hud_state.lower()}.")
            status_parts.append("Microphone is muted." if is_muted else "Microphone is active.")
            if getattr(target, "_current_file", None):
                status_parts.append(f"Loaded file: {target._current_file}.")
            else:
                status_parts.append("No file currently attached.")
            if getattr(target, "_webcam_open", False):
                status_parts.append("Webcam video stream is active.")
            else:
                status_parts.append("Webcam is off.")
        status_parts.append("Prompt box is ready. Press Ctrl+L to focus prompt input. Press Ctrl+R to read latest response. Press Ctrl+F2 to toggle accessibility mode.")
        full_msg = " ".join(status_parts)
        self.announce(full_msg, interrupt=True)

    def toggle(self, main_window) -> bool:
        """Toggles Accessibility AAA mode on or off with debounce protection."""
        import time
        now = time.monotonic()
        if (now - self._last_toggle_time) < 0.40:
            return self._active
        self._last_toggle_time = now

        self._active = not self._active
        save_accessibility_mode(self._active)
        self._mw = main_window

        if self._active:
            self.activate_aaa_mode(main_window)
        else:
            self.deactivate_aaa_mode(main_window)

        self.mode_changed.emit(self._active)
        return self._active

    def activate_aaa_mode(self, mw) -> None:
        """Enables WCAG AAA high contrast visuals, accessible labeling, and auditory announcements."""
        self._mw = mw
        self._active = True

        # 1. Apply high-contrast AAA stylesheet
        mw.setStyleSheet(self.AAA_STYLESHEET)

        # 2. Configure Prompt Box for Accessibility
        if hasattr(mw, "_input"):
            mw._input.setAccessibleName("Command Prompt Input Box")
            mw._input.setAccessibleDescription(
                "Type your question or command for JARVIS here and press Enter. "
                "Press Ctrl+F2 to toggle accessibility mode. Press Escape to clear or interrupt."
            )
            mw._input.setPlaceholderText("Command Input [Accessibility AAA Mode Active — Press Enter to send]…")
            mw._input.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            mw._input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            mw._input.setFocus()

        # 3. Configure Response & Activity Log
        if hasattr(mw, "_log"):
            mw._log.setAccessibleName("JARVIS Conversation Response History and Activity Log")
            mw._log.setAccessibleDescription(
                "Read-only transcript of conversation, responses, and notifications. "
                "Use Up and Down arrow keys to review lines, or press Ctrl+R to hear the latest answer."
            )
            mw._log.setFont(QFont("Consolas", 12))
            mw._log.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 4. Configure Content Display (Briefings & Web Search)
        if hasattr(mw, "_content_display"):
            mw._content_display.setAccessibleName("Detailed Content and Briefing Viewer")
            mw._content_display.setAccessibleDescription(
                "Displays long-form briefings, research results, and document text. "
                "Navigate content using arrow keys or Page Up and Page Down."
            )
            mw._content_display.setFont(QFont("Consolas", 12))
            mw._content_display.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 5. Configure Interactive Buttons
        if hasattr(mw, "_interrupt_btn"):
            mw._interrupt_btn.setAccessibleName("Interrupt JARVIS Button")
            mw._interrupt_btn.setAccessibleDescription("Press Enter or Space, or press Escape anytime, to immediately stop JARVIS speech.")
            mw._interrupt_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        if hasattr(mw, "_drop_zone"):
            mw._drop_zone.setAccessibleName("File Upload and Drop Zone")
            mw._drop_zone.setAccessibleDescription("Press Enter or Space to open file picker and upload a document to JARVIS.")
            mw._drop_zone.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        if hasattr(mw, "_webcam_header_btn"):
            mw._webcam_header_btn.setAccessibleName("Toggle Live Webcam Button")
            mw._webcam_header_btn.setAccessibleDescription("Press Enter or Space, or press F7 anytime, to open or close the live webcam stream on the HUD.")
            mw._webcam_header_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 6. Configure HUD Accessibility
        if hasattr(mw, "hud"):
            mw.hud.setAccessibleName("JARVIS Holographic Face and Screen Status")
            mw.hud.setAccessibleDescription(f"Visual face display and audio meter. Current state: {mw.hud.state}.")

        # 7. Add Screen Reader Status Bar / Label if not present
        if not hasattr(mw, "_a11y_status_bar"):
            mw._a11y_status_bar = QLabel("ACCESSIBILITY AAA MODE ACTIVE  •  [Ctrl+L] Focus Input  •  [Ctrl+R] Read Response  •  [Ctrl+H] Screen Status  •  [Ctrl+U] Telemetry  •  [Ctrl+B] Briefing  •  [F7] Webcam")
            mw._a11y_status_bar.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            mw._a11y_status_bar.setStyleSheet("background-color: #FFFF00 !important; color: #000000 !important; padding: 4px 10px; font-weight: bold;")
            mw._a11y_status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            try:
                mw.centralWidget().layout().insertWidget(1, mw._a11y_status_bar)
            except Exception:
                pass
        if hasattr(mw, "_a11y_status_bar"):
            mw._a11y_status_bar.show()

        # 8. Announce Activation
        announcement = (
            "Accessibility Mode Level Triple A activated with NVDA screen reader integration. "
            "All screens, prompt box, response history, webcam feed, and system controls are now fully screen reader readable "
            "and optimized for keyboard navigation. "
            "Use Tab to navigate, Control plus L to jump to prompt input, Control plus R to read latest response, "
            "Control plus H to hear screen status, Control plus U for system telemetry, Control plus B for briefings, "
            "F7 to toggle live webcam feed, and Escape to interrupt."
        )
        self.announce(announcement, interrupt=True)

        if hasattr(mw, "_log"):
            mw._log.append_log("SYS: [A11Y] WCAG 2.2 AAA Accessibility Mode with NVDA Screen Reader ACTIVATED.")

    def deactivate_aaa_mode(self, mw) -> None:
        """Restores standard visual theme and layout."""
        self._mw = mw
        self._active = False

        # Reset main window stylesheet to default empty
        mw.setStyleSheet("")

        if hasattr(mw, "_a11y_status_bar"):
            mw._a11y_status_bar.hide()

        from ui import C

        if hasattr(mw, "_input"):
            mw._input.setPlaceholderText("Type a command or question…")
            mw._input.setFont(QFont("Courier New", 9))
            mw._input.setStyleSheet(f"""
                QLineEdit {{
                    background: #000d14; color: {C.WHITE};
                    border: 1px solid {C.BORDER}; border-radius: 3px; padding: 3px 7px;
                }}
                QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
            """)

        if hasattr(mw, "_log"):
            mw._log.setFont(QFont("Courier New", 9))
            mw._log.setStyleSheet(f"""
                QTextEdit {{
                    background: {C.PANEL};
                    color: {C.TEXT};
                    border: 1px solid {C.BORDER};
                    border-radius: 4px;
                    padding: 6px;
                    selection-background-color: {C.PRI_GHO};
                }}
                QScrollBar:vertical {{
                    background: {C.BG};
                    width: 8px;
                    border: none;
                }}
                QScrollBar::handle:vertical {{
                    background: {C.BORDER};
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
            """)

        if hasattr(mw, "_content_display"):
            mw._content_display.setFont(QFont("Courier New", 8))
            mw._content_display.setStyleSheet(f"""
                QTextEdit {{
                    background: {C.DARK};
                    color: {C.TEXT};
                    border: 1px solid {C.BORDER};
                    border-radius: 3px;
                    padding: 6px 8px;
                    selection-background-color: {C.PRI_GHO};
                }}
            """)

        announcement = "Accessibility Mode deactivated. Standard visual interface restored."
        self.announce(announcement, interrupt=True)

        if hasattr(mw, "_log"):
            mw._log.append_log("SYS: [A11Y] Accessibility Mode deactivated.")


# Global singleton instance
accessibility_manager = AccessibilityManager()
