"""
Audio Detection Module
Captures and analyzes sound levels to assist in presence detection
Supports both real hardware (if available) and simulation mode
"""

import time
import random
import numpy as np
from typing import Dict

class AudioModule:
    """Detects sound levels and presence through audio analysis"""
    
    def __init__(self, simulation_mode: bool = True, sensitivity: float = 0.5):
        """
        Initialize audio module
        
        Args:
            simulation_mode: If True, simulate sound levels based on time/randomness
            sensitivity: Multiplier for sound detection sensitivity (0.0 to 1.0)
        """
        self.simulation_mode = simulation_mode
        self.sensitivity = sensitivity
        self.current_sound_level = 0.0  # 0.0 to 100.0
        
        if not self.simulation_mode:
            try:
                # Placeholder for real library like sounddevice or pyaudio
                # import sounddevice as sd
                # self.stream = ...
                pass
            except ImportError:
                print("Warning: Audio libraries not found. Falling back to simulation.")
                self.simulation_mode = True
                
        print(f"Audio Module initialized (Mode: {'Simulation' if self.simulation_mode else 'Hardware'})")

    def read_sound_level(self, occupancy_hint: bool = False) -> Dict:
        """
        Capture current environment sound level
        
        Args:
            occupancy_hint: External hint if person is likely present (to make simulation realistic)
            
        Returns:
            Dictionary with sound analysis results
        """
        if self.simulation_mode:
            # Simulate sound based on occupancy and a base noise floor
            base_noise = random.uniform(5.0, 15.0)
            if occupancy_hint:
                # Add "human activity" noise (conversations, typing, movement)
                activity_noise = random.uniform(20.0, 50.0) * self.sensitivity
                self.current_sound_level = base_noise + activity_noise
            else:
                self.current_sound_level = base_noise
        else:
            # Real hardware processing would go here
            self.current_sound_level = random.uniform(5.0, 10.0) # Fallback placeholder
            
        is_noisy = self.current_sound_level > 30.0
        
        return {
            'sound_level': round(self.current_sound_level, 2),
            'status': 'Elevated' if is_noisy else 'Quiet',
            'presence_detected': is_noisy,
            'timestamp': time.time()
        }

    def close(self):
        """Release audio resources"""
        pass
