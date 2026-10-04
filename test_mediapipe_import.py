try:
    import mediapipe as mp
    print(f"MediaPipe version: {mp.__version__}")
    print("Attempting to access mp.solutions.pose...")
    pose = mp.solutions.pose
    print("Success! mp.solutions.pose is available.")
except Exception as e:
    print(f"Error: {e}")
