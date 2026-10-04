"""
Main Application Entry Point
Smart Home Automation System - Energy Efficient with Computer Vision
"""

import cv2
import configparser
import time
from typing import Dict, Optional
import numpy as np
import os

# Suppress OpenCV warnings
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
try:
    # Try to set log level (available in OpenCV 4.5+)
    if hasattr(cv2, 'setLogLevel'):
        # Try different possible constant names
        if hasattr(cv2, 'LOG_LEVEL_ERROR'):
            cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
        elif hasattr(cv2, 'LOG_LEVEL_SILENT'):
            cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
        elif hasattr(cv2, 'utils'):
            # Alternative method for newer versions
            cv2.utils.setLogLevel(0)  # 0 = silent
except (AttributeError, TypeError):
    # If log level setting is not available, continue without it
    pass

# Import all modules
from detection_module import DetectionModule
from pose_motion_module import PoseMotionModule
from brightness_module import BrightnessModule
from airflow_module import AirflowModule
from energy_manager import EnergyManager
from audio_module import AudioModule
from screen_brightness_controller import ScreenBrightnessController
from gui_interface import SmartHomeGUI
import tkinter as tk
from api_v2 import create_app, socketio, emit_system_update
import threading


class SmartHomeAutomation:
    """Main application class"""
    
    def __init__(self, config_file: str = 'config.ini'):
        """Initialize the smart home automation system"""
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Initialize camera with better error handling
        self.cap = None
        self.camera_index = int(self.config.get('Camera', 'camera_index', fallback='0'))
        self.camera_available = False
        self._initialize_camera()
        
        # Initialize modules
        self.detection_module = DetectionModule(
            model_type=self.config.get('Detection', 'detection_model', fallback='yolo'),
            confidence_threshold=float(self.config.get('Detection', 'confidence_threshold', fallback='0.5'))
        )
        
        self.pose_motion_module = PoseMotionModule(
            model_type=self.config.get('Pose', 'pose_model', fallback='mediapipe'),
            motion_sensitivity=int(self.config.get('Pose', 'motion_sensitivity', fallback='5'))
        )
        
        self.brightness_module = BrightnessModule(
            brightness_threshold=int(self.config.get('Brightness', 'brightness_threshold', fallback='100')),
            target_brightness=int(self.config.get('Brightness', 'target_brightness', fallback='150'))
        )
        
        self.airflow_module = AirflowModule(
            simulation_mode=self.config.getboolean('Airflow', 'simulation_mode', fallback=True),
            sensor_port=self.config.get('Airflow', 'sensor_port', fallback=''),
            optimal_airflow_min=float(self.config.get('Airflow', 'optimal_airflow_min', fallback='0.5')),
            optimal_airflow_max=float(self.config.get('Airflow', 'optimal_airflow_max', fallback='2.0'))
        )
        
        self.energy_manager = EnergyManager(
            auto_off_delay=int(self.config.get('Energy', 'auto_off_delay', fallback='300')),
            energy_saving_mode=self.config.getboolean('Energy', 'energy_saving_mode', fallback=True),
            comfort_temp_min=float(self.config.get('Energy', 'comfort_temp_min', fallback='20')),
            comfort_temp_max=float(self.config.get('Energy', 'comfort_temp_max', fallback='24'))
        )
        
        self.audio_module = AudioModule(
            simulation_mode=self.config.getboolean('Audio', 'simulation_mode', fallback=True),
            sensitivity=float(self.config.get('Audio', 'sensitivity', fallback='0.5'))
        )

        # Screen brightness controller (presence-driven)
        self.screen_brightness = ScreenBrightnessController(
            simulation_mode=self.config.getboolean('Brightness', 'simulation_mode', fallback=True)
        )
        self._last_brightness_state = None   # track last state to avoid redundant calls
        
        # Current state
        self.current_frame = None
        self.current_data = {
            'detections': {'humans': [], 'animals': []},
            'pose_analysis': {},
            'brightness_analysis': {
                'mean_brightness': 0, 
                'status': 'optimal', 
                'adjustment_needed': False,
                'recommendation': 'Initializing...'
            },
            'airflow_analysis': {
                'airflow_value': 0, 
                'status': 'optimal', 
                'adjustment_needed': False,
                'recommendation': 'Initializing...'
            },
            'audio_analysis': {
                'presence_detected': False, 
                'sound_level': 0,
                'recommendation': 'Initializing...'
            },
            'decisions': {},
            'energy_stats': {},
            'recommendations': []
        }
        
        # Performance & FPS tracking
        self.fps = 0
        self.last_fps_time = time.time()
        self.frame_count = 0
        self.process_every_n_frames = 3  # Run heavy detection every 3 frames
        self.frame_index = 0
        self.last_detections = {'humans': [], 'animals': []}
        
        self.gui = None # Will be set by main()
        
        # Error message flag to prevent spam
        self.camera_error_shown = False
        
        # Start Professional API v2 in background
        self.flask_app = create_app()
        self.api_thread = threading.Thread(
            target=lambda: socketio.run(self.flask_app, port=5000, host='0.0.0.0', debug=False, use_reloader=False, allow_unsafe_werkzeug=True),
            daemon=True
        )
        self.api_thread.start()
        
        print("Smart Home Automation System initialized successfully!")
        if not self.camera_available:
            print("Warning: Camera not available. System will run in simulation mode.")
    
    def _initialize_camera(self):
        """Initialize camera with automatic detection"""
        # Try configured camera index first
        if self._try_camera(self.camera_index):
            self.camera_available = True
            return
        
        # Try other camera indices (0-4)
        print(f"Camera index {self.camera_index} not available. Trying other cameras...")
        for idx in range(5):
            if idx != self.camera_index:
                if self._try_camera(idx):
                    self.camera_index = idx
                    self.camera_available = True
                    print(f"Camera found at index {idx}")
                    return
        
        # No camera found
        self.camera_available = False
        print("No camera found. Please check:")
        print("1. Camera is connected")
        print("2. No other application is using the camera")
        print("3. Camera drivers are installed")
        print("4. Try changing camera_index in config.ini")
    
    def _try_camera(self, index: int) -> bool:
        """Try to open camera at given index with multiple backends"""
        # Try different backends in order of preference
        # MSMF is more reliable on modern Windows 10/11
        backends = [
            (cv2.CAP_MSMF, "Media Foundation"),  # Windows Media Foundation (most reliable)
            (cv2.CAP_DSHOW, "DirectShow"),  # Windows DirectShow (legacy)
            (cv2.CAP_ANY, "Any/Default"),  # Default/Any backend
        ]
        
        for backend, backend_name in backends:
            try:
                cap = cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    # Give camera a moment to initialize
                    import time
                    time.sleep(0.1)
                    
                    # Test if we can read a frame (try multiple times)
                    for attempt in range(3):
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            # Verify frame has valid dimensions
                            if frame.shape[0] > 0 and frame.shape[1] > 0:
                                # Set camera properties
                                width = int(self.config.get('Camera', 'width', fallback='640'))
                                height = int(self.config.get('Camera', 'height', fallback='480'))
                                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                                self.cap = cap
                                print(f"✓ Camera {index} opened successfully using {backend_name} backend")
                                return True
                        time.sleep(0.1)
                    
                    # If we get here, camera opened but couldn't read frames
                    cap.release()
            except Exception:
                # Silently try next backend
                continue
        
        return False
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process a single frame through all modules with performance optimization"""
        # Sync Domain from GUI if available
        if self.gui:
            current_domain = self.gui.domain_var.get()
            if self.energy_manager.domain_mode != current_domain:
                self.energy_manager.set_domain(current_domain)
                
        result_frame = frame.copy()
        
        # 1. Detection (Optimized with frame skipping)
        if self.frame_index % self.process_every_n_frames == 0:
            detections = self.detection_module.detect(frame)
            self.last_detections = detections
        else:
            detections = self.last_detections
            
        self.frame_index += 1
        result_frame = self.detection_module.draw_detections(result_frame, detections)
        
        # 2. Pose and motion analysis (Optimized with frame skipping)
        pose_analysis = self.current_data.get('pose_analysis', {'pose_detected': False, 'motion_level': 0.0, 'activity_type': 'none'})
        
        if detections['humans'] and self.frame_index % self.process_every_n_frames == 0:
            # Analyze first human detected
            human_bbox = detections['humans'][0][:4]
            pose_analysis = self.pose_motion_module.analyze_frame(frame, human_bbox)
        
        if pose_analysis.get('pose_detected', False):
            result_frame = self.pose_motion_module.draw_pose(result_frame, pose_analysis)
        
        # 3. Brightness analysis (Optimized skipping)
        if self.frame_index % 2 == 0:
            brightness_analysis = self.brightness_module.analyze_frame(frame)
        else:
            brightness_analysis = self.current_data.get('brightness_analysis', {})
        
        result_frame = self.brightness_module.draw_brightness_overlay(result_frame, brightness_analysis)
        
        # 4. Airflow analysis (Lower frequency)
        if self.frame_index % 10 == 0:
            airflow_analysis = self.airflow_module.read_airflow()
        else:
            airflow_analysis = self.current_data.get('airflow_analysis', {})
        
        # 5. Audio presence analysis (Lower frequency)
        if self.frame_index % 5 == 0:
            audio_analysis = self.audio_module.read_sound_level(occupancy_hint=bool(detections['humans']))
        else:
            audio_analysis = self.current_data.get('audio_analysis', {})
        
        # 6. Energy management decisions
        decisions = self.energy_manager.make_decisions(
            detections, pose_analysis, brightness_analysis, airflow_analysis, audio_analysis
        )

        # 7. Presence-driven screen brightness adjustment
        humans_found = len(detections.get('humans', [])) > 0
        if humans_found:
            new_brightness_state = 'present'
            target_brightness    = self.screen_brightness.LEVEL_HIGH
        elif self.energy_manager.is_occupied:
            new_brightness_state = 'leaving'
            target_brightness    = self.screen_brightness.LEVEL_MEDIUM
        else:
            new_brightness_state = 'absent'
            target_brightness    = self.screen_brightness.LEVEL_LOW

        if new_brightness_state != self._last_brightness_state:
            self.screen_brightness.smooth_set(target_brightness, duration=1.2)
            self._last_brightness_state = new_brightness_state
        
        # Update current data
        self.current_data = {
            'detections': detections,
            'pose_analysis': pose_analysis,
            'brightness_analysis': brightness_analysis,
            'airflow_analysis': airflow_analysis,
            'audio_analysis': audio_analysis,
            'decisions': decisions,
            'energy_stats': self.energy_manager.get_energy_statistics(),
            'recommendations': self.energy_manager.get_recommendations()
        }
        
        # Update API bridge (Real-time Broadcast)
        emit_system_update(self.current_data)
        
        # Draw additional information on frame
        result_frame = self._draw_info_overlay(result_frame)
        
        return result_frame
    
    def _draw_info_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw additional information overlay with background for clarity"""
        result_frame = frame.copy()
        h, w = frame.shape[:2]
        
        # Add a semi-transparent background for bottom-left status
        overlay = result_frame.copy()
        cv2.rectangle(overlay, (5, h - 70), (250, h - 5), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, result_frame, 0.6, 0, result_frame)
        
        # Draw FPS (Top-Right)
        fps_text = f"FPS: {self.fps:.1f}"
        cv2.putText(result_frame, fps_text, (w - 110, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Draw occupancy status (Bottom-Left)
        occupancy = self.current_data['decisions'].get('occupancy_status', 'unknown')
        color = (0, 255, 0) if occupancy == 'occupied' else (0, 0, 255)
        cv2.putText(result_frame, f"Occupancy: {occupancy.title()}", (10, h - 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Draw screen brightness level
        bright_val  = self.screen_brightness.current_brightness
        bright_state = self._last_brightness_state or 'unknown'
        bright_col  = (0, 230, 100) if bright_state == 'present' else \
                      (0, 190, 255) if bright_state == 'leaving' else (80, 80, 220)
        cv2.putText(result_frame, f"Screen: {bright_val}% [{bright_state.upper()}]",
                   (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, bright_col, 2)

        # Draw energy saving mode
        if self.current_data['decisions'].get('energy_saving_active', False):
            cv2.putText(result_frame, "Energy Saving: ON", (10, h - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return result_frame
    
    def get_data(self) -> Dict:
        """Get current system data for GUI"""
        data = self.current_data.copy()
        data['camera_available'] = self.camera_available
        return data
    
    def run_video_processing(self):
        """Run video processing loop (called from GUI)"""
        # Check if camera is available
        if not self.camera_available or self.cap is None:
            if not self.camera_error_shown:
                print("Camera not available. Creating test pattern...")
                self.camera_error_shown = True
            # Return a test pattern frame instead
            return self._create_test_pattern()
        
        if not self.cap.isOpened():
            # Try to reinitialize camera
            self.camera_error_shown = False
            self._initialize_camera()
            if not self.camera_available:
                return self._create_test_pattern()
        
        ret, frame = self.cap.read()
        if not ret or frame is None:
            # Camera read failed, try to reinitialize
            if not self.camera_error_shown:
                print("Camera read failed. Attempting to reinitialize...")
                self.camera_error_shown = True
            self._initialize_camera()
            if not self.camera_available:
                return self._create_test_pattern()
            # Try reading again
            ret, frame = self.cap.read()
            if not ret or frame is None:
                return self._create_test_pattern()
        
        # Reset error flag on successful read
        self.camera_error_shown = False
        
        # Process frame
        processed_frame = self.process_frame(frame)
        self.current_frame = processed_frame
        
        # Update FPS
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_fps_time = current_time
        
        return processed_frame
    
    def _create_test_pattern(self) -> np.ndarray:
        """Create a test pattern when camera is not available"""
        width = int(self.config.get('Camera', 'width', fallback='640'))
        height = int(self.config.get('Camera', 'height', fallback='480'))
        
        # Create a test pattern frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add some text and graphics
        cv2.putText(frame, "Camera Not Available", (width//2 - 150, height//2 - 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(frame, "Please check camera connection", (width//2 - 180, height//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, "or edit config.ini to change camera_index", (width//2 - 200, height//2 + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Draw a simple pattern
        cv2.rectangle(frame, (50, 50), (width-50, height-50), (100, 100, 100), 2)
        cv2.circle(frame, (width//2, height//2), 50, (50, 50, 50), 2)
        
        # Still process it for brightness analysis (simulation mode)
        brightness_analysis = self.brightness_module.analyze_frame(frame)
        airflow_analysis = self.airflow_module.read_airflow()
        
        # Create minimal detections
        detections = {'humans': [], 'animals': []}
        pose_analysis = {'pose_detected': False, 'motion_level': 0.0, 'activity_type': 'none'}
        
        decisions = self.energy_manager.make_decisions(
            detections, pose_analysis, brightness_analysis, airflow_analysis
        )
        
        # Update current data
        self.current_data = {
            'detections': detections,
            'pose_analysis': pose_analysis,
            'brightness_analysis': brightness_analysis,
            'airflow_analysis': airflow_analysis,
            'decisions': decisions,
            'energy_stats': self.energy_manager.get_energy_statistics(),
            'recommendations': self.energy_manager.get_recommendations()
        }
        
        # Broadcast to web dashboard even in simulation mode
        emit_system_update(self.current_data)
        
        return frame
    
    def cleanup(self):
        """Cleanup resources"""
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
        self.energy_manager.finalize_session()
        self.airflow_module.close()
        cv2.destroyAllWindows()
        print("System cleaned up")


def main():
    """Main entry point"""
    # Create application instance
    app = SmartHomeAutomation('config.ini')
    
    # Create GUI
    root = tk.Tk()
    
    # Create GUI with callbacks
    def video_callback():
        if hasattr(app, 'gui') and app.gui.is_running:
            return app.run_video_processing()
        return None
    
    def data_callback():
        return app.get_data()
    
    gui = SmartHomeGUI(root, video_callback, data_callback)
    app.gui = gui
    
    # Update video in GUI
    def update_video():
        if gui.is_running:
            frame = video_callback()
            if frame is not None:
                gui.update_video_frame(frame)
        root.after(33, update_video)  # ~30 FPS
    
    update_video()
    
    # Handle window close
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start GUI main loop
    print("Starting GUI...")
    root.mainloop()


if __name__ == "__main__":
    main()