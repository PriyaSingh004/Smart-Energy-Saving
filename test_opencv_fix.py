import cv2
import numpy as np
from pose_motion_module import PoseMotionModule

def test_optical_flow_fix():
    print("Starting verification test for OpenCV optical flow fix...")
    
    # Initialize module in basic mode (where the error occurs)
    module = PoseMotionModule(model_type='basic')
    
    # Create two frames of different sizes
    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
    frame2 = np.zeros((120, 120, 3), dtype=np.uint8)
    
    try:
        print("Processing first frame (100x100)...")
        results1 = module.analyze_frame(frame1)
        
        print("Processing second frame (120x120) - this should NOT crash now...")
        results2 = module.analyze_frame(frame2)
        
        print("Processing third frame (120x120) - optical flow should work now...")
        frame3 = np.zeros((120, 120, 3), dtype=np.uint8)
        # Add some "motion"
        frame3[20:40, 20:40] = 255
        results3 = module.analyze_frame(frame3)
        
        print("Test passed successfully! No cv2.error occurred.")
        return True
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False

if __name__ == "__main__":
    test_opencv_fix = test_optical_flow_fix()
    if not test_opencv_fix:
        exit(1)
