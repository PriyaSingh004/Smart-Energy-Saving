"""
Human and Animal Detection Module
Uses OpenCV and YOLO/MediaPipe for accurate detection
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
try:
    from ultralytics import YOLO
    import torch
    YOLO_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    YOLO_AVAILABLE = False
    CUDA_AVAILABLE = False
    print("Warning: YOLO or Torch not available. Install ultralytics/torch for better detection.")


class DetectionModule:
    """Detects humans and animals in video frames"""
    
    def __init__(self, model_type: str = 'yolo', confidence_threshold: float = 0.5):
        """
        Initialize detection module
        
        Args:
            model_type: 'yolo', 'mediapipe', or 'cascade'
            confidence_threshold: Confidence threshold for detections
        """
        self.model_type = model_type
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.human_cascade = None
        self.animal_cascade = None
        
        # Initialize the selected model
        if model_type == 'yolo' and YOLO_AVAILABLE:
            try:
                self.model = YOLO('yolov8n.pt')  # nano model for speed
                if CUDA_AVAILABLE:
                    self.model.to('cuda')
                    print("YOLO model loaded on GPU (CUDA)")
                else:
                    print("YOLO model loaded on CPU")
            except Exception as e:
                print(f"Failed to load YOLO model: {e}. Falling back to cascade.")
                model_type = 'cascade'
        
        if model_type == 'cascade':
            # Load Haar cascades for human detection
            try:
                self.human_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_fullbody.xml'
                )
                # Try to load animal cascades if available
                try:
                    self.animal_cascade = cv2.CascadeClassifier(
                        cv2.data.haarcascades + 'haarcascade_frontalcatface.xml'
                    )
                except:
                    pass
                print("Cascade classifiers loaded")
            except Exception as e:
                print(f"Failed to load cascade classifiers: {e}")
        
        # Class IDs for YOLO (COCO dataset)
        self.human_class_id = 0  # person
        self.animal_class_ids = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]  # animals
        
    def detect(self, frame: np.ndarray) -> Dict[str, List[Tuple]]:
        """
        Detect humans and animals in frame
        
        Args:
            frame: Input BGR image frame
            
        Returns:
            Dictionary with 'humans' and 'animals' keys containing lists of (x, y, w, h) bounding boxes
        """
        results = {'humans': [], 'animals': []}
        
        if self.model_type == 'yolo' and self.model is not None:
            results = self._detect_yolo(frame)
        elif self.model_type == 'cascade' or self.human_cascade is not None:
            results = self._detect_cascade(frame)
        else:
            # Fallback: simple motion-based detection
            results = self._detect_motion(frame)
        
        return results
    
    def _detect_yolo(self, frame: np.ndarray) -> Dict[str, List[Tuple]]:
        """Detect using YOLO model with performance optimizations"""
        results = {'humans': [], 'animals': []}
        
        try:
            # Optimize: use smaller image size for faster CPU inference
            yolo_results = self.model(frame, verbose=False, imgsz=256) # Reduced from 320 to 256
            
            for result in yolo_results:
                boxes = result.boxes
                for box in boxes:
                    confidence = float(box.conf[0])
                    if confidence < self.confidence_threshold:
                        continue
                    
                    class_id = int(box.cls[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    w, h = x2 - x1, y2 - y1
                    
                    if class_id == self.human_class_id:
                        results['humans'].append((x1, y1, w, h, confidence))
                        # Trigger alert if unusual activity (e.g., after hours)
                        self._check_unusual_activity(x1, y1, w, h)
                    elif class_id in self.animal_class_ids:
                        results['animals'].append((x1, y1, w, h, confidence))
        except Exception as e:
            print(f"YOLO detection error: {e}")
        
        return results

    def _check_unusual_activity(self, x, y, w, h):
        """Internal logic for triggering alerts based on human movement"""
        # This can be expanded to check time of day or restricted zones
        pass
    
    def _detect_cascade(self, frame: np.ndarray) -> Dict[str, List[Tuple]]:
        """Detect using Haar cascades"""
        results = {'humans': [], 'animals': []}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect humans
        if self.human_cascade is not None:
            humans = self.human_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            results['humans'] = [tuple(h) for h in humans]
        
        # Detect animals (if cascade available)
        if self.animal_cascade is not None:
            animals = self.animal_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            results['animals'] = [tuple(a) for a in animals]
        
        return results
    
    def _detect_motion(self, frame: np.ndarray) -> Dict[str, List[Tuple]]:
        """Fallback motion-based detection (simple implementation)"""
        # This is a placeholder - in production, use proper background subtraction
        results = {'humans': [], 'animals': []}
        return results
    
    def draw_detections(self, frame: np.ndarray, detections: Dict[str, List[Tuple]]) -> np.ndarray:
        """
        Draw detection bounding boxes on frame
        
        Args:
            frame: Input frame
            detections: Detection results from detect() method
            
        Returns:
            Frame with drawn bounding boxes
        """
        result_frame = frame.copy()
        
        # Draw human detections in green
        for x, y, w, h, *rest in detections['humans']:
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(result_frame, 'Human', (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw animal detections in blue
        for x, y, w, h, *rest in detections['animals']:
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(result_frame, 'Animal', (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        return result_frame



