try:
    print("Testing DetectionModule import...")
    from detection_module import DetectionModule
    print("Success! DetectionModule loaded.")
    
    print("Testing YOLO initialization...")
    detector = DetectionModule(model_type='yolo')
    if detector.model is not None:
        print("Success! YOLO model initialized.")
    else:
        print("YOLO model not initialized (fallback to cascade).")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
