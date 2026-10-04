# Troubleshooting Guide

## Camera Issues

### Problem: "Camera not available" or DirectShow warnings

**Solution:**
1. **First, run the camera test utility:**
   ```bash
   python test_camera.py
   ```
   This will automatically test all camera backends and find the working one.

2. **The system now tries multiple backends automatically:**
   - Media Foundation (MSMF) - Most reliable on Windows 10/11
   - DirectShow - Legacy Windows
   - Default backend - Fallback option

3. **If camera still doesn't work:**
   - Close other applications using the camera (Zoom, Teams, Skype, etc.)
   - Check Windows Camera Privacy Settings:
     - Settings → Privacy → Camera → Allow apps to access your camera
   - Unplug and reconnect the camera
   - Check Device Manager for camera issues
   - Restart your computer

### Problem: OpenCV warnings about backends

**Solution:** These warnings are now suppressed. The system will automatically try different backends silently.

## Missing Dependencies

### Problem: "YOLO not available" or "MediaPipe not available"

**Solution:**
1. **Run the dependency installer:**
   ```bash
   python install_dependencies.py
   ```
   This will automatically check and install missing packages.

2. **Or install manually:**
   ```bash
   pip install ultralytics mediapipe
   ```

3. **Note:** The system will work without these packages, but with reduced functionality:
   - Without YOLO: Uses Haar Cascade for detection (less accurate)
   - Without MediaPipe: Uses basic motion detection (less detailed pose analysis)

## System Still Not Working

### If the camera test utility finds no cameras:

1. **Check Windows Camera Privacy:**
   - Windows Settings → Privacy → Camera
   - Enable "Allow apps to access your camera"
   - Enable "Allow desktop apps to access your camera"

2. **Check if camera works in Windows Camera app:**
   - Open Windows Camera app
   - If it doesn't work there, it's a Windows/driver issue, not the application

3. **Update camera drivers:**
   - Device Manager → Cameras → Right-click your camera → Update driver

4. **Try a different USB port** (if using USB camera)

### The system will still run in simulation mode:
- Even without a camera, the system will display a test pattern
- Brightness and airflow monitoring will still work (simulated)
- Energy management logic will function
- You can test all features except visual detection

## Performance Issues

### Problem: Slow frame rate or laggy GUI

**Solutions:**
1. **Reduce camera resolution in config.ini:**
   ```ini
   [Camera]
   width = 320
   height = 240
   ```

2. **Increase update interval in config.ini:**
   ```ini
   [GUI]
   update_interval = 200  # milliseconds (higher = less frequent updates)
   ```

3. **Use simpler detection model:**
   ```ini
   [Detection]
   detection_model = cascade  # Instead of yolo
   ```

## Getting Help

If you're still having issues:

1. Check the logs tab in the GUI for error messages
2. Run `test_camera.py` and note which backends work
3. Check the console output for specific error messages
4. Ensure all dependencies are installed: `pip install -r requirements.txt`

---

**Remember:** The system is designed to work gracefully even without a camera - it will run in simulation mode and you can still test all features!



