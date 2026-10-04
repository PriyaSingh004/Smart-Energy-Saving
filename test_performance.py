
import cv2
import time
import numpy as np
from detection_module import DetectionModule
from pose_motion_module import PoseMotionModule

def test_performance():
    print("Starting performance test...")
    detection = DetectionModule(model_type='yolo')
    pose = PoseMotionModule(model_type='mediapipe')
    
    # Create a dummy frame (640x480)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add a white rectangle to simulate a "person"
    cv2.rectangle(frame, (200, 200), (440, 480), (255, 255, 255), -1)
    
    # Measure YOLO
    start = time.time()
    detections = detection.detect(frame)
    end = time.time()
    print(f"YOLO Detection time: {(end - start)*1000:.2f} ms")
    
    # Measure MediaPipe Pose
    if detections['humans']:
        bbox = detections['humans'][0][:4]
        start = time.time()
        pose_res = pose.analyze_frame(frame, bbox)
        end = time.time()
        print(f"MediaPipe Pose time: {(end - start)*1000:.2f} ms")
    else:
        print("No human detected in dummy frame, skipping pose test.")
        
    # Measure Basic Motion (Optical Flow)
    pose_basic = PoseMotionModule(model_type='basic')
    # Use two frames for optical flow
    frame1 = frame.copy()
    frame2 = frame.copy()
    cv2.rectangle(frame2, (210, 200), (450, 480), (255, 255, 255), -1)
    
    pose_basic.analyze_frame(frame1) # First frame sets prev_frame
    start = time.time()
    pose_basic.analyze_frame(frame2)
    end = time.time()
    print(f"Basic Motion (Optical Flow) time: {(end - start)*1000:.2f} ms")

if __name__ == "__main__":
    test_performance()
