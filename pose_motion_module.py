"""
Pose and Motion Analysis Module
Analyzes human pose and motion for better decision making
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
try:
    import mediapipe as mp
    # Check if the needed legacy solutions API is available (missing in some Python 3.14 builds)
    if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'pose'):
        MEDIAPIPE_AVAILABLE = True
    else:
        MEDIAPIPE_AVAILABLE = False
        print("Warning: MediaPipe installed but legacy 'solutions' module is missing. Pose tracking disabled.")
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("Warning: MediaPipe not available. Install mediapipe for pose estimation.")


class PoseMotionModule:
    """Analyzes human pose and motion patterns"""
    
    def __init__(self, model_type: str = 'mediapipe', motion_sensitivity: int = 5):
        """
        Initialize pose and motion analysis module
        
        Args:
            model_type: 'mediapipe' or 'basic'
            motion_sensitivity: Motion sensitivity level (1-10)
        """
        self.model_type = model_type
        self.motion_sensitivity = max(1, min(10, motion_sensitivity))
        self.mp_pose = None
        self.pose = None
        
        # Motion tracking
        self.prev_frame = None
        self.motion_history = []
        self.max_history = 30
        
        # Pose keypoints storage
        self.prev_landmarks = None
        self.current_landmarks = None
        
        if (model_type == 'mediapipe' and MEDIAPIPE_AVAILABLE):
            try:
                self.mp_pose = mp.solutions.pose
                self.pose = self.mp_pose.Pose(
                    static_image_mode=False,
                    model_complexity=0, # Changed from 1 to 0 for better performance
                    smooth_landmarks=True,
                    enable_segmentation=False,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                print("MediaPipe pose model loaded successfully")
            except Exception as e:
                print(f"Failed to load MediaPipe: {e}. Using basic motion detection.")
                self.model_type = 'basic'
        
        if self.model_type == 'basic' or self.pose is None:
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=50, detectShadows=True
            )
            self.model_type = 'basic'
    
    def analyze_frame(self, frame: np.ndarray, human_bbox: Optional[Tuple] = None) -> Dict:
        """
        Analyze pose and motion in frame
        
        Args:
            frame: Input BGR image frame
            human_bbox: Optional bounding box (x, y, w, h) to focus analysis on human region
            
        Returns:
            Dictionary with pose and motion analysis results
        """
        results = {
            'pose_detected': False,
            'motion_level': 0.0,
            'activity_type': 'none',
            'keypoints': [],
            'motion_vector': None,
            'is_active': False
        }
        
        # Extract region of interest if bbox provided
        roi_frame = frame
        if human_bbox:
            x, y, w, h = human_bbox[:4]
            x, y = max(0, x), max(0, y)
            roi_frame = frame[y:y+h, x:x+w]
            if roi_frame.size == 0:
                return results
        
        # Analyze pose
        if self.model_type == 'mediapipe' and self.pose is not None:
            pose_results = self._analyze_pose_mediapipe(roi_frame)
            results.update(pose_results)
        else:
            # Basic motion analysis
            motion_results = self._analyze_motion_basic(roi_frame)
            results.update(motion_results)
        
        # Update motion history
        self._update_motion_history(results['motion_level'])
        
        # Determine activity type
        results['activity_type'] = self._classify_activity(results)
        results['is_active'] = bool(results['motion_level'] > (self.motion_sensitivity / 10.0))
        
        return results
    
    def _analyze_pose_mediapipe(self, frame: np.ndarray) -> Dict:
        """Analyze pose using MediaPipe"""
        results = {
            'pose_detected': False,
            'motion_level': 0.0,
            'keypoints': [],
            'motion_vector': None
        }
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_results = self.pose.process(rgb_frame)
        
        if mp_results.pose_landmarks:
            results['pose_detected'] = True
            
            # Extract keypoints
            landmarks = []
            h, w = frame.shape[:2]
            
            for landmark in mp_results.pose_landmarks.landmark:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                landmarks.append((x, y, landmark.visibility))
            
            results['keypoints'] = landmarks
            self.current_landmarks = landmarks
            
            # Calculate motion from previous frame
            if self.prev_landmarks is not None and len(landmarks) == len(self.prev_landmarks):
                motion_vectors = []
                for i, (curr, prev) in enumerate(zip(landmarks, self.prev_landmarks)):
                    if curr[2] > 0.5 and prev[2] > 0.5:  # Only visible landmarks
                        dx = curr[0] - prev[0]
                        dy = curr[1] - prev[1]
                        motion_vectors.append((dx, dy))
                
                if motion_vectors:
                    # Calculate average motion magnitude
                    avg_motion = np.mean([np.sqrt(dx**2 + dy**2) for dx, dy in motion_vectors])
                    results['motion_level'] = float(min(1.0, avg_motion / 50.0))  # Normalize
                    results['motion_vector'] = [float(x) for x in np.mean(motion_vectors, axis=0)]
            
            self.prev_landmarks = landmarks
        
        return results
    
    def _analyze_motion_basic(self, frame: np.ndarray) -> Dict:
        """Basic motion analysis using background subtraction"""
        results = {
            'pose_detected': False,
            'motion_level': 0.0,
            'motion_vector': None
        }
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fg_mask = self.bg_subtractor.apply(gray)
        
        # Calculate motion level
        motion_pixels = np.sum(fg_mask > 0)
        total_pixels = frame.shape[0] * frame.shape[1]
        results['motion_level'] = min(1.0, motion_pixels / (total_pixels * 0.1))
        
        # Optical flow removed for performance
        results['motion_vector'] = [0.0, 0.0]
        self.prev_frame = gray
        
        self.prev_frame = gray
        results['pose_detected'] = results['motion_level'] > 0.1
        return results
    
    def _update_motion_history(self, motion_level: float):
        """Update motion history for pattern analysis"""
        self.motion_history.append(motion_level)
        if len(self.motion_history) > self.max_history:
            self.motion_history.pop(0)
    
    def _classify_activity(self, results: Dict) -> str:
        """Classify activity type based on motion and pose"""
        motion_level = results['motion_level']
        landmarks = results.get('keypoints', [])
        
        # Motion-based levels
        if motion_level > 0.6:
            return 'very_active'
        elif motion_level > 0.3:
            return 'active'
            
        # Pose-based classification if landmarks are available
        if landmarks:
            # Simple heuristic: Check y-coordinates of head (index 0) vs hips (index 23, 24)
            # MediaPipe Pose landmarks: 0 is nose, 23/24 are left/right hips
            if len(landmarks) > 24:
                nose_y = landmarks[0][1]
                hip_y = (landmarks[23][1] + landmarks[24][1]) / 2.0
                
                # If nose is close to hip level, person is likely resting/lying down
                if abs(nose_y - hip_y) < 50 and motion_level < 0.1:
                    return 'resting'
                
                # If nose is significantly higher than hips but motion is low, person is sitting/standing
                if nose_y < hip_y - 100 and motion_level < 0.1:
                    return 'working/reading'
        
        if motion_level < 0.1:
            return 'idle'
        elif motion_level < 0.3:
            return 'walking'
            
        return 'active'
    
    def get_motion_statistics(self) -> Dict:
        """Get motion statistics from history"""
        if not self.motion_history:
            return {'avg_motion': 0.0, 'peak_motion': 0.0, 'stability': 1.0}
        
        avg_motion = np.mean(self.motion_history)
        peak_motion = np.max(self.motion_history)
        
        # Calculate stability (lower variance = more stable)
        if len(self.motion_history) > 1:
            variance = np.var(self.motion_history)
            stability = 1.0 / (1.0 + variance)
        else:
            stability = 1.0
        
        return {
            'avg_motion': avg_motion,
            'peak_motion': peak_motion,
            'stability': stability
        }
    
    def draw_pose(self, frame: np.ndarray, analysis: Dict) -> np.ndarray:
        """Draw pose keypoints and motion indicators on frame with improved HUD"""
        result_frame = frame.copy()
        h, w = frame.shape[:2]
        
        # Add a semi-transparent background for the top-left HUD
        overlay = result_frame.copy()
        cv2.rectangle(overlay, (5, 5), (280, 85), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, result_frame, 0.6, 0, result_frame)
        
        if analysis['pose_detected'] and analysis['keypoints']:
            # Draw keypoints
            for x, y, visibility in analysis['keypoints']:
                if visibility > 0.5:
                    cv2.circle(result_frame, (x, y), 3, (0, 255, 255), -1)
        
        # Draw motion level indicator
        motion_level = analysis['motion_level']
        # Background for bar
        cv2.rectangle(result_frame, (10, 10), (110, 30), (50, 50, 50), -1)
        # Progress bar
        cv2.rectangle(result_frame, (10, 10), (10 + int(motion_level * 100), 30), 
                     (0, 255, 0), -1)
        # Border for bar
        cv2.rectangle(result_frame, (10, 10), (110, 30), (200, 200, 200), 1)
        
        cv2.putText(result_frame, f'Motion: {motion_level:.2f}', (120, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw activity type - Moved down to (10, 65) to avoid overlap
        activity = analysis['activity_type']
        cv2.putText(result_frame, f'Activity: {activity.replace("_", " ").title()}', (10, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return result_frame



