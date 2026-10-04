"""
Gaze Detection Module
Detects whether the user is looking at the screen using MediaPipe Face Mesh.
Falls back to frontal-face cascade detection if Face Mesh is unavailable.
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple

# ── MediaPipe availability check ─────────────────────────────────────────────
try:
    import mediapipe as mp

    _fm = mp.solutions.face_mesh if hasattr(mp, "solutions") else None
    _fd = mp.solutions.face_detection if hasattr(mp, "solutions") else None
    MEDIAPIPE_FACE_MESH_AVAILABLE = _fm is not None
    MEDIAPIPE_FACE_DETECT_AVAILABLE = _fd is not None
except ImportError:
    MEDIAPIPE_FACE_MESH_AVAILABLE = False
    MEDIAPIPE_FACE_DETECT_AVAILABLE = False
    _fm = None
    _fd = None

# ── MediaPipe Face Mesh iris landmark indices ─────────────────────────────────
# Left eye: outer=33, inner=133, top=159, bottom=145, iris centre=468
# Right eye: outer=362, inner=263, top=386, bottom=374, iris centre=473
_LEFT_EYE_OUTER = 33
_LEFT_EYE_INNER = 133
_LEFT_EYE_TOP = 159
_LEFT_EYE_BOT = 145
_LEFT_IRIS = 468          # available only in Face Mesh with refine_landmarks=True

_RIGHT_EYE_OUTER = 362
_RIGHT_EYE_INNER = 263
_RIGHT_EYE_TOP = 386
_RIGHT_EYE_BOT = 374
_RIGHT_IRIS = 473

# Gaze direction thresholds (ratio of iris offset relative to eye width)
_H_THRESHOLD = 0.15   # horizontal: fraction beyond which classified as left/right
_V_THRESHOLD = 0.12   # vertical:   fraction beyond which classified as up/down


class GazeDetector:
    """
    Detects gaze direction from a video frame.

    Returns a result dict:
        {
            'looking_at_screen': bool,
            'confidence':        float  (0-1),
            'face_detected':     bool,
            'gaze_direction':    str    ('center'|'left'|'right'|'up'|'down'|'unknown'),
            'eye_open':          bool,
        }
    """

    def __init__(self,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 look_away_grace_frames: int = 8):
        """
        Args:
            min_detection_confidence: MediaPipe detection confidence threshold.
            min_tracking_confidence:  MediaPipe tracking confidence threshold.
            look_away_grace_frames:   How many consecutive non-gaze frames before
                                      marking the user as 'not looking'.
        """
        self.grace_frames = look_away_grace_frames
        self._not_looking_count = 0        # consecutive frames without gaze
        self._face_mesh = None
        self._face_detect = None
        self._cascade = None
        self._mode = "none"

        # ── Try Face Mesh (best accuracy, includes iris landmarks) ──────────
        if MEDIAPIPE_FACE_MESH_AVAILABLE:
            try:
                self._face_mesh = _fm.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,          # enables iris landmarks 468-477
                    min_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                    static_image_mode=False,
                )
                self._mode = "face_mesh"
                print("[GazeDetector] Using MediaPipe Face Mesh with iris landmarks.")
                return
            except Exception as e:
                print(f"[GazeDetector] Face Mesh init failed: {e}")

        # ── Fallback 1: MediaPipe Face Detection ────────────────────────────
        if MEDIAPIPE_FACE_DETECT_AVAILABLE:
            try:
                self._face_detect = _fd.FaceDetection(
                    model_selection=0,
                    min_detection_confidence=min_detection_confidence,
                )
                self._mode = "face_detection"
                print("[GazeDetector] Using MediaPipe Face Detection (no iris).")
                return
            except Exception as e:
                print(f"[GazeDetector] Face Detection init failed: {e}")

        # ── Fallback 2: OpenCV Haar Cascade ─────────────────────────────────
        try:
            self._cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self._mode = "cascade"
            print("[GazeDetector] Using OpenCV Haar Cascade (face presence only).")
        except Exception as e:
            print(f"[GazeDetector] Cascade init failed: {e}. Gaze detection disabled.")
            self._mode = "none"

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def detect_gaze(self, frame: np.ndarray) -> Dict:
        """
        Analyse a BGR video frame and return gaze state.

        Returns:
            dict with keys: looking_at_screen, confidence, face_detected,
                            gaze_direction, eye_open
        """
        result = {
            "looking_at_screen": False,
            "confidence": 0.0,
            "face_detected": False,
            "gaze_direction": "unknown",
            "eye_open": False,
        }

        if self._mode == "face_mesh":
            self._detect_face_mesh(frame, result)
        elif self._mode == "face_detection":
            self._detect_face_detection(frame, result)
        elif self._mode == "cascade":
            self._detect_cascade(frame, result)
        # else: leave defaults

        # Apply grace-frame smoothing to avoid flickering
        if result["looking_at_screen"]:
            self._not_looking_count = 0
        else:
            self._not_looking_count += 1
            if self._not_looking_count <= self.grace_frames:
                # Consider still "looking" during grace period
                result["looking_at_screen"] = True
                result["gaze_direction"] = result.get("gaze_direction", "center")

        return result

    def draw_gaze_overlay(self, frame: np.ndarray, result: Dict) -> np.ndarray:
        """Draw a semi-transparent gaze status HUD on the frame."""
        out = frame.copy()
        h, w = out.shape[:2]

        # ── Status banner ────────────────────────────────────────────────────
        looking = result["looking_at_screen"]
        conf    = result["confidence"]
        direction = result["gaze_direction"]

        banner_h = 52
        overlay = out.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, out, 0.45, 0, out)

        # Indicator dot
        dot_color = (0, 230, 120) if looking else (0, 80, 220)
        cv2.circle(out, (24, 26), 10, dot_color, -1)
        cv2.circle(out, (24, 26), 10, (255, 255, 255), 1)

        # Status text
        status_text = "LOOKING AT SCREEN" if looking else "NOT LOOKING"
        cv2.putText(out, status_text, (44, 22),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6,
                    (255, 255, 255), 1, cv2.LINE_AA)

        detail = f"Direction: {direction.upper()}  |  Confidence: {conf:.0%}"
        cv2.putText(out, detail, (44, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (180, 180, 180), 1, cv2.LINE_AA)

        # ── Gaze direction arrows ─────────────────────────────────────────────
        cx, cy = w // 2, h - 60
        arrow_len = 30
        arrow_color = (0, 210, 255)

        dirs = {
            "left":  (cx - arrow_len, cy,  (arrow_len, 0)),
            "right": (cx,             cy,  (arrow_len, 0)),
            "up":    (cx,  cy - arrow_len, (0, arrow_len)),
            "down":  (cx,             cy,  (0, arrow_len)),
        }
        # Draw small compass rose
        for d, (sx, sy, (dx, dy)) in dirs.items():
            active = direction == d
            clr = (0, 230, 120) if active else (80, 80, 80)
            ex = sx + (dx if "right" in d else -dx if "left" in d else 0)
            ey = sy + (dy if "down" in d else -dy if "up" in d else 0)
            cv2.arrowedLine(out, (cx, cy),
                            (cx + (arrow_len if d == "right" else -arrow_len if d == "left" else 0),
                             cy + (arrow_len if d == "down" else -arrow_len if d == "up" else 0)),
                            clr, 2, tipLength=0.4)

        # Center dot
        cv2.circle(out, (cx, cy), 4, (255, 255, 255), -1)

        return out

    # ─────────────────────────────────────────────────────────────────────────
    # Internal detection methods
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_face_mesh(self, frame: np.ndarray, result: Dict):
        """Full iris-landmark gaze detection via Face Mesh."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_result = self._face_mesh.process(rgb)

        if not mp_result.multi_face_landmarks:
            return

        result["face_detected"] = True
        lm = mp_result.multi_face_landmarks[0].landmark
        h, w = frame.shape[:2]

        def px(idx: int) -> Tuple[int, int]:
            return int(lm[idx].x * w), int(lm[idx].y * h)

        # ── Eye openness check (EAR — eye aspect ratio) ──────────────────────
        # Left eye
        l_top, l_bot = px(_LEFT_EYE_TOP), px(_LEFT_EYE_BOT)
        l_out, l_in  = px(_LEFT_EYE_OUTER), px(_LEFT_EYE_INNER)
        l_ear = _dist(l_top, l_bot) / (_dist(l_out, l_in) + 1e-6)

        # Right eye
        r_top, r_bot = px(_RIGHT_EYE_TOP), px(_RIGHT_EYE_BOT)
        r_out, r_in  = px(_RIGHT_EYE_OUTER), px(_RIGHT_EYE_INNER)
        r_ear = _dist(r_top, r_bot) / (_dist(r_out, r_in) + 1e-6)

        ear = (l_ear + r_ear) / 2.0
        result["eye_open"] = ear > 0.18   # eyes are open if EAR > threshold

        if not result["eye_open"]:
            result["gaze_direction"] = "eyes_closed"
            result["confidence"] = 0.85
            return

        # ── Iris-based gaze direction ─────────────────────────────────────────
        # Check if iris landmarks (468+) are available
        num_landmarks = len(mp_result.multi_face_landmarks[0].landmark)
        if num_landmarks > _LEFT_IRIS:
            l_iris = px(_LEFT_IRIS)
            r_iris = px(_RIGHT_IRIS)

            # Horizontal ratio: 0 = leftmost, 1 = rightmost
            def h_ratio(iris, outer, inner):
                w_eye = abs(inner[0] - outer[0]) + 1e-6
                return (iris[0] - outer[0]) / w_eye

            # Vertical ratio: 0 = topmost, 1 = bottommost
            def v_ratio(iris, top, bot):
                h_eye = abs(bot[1] - top[1]) + 1e-6
                return (iris[1] - top[1]) / h_eye

            lh = h_ratio(l_iris, l_out, l_in)
            rh = h_ratio(r_iris, r_out, r_in)
            lv = v_ratio(l_iris, l_top, l_bot)
            rv = v_ratio(r_iris, r_top, r_bot)

            avg_h = (lh + rh) / 2.0   # < 0.5 → looking left, > 0.5 → right
            avg_v = (lv + rv) / 2.0   # < 0.5 → looking up,   > 0.5 → down

            # Determine direction
            direction = "center"
            if avg_h < 0.5 - _H_THRESHOLD:
                direction = "left"
            elif avg_h > 0.5 + _H_THRESHOLD:
                direction = "right"
            elif avg_v < 0.5 - _V_THRESHOLD:
                direction = "up"
            elif avg_v > 0.5 + _V_THRESHOLD:
                direction = "down"

            result["gaze_direction"] = direction
            result["looking_at_screen"] = (direction == "center")
            result["confidence"] = min(1.0, 0.6 + (1.0 - abs(avg_h - 0.5) * 3))

        else:
            # No iris landmarks available — use face presence as proxy
            result["gaze_direction"] = "center"
            result["looking_at_screen"] = True
            result["confidence"] = 0.55

    def _detect_face_detection(self, frame: np.ndarray, result: Dict):
        """Face detection fallback — presence implies looking."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_result = self._face_detect.process(rgb)

        if mp_result.detections:
            best = max(mp_result.detections,
                       key=lambda d: d.score[0] if d.score else 0)
            conf = best.score[0] if best.score else 0.5
            result["face_detected"] = True
            result["looking_at_screen"] = True
            result["gaze_direction"] = "center"
            result["confidence"] = float(conf)
            result["eye_open"] = True

    def _detect_cascade(self, frame: np.ndarray, result: Dict):
        """Haar cascade fallback — face presence implies looking."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )
        if len(faces) > 0:
            result["face_detected"] = True
            result["looking_at_screen"] = True
            result["gaze_direction"] = "center"
            result["confidence"] = 0.60
            result["eye_open"] = True

    def release(self):
        """Release MediaPipe resources."""
        if self._face_mesh:
            self._face_mesh.close()
        if self._face_detect:
            self._face_detect.close()


# ── Utility ───────────────────────────────────────────────────────────────────

def _dist(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))
