# Find My Phone - Apple-Style Device Tracking System

A complete device tracking and sharing system built with Flask, Socket.IO, and Leaflet. Works like Apple's Find My, with device registration, real-time tracking, permission-based sharing, remote actions (alarm, lock), and multi-viewer support.

## Architecture Overview

### Key Components

1. **Database Models**
   - `TrackedDevice`: Individual devices registered for tracking
   - `LocationHistory`: GPS location records with timestamps
   - `DeviceShare`: Sharing permissions and access tokens for viewers
   - `User`: Device owners and viewers

2. **API Endpoints** (`/api/findmy/*`)
   - Device management (register, list, update)
   - Location tracking (update, get current, get history)
   - Device actions (alarm, lock, unlock)
   - Device sharing (create, list, revoke shares)

3. **Real-time Events** (Socket.IO)
   - Location broadcasts to viewers
   - Device state changes (online/offline)
   - Remote commands (alarm, lock, unlock)
   - Action acknowledgments

4. **User Interfaces**
   - **Owner Dashboard** (`/findmy`): Manage devices, view all locations on map
   - **Shared Viewer** (`/findmy/viewer`): View shared device based on permissions
   - **Device Agent** (`/findmy/agent`): Runs on the device, enables GPS reporting and receives remote commands

## Permission Levels

Find My supports three permission levels for sharing:

### `view_only`
- Can see device location on map
- Can see location history
- Cannot trigger actions
- **Best for**: Family members who just need to know if you're safe

### `view_and_alert`
- Can view location
- Can trigger emergency alarm
- Cannot lock/unlock device
- **Best for**: Trusted contacts who can help in emergencies

### `full_control`
- Can view location
- Can trigger alarm
- Can remote lock device
- Can unlock with PIN
- **Best for**: Owner's primary account, emergency contacts with full trust

## Quick Start

### 1. Owner Registers Device

```bash
POST /api/findmy/device/register
Content-Type: application/json

{
    "device_label": "Phil's iPhone",
    "device_type": "iPhone"
}

Response:
{
    "success": true,
    "device_id": 1,
    "device_token": "DEV-abc123xyz...",
    "device_label": "Phil's iPhone"
}
```

### 2. Device Agent Connects & Starts Tracking

Visit `/findmy/agent` on the device:
- Paste device token
- Click "Connect Device"
- Click "Start Live Tracking"
- Device begins reporting GPS every 5 seconds

### 3. Owner Views Dashboard

Visit `/findmy` (requires login):
- Sees all owned devices with live status
- Views current location on map
- Can register new devices
- Can share devices with others

### 4. Owner Shares Device

```bash
POST /api/findmy/device/1/share
Content-Type: application/json

{
    "viewer_user_id": 5,
    "permission_level": "view_and_alert",
    "expires_in_days": 7
}

Response:
{
    "success": true,
    "share_code": "ABC123",
    "share_token": "token_xyz...",
    "share_id": 42
}
```

### 5. Viewer Accesses Shared Device

Visit `/findmy/viewer?device_id=1&token=token_xyz`
- Sees device location in real-time
- Controls limited to their permission level
- Can trigger alarm if permission allows
- Automatically disconnects when share expires

## API Reference

### Device Management

#### Register Device
```
POST /api/findmy/device/register
Authorization: Session
```

#### List Owned Devices
```
GET /api/findmy/device/list
Authorization: Session
```

#### Get Device Details
```
GET /api/findmy/device/{device_id}
Authorization: Session
```

#### Update Device Settings
```
PUT /api/findmy/device/{device_id}/update
Authorization: Session
```

### Location Tracking

#### Update Location (Device Reports)
```
POST /api/findmy/device/{device_id}/location/update
Authorization: Bearer {device_token}
Content-Type: application/json

{
    "latitude": 5.6037,
    "longitude": -0.1870,
    "accuracy": 10.5
}
```

#### Get Current Location
```
GET /api/findmy/device/{device_id}/location/current?share_token={token}
```

#### Get Location History
```
GET /api/findmy/device/{device_id}/location/history?limit=100&share_token={token}
```

### Device Actions

#### Trigger Alarm
```
POST /api/findmy/device/{device_id}/alarm?share_token={token}
```

#### Remote Lock
```
POST /api/findmy/device/{device_id}/lock?share_token={token}
Content-Type: application/json

{
    "message": "Device locked remotely",
    "contact_number": "+1-234-567-8900"
}
```

#### Unlock with PIN
```
POST /api/findmy/device/{device_id}/unlock
Authorization: Bearer {device_token}
Content-Type: application/json

{
    "pin": "1234"
}
```

### Device Sharing

#### Create Share
```
POST /api/findmy/device/{device_id}/share
Authorization: Session
```

#### List Shares
```
GET /api/findmy/device/{device_id}/shares
Authorization: Session
```

#### Revoke Share
```
DELETE /api/findmy/device/{device_id}/share/{share_id}
Authorization: Session
```

#### Access Public Share
```
GET /api/findmy/share/{share_code}/access
```

## Socket.IO Events

