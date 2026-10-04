"""
Gaze-Aware Adaptive Brightness System
======================================
Orchestrates the GazeDetector and ScreenBrightnessController to automatically
adjust screen brightness based on whether the user is looking at the screen.

Run directly:
    python gaze_brightness_system.py

Press  Q  or  Escape  in the preview window to quit.

State machine:
    LOOKING   →  brightness HIGH   (user looking forward)
    AWAY      →  brightness MEDIUM (face detected but gaze away)
    ABSENT    →  brightness LOW    (no face detected)
"""

import cv2
import time
import logging
from typing import Optional

from gaze_module import GazeDetector
from screen_brightness_controller import ScreenBrightnessController

# ── Optional database logging (uses existing smart_energy.db) ─────────────────
try:
    from database import DatabaseManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("GazeBrightnessSystem")


# ─────────────────────────────────────────────────────────────────────────────
# State machine states
# ─────────────────────────────────────────────────────────────────────────────
STATE_LOOKING = "LOOKING"
STATE_AWAY    = "AWAY"
STATE_ABSENT  = "ABSENT"


class GazeBrightnessSystem:
    """
    Main controller — ties gaze detection to adaptive brightness.

    Config params:
        camera_index         : OpenCV camera index (default 0)
        away_delay_sec       : Seconds of look-away before switching to AWAY state
        absent_delay_sec     : Seconds of no-face before switching to ABSENT state
        transition_duration  : Brightness transition animation time in seconds
        show_preview         : Show live camera preview window
        frame_skip           : Process every N-th frame (reduces CPU load)
    """

    def __init__(self,
                 camera_index: int = 0,
                 away_delay_sec: float = 3.0,
                 absent_delay_sec: float = 6.0,
                 transition_duration: float = 1.2,
                 show_preview: bool = True,
                 frame_skip: int = 2):

        self.camera_index       = camera_index
        self.away_delay         = away_delay_sec
        self.absent_delay       = absent_delay_sec
        self.transition_dur     = transition_duration
        self.show_preview       = show_preview
        self.frame_skip         = frame_skip

        # Sub-modules
        self.gaze    = GazeDetector()
        self.display = ScreenBrightnessController()

        # Optional DB
        self.db: Optional[object] = None
        if DB_AVAILABLE:
            try:
                self.db = DatabaseManager("smart_energy.db")
                log.info("Database logging enabled (smart_energy.db)")
            except Exception as e:
                log.warning(f"DB init failed: {e}")

        # State
        self._state                = STATE_LOOKING
        self._last_looking_time    = time.time()
        self._last_face_time       = time.time()
        self._last_brightness      = self.display.current_brightness
        self._last_log_brightness  = -1
        self._stats = {
            "looking_seconds": 0.0,
            "away_seconds":    0.0,
            "absent_seconds":  0.0,
            "state_changes":   0,
            "start_time":      time.time(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Main run loop
    # ─────────────────────────────────────────────────────────────────────────

    def run(self):
        """Start the camera loop. Blocks until the user quits."""
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            log.error(f"Cannot open camera index {self.camera_index}.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS,          15)

        log.info("Camera opened. Press Q or Esc to quit.")
        log.info("─" * 55)

        frame_idx = 0
        last_result = {
            "looking_at_screen": True,
            "face_detected": False,
            "confidence": 0.0,
            "gaze_direction": "unknown",
            "eye_open": False,
        }

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    log.warning("Failed to read frame — retrying…")
                    time.sleep(0.05)
                    continue

                frame_idx += 1

                # ── Run gaze detection every N frames ─────────────────────
                if frame_idx % self.frame_skip == 0:
                    last_result = self.gaze.detect_gaze(frame)
                    self._update_state(last_result)

                # ── Draw overlay ──────────────────────────────────────────
                display_frame = self.gaze.draw_gaze_overlay(frame, last_result)
                display_frame = self._draw_system_hud(display_frame)

                # ── Show preview ──────────────────────────────────────────
                if self.show_preview:
                    cv2.imshow("Gaze-Aware Brightness  [ Q = quit ]", display_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), ord("Q"), 27):  # Q or Esc
                        break

        finally:
            cap.release()
            if self.show_preview:
                cv2.destroyAllWindows()
            self.gaze.release()
            self._print_session_summary()

    # ─────────────────────────────────────────────────────────────────────────
    # State machine
    # ─────────────────────────────────────────────────────────────────────────

    def _update_state(self, result: dict):
        """Update state and trigger brightness changes when state transitions occur."""
        now = time.time()
        looking  = result["looking_at_screen"]
        has_face = result["face_detected"]

        if looking:
            self._last_looking_time = now
            self._last_face_time    = now
        elif has_face:
            self._last_face_time    = now

        # Determine new state
        time_not_looking = now - self._last_looking_time
        time_no_face     = now - self._last_face_time

        if looking:
            new_state = STATE_LOOKING
        elif time_no_face >= self.absent_delay:
            new_state = STATE_ABSENT
        elif time_not_looking >= self.away_delay:
            new_state = STATE_AWAY
        else:
            new_state = self._state   # stay in current state during grace period

        # Track time in each state
        elapsed = now - getattr(self, "_prev_tick", now)
        self._prev_tick = now
        if self._state == STATE_LOOKING:
            self._stats["looking_seconds"] += elapsed
        elif self._state == STATE_AWAY:
            self._stats["away_seconds"] += elapsed
        else:
            self._stats["absent_seconds"] += elapsed

        # State change → adjust brightness
        if new_state != self._state:
            self._stats["state_changes"] += 1
            self._state = new_state
            target_brightness = self._brightness_for_state(new_state)
            self.display.smooth_set(target_brightness, self.transition_dur)
            log.info(
                f"State: {new_state:8s}  →  Brightness target: {target_brightness}%  "
                f"| Confidence: {result['confidence']:.0%}  "
                f"| Direction: {result['gaze_direction']}"
            )
            self._log_to_db(new_state, target_brightness)

    def _brightness_for_state(self, state: str) -> int:
        if state == STATE_LOOKING:
            return self.display.LEVEL_HIGH
        elif state == STATE_AWAY:
            return self.display.LEVEL_MEDIUM
        else:
            return self.display.LEVEL_LOW

    # ─────────────────────────────────────────────────────────────────────────
    # UI overlay helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_system_hud(self, frame) -> object:
        """Draw bottom-right system info panel."""
        import cv2
        h, w = frame.shape[:2]

        # Panel background
        panel_w, panel_h = 230, 110
        px1, py1 = w - panel_w - 10, h - panel_h - 10
        px2, py2 = w - 10, h - 10

        overlay = frame.copy()
        cv2.rectangle(overlay, (px1, py1), (px2, py2), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.rectangle(frame, (px1, py1), (px2, py2), (60, 60, 60), 1)

        # State colour
        state_colours = {
            STATE_LOOKING: (0, 230, 120),
            STATE_AWAY:    (0, 180, 255),
            STATE_ABSENT:  (80,  80, 220),
        }
        sc = state_colours.get(self._state, (200, 200, 200))

        # Text lines
        lines = [
            (f"State:  {self._state}",           sc),
            (f"Screen: {self.display.current_brightness}%", (255, 255, 255)),
            (f"Looking: {self._fmt_time(self._stats['looking_seconds'])}", (0, 230, 120)),
            (f"Away:    {self._fmt_time(self._stats['away_seconds'])}",    (0, 180, 255)),
            (f"Absent:  {self._fmt_time(self._stats['absent_seconds'])}",  (80, 80, 220)),
        ]
        for i, (text, colour) in enumerate(lines):
            cv2.putText(frame, text, (px1 + 8, py1 + 22 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, colour, 1, cv2.LINE_AA)

        # Brightness bar
        bar_x1, bar_y1 = px1 + 8, py2 - 14
        bar_x2 = px2 - 8
        bw = int((self.display.current_brightness / 100.0) * (bar_x2 - bar_x1))
        cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y1 + 6), (40, 40, 40), -1)
        cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x1 + bw, bar_y1 + 6), sc, -1)
        cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y1 + 6), (80, 80, 80), 1)

        return frame

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    # ─────────────────────────────────────────────────────────────────────────
    # Database & session summary
    # ─────────────────────────────────────────────────────────────────────────

    def _log_to_db(self, state: str, brightness: int):
        """Optionally log brightness events to the database."""
        if self.db is None:
            return
        try:
            # Reuse the energy log table with a custom device label
            power_estimate = brightness * 0.5  # rough watt estimate for backlight
            self.db.log_energy(
                device="screen_backlight",
                state=state,
                power_watts=float(power_estimate),
                energy_kwh=0.0,
                cost_usd=0.0,
            )
        except Exception:
            pass

    def _print_session_summary(self):
        s = self._stats
        total = s["looking_seconds"] + s["away_seconds"] + s["absent_seconds"]
        total = max(total, 1.0)
        log.info("─" * 55)
        log.info("SESSION SUMMARY")
        log.info(f"  Duration      : {self._fmt_time(total)}")
        log.info(f"  Looking       : {self._fmt_time(s['looking_seconds'])}  ({s['looking_seconds']/total:.0%})")
        log.info(f"  Away          : {self._fmt_time(s['away_seconds'])}  ({s['away_seconds']/total:.0%})")
        log.info(f"  Absent        : {self._fmt_time(s['absent_seconds'])}  ({s['absent_seconds']/total:.0%})")
        log.info(f"  State changes : {s['state_changes']}")
        log.info("─" * 55)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Gaze-Aware Adaptive Screen Brightness System"
    )
    parser.add_argument("--camera",     type=int,   default=0,
                        help="Camera index (default: 0)")
    parser.add_argument("--away-delay", type=float, default=3.0,
                        help="Seconds before reducing brightness when gaze is away (default: 3)")
    parser.add_argument("--absent-delay", type=float, default=6.0,
                        help="Seconds before minimum brightness when no face detected (default: 6)")
    parser.add_argument("--no-preview", action="store_true",
                        help="Run headless (no camera preview window)")
    parser.add_argument("--frame-skip", type=int, default=2,
                        help="Process every N-th frame to reduce CPU usage (default: 2)")
    args = parser.parse_args()

    system = GazeBrightnessSystem(
        camera_index       = args.camera,
        away_delay_sec     = args.away_delay,
        absent_delay_sec   = args.absent_delay,
        show_preview       = not args.no_preview,
        frame_skip         = args.frame_skip,
    )
    system.run()


if __name__ == "__main__":
    main()
