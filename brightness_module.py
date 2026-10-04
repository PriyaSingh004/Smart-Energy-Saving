"""
Brightness Monitoring Module
Monitors ambient brightness and provides lighting control recommendations
"""

import cv2
import numpy as np
from typing import Dict, Tuple, List


class BrightnessModule:
    """Monitors and analyzes brightness levels"""
    
    def __init__(self, brightness_threshold: int = 100, target_brightness: int = 150):
        """
        Initialize brightness monitoring module
        
        Args:
            brightness_threshold: Minimum acceptable brightness level (0-255)
            target_brightness: Target brightness level for comfort (0-255)
        """
        self.brightness_threshold = brightness_threshold
        self.target_brightness = target_brightness
        self.brightness_history = []
        self.max_history = 100
        
        # Lighting zones (for multi-zone control)
        self.zones = []
    
    def analyze_frame(self, frame: np.ndarray, region: Tuple[int, int, int, int] = None) -> Dict:
        """
        Analyze brightness in frame or region
        
        Args:
            frame: Input BGR image frame
            region: Optional region (x, y, w, h) to analyze. If None, analyzes entire frame.
            
        Returns:
            Dictionary with brightness analysis results
        """
        # Extract region of interest
        if region:
            x, y, w, h = region
            roi = frame[y:y+h, x:x+w]
        else:
            roi = frame
        
        # Convert to grayscale for brightness calculation
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Calculate brightness metrics
        mean_brightness = np.mean(gray)
        median_brightness = np.median(gray)
        std_brightness = np.std(gray)
        min_brightness = np.min(gray)
        max_brightness = np.max(gray)
        
        # Determine brightness status
        if mean_brightness < self.brightness_threshold:
            status = 'too_dark'
        elif mean_brightness > self.target_brightness + 30:
            status = 'too_bright'
        else:
            status = 'optimal'
        
        # Calculate adjustment recommendation
        brightness_diff = self.target_brightness - mean_brightness
        adjustment_needed = abs(brightness_diff) > 20
        adjustment_percentage = int((brightness_diff / 255.0) * 100)
        
        results = {
            'mean_brightness': float(mean_brightness),
            'median_brightness': float(median_brightness),
            'std_brightness': float(std_brightness),
            'min_brightness': float(min_brightness),
            'max_brightness': float(max_brightness),
            'status': status,
            'adjustment_needed': bool(adjustment_needed),
            'adjustment_percentage': int(adjustment_percentage),
            'recommendation': self._get_recommendation(status, brightness_diff)
        }
        
        # Update history
        self.brightness_history.append(mean_brightness)
        if len(self.brightness_history) > self.max_history:
            self.brightness_history.pop(0)
        
        return results
    
    def _get_recommendation(self, status: str, brightness_diff: float) -> str:
        """Get lighting adjustment recommendation"""
        if status == 'too_dark':
            return f"Increase lighting by {abs(int(brightness_diff))} units"
        elif status == 'too_bright':
            return f"Decrease lighting by {abs(int(brightness_diff))} units"
        else:
            return "Lighting is optimal"
    
    def analyze_zones(self, frame: np.ndarray, zones: List[Tuple[int, int, int, int]]) -> Dict:
        """
        Analyze brightness in multiple zones
        
        Args:
            frame: Input frame
            zones: List of (x, y, w, h) tuples defining zones
            
        Returns:
            Dictionary with zone-wise brightness analysis
        """
        zone_results = {}
        
        for i, zone in enumerate(zones):
            zone_results[f'zone_{i}'] = self.analyze_frame(frame, zone)
        
        # Calculate overall recommendation
        avg_brightness = np.mean([r['mean_brightness'] for r in zone_results.values()])
        overall_status = 'optimal'
        if avg_brightness < self.brightness_threshold:
            overall_status = 'too_dark'
        elif avg_brightness > self.target_brightness + 30:
            overall_status = 'too_bright'
        
        return {
            'zones': zone_results,
            'overall_brightness': float(avg_brightness),
            'overall_status': overall_status
        }
    
    def get_brightness_statistics(self) -> Dict:
        """Get brightness statistics from history"""
        if not self.brightness_history:
            return {
                'avg_brightness': 0.0,
                'min_brightness': 0.0,
                'max_brightness': 0.0,
                'stability': 1.0
            }
        
        avg_brightness = np.mean(self.brightness_history)
        min_brightness = np.min(self.brightness_history)
        max_brightness = np.max(self.brightness_history)
        
        # Calculate stability (lower variance = more stable)
        if len(self.brightness_history) > 1:
            variance = np.var(self.brightness_history)
            stability = 1.0 / (1.0 + variance / 100.0)
        else:
            stability = 1.0
        
        return {
            'avg_brightness': float(avg_brightness),
            'min_brightness': float(min_brightness),
            'max_brightness': float(max_brightness),
            'stability': float(stability)
        }
    
    def draw_brightness_overlay(self, frame: np.ndarray, analysis: Dict) -> np.ndarray:
        """Draw brightness analysis overlay on frame (Bottom-Right)"""
        result_frame = frame.copy()
        h, w = frame.shape[:2]
        
        # Draw brightness indicator
        brightness = analysis['mean_brightness']
        status = analysis['status']
        
        # Color based on status
        if status == 'too_dark':
            color = (0, 0, 255)  # Red
        elif status == 'too_bright':
            color = (0, 165, 255)  # Orange
        else:
            color = (0, 255, 0)  # Green
        
        # Setup coordinates for bottom-right placement
        bar_width = 180
        bar_height = 15
        margin = 10
        # Box background for clarity
        box_x1, box_y1 = w - bar_width - 25, h - 85
        box_x2, box_y2 = w - 5, h - 5
        
        overlay = result_frame.copy()
        cv2.rectangle(overlay, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, result_frame, 0.6, 0, result_frame)
        
        # Bar coordinates
        x, y = w - bar_width - 15, h - 45
        
        # Background bar
        cv2.rectangle(result_frame, (x, y), (x + bar_width, y + bar_height), (50, 50, 50), -1)
        
        # Brightness level
        brightness_width = int((min(255, brightness) / 255.0) * bar_width)
        cv2.rectangle(result_frame, (x, y), (x + brightness_width, y + bar_height), color, -1)
        
        # Border
        cv2.rectangle(result_frame, (x, y), (x + bar_width, y + bar_height), (200, 200, 200), 1)
        
        # Text
        cv2.putText(result_frame, f'Brightness: {brightness:.0f}', (x, y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(result_frame, analysis['recommendation'], (x - 20, y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        return result_frame