### Client → Server

#### Join Device Room
```javascript
socket.emit('findmy:join_device_room', {
    device_id: 1,
    share_token: "token_xyz" // optional
});
```

#### Device Goes Online
```javascript
socket.emit('findmy:device_online', {});
```

#### Device Goes Offline
```javascript
socket.emit('findmy:device_offline', {});
```

#### Alarm Acknowledged
```javascript
socket.emit('findmy:alarm_ack', {});
```

#### Lock Acknowledged
```javascript
socket.emit('findmy:lock_ack', {});
```

### Server → Clients

#### Location Update
```javascript
// Broadcast to device room
{
    device_id: 1,
    latitude: 5.6037,
    longitude: -0.1870,
    accuracy: 10.5,
    timestamp: "2024-01-15T10:30:00Z"
}
```

#### Device Status Changed
```javascript
{
    device_id: 1,
    status: "online" | "offline",
    timestamp: "2024-01-15T10:30:00Z"
}
```

#### Device Locked
```javascript
{
    device_id: 1,
    message: "Device locked remotely",
    contact_number: "+1-234-567-8900",
    timestamp: "2024-01-15T10:30:00Z"
}
```

#### Device Unlocked
```javascript
{
    device_id: 1,
    timestamp: "2024-01-15T10:30:00Z"
}
```

## Testing Workflow

### End-to-End Test Flow

1. **Setup Owner Account**
   - Login as `phil` or create new account
   - Navigate to `/findmy`

2. **Register Test Device**
   - Click "Register Device"
   - Name: "Test iPhone"
   - Type: "iPhone"
   - Copy device token

3. **Open Device Agent**
   - Open new tab: `http://localhost:5000/findmy/agent`
   - Paste device token
   - Click "Connect Device"

4. **Start Location Updates**
   - Click "Start Live Tracking"
   - Device will request GPS access
   - Owner dashboard should show device as "Online"

5. **Share Device**
   - Owner dashboard: Click "Share" on device
   - Create share with:
     - Permission: "view_and_alert"
     - Expires in: 7 days
   - Copy share code

6. **Test Shared Viewer**
   - Open incognito window or logout
   - Navigate to `/findmy/viewer?device_id=1&token={share_token}`
   - Should see device location and alarm button

7. **Test Alarm**
   - Viewer clicks "Emergency Alarm"
   - Device agent should show alarm notification
   - Alarm sound plays

8. **Test Full Control**
   - Share device again with "full_control" permission
   - Viewer can now click "Remote Lock"
   - Device shows lock screen
   - Viewer enters PIN (1234 by default)
   - Device unlocks

## Development Notes

### Key Files

```
backend/
├── app.py                  # Main Flask app, database models
├── findmy_api.py          # All REST API endpoints
└── findmy_socketio.py     # Socket.IO event handlers

templates/
├── findmy_owner.html      # Owner dashboard
├── findmy_viewer.html     # Shared device viewer
└── findmy_device_agent.html # Device agent UI
```

### Default Test PIN

Default lock PIN is `1234`. To set a custom PIN when registering a device, pass `lock_pin` in the request.

### Location Update Frequency

Device reports location every 5 seconds by default. Adjust in `findmy_device_agent.html`:

```javascript
{
    enableHighAccuracy: true,
    maximumAge: 5000,  // <-- Change this (milliseconds)
    timeout: 10000
}
```

### Database

Tables automatically created on startup:
- `tracked_device`: Device registry
- `location_history`: GPS location records
- `device_share`: Sharing permissions and tokens
- `user`: Account information

## Security Considerations

1. **Device Token**: Should be treated like a password. Never log or expose publicly.
2. **Share Token**: Can be time-limited. Automatically invalidated after `expires_at`.
3. **PIN**: Hashed using werkzeug's `generate_password_hash()`.
4. **Permission Levels**: Enforced on all endpoints. No way to bypass.
5. **HTTPS**: Recommended for production to protect tokens in transit.

## Future Enhancements

- [ ] Geofencing (alerts when device leaves area)
- [ ] Location history export (CSV/PDF)
- [ ] Multi-device tracking on one map
- [ ] Batch sharing (share multiple devices)
- [ ] Android/iOS app integration
- [ ] Battery level tracking
- [ ] Network info (WiFi/cellular)
- [ ] Photo library backup
- [ ] Anti-theft mode (aggressive tracking)
- [ ] Family location groups

## Troubleshooting

### Device Not Showing on Map
- Check device token is correct
- Verify GPS is enabled and permissions granted
- Check browser console for errors
- Confirm device is connected to internet

### Location Updates Not Real-time
- Check Socket.IO connection in browser DevTools
- Verify device is actively tracking (not "Idle")
- Check browser has granted location permissions

### Shared Link Not Working
- Verify share token hasn't expired
- Check share is still active (not revoked)
- Clear browser cache
- Verify device_id matches

### Lock Screen Not Showing
- Verify device has "full_control" permission
- Check Socket.IO connection
- Ensure PIN is set on device

## Support

For issues, questions, or contributions, refer to the main project repository.
