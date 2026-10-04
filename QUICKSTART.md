# Quick Start Guide

## Installation (5 minutes)

1. **Install Python 3.8+** (if not already installed)
   - Download from https://www.python.org/downloads/

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python main.py
   ```

## First Run

1. **Check Camera**
   - The application will try to use camera index 0 (default webcam)
   - If you have multiple cameras, edit `config.ini` and change `camera_index`

2. **Start Monitoring**
   - Click "▶ Start" button in the GUI
   - You should see the camera feed with detection overlays

3. **View Information**
   - Switch between tabs to see different information:
     - **Detection**: Human/animal counts and pose analysis
     - **Environment**: Brightness and airflow levels
     - **Energy**: Energy consumption and savings
     - **Logs**: System activity

## Basic Configuration

Edit `config.ini` to customize:

```ini
[Camera]
camera_index = 0        # Change if using different camera

[Detection]
confidence_threshold = 0.5    # Lower = more detections, Higher = more accurate

[Energy]
auto_off_delay = 300    # Seconds before auto-off (5 minutes)
energy_saving_mode = true
```

## Troubleshooting

### "Camera not found"
- Close other applications using the camera
- Try different camera_index values (0, 1, 2...)
- Check camera permissions

### "YOLO model not found"
- The app will download YOLO model automatically on first run
- Ensure internet connection for first run
- Or use cascade detection by setting `detection_model = cascade` in config

### "Module not found"
- Install dependencies: `pip install -r requirements.txt`
- Ensure you're using Python 3.8+

## Tips

- **Better Detection**: Ensure good lighting and clear view of the area
- **Performance**: Lower camera resolution in config for better performance
- **Energy Saving**: Adjust `auto_off_delay` based on your needs
- **Simulation Mode**: Airflow sensor runs in simulation mode by default (no hardware needed)

## Next Steps

- Read the full README.md for advanced configuration
- Customize detection thresholds for your environment
- Connect physical sensors for airflow monitoring
- Integrate with smart home devices

Enjoy your energy-efficient smart home automation system! 🏠✨



