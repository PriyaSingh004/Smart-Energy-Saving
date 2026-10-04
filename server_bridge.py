"""
Dashboard API Bridge
Flask server to bridge the Python system with the Web Dashboard
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
from datetime import datetime
try:
    from waitress import serve
    WAITRESS_AVAILABLE = True
except ImportError:
    WAITRESS_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# Global state to store latest data from the main system
latest_data = {
    'stats': {
        'energy': 0.0,
        'cost': 0.0,
        'savings': 0.0,
        'carbon': 0.0,
        'occupancy': 'unoccupied',
        'duration': 0
    },
    'devices': {
        'lights': 'off',
        'ventilation': 'off'
    },
    'occupancy': 'unoccupied',
    'activities': []
}

@app.route('/', methods=['GET'])
def index():
    """Root route to show API is running"""
    return jsonify({
        'status': 'online',
        'message': 'Smart Energy API is running',
        'endpoints': {
            'status': '/api/status',
            'control': '/api/control'
        },
        'dashboard_instruction': 'To view the UI, run "npm run dev" in the web_dashboard folder'
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get latest system status"""
    return jsonify(latest_data)

@app.route('/api/control', methods=['POST'])
def control_device():
    """Control a device from the dashboard"""
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    device = data.get('device')
    state = data.get('state')
    # In a real system, this would send a command to the hardware/main loop
    print(f"Control command received: {device} -> {state}")
    return jsonify({'status': 'success', 'message': f'{device} set to {state}'})

def update_bridge_data(new_data):
    """Method called by the main system to update bridge data"""
    global latest_data
    
    # Safe updates to avoid lint issues with dynamic dicts
    stats = latest_data['stats']
    energy_info = new_data.get('energy_stats', {})
    
    stats['energy'] = energy_info.get('total_energy_kwh', 0.0)
    stats['cost'] = energy_info.get('total_cost_usd', 0.0)
    stats['savings'] = energy_info.get('estimated_savings_usd', 0.0)
    stats['carbon'] = energy_info.get('carbon_footprint_kg', 0.0)
    
    # Tracking occupancy and duration
    decisions = new_data.get('decisions', {})
    stats['occupancy'] = decisions.get('occupancy_status', 'unoccupied')
    stats['duration'] = decisions.get('duration_seconds', 0)
    
    latest_data['occupancy'] = stats['occupancy']
    
    devices = latest_data['devices']
    devices['lights'] = decisions.get('lights', 'off')
    devices['ventilation'] = decisions.get('ventilation', 'off')
    
    # Add activity if relevant
    if new_data.get('pose_analysis', {}).get('activity_type'):
        activity = {
            'id': int(time.time()),
            'time': datetime.now().strftime("%H:%M:%S"),
            'message': f"Activity: {new_data['pose_analysis']['activity_type']}",
            'type': 'system'
        }
        # Cast to list to avoid lint issues if any
        activities = latest_data.get('activities', [])
        if isinstance(activities, list):
            activities.insert(0, activity)
            latest_data['activities'] = activities[:10]

def start_api_server():
    """Function to start the server in a separate thread"""
    if WAITRESS_AVAILABLE:
        print("Starting production-ready server (Waitress) on port 5000...")
        serve(app, host='0.0.0.0', port=5000)
    else:
        print("Waitress not found. Starting Flask development server on port 5000...")
        app.run(port=5000, host='0.0.0.0')

if __name__ == '__main__':
    start_api_server()
