"""
Find My Phone - Socket.IO Real-time Events

Handles real-time location updates, device actions, and viewer notifications.
"""

from flask_socketio import join_room, leave_room, emit
from datetime import datetime, UTC


def init_findmy_socketio(socketio, db):
    """Initialize Find My Phone Socket.IO event handlers."""

    @socketio.on('findmy:join_device_room')
    def join_device_room(data):
        """Join room for real-time updates of a specific device.
        
        Data:
        {
            "device_id": 1,
            "share_token": "abc123xyz" (optional for share-based access)
        }
        """
        from flask import session
        from backend.app import TrackedDevice, DeviceShare
        
        device_id = data.get('device_id')
        share_token = data.get('share_token')
        user_id = session.get('user_id')

        if not device_id:
            emit('error', {'message': 'device_id required'})
            return

        try:
            device = TrackedDevice.query.get(device_id)
            if not device:
                emit('error', {'message': 'Device not found'})
                return

            # Check permission
            has_permission = False

            # Owner always has permission
            if user_id and device.owner_user_id == user_id:
                has_permission = True

            # Check if shared with this user
            if not has_permission and user_id:
                share = DeviceShare.query.filter_by(
                    device_id=device_id,
                    viewer_user_id=user_id,
                    is_active=True
                ).first()
                if share and (not share.expires_at or share.expires_at > datetime.now(UTC)):
                    has_permission = True

            # Check public share
            if not has_permission and share_token:
                share = DeviceShare.query.filter_by(
                    device_id=device_id,
                    share_token=share_token,
                    is_active=True
                ).first()
                if share and (not share.expires_at or share.expires_at > datetime.now(UTC)):
                    has_permission = True

            if not has_permission:
                emit('error', {'message': 'Access denied'})
                return

            room_id = f'device:{device_id}'
            join_room(room_id)
            emit('joined_room', {'device_id': device_id, 'room': room_id})

        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('findmy:leave_device_room')
    def leave_device_room(data):
        """Leave device room."""
        device_id = data.get('device_id')
        if device_id:
            room_id = f'device:{device_id}'
            leave_room(room_id)
            emit('left_room', {'device_id': device_id})

    @socketio.on('findmy:device_online')
    def device_online(data):
        """Device agent reports it's online.
        
        Headers (via auth):
        Authorization: Bearer {device_token}
        """
        from flask import request
        from backend.app import TrackedDevice

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            emit('error', {'message': 'Invalid auth'})
            return

        device_token = auth_header.split('Bearer ')[1]

        try:
            device = TrackedDevice.query.filter_by(device_token=device_token).first()
            if not device:
                emit('error', {'message': 'Device not found'})
                return

            device.last_seen_at = datetime.now(UTC)
            db.session.commit()

            # Notify viewers
            room_id = f'device:{device.id}'
            emit('device_status_changed', {
                'device_id': device.id,
                'status': 'online',
                'timestamp': device.last_seen_at.isoformat()
            }, room=room_id)

        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('findmy:device_offline')
    def device_offline(data):
        """Device agent reports it's going offline."""
        from flask import request
        from backend.app import TrackedDevice

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            emit('error', {'message': 'Invalid auth'})
            return

        device_token = auth_header.split('Bearer ')[1]

        try:
            device = TrackedDevice.query.filter_by(device_token=device_token).first()
            if not device:
                emit('error', {'message': 'Device not found'})
                return

            # Notify viewers
            room_id = f'device:{device.id}'
            emit('device_status_changed', {
                'device_id': device.id,
                'status': 'offline',
                'timestamp': datetime.now(UTC).isoformat()
            }, room=room_id)

        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('findmy:location_update_stream')
    def location_update_stream(data):
        """Stream location update to all viewers (real-time).
        
        Data:
        {
            "device_id": 1,
            "latitude": 5.6037,
            "longitude": -0.1870,
            "accuracy": 10.5,
            "timestamp": "2024-01-15T10:30:00Z"
        }
        """
        from backend.app import TrackedDevice

        device_id = data.get('device_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')

        if not all([device_id, latitude, longitude]):
            emit('error', {'message': 'Missing required fields'})
            return

        try:
            device = TrackedDevice.query.get(device_id)
            if not device:
                emit('error', {'message': 'Device not found'})
                return

            # Broadcast to all viewers in device room
            room_id = f'device:{device_id}'
            emit('findmy:location_update_stream', {
                'device_id': device_id,
                'latitude': latitude,
                'longitude': longitude,
                'accuracy': accuracy,
                'timestamp': datetime.now(UTC).isoformat()
            }, room=room_id)

        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('findmy:alarm_ack')
    def alarm_ack(data):
        """Device acknowledges alarm was received/played."""
        from flask import request
        from backend.app import TrackedDevice

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            emit('error', {'message': 'Invalid auth'})
            return

        device_token = auth_header.split('Bearer ')[1]

        try:
            device = TrackedDevice.query.filter_by(device_token=device_token).first()
            if not device:
                emit('error', {'message': 'Device not found'})
                return

            # Notify viewers
            room_id = f'device:{device.id}'
            emit('alarm_acknowledged', {
                'device_id': device.id,
                'timestamp': datetime.now(UTC).isoformat()
            }, room=room_id)

        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('findmy:lock_ack')
    def lock_ack(data):
        """Device acknowledges remote lock was received."""
        from flask import request
        from backend.app import TrackedDevice

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            emit('error', {'message': 'Invalid auth'})
            return

        device_token = auth_header.split('Bearer ')[1]

        try:
            device = TrackedDevice.query.filter_by(device_token=device_token).first()
            if not device:
                emit('error', {'message': 'Device not found'})
                return

            # Notify viewers
            room_id = f'device:{device.id}'
            emit('lock_acknowledged', {
                'device_id': device.id,
                'timestamp': datetime.now(UTC).isoformat()
            }, room=room_id)

        except Exception as e:
            emit('error', {'message': str(e)})
