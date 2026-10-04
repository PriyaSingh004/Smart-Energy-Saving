# Smart Home Automation System - Energy Efficient with Computer Vision

A comprehensive Python-based smart home automation system that uses OpenCV and computer vision to monitor and optimize energy consumption while ensuring comfort and environmental friendliness.

## Features

### 🎯 Core Capabilities

1. **Human and Animal Detection**
   - Accurate detection using YOLO or Haar Cascade classifiers
   - Real-time presence monitoring
   - Configurable confidence thresholds

2. **Pose and Motion Analysis**
   - Human pose estimation using MediaPipe
   - Motion level analysis
   - Activity classification (sitting, walking, active, etc.)
   - Better decision-making based on user activity

3. **Brightness Monitoring**
   - Real-time ambient brightness analysis
   - Automatic lighting adjustment recommendations
   - Multi-zone brightness monitoring support

4. **Airflow Monitoring**
   - Airflow sensor integration (or simulation mode)
   - Ventilation control recommendations
   - Optimal airflow range management

5. **Adaptive Screen Brightness (Presence-Aware)**
   - **Hindi**: यह सिस्टम वेबकैम के ज़रिए इंसानी मौजूदगी का पता लगाने के लिए 'कंप्यूटर विज़न' का इस्तेमाल करता है, और लैपटॉप स्क्रीन की ब्राइटनेस को अपने-आप एडजस्ट करता है। जब किसी इंसान का पता चलता है, तो सिस्टम बेहतर विज़िबिलिटी के लिए ब्राइटनेस बढ़ा देता है। जब कुछ समय तक किसी इंसान का पता नहीं चलता, तो सिस्टम बिजली बचाने के लिए ब्राइटनेस कम कर देता है।
   - **English**: Uses computer vision to detect human presence and dynamically adjusts laptop screen brightness. Increases brightness when present, and dims when absent to save energy.

6. **Energy Management**
   - Intelligent automation decisions
   - Energy consumption tracking
   - Cost and savings calculations
   - Carbon footprint estimation
   - Auto-off when no presence detected

7. **User-Friendly Interface**
   - Modern GUI with real-time video feed
   - Dashboard with multiple information tabs
   - System logs and recommendations
   - Easy start/stop controls

8. **Environmentally Friendly**
   - Energy-saving optimizations
   - Automatic device control
   - Carbon footprint tracking
   - Sustainable living recommendations

## Installation

### Prerequisites

- Python 3.8 or higher
- Webcam or camera device
- Windows/Linux/macOS

### Setup Steps

1. **Clone or download the project**
   ```bash
   cd Smart-Energy-Saving
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system**
   - Edit `config.ini` to adjust settings
   - Configure camera index, detection thresholds, etc.

4. **Run the application**
   ```bash
   python main.py
   ```

## Configuration

The `config.ini` file allows you to customize:

- **Detection**: Model type, confidence thresholds, animal detection
- **Pose**: Pose estimation model, motion sensitivity
- **Brightness**: Thresholds, target levels, auto-adjustment
- **Airflow**: Sensor port, simulation mode, optimal ranges
- **Energy**: Auto-off delay, energy saving mode, comfort settings
- **GUI**: Window size, update intervals
- **Camera**: Camera index, resolution, FPS

## Usage

1. **Start the Application**
   - Run `python main.py`
   - The GUI window will open

2. **Start the System**
   - Click the "▶ Start" button to begin monitoring
   - The camera feed will start processing

3. **Monitor Information**
   - **Detection Tab**: View human/animal counts and pose analysis
   - **Environment Tab**: Monitor brightness and airflow levels
   - **Energy Tab**: Track energy consumption and savings
   - **Logs Tab**: View system activity logs

4. **Stop the System**
   - Click the "⏹ Stop" button to pause monitoring

## Project Structure

```
smart-energy/
├── main.py                 # Main application entry point
├── detection_module.py     # Human/animal detection
├── pose_motion_module.py   # Pose and motion analysis
├── brightness_module.py    # Ambient brightness monitoring
├── gaze_module.py          # Eye gaze & iris tracking
├── screen_brightness_controller.py # OS brightness library
├── presence_brightness_system.py # Standalone presence-brightness runner
├── airflow_module.py       # Airflow monitoring
├── energy_manager.py       # Energy management logic
├── gui_interface.py        # User interface
├── config.ini              # Configuration file
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Technical Details

### Detection Models

- **YOLO (Recommended)**: Uses Ultralytics YOLOv8 for accurate object detection
- **Haar Cascade**: Fallback option using OpenCV cascades
- **MediaPipe**: For pose estimation and motion analysis

### Energy Optimization

- Automatic device control based on presence
- Smart lighting adjustment
- Ventilation optimization
- Energy consumption tracking and reporting

### Sensor Integration

- **Camera**: For visual detection and monitoring
- **Airflow Sensor**: Optional serial sensor (supports simulation mode)
- **Brightness**: Calculated from camera frames

## Customization

### Adding New Sensors

1. Create a new module file (e.g., `temperature_module.py`)
2. Implement sensor reading and analysis
3. Integrate with `energy_manager.py`
4. Update GUI to display sensor data

### Extending Detection

- Modify `detection_module.py` to add new detection classes
- Update YOLO model or add custom classifiers
- Adjust confidence thresholds in config

### Customizing GUI

- Edit `gui_interface.py` to modify layout
- Add new tabs or information panels
- Customize colors and styles

## Troubleshooting

### Camera Not Working
- Check camera index in `config.ini`
- Ensure camera is not being used by another application
- Try different camera indices (0, 1, 2, etc.)

### Detection Not Working
- Install YOLO: `pip install ultralytics`
- Check if model downloads correctly
- Lower confidence threshold in config
- Ensure good lighting conditions

### Performance Issues
- Reduce camera resolution in config
- Lower FPS limit
- Use simpler detection models (Haar Cascade)
- Close other applications

## Future Enhancements

- [ ] Temperature sensor integration
- [ ] Multi-camera support
- [ ] Cloud connectivity and remote monitoring
- [ ] Machine learning for predictive energy optimization
- [ ] Mobile app integration
- [ ] Voice control support
- [ ] Integration with smart home platforms (Home Assistant, etc.)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source and available for educational and personal use.

## Acknowledgments

- OpenCV community
- Ultralytics for YOLO models
- Google MediaPipe team
- Python community

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review configuration settings
3. Check system logs in the GUI
4. Ensure all dependencies are installed correctly

## 👥 Team Members

This project was developed collaboratively as a final-year academic project by a team of two.

- **Priya Singh** — Team Member
- **Jaypal Chaudhary** — Team Member

---

**Made with ❤️ for a sustainable and energy-efficient future**


