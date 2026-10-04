"""
Camera Test Utility
Helps users find and test their camera
"""

import cv2
import sys
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


def test_camera(index):
    """Test if camera at given index works"""
    print(f"Testing camera index {index}...", end=" ")
    
    # Try different backends
    backends = [
        (cv2.CAP_MSMF, "MSMF"),
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_ANY, "Default"),
    ]
    
    cap = None
    backend_name = None
    
    for backend, name in backends:
        try:
            test_cap = cv2.VideoCapture(index, backend)
            if test_cap.isOpened():
                import time
                time.sleep(0.2)  # Give camera time to initialize
                ret, frame = test_cap.read()
                if ret and frame is not None and frame.size > 0:
                    if frame.shape[0] > 0 and frame.shape[1] > 0:
                        cap = test_cap
                        backend_name = name
                        break
                else:
                    test_cap.release()
            else:
                test_cap.release()
        except:
            continue
    
    if cap is None or not cap.isOpened():
        print("❌ Failed to open")
        return False
    
    # Try to read a frame
    ret, frame = cap.read()
    if not ret or frame is None:
        print("❌ Opened but cannot read frames")
        cap.release()
        return False
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"✅ Working! Resolution: {width}x{height}, FPS: {fps:.1f} (Backend: {backend_name})")
    
    # Show preview for 3 seconds
    print(f"Showing preview for 3 seconds (press 'q' to skip)...")
    import time
    start_time = time.time()
    
    while time.time() - start_time < 3:
        ret, frame = cap.read()
        if ret:
            cv2.imshow(f'Camera {index} - Press Q to skip', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()
    cap.release()
    return True


def main():
    """Main function to test cameras"""
    print("=" * 60)
    print("Camera Test Utility")
    print("=" * 60)
    print()
    
    # Test cameras from index 0 to 4
    working_cameras = []
    
    for i in range(5):
        if test_camera(i):
            working_cameras.append(i)
        print()
    
    print("=" * 60)
    if working_cameras:
        print(f"✅ Found {len(working_cameras)} working camera(s): {working_cameras}")
        print(f"\nRecommended camera_index: {working_cameras[0]}")
        print("\nTo use this camera, edit config.ini and set:")
        print(f"   camera_index = {working_cameras[0]}")
    else:
        print("❌ No working cameras found!")
        print("\nTroubleshooting:")
        print("1. Make sure your camera is connected")
        print("2. Close other applications using the camera")
        print("3. Check camera drivers are installed")
        print("4. Try unplugging and reconnecting the camera")
        print("5. On Windows, check Device Manager for camera issues")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        cv2.destroyAllWindows()
        sys.exit(0)

