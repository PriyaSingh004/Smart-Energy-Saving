from flask import Blueprint, jsonify
from ..models import EnergyLog, ActivityLog, DeviceState

status_bp = Blueprint('status', __name__, url_prefix='/api')

@status_bp.route('/status', methods=['GET'])
def get_status():
    # Import latest_data from the package
    from .. import latest_data
    return jsonify(latest_data)

@status_bp.route('/control', methods=['POST'])
def control_device():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    device = data.get('device')
    state = data.get('state')
    
    # Update DeviceState in DB
    from ..models import db, DeviceState
    dev_state = DeviceState.query.filter_by(device_name=device).first()
    if not dev_state:
        dev_state = DeviceState(device_name=device)
        db.session.add(dev_state)
    
    dev_state.state = 'on' if state else 'off'
    db.session.commit()
    
    print(f"WEB CONTROL: {device} set to {state}")
    return jsonify({'status': 'success', 'message': f'{device} set to {state}'})

@status_bp.route('/history', methods=['GET'])
def get_history():
    logs = EnergyLog.query.order_by(EnergyLog.timestamp.desc()).limit(50).all()
    return jsonify([{
        "timestamp": log.timestamp.isoformat(),
        "device": log.device,
        "energy": log.energy_kwh,
        "power": log.power_watts,
        "cost": log.cost_usd
    } for log in logs])
