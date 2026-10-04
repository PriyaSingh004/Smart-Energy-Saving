import sys
import os

# Add project root to path
sys.path.append(os.path.abspath('.'))

from api_v2 import create_app, db
from api_v2.models import User, DeviceState, EnergyLog, ActivityLog

app = create_app()
with app.app_context():
    db.create_all()
    # Add initial device states if empty
    if not DeviceState.query.first():
        devices = ['lights', 'ventilation', 'heating', 'cooling']
        for d in devices:
            db.session.add(DeviceState(device_name=d, state='off'))
        db.session.commit()
    print("Database initialized successfully!")
