from gaze_module import GazeDetector
from screen_brightness_controller import ScreenBrightnessController
from gaze_brightness_system import GazeBrightnessSystem
from energy_manager import EnergyManager

# Test gaze detector init
g = GazeDetector()
print(f'[OK] GazeDetector  mode={g._mode}')

# Test brightness controller init
b = ScreenBrightnessController()
print(f'[OK] BrightnessCtrl current={b.current_brightness}%')

# Test energy manager accepts gaze_analysis kwarg
em = EnergyManager()
d = em.make_decisions(
    detections={'humans': [], 'animals': []},
    pose_analysis={
        'motion_level': 0, 'activity_type': 'idle',
        'pose_detected': False, 'keypoints': [],
        'motion_vector': None, 'is_active': False
    },
    brightness_analysis={
        'mean_brightness': 120, 'status': 'optimal',
        'adjustment_needed': False, 'adjustment_percentage': 0,
        'recommendation': 'OK'
    },
    airflow_analysis={'status': 'optimal', 'adjustment_needed': False},
    gaze_analysis={
        'looking_at_screen': True, 'face_detected': True,
        'confidence': 0.9, 'gaze_direction': 'center'
    }
)
print(f'[OK] EnergyManager  gaze_looking={d["gaze_looking"]}  screen_brightness={d["screen_brightness"]}%')

g.release()
print()
print('All modules loaded successfully.')
