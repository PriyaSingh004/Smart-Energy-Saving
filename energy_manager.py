"""
Energy Management Module
Coordinates all modules to optimize energy usage while ensuring comfort
"""

import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta


from database import DatabaseManager


class EnergyManager:
    """Manages energy-efficient automation decisions"""
    
    def __init__(self, auto_off_delay: int = 300, energy_saving_mode: bool = True,
                 comfort_temp_min: float = 20, comfort_temp_max: float = 24,
                 db_path: str = 'smart_energy.db'):
        """
        Initialize energy manager
        
        Args:
            auto_off_delay: Seconds to wait before auto-off when no presence detected
            energy_saving_mode: Enable energy saving optimizations
            comfort_temp_min: Minimum comfortable temperature in Celsius
            comfort_temp_max: Maximum comfortable temperature in Celsius
            db_path: Path to SQLite database
        """
        self.auto_off_delay = auto_off_delay
        self.energy_saving_mode = energy_saving_mode
        self.comfort_temp_min = comfort_temp_min
        self.comfort_temp_max = comfort_temp_max
        
        # Database persistence
        self.db = DatabaseManager(db_path)
        
        # State tracking
        self.last_presence_time = time.time()
        self.presence_start_time = None
        self.is_occupied = False
        self.is_present_now = False
        self.domain_mode = 'home'  # options: 'home', 'office', 'industrial'
        self.sound_presence = False
        
        self.device_states = {
            'lights': 'off',
            'heating': 'off',
            'cooling': 'off',
            'ventilation': 'off'
        }
        
        # Energy statistics
        self.energy_consumption = {
            'lights': 0.0,  # kWh
            'heating': 0.0,
            'cooling': 0.0,
            'ventilation': 0.0
        }
        self.current_power_watts = 0.0
        self.session_start_time = time.time()
        self.last_log_time = time.time()
        self.last_decision_time = time.time() # Track actual time between frames
        
        # Decision history
        self.decision_history = []
    
    def update_presence(self, humans_detected: int, animals_detected: int, sound_detected: bool = False):
        """Update presence detection status incorporating computer vision and audio"""
        # Sound detection provides an additional hint for presence (e.g., someone around the corner)
        has_presence = humans_detected > 0 or animals_detected > 0 or sound_detected
        self.sound_presence = sound_detected
        
        # Override auto_off_delay to 10 seconds for immediate showcase
        self.auto_off_delay = 10
        
        if has_presence:
            if not self.is_present_now:
                self.presence_start_time = time.time()
            self.last_presence_time = time.time()
            self.is_occupied = True
            self.is_present_now = True
        else:
            self.is_present_now = False
            # Check if auto-off delay has passed
            if self.last_presence_time:
                time_since_presence = time.time() - self.last_presence_time
                
                # In Office/Industrial domains, we might have longer grace periods
                effective_delay = self.auto_off_delay
                if self.domain_mode == 'office': effective_delay *= 1.5
                elif self.domain_mode == 'industrial': effective_delay *= 2.0
                
                if time_since_presence > effective_delay:
                    self.is_occupied = False
    
    def make_decisions(self, detections: Dict, pose_analysis: Dict,
                      brightness_analysis: Dict, airflow_analysis: Dict,
                      audio_analysis: Optional[Dict] = None,
                      gaze_analysis: Optional[Dict] = None) -> Dict:
        """
        Make energy-efficient automation decisions based on Vision, Environment, and Audio
        """
        humans = len(detections.get('humans', []))
        animals = len(detections.get('animals', []))
        sound_detected = audio_analysis.get('presence_detected', False) if audio_analysis else False
        
        # Update presence
        self.update_presence(humans, animals, sound_detected)
        
        # Calculate remaining time
        effective_delay = self.auto_off_delay
        if self.domain_mode == 'office': effective_delay *= 1.5
        elif self.domain_mode == 'industrial': effective_delay *= 2.0
        
        if self.is_present_now:
            remaining_time = effective_delay
        elif self.is_occupied:
            time_since = time.time() - self.last_presence_time
            remaining_time = max(0.0, effective_delay - time_since)
        else:
            remaining_time = 0.0

        # Occupancy-Based Control: ONE master variable mapping
        if self.is_occupied:
            light_state = 'on'
            fan_state = 'on'
            ac_state = 'on'
            system_status = 'on'
        else:
            light_state = 'off'
            fan_state = 'off'
            ac_state = 'off'
            system_status = 'off'
        
        # ── Gaze-aware screen brightness ───────────────────────────────────
        if gaze_analysis:
            gaze_looking  = gaze_analysis.get('looking_at_screen', False)
            face_detected = gaze_analysis.get('face_detected', False)
            if gaze_looking:
                screen_brightness = 90    # user actively looking
            elif face_detected:
                screen_brightness = 45    # user present but glancing away
            else:
                screen_brightness = 15    # no user — save power
        else:
            # Fallback to occupancy-based estimate
            gaze_looking      = self.is_present_now
            screen_brightness = 80 if self.is_occupied else 15

        decisions = {
            'lights': light_state,
            'ventilation': fan_state,
            'heating': 'off',
            'cooling': ac_state,
            'light': light_state.upper(),
            'fan': fan_state.upper(),
            'ac': ac_state.upper(),
            'system_status': system_status.upper(),
            'remaining_time': int(remaining_time),
            'energy_saving_active': self.energy_saving_mode,
            'domain_mode': self.domain_mode,
            'occupancy_status': 'occupied' if self.is_occupied else 'unoccupied',
            'duration_seconds': int(time.time() - self.presence_start_time) if (self.is_present_now and self.presence_start_time) else 0,
            'timestamp': datetime.now().isoformat(),
            # Gaze-aware fields
            'gaze_looking':      gaze_looking,
            'screen_brightness': screen_brightness,
        }
        
        # Domain specific adjustments
        if self.domain_mode == 'industrial':
            # Industrial mode might keep ventilation higher regardless of occupancy
            if decisions.get('ventilation') == 'off' and self.energy_saving_mode:
                decisions['ventilation'] = 'low' # Safety minimum
                decisions['fan'] = 'LOW'
        
        # Update device states (mapped for legacy support)
        for device in ['lights', 'ventilation', 'heating', 'cooling']:
            if device in decisions and device in self.device_states:
                self.device_states[device] = decisions[device]
        
        self.decision_history.append(decisions.copy())
        if len(self.decision_history) > 100:
            self.decision_history.pop(0)
        
        self._update_energy_consumption(decisions)
        
        # Push to real-time dashboard via API bridge if needed
        # In v2, this would use socketio.emit
        
        return decisions

    def set_domain(self, mode: str):
        """Switch operational domain (home/office/industrial)"""
        if mode in ['home', 'office', 'industrial']:
            self.domain_mode = mode
            print(f"System profile switched to: {mode}")
    
    def _decide_lighting(self, brightness: Dict, pose: Dict) -> str:
        """Decide lighting control"""
        if not self.is_occupied and self.energy_saving_mode:
            return 'off'
        
        if brightness['adjustment_needed']:
            if brightness['status'] == 'too_dark':
                return 'increase'
            elif brightness['status'] == 'too_bright':
                return 'decrease'
        
        # Dim lights if user is inactive
        if pose.get('activity_type') == 'sitting/standing' and self.energy_saving_mode:
            return 'dim'
        
        return 'optimal'
    
    def _decide_ventilation(self, airflow: Dict, pose: Dict) -> str:
        """Decide ventilation control"""
        if not self.is_occupied and self.energy_saving_mode:
            return 'off'
        
        if airflow['adjustment_needed']:
            if airflow['status'] == 'too_low':
                return 'increase'
            elif airflow['status'] == 'too_high':
                return 'decrease'
        
        # Adjust based on activity level
        if pose.get('activity_type') in ['active', 'very_active']:
            return 'increase'
        
        return 'optimal'
    
    def _decide_heating(self, airflow: Dict) -> str:
        """Decide heating control (simplified - would use temperature sensor in real implementation)"""
        if not self.is_occupied and self.energy_saving_mode:
            return 'off'
        
        # This is a placeholder - would integrate with temperature sensor
        return 'off'
    
    def _decide_cooling(self, airflow: Dict) -> str:
        """Decide cooling control (simplified - would use temperature sensor in real implementation)"""
        if not self.is_occupied and self.energy_saving_mode:
            return 'off'
        
        # This is a placeholder - would integrate with temperature sensor
        return 'off'
    
    def _update_energy_consumption(self, decisions: Dict):
        """Update estimated energy consumption"""
        # Power consumption estimates (in watts when on)
        power_consumption = {
            'lights': {'on': 60, 'increase': 80, 'decrease': 40, 'dim': 30, 'optimal': 60, 'off': 0},
            'ventilation': {'on': 50, 'increase': 70, 'decrease': 30, 'optimal': 50, 'off': 0},
            'heating': {'on': 2000, 'optimal': 2000, 'off': 0},
            'cooling': {'on': 1500, 'optimal': 1500, 'off': 0}
        }
        
        # Calculate energy for this update cycle based on actual elapsed time
        current_time = time.time()
        elapsed_seconds = current_time - self.last_decision_time
        self.last_decision_time = current_time
        
        dt = elapsed_seconds / 3600.0  # Convert elapsed seconds to hours
        
        current_power = 0.0
        for device in ['lights', 'ventilation', 'heating', 'cooling']:
            if device in decisions:
                state = decisions[device]
                power = power_consumption[device].get(state, 0)
                current_power += power
                energy_added = power * dt / 1000.0
                self.energy_consumption[device] += energy_added  # Convert to kWh
                
                # Log to database every minute (approximate)
                if time.time() - self.last_log_time >= 60.0:
                    cost_per_kwh = 0.12
                    self.db.log_energy(device, str(state), float(power), float(energy_added), float(energy_added * cost_per_kwh))
        
        
        self.current_power_watts = current_power
        if time.time() - self.last_log_time >= 60.0:
            self.last_log_time = time.time()
    
    def get_energy_statistics(self) -> Dict:
        """Get energy consumption statistics"""
        total_energy = sum(self.energy_consumption.values())
        session_duration = (time.time() - self.session_start_time) / 3600.0  # hours
        
        # Estimate cost (assuming $0.12 per kWh)
        cost_per_kwh = 0.12
        total_cost = total_energy * cost_per_kwh
        
        # Estimate savings from energy-saving mode
        estimated_savings = 0.0
        if self.energy_saving_mode:
            # Rough estimate: 30% savings
            estimated_savings = total_energy * 0.3 * cost_per_kwh
        
        return {
            'total_energy_kwh': round(total_energy, 4),
            'total_cost_usd': round(total_cost, 4),
            'estimated_savings_usd': round(estimated_savings, 4),
            'session_duration_hours': round(session_duration, 2),
            'current_power_watts': round(self.current_power_watts, 2),
            'average_power_watts': round(total_energy / session_duration * 1000, 2) if session_duration > 0 else 0,
            'breakdown': {k: round(v, 4) for k, v in self.energy_consumption.items()},
            'carbon_footprint_kg': round(total_energy * 0.5, 2)  # Rough estimate: 0.5 kg CO2 per kWh
        }
    
    def get_recommendations(self) -> List[str]:
        """Get energy-saving recommendations"""
        recommendations = []
        
        stats = self.get_energy_statistics()
        
        if stats['average_power_watts'] > 3000:
            recommendations.append("High energy consumption detected. Consider reducing device usage.")
        
        if not self.is_occupied:
            recommendations.append("No presence detected. All devices are in energy-saving mode.")
        
        if self.energy_consumption['lights'] > self.energy_consumption['ventilation']:
            recommendations.append("Consider using more natural light to reduce lighting energy.")
        
        # Check decision history for patterns
        if len(self.decision_history) > 10:
            recent_decisions = self.decision_history[-10:]
            lights_always_on = all(d.get('lights') != 'off' for d in recent_decisions)
            if lights_always_on and self.energy_saving_mode:
                recommendations.append("Lights are frequently on. Consider adjusting brightness threshold.")
        
        return recommendations

    def finalize_session(self):
        """Save final session summary to database"""
        stats = self.get_energy_statistics()
        summary = {
            'start_time': datetime.fromtimestamp(self.session_start_time).isoformat(),
            'end_time': datetime.now().isoformat(),
            'total_energy_kwh': float(stats.get('total_energy_kwh', 0)),
            'total_cost_usd': float(stats.get('total_cost_usd', 0)),
            'estimated_savings_usd': float(stats.get('estimated_savings_usd', 0)),
            'carbon_footprint_kg': float(stats.get('carbon_footprint_kg', 0))
        }
        self.db.save_session_summary(summary)
        print(f"Session summary saved: {stats['total_energy_kwh']:.4f} kWh")



