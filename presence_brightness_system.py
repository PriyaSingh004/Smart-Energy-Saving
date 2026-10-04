"""
Presence-Based Adaptive Brightness System
==========================================
Uses YOLOv8 / Haar Cascade to detect human presence through the webcam and
automatically adjusts the laptop screen brightness:

  Human detected       →  brightness HIGH   (90 %)
  No human for N secs  →  brightness LOW    (15 %)
  Transition state     →  brightness MEDIUM (45 %)

Run:
    python presence_brightness_system.py
    python presence_brightness_system.py --no-preview --absent-delay 10
"""

import cv2
import time
import logging
import argparse
import threading
import numpy as np
from typing import Optional

from detection_module import DetectionModule
from screen_brightness_controller import ScreenBrightnessController

# Optional DB
try:
    from database import DatabaseManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("PresenceBrightness")

# ── States ─────────────────────────────────────────────────────────────────────
STATE_PRESENT  = "PRESENT"   # human detected
STATE_LEAVING  = "LEAVING"   # grace period — was present, now absent
STATE_ABSENT   = "ABSENT"    # no human for absent_delay seconds


class PresenceBrightnessSystem:
    """
    Detects human presence via webcam and adjusts screen brightness accordingly.

    Args:
        camera_index:      OpenCV camera index (default 0)
        absent_delay_sec:  Seconds after losing detection before dimming (default 8)
        transition_sec:    Brightness animation duration in seconds (default 1.5)
        confidence:        YOLO detection confidence threshold (default 0.5)
        show_preview:      Show live camera window (default True)
        frame_skip:        Run detection every N frames to save CPU (default 3)
    """

    BRIGHTNESS_PRESENT = 90
    BRIGHTNESS_LEAVING = 50
    BRIGHTNESS_ABSENT  = 15

    def __init__(self,
                 camera_index:     int   = 0,
                 absent_delay_sec: float = 8.0,
                 transition_sec:   float = 1.5,
                 confidence:       float = 0.5,
                 show_preview:     bool  = True,
                 frame_skip:       int   = 3):

        self.camera_index    = camera_index
        self.absent_delay    = absent_delay_sec
        self.transition_sec  = transition_sec
        self.show_preview    = show_preview
        self.frame_skip      = frame_skip

        # Sub-modules
        self.detector = DetectionModule(model_type='yolo',
                                        confidence_threshold=confidence)
        self.display  = ScreenBrightnessController()

        # Optional DB
        self.db: Optional[object] = None
        if DB_AVAILABLE:
            try:
                self.db = DatabaseManager("smart_energy.db")
                log.info("Database logging active (smart_energy.db)")
            except Exception as e:
                log.warning(f"DB unavailable: {e}")

        # State
        self._state             = STATE_PRESENT
        self._last_present_time = time.time()
        self._stats = {
            "present_seconds": 0.0,
            "leaving_seconds": 0.0,
            "absent_seconds":  0.0,
            "state_changes":   0,
            "energy_saved_pct": 0.0,
            "start_time":      time.time(),
        }
        self._prev_tick = time.time()

    # ─────────────────────────────────────────────────────────────────────────
    # Main loop
    # ─────────────────────────────────────────────────────────────────────────

    def run(self):
        """Start the main detection + brightness control loop."""
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_MSMF)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            log.error(f"Cannot open camera {self.camera_index}.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 15)

        log.info("═" * 55)
        log.info("  Presence-Based Adaptive Brightness System  ")
        log.info("  Press Q or Esc to quit")
        log.info("═" * 55)

        frame_idx    = 0
        last_dets    = {'humans': [], 'animals': []}

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                frame_idx += 1

                # ── Run YOLO detection every N frames ──────────────────────
                if frame_idx % self.frame_skip == 0:
                    last_dets = self.detector.detect(frame)
                    self._update_state(last_dets)

                # ── Draw overlays ──────────────────────────────────────────
                vis_frame = self.detector.draw_detections(frame.copy(), last_dets)
                vis_frame = self._draw_hud(vis_frame, last_dets)

                if self.show_preview:
                    cv2.imshow("Presence-Aware Brightness  [ Q = quit ]", vis_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), ord("Q"), 27):
                        break

        finally:
            cap.release()
            if self.show_preview:
                cv2.destroyAllWindows()
            self._compute_energy_savings()
            self._print_summary()

    # ─────────────────────────────────────────────────────────────────────────
    # State machine
    # ─────────────────────────────────────────────────────────────────────────

    def _update_state(self, detections: dict):
        now          = time.time()
        num_humans   = len(detections.get('humans', []))
        elapsed      = now - self._prev_tick
        self._prev_tick = now

        # Accumulate time per state
        if self._state == STATE_PRESENT:
            self._stats["present_seconds"] += elapsed
        elif self._state == STATE_LEAVING:
            self._stats["leaving_seconds"] += elapsed
        else:
            self._stats["absent_seconds"]  += elapsed

        # Determine new state
        if num_humans > 0:
            self._last_present_time = now
            new_state = STATE_PRESENT
        else:
            time_gone = now - self._last_present_time
            if time_gone < self.absent_delay * 0.4:
                new_state = STATE_PRESENT   # still in initial grace
            elif time_gone < self.absent_delay:
                new_state = STATE_LEAVING   # countdown phase
            else:
                new_state = STATE_ABSENT

        # Only act on state transitions
        if new_state != self._state:
            self._stats["state_changes"] += 1
            self._state = new_state
            target = self._brightness_for_state(new_state)
            self.display.smooth_set(target, self.transition_sec)

            tag = {"PRESENT": "[ON] ", "LEAVING": "[~~]", "ABSENT": "[OFF]"}.get(new_state, "")
            log.info(
                f"{tag} State -> {new_state:8s}  |  "
                f"Brightness target: {target}%  |  "
                f"Humans: {num_humans}"
            )
            self._log_to_db(new_state, target)

    def _brightness_for_state(self, state: str) -> int:
        return {
            STATE_PRESENT: self.BRIGHTNESS_PRESENT,
            STATE_LEAVING: self.BRIGHTNESS_LEAVING,
            STATE_ABSENT:  self.BRIGHTNESS_ABSENT,
        }.get(state, self.BRIGHTNESS_ABSENT)

    # ─────────────────────────────────────────────────────────────────────────
    # HUD overlay
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_hud(self, frame: np.ndarray, detections: dict) -> np.ndarray:
        h, w = frame.shape[:2]
        num_humans = len(detections.get('humans', []))

        # ── Top banner ──────────────────────────────────────────────────────
        banner_h = 56
        overlay  = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (10, 10, 10), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        state_colours = {
            STATE_PRESENT: (0, 230, 100),
            STATE_LEAVING: (0, 190, 255),
            STATE_ABSENT:  (60,  60, 220),
        }
        sc = state_colours.get(self._state, (200, 200, 200))

        # Indicator dot
        cv2.circle(frame, (26, 28), 11, sc, -1)
        cv2.circle(frame, (26, 28), 11, (255, 255, 255), 1)

        # State label
        label = {
            STATE_PRESENT: "HUMAN DETECTED — Brightness HIGH",
            STATE_LEAVING: "LEAVING — Brightness REDUCING...",
            STATE_ABSENT:  "NO HUMAN — Energy Save Mode",
        }.get(self._state, self._state)

        cv2.putText(frame, label, (48, 24),
                    cv2.FONT_HERSHEY_DUPLEX, 0.62,
                    (255, 255, 255), 1, cv2.LINE_AA)

        sub = (f"Humans in frame: {num_humans}  |  "
               f"Screen: {self.display.current_brightness}%  |  "
               f"Absent delay: {self.absent_delay:.0f}s")
        cv2.putText(frame, sub, (48, 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (160, 160, 160), 1, cv2.LINE_AA)

        # ── Right panel ─────────────────────────────────────────────────────
        pw, ph = 200, 145
        px1, py1 = w - pw - 8, h - ph - 8
        px2, py2 = w - 8,      h - 8

        panel = frame.copy()
        cv2.rectangle(panel, (px1, py1), (px2, py2), (12, 12, 12), -1)
        cv2.addWeighted(panel, 0.65, frame, 0.35, 0, frame)
        cv2.rectangle(frame, (px1, py1), (px2, py2), (55, 55, 55), 1)

        lines = [
            ("SYSTEM STATUS",                (200, 200, 200)),
            (f"State:   {self._state}",      sc),
            (f"Screen:  {self.display.current_brightness}%", (255, 255, 255)),
            (f"Present: {self._fmt(self._stats['present_seconds'])}", (0, 230, 100)),
            (f"Leaving: {self._fmt(self._stats['leaving_seconds'])}", (0, 190, 255)),
            (f"Absent:  {self._fmt(self._stats['absent_seconds'])}", (60, 60, 220)),
        ]
        for i, (txt, col) in enumerate(lines):
            cv2.putText(frame, txt, (px1 + 8, py1 + 20 + i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, col, 1, cv2.LINE_AA)

        # Brightness bar
        bx1, by1 = px1 + 8,  py2 - 12
        bx2      = px2 - 8
        bw = int((self.display.current_brightness / 100.0) * (bx2 - bx1))
        cv2.rectangle(frame, (bx1, by1), (bx2, by1 + 7), (35, 35, 35), -1)
        cv2.rectangle(frame, (bx1, by1), (bx1 + bw, by1 + 7), sc, -1)
        cv2.rectangle(frame, (bx1, by1), (bx2, by1 + 7), (70, 70, 70), 1)

        # ── Human count badge ───────────────────────────────────────────────
        badge_x, badge_y = 12, h - 22
        badge_txt = f"Humans: {num_humans}"
        cv2.rectangle(frame, (badge_x - 4, badge_y - 15),
                      (badge_x + 120, badge_y + 5), (0, 0, 0), -1)
        cv2.putText(frame, badge_txt, (badge_x, badge_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 230, 100) if num_humans else (60, 60, 220), 1, cv2.LINE_AA)

        return frame

    @staticmethod
    def _fmt(s: float) -> str:
        return f"{int(s//60):02d}:{int(s%60):02d}"

    # ─────────────────────────────────────────────────────────────────────────
    # Logging & summary
    # ─────────────────────────────────────────────────────────────────────────

    def _log_to_db(self, state: str, brightness: int):
        if self.db is None:
            return
        try:
            power = brightness * 0.5
            self.db.log_energy("screen_backlight", state, float(power), 0.0, 0.0)
        except Exception:
            pass

    def _compute_energy_savings(self):
        s = self._stats
        total = s["present_seconds"] + s["leaving_seconds"] + s["absent_seconds"]
        if total < 1:
            return
        # Compare actual vs always-on scenario
        actual_energy = (
            s["present_seconds"] * self.BRIGHTNESS_PRESENT +
            s["leaving_seconds"] * self.BRIGHTNESS_LEAVING +
            s["absent_seconds"]  * self.BRIGHTNESS_ABSENT
        )
        max_energy = total * self.BRIGHTNESS_PRESENT
        s["energy_saved_pct"] = 100.0 * (1.0 - actual_energy / max_energy)

    def _print_summary(self):
        s = self._stats
        total = s["present_seconds"] + s["leaving_seconds"] + s["absent_seconds"]
        total = max(total, 1.0)
        log.info("═" * 55)
        log.info("SESSION SUMMARY")
        log.info(f"  Total duration : {self._fmt(total)}")
        log.info(f"  Human present  : {self._fmt(s['present_seconds'])}  ({s['present_seconds']/total:.0%})")
        log.info(f"  Grace period   : {self._fmt(s['leaving_seconds'])}  ({s['leaving_seconds']/total:.0%})")
        log.info(f"  Absent (dim)   : {self._fmt(s['absent_seconds'])}  ({s['absent_seconds']/total:.0%})")
        log.info(f"  State changes  : {s['state_changes']}")
        log.info(f"  Energy saved   : ~{s['energy_saved_pct']:.1f}%  (vs always-on at 90%)")
        log.info("═" * 55)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Presence-Based Adaptive Screen Brightness System"
    )
    parser.add_argument("--camera",       type=int,   default=0,
                        help="Camera index (default: 0)")
    parser.add_argument("--absent-delay", type=float, default=8.0,
                        help="Seconds without human before dimming (default: 8)")
    parser.add_argument("--confidence",   type=float, default=0.5,
                        help="YOLO detection confidence threshold (default: 0.5)")
    parser.add_argument("--no-preview",   action="store_true",
                        help="Run headless (no OpenCV preview window)")
    parser.add_argument("--frame-skip",   type=int,   default=3,
                        help="Process every Nth frame (default: 3)")
    args = parser.parse_args()

    system = PresenceBrightnessSystem(
        camera_index     = args.camera,
        absent_delay_sec = args.absent_delay,
        confidence       = args.confidence,
        show_preview     = not args.no_preview,
        frame_skip       = args.frame_skip,
    )
    system.run()


if __name__ == "__main__":
    main()
