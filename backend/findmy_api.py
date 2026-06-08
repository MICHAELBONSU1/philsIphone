"""
Find My Phone - Apple-style API endpoints

This module contains all device tracking, sharing, and location APIs.
"""

from flask import request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, UTC, timedelta
import secrets
import string


def init_findmy_routes(app, db, socketio):
    """Initialize Find My Phone API routes."""

    # =====================================================================
    # DEVICE REGISTRATION & MANAGEMENT
    # =====================================================================

    @app.route('/api/findmy/device/register', methods=['POST'])
    def register_device():
        """Register a new device for tracking.
        
        Request:
        {
            "device_label": "Phil's iPhone",
            "device_type": "iPhone"
        }
        
        Response:
        {
            "success": true,
            "device_id": 1,
            "device_token": "DEV-abc123xyz",
            "message": "Device registered"
        }
        """
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json() or {}
        device_label = data.get('device_label', 'My Device')
        device_type = data.get('device_type', 'iPhone')

        # Generate unique device token
        device_token = 'DEV-' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

        try:
            from backend.app import TrackedDevice
            device = TrackedDevice(
                owner_user_id=session['user_id'],
                device_label=device_label,
                device_type=device_type,
                device_token=device_token,
                is_active=True
            )
            db.session.add(device)
            db.session.commit()

            return jsonify({
                'success': True,
                'device_id': device.id,
                'device_token': device_token,
                'device_label': device.device_label,
                'message': 'Device registered successfully'
            }), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/list', methods=['GET'])
    def list_devices():
        """List all devices owned by the current user."""
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            from backend.app import TrackedDevice
            devices = TrackedDevice.query.filter_by(
                owner_user_id=session['user_id'],
                is_active=True
            ).all()

            result = []
            for dev in devices:
                result.append({
                    'id': dev.id,
                    'device_label': dev.device_label,
                    'device_type': dev.device_type,
                    'last_lat': dev.last_lat,
                    'last_lon': dev.last_lon,
                    'last_seen_at': dev.last_seen_at.isoformat() if dev.last_seen_at else None,
                    'is_active': dev.is_active,
                    'created_at': dev.created_at.isoformat()
                })

            return jsonify({
                'success': True,
                'devices': result,
                'count': len(result)
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/<int:device_id>', methods=['GET'])
    def get_device(device_id):
        """Get device details (owner only)."""
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            from backend.app import TrackedDevice
            device = TrackedDevice.query.filter_by(
                id=device_id,
                owner_user_id=session['user_id']
            ).first()

            if not device:
                return jsonify({'error': 'Device not found'}), 404

            return jsonify({
                'success': True,
                'device': {
                    'id': device.id,
                    'device_label': device.device_label,
                    'device_type': device.device_type,
                    'last_lat': device.last_lat,
                    'last_lon': device.last_lon,
                    'last_seen_at': device.last_seen_at.isoformat() if device.last_seen_at else None,
                    'is_active': device.is_active,
                    'created_at': device.created_at.isoformat()
                }
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/<int:device_id>/update', methods=['PUT'])
    def update_device(device_id):
        """Update device settings (owner only)."""
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json() or {}

        try:
            from backend.app import TrackedDevice
            device = TrackedDevice.query.filter_by(
                id=device_id,
                owner_user_id=session['user_id']
            ).first()

            if not device:
                return jsonify({'error': 'Device not found'}), 404

            if 'device_label' in data:
                device.device_label = data['device_label']

            if 'lock_pin' in data:
                device.lock_pin_hash = generate_password_hash(data['lock_pin'])

            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Device updated',
                'device': {
                    'id': device.id,
                    'device_label': device.device_label,
                    'device_type': device.device_type
                }
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # =====================================================================
    # LOCATION TRACKING
    # =====================================================================

    @app.route('/api/findmy/device/<int:device_id>/location/update', methods=['POST'])
    def update_device_location(device_id):
        """Update device location (device agent reports).
        
        Headers:
        Authorization: Bearer {device_token}
        
        Request:
        {
            "latitude": 5.6037,
            "longitude": -0.1870,
            "accuracy": 10.5
        }
        """
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid auth header'}), 401

        device_token = auth_header.split('Bearer ')[1]

        try:
            from backend.app import TrackedDevice, LocationHistory
            device = TrackedDevice.query.filter_by(device_token=device_token).first()

            if not device:
                return jsonify({'error': 'Device token invalid'}), 401

            data = request.get_json() or {}
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            accuracy = data.get('accuracy')

            if latitude is None or longitude is None:
                return jsonify({'error': 'latitude and longitude required'}), 400

            # Update device location
            device.last_lat = latitude
            device.last_lon = longitude
            device.last_seen_at = datetime.now(UTC)

            # Record history
            history = LocationHistory(
                device_id=device.id,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy
            )

            db.session.add(history)
            db.session.commit()

            # Broadcast to viewers via Socket.IO
            timestamp_iso = datetime.now(UTC).isoformat()
            socketio.emit('findmy:location_update_stream', {
                'device_id': device.id,
                'latitude': latitude,
                'longitude': longitude,
                'accuracy': accuracy,
                'timestamp': timestamp_iso
            }, room=f'device:{device.id}')

            return jsonify({
                'success': True,
                'message': 'Location updated'
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/<int:device_id>/location/current', methods=['GET'])
    def get_current_location(device_id):
        """Get current device location (viewers with permission).
        
        Query params:
        share_token: (optional) for share-based access
        """
        share_token = request.args.get('share_token')
        user_id = session.get('user_id')

        try:
            from backend.app import TrackedDevice, DeviceShare
            device = TrackedDevice.query.get(device_id)

            if not device:
                return jsonify({'error': 'Device not found'}), 404

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
                return jsonify({'error': 'Access denied'}), 403

            return jsonify({
                'success': True,
                'location': {
                    'device_id': device.id,
                    'device_label': device.device_label,
                    'latitude': device.last_lat,
                    'longitude': device.last_lon,
                    'accuracy': None,
                    'last_seen_at': device.last_seen_at.isoformat() if device.last_seen_at else None
                }
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/<int:device_id>/location/history', methods=['GET'])
    def get_location_history(device_id):
        """Get location history (owner or authorized viewers).
        
        Query params:
        limit: max results (default 100)
        share_token: for share-based access
        """
        limit = request.args.get('limit', 100, type=int)
        share_token = request.args.get('share_token')
        user_id = session.get('user_id')

        try:
            from backend.app import TrackedDevice, DeviceShare, LocationHistory
            device = TrackedDevice.query.get(device_id)

            if not device:
                return jsonify({'error': 'Device not found'}), 404

            # Permission check (same as get_current_location)
            has_permission = False
            if user_id and device.owner_user_id == user_id:
                has_permission = True
            elif user_id:
                share = DeviceShare.query.filter_by(
                    device_id=device_id,
                    viewer_user_id=user_id,
                    is_active=True
                ).first()
                if share and (not share.expires_at or share.expires_at > datetime.now(UTC)):
                    has_permission = True
            if not has_permission and share_token:
                share = DeviceShare.query.filter_by(
                    device_id=device_id,
                    share_token=share_token,
                    is_active=True
                ).first()
                if share and (not share.expires_at or share.expires_at > datetime.now(UTC)):
                    has_permission = True

            if not has_permission:
                return jsonify({'error': 'Access denied'}), 403

            history = LocationHistory.query.filter_by(device_id=device_id)\
                .order_by(LocationHistory.timestamp.desc())\
                .limit(limit).all()

            result = []
            for loc in history:
                result.append({
                    'latitude': loc.latitude,
                    'longitude': loc.longitude,
                    'accuracy': loc.accuracy,
                    'timestamp': loc.timestamp.isoformat()
                })

            return jsonify({
                'success': True,
                'history': result,
                'count': len(result)
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # =====================================================================
    # DEVICE ACTIONS (Alarm, Lock, Unlock)
    # =====================================================================

    @app.route('/api/findmy/device/<int:device_id>/alarm', methods=['POST'])
    def trigger_alarm(device_id):
        """Trigger alarm on device (requires view_and_alert permission)."""
        share_token = request.args.get('share_token')
        user_id = session.get('user_id')

        try:
            from backend.app import TrackedDevice, DeviceShare
            device = TrackedDevice.query.get(device_id)

            if not device:
                return jsonify({'error': 'Device not found'}), 404

            # Check permission
            has_permission = False
            min_permission = 'view_and_alert'

            if user_id and device.owner_user_id == user_id:
                has_permission = True
            elif user_id:
                share = DeviceShare.query.filter_by(
                    device_id=device_id,
                    viewer_user_id=user_id,
                    is_active=True
                ).first()
                if share and (not share.expires_at or share.expires_at > datetime.now(UTC)):
                    # Check permission level
                    if share.permission_level in ['view_and_alert', 'full_control']:
                        has_permission = True

            if not has_permission:
                return jsonify({'error': 'Access denied'}), 403

            # Broadcast alarm event
            socketio.emit('alarm_triggered', {
                'device_id': device.id,
                'timestamp': datetime.now(UTC).isoformat()
            }, room=f'device:{device.id}')

            return jsonify({
                'success': True,
                'message': 'Alarm triggered'
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/<int:device_id>/lock', methods=['POST'])
    def remote_lock(device_id):
        """Remote lock device (requires full_control permission)."""
        share_token = request.args.get('share_token')
        user_id = session.get('user_id')
        data = request.get_json() or {}

        try:
            from backend.app import TrackedDevice, DeviceShare
            device = TrackedDevice.query.get(device_id)

            if not device:
                return jsonify({'error': 'Device not found'}), 404

            # Check permission
            has_permission = False

            if user_id and device.owner_user_id == user_id:
                has_permission = True
            elif user_id:
                share = DeviceShare.query.filter_by(
                    device_id=device_id,
                    viewer_user_id=user_id,
                    is_active=True
                ).first()
                if share and (not share.expires_at or share.expires_at > datetime.now(UTC)):
                    if share.permission_level == 'full_control':
                        has_permission = True

            if not has_permission:
                return jsonify({'error': 'Access denied'}), 403

            message = data.get('message', 'Device locked remotely')
            contact_number = data.get('contact_number', '')

            # Broadcast lock event
            socketio.emit('device_locked', {
                'device_id': device.id,
                'message': message,
                'contact_number': contact_number,
                'timestamp': datetime.now(UTC).isoformat()
            }, room=f'device:{device.id}')

            return jsonify({
                'success': True,
                'message': 'Device locked'
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/<int:device_id>/unlock', methods=['POST'])
    def remote_unlock(device_id):
        """Unlock device with PIN (device agent verifies PIN)."""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid auth header'}), 401

        device_token = auth_header.split('Bearer ')[1]
        data = request.get_json() or {}

        try:
            from backend.app import TrackedDevice
            device = TrackedDevice.query.filter_by(device_token=device_token).first()

            if not device:
                return jsonify({'error': 'Device token invalid'}), 401

            pin = data.get('pin')
            if not pin:
                return jsonify({'error': 'PIN required'}), 400

            if not device.lock_pin_hash or not check_password_hash(device.lock_pin_hash, pin):
                return jsonify({'error': 'Invalid PIN'}), 401

            # Broadcast unlock event
            socketio.emit('device_unlocked', {
                'device_id': device.id,
                'timestamp': datetime.now(UTC).isoformat()
            }, room=f'device:{device.id}')

            return jsonify({
                'success': True,
                'message': 'Device unlocked'
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # =====================================================================
    # DEVICE SHARING
    # =====================================================================

    @app.route('/api/findmy/device/<int:device_id>/share', methods=['POST'])
    def share_device(device_id):
        """Share device with another user (owner only).
        
        Request:
        {
            "viewer_user_id": 5,
            "permission_level": "view_only",
            "expires_in_days": 7
        }
        """
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json() or {}

        try:
            from backend.app import TrackedDevice, DeviceShare
            device = TrackedDevice.query.filter_by(
                id=device_id,
                owner_user_id=session['user_id']
            ).first()

            if not device:
                return jsonify({'error': 'Device not found'}), 404

            viewer_user_id = data.get('viewer_user_id')
            permission_level = data.get('permission_level', 'view_only')
            expires_in_days = data.get('expires_in_days')

            if permission_level not in ['view_only', 'view_and_alert', 'full_control']:
                return jsonify({'error': 'Invalid permission level'}), 400

            # Generate share code and token
            share_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            share_token = secrets.token_urlsafe(32)

            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

            share = DeviceShare(
                device_id=device_id,
                viewer_user_id=viewer_user_id,
                share_code=share_code,
                share_token=share_token,
                permission_level=permission_level,
                expires_at=expires_at,
                is_active=True
            )

            db.session.add(share)
            db.session.commit()

            return jsonify({
                'success': True,
                'share_id': share.id,
                'share_code': share_code,
                'share_token': share_token,
                'message': 'Device shared'
            }), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/<int:device_id>/shares', methods=['GET'])
    def list_shares(device_id):
        """List all shares for a device (owner only)."""
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            from backend.app import TrackedDevice, DeviceShare
            device = TrackedDevice.query.filter_by(
                id=device_id,
                owner_user_id=session['user_id']
            ).first()

            if not device:
                return jsonify({'error': 'Device not found'}), 404

            shares = DeviceShare.query.filter_by(device_id=device_id).all()

            result = []
            for share in shares:
                result.append({
                    'share_id': share.id,
                    'share_code': share.share_code,
                    'viewer_user_id': share.viewer_user_id,
                    'permission_level': share.permission_level,
                    'expires_at': share.expires_at.isoformat() if share.expires_at else None,
                    'is_active': share.is_active,
                    'created_at': share.created_at.isoformat()
                })

            return jsonify({
                'success': True,
                'shares': result,
                'count': len(result)
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/device/<int:device_id>/share/<int:share_id>/revoke', methods=['DELETE'])
    def revoke_share(device_id, share_id):
        """Revoke a device share (owner only)."""
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            from backend.app import TrackedDevice, DeviceShare
            device = TrackedDevice.query.filter_by(
                id=device_id,
                owner_user_id=session['user_id']
            ).first()

            if not device:
                return jsonify({'error': 'Device not found'}), 404

            share = DeviceShare.query.get(share_id)

            if not share or share.device_id != device_id:
                return jsonify({'error': 'Share not found'}), 404

            db.session.delete(share)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Share revoked'
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/findmy/share/<share_code>/access', methods=['GET'])
    def access_public_share(share_code):
        """Access device via public share code."""
        try:
            from backend.app import DeviceShare
            share = DeviceShare.query.filter_by(share_code=share_code, is_active=True).first()

            if not share:
                return jsonify({'error': 'Share not found'}), 404

            if share.expires_at and share.expires_at < datetime.now(UTC):
                return jsonify({'error': 'Share expired'}), 410

            return jsonify({
                'success': True,
                'share_token': share.share_token,
                'device_id': share.device_id,
                'permission_level': share.permission_level,
                'expires_at': share.expires_at.isoformat() if share.expires_at else None
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500
