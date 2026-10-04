"""
Screen Brightness Controller
Provides smooth, animated screen brightness adjustment on Windows.

Primary:  screen-brightness-control library  (pip install screen-brightness-control)
Fallback: PowerShell WMI  (built-in on Windows, no install needed)
"""

import threading
import time
import subprocess
import logging
import warnings
from typing import Optional

# Suppress the harmless EDIDParseError warning from screen-brightness-control
# that occurs on some laptop display drivers (e.g. CMN14C3)
logging.getLogger("screen_brightness_control").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*EDIDParseError.*")

# ── Library availability check ────────────────────────────────────────────────
try:
    import screen_brightness_control as sbc
    SBC_AVAILABLE = True
except ImportError:
    SBC_AVAILABLE = False


class ScreenBrightnessController:
    """
    Controls screen brightness with smooth animated transitions.

    Usage:
        ctrl = ScreenBrightnessController()
        ctrl.set_brightness(80)          # instant
        ctrl.smooth_set(20, duration=1.5) # animated over 1.5 s
    """

    # Brightness level presets
    LEVEL_HIGH   = 90    # user is looking at screen
    LEVEL_MEDIUM = 45    # user detected but not looking
    LEVEL_LOW    = 15    # no user detected (energy saving)

    def __init__(self,
                 min_brightness: int = 5,
                 max_brightness: int = 100,
                 transition_steps: int = 20,
                 simulation_mode: bool = False):
        """
        Args:
            min_brightness:    Lowest brightness percentage allowed.
            max_brightness:    Highest brightness percentage allowed.
            transition_steps:  Number of intermediate steps for smooth animation.
            simulation_mode:   If True, logic runs but actual OS brightness is NOT changed.
        """
        self.min_brightness = max(0, min_brightness)
        self.max_brightness = min(100, max_brightness)
        self.transition_steps = transition_steps
        self.simulation_mode = simulation_mode

        self._current_level: int = self._read_current()
        self._target_level: int = self._current_level
        self._lock = threading.Lock()
        self._transition_thread: Optional[threading.Thread] = None

        mode_str = "SIMULATION" if self.simulation_mode else ("SBC" if SBC_AVAILABLE else "PS WMI")
        print(f"[BrightnessCtrl] Mode: {mode_str}")
        print(f"[BrightnessCtrl] Current brightness: {self._current_level}%")

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def current_brightness(self) -> int:
        """Current brightness level (0–100)."""
        return self._current_level

    def set_brightness(self, level: int) -> bool:
        """
        Set brightness immediately (no animation).

        Args:
            level: Target brightness 0–100.
        Returns:
            True if successful.
        """
        level = self._clamp(level)
        success = self._apply(level)
        if success:
            self._current_level = level
            self._target_level  = level
        return success

    def smooth_set(self, target: int, duration: float = 1.2) -> threading.Thread:
        """
        Gradually animate brightness from current to target over `duration` seconds.
        Non-blocking — runs on a background thread.

        Args:
            target:   Target brightness 0–100.
            duration: Transition time in seconds.
        Returns:
            The background Thread object.
        """
        target = self._clamp(target)
        self._target_level = target

        # Cancel any in-progress transition
        # (thread checks _target_level each step and re-routes if changed)
        t = threading.Thread(
            target=self._animate,
            args=(self._current_level, target, duration),
            daemon=True,
            name="BrightnessTransition",
        )
        self._transition_thread = t
        t.start()
        return t

    def get_recommended_level(self, gaze_result: dict) -> int:
        """
        Return the recommended brightness level based on gaze state.

        Args:
            gaze_result: Dict from GazeDetector.detect_gaze()
        Returns:
            Brightness percentage.
        """
        if gaze_result.get("looking_at_screen"):
            return self.LEVEL_HIGH
        elif gaze_result.get("face_detected"):
            return self.LEVEL_MEDIUM
        else:
            return self.LEVEL_LOW

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _animate(self, start: int, end: int, duration: float):
        """Smoothly transition brightness in background thread."""
        if start == end:
            return

        steps = self.transition_steps
        delay = duration / steps

        for i in range(1, steps + 1):
            # If the target changed externally, abort this animation
            if self._target_level != end:
                break

            t = i / steps              # 0..1
            ease = t * t * (3 - 2 * t)  # smoothstep easing
            level = int(start + (end - start) * ease)
            level = self._clamp(level)

            self._apply(level)
            self._current_level = level
            time.sleep(delay)

    def _clamp(self, level: int) -> int:
        return max(self.min_brightness, min(self.max_brightness, int(level)))

    def _apply(self, level: int) -> bool:
        """Apply brightness to the physical display (if not in simulation mode)."""
        if self.simulation_mode:
            # In simulation mode, we just return True to indicate "logic success"
            return True

        if SBC_AVAILABLE:
            return self._apply_sbc(level)
        else:
            return self._apply_powershell(level)

    def _apply_sbc(self, level: int) -> bool:
        """Use screen-brightness-control library."""
        try:
            sbc.set_brightness(level)
            return True
        except Exception as e:
            print(f"[BrightnessCtrl] sbc error: {e} — trying PowerShell fallback")
            return self._apply_powershell(level)

    def _apply_powershell(self, level: int) -> bool:
        """
        Fallback: set brightness via PowerShell WMI.
        Works on most Windows laptops / monitors with DDC/CI support.
        """
        cmd = (
            f"(Get-WmiObject -Namespace root/WMI "
            f"-Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", cmd],
                capture_output=True, text=True, timeout=3
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[BrightnessCtrl] PowerShell error: {e}")
            return False

    def _read_current(self) -> int:
        """Read current brightness level from OS."""
        if SBC_AVAILABLE:
            try:
                val = sbc.get_brightness()
                if isinstance(val, list):
                    return int(val[0])
                return int(val)
            except Exception:
                pass

        # PowerShell read
        cmd = (
            "(Get-WmiObject -Namespace root/WMI "
            "-Class WmiMonitorBrightness).CurrentBrightness"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", cmd],
                capture_output=True, text=True, timeout=3
            )
            return int(result.stdout.strip())
        except Exception:
            return 70  # safe fallback
