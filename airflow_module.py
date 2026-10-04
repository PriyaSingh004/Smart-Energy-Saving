"""
Airflow Monitoring Module
Monitors airflow and provides ventilation control recommendations
"""

import numpy as np
import random
import time
from typing import Dict, Optional
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class AirflowModule:
    """Monitors airflow and ventilation"""
    
    def __init__(self, simulation_mode: bool = True, sensor_port: Optional[str] = None,
                 optimal_airflow_min: float = 0.5, optimal_airflow_max: float = 2.0):
        """
        Initialize airflow monitoring module
        
        Args:
            simulation_mode: If True, simulate sensor readings
            sensor_port: Serial port for physical sensor (e.g., 'COM3' or '/dev/ttyUSB0')
            optimal_airflow_min: Minimum optimal airflow in m/s
            optimal_airflow_max: Maximum optimal airflow in m/s
        """
        self.simulation_mode = simulation_mode
        self.sensor_port = sensor_port
        self.optimal_airflow_min = optimal_airflow_min
        self.optimal_airflow_max = optimal_airflow_max
        self.serial_connection = None
        
        # Airflow history
        self.airflow_history = []
        self.max_history = 100
        self.last_update_time = time.time()
        
        # Simulation parameters
        self.simulated_airflow = 1.0  # m/s
        self.simulation_trend = 0.0
        
        # Initialize sensor if not in simulation mode
        if not simulation_mode and sensor_port and SERIAL_AVAILABLE:
            try:
                self.serial_connection = serial.Serial(
                    sensor_port, baudrate=9600, timeout=1
                )
                print(f"Airflow sensor connected on {sensor_port}")
            except Exception as e:
                print(f"Failed to connect to airflow sensor: {e}. Using simulation mode.")
                self.simulation_mode = True
    
    def read_airflow(self) -> Dict:
        """
        Read current airflow value
        
        Returns:
            Dictionary with airflow analysis results
        """
        if self.simulation_mode:
            airflow = self._simulate_airflow()
        else:
            airflow = self._read_sensor()
        
        # Analyze airflow
        status = self._analyze_airflow(airflow)
        adjustment_needed = status != 'optimal'
        
        # Calculate adjustment recommendation
        if airflow < self.optimal_airflow_min:
            recommendation = f"Increase ventilation. Current: {airflow:.2f} m/s (target: {self.optimal_airflow_min}-{self.optimal_airflow_max} m/s)"
            adjustment_percentage = int(((self.optimal_airflow_min - airflow) / self.optimal_airflow_min) * 100)
        elif airflow > self.optimal_airflow_max:
            recommendation = f"Decrease ventilation. Current: {airflow:.2f} m/s (target: {self.optimal_airflow_min}-{self.optimal_airflow_max} m/s)"
            adjustment_percentage = int(((airflow - self.optimal_airflow_max) / self.optimal_airflow_max) * 100)
        else:
            recommendation = f"Airflow is optimal: {airflow:.2f} m/s"
            adjustment_percentage = 0
        
        results = {
            'airflow_value': float(airflow),
            'status': status,
            'adjustment_needed': adjustment_needed,
            'adjustment_percentage': adjustment_percentage,
            'recommendation': recommendation,
            'optimal_range': (self.optimal_airflow_min, self.optimal_airflow_max),
            'timestamp': time.time()
        }
        
        # Update history
        self.airflow_history.append(airflow)
        if len(self.airflow_history) > self.max_history:
            self.airflow_history.pop(0)
        
        self.last_update_time = time.time()
        
        return results
    
    def _simulate_airflow(self) -> float:
        """Simulate airflow sensor readings"""
        # Simulate realistic airflow variations
        current_time = time.time()
        
        # Add some trend and variation
        variation = random.uniform(-0.1, 0.1)
        self.simulation_trend += random.uniform(-0.05, 0.05)
        self.simulation_trend = max(-0.2, min(0.2, self.simulation_trend))
        
        self.simulated_airflow += variation + self.simulation_trend * 0.1
        self.simulated_airflow = max(0.1, min(5.0, self.simulated_airflow))  # Clamp between 0.1 and 5.0 m/s
        
        return self.simulated_airflow
    
    def _read_sensor(self) -> float:
        """Read from physical sensor"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return self._simulate_airflow()  # Fallback to simulation
        
        try:
            # Read from serial port (adjust based on your sensor protocol)
            if self.serial_connection.in_waiting > 0:
                line = self.serial_connection.readline().decode('utf-8').strip()
                # Parse sensor data (adjust based on your sensor format)
                try:
                    airflow = float(line)
                    return airflow
                except ValueError:
                    pass
        except Exception as e:
            print(f"Error reading sensor: {e}")
        
        return self.simulated_airflow  # Fallback
    
    def _analyze_airflow(self, airflow: float) -> str:
        """Analyze airflow status"""
        if airflow < self.optimal_airflow_min:
            return 'too_low'
        elif airflow > self.optimal_airflow_max:
            return 'too_high'
        else:
            return 'optimal'
    
    def get_airflow_statistics(self) -> Dict:
        """Get airflow statistics from history"""
        if not self.airflow_history:
            return {
                'avg_airflow': 0.0,
                'min_airflow': 0.0,
                'max_airflow': 0.0,
                'stability': 1.0
            }
        
        avg_airflow = np.mean(self.airflow_history)
        min_airflow = np.min(self.airflow_history)
        max_airflow = np.max(self.airflow_history)
        
        # Calculate stability
        if len(self.airflow_history) > 1:
            variance = np.var(self.airflow_history)
            stability = 1.0 / (1.0 + variance)
        else:
            stability = 1.0
        
        return {
            'avg_airflow': float(avg_airflow),
            'min_airflow': float(min_airflow),
            'max_airflow': float(max_airflow),
            'stability': float(stability)
        }
    
    def set_airflow_range(self, min_airflow: float, max_airflow: float):
        """Update optimal airflow range"""
        self.optimal_airflow_min = min_airflow
        self.optimal_airflow_max = max_airflow
    
    def close(self):
        """Close sensor connection"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()



