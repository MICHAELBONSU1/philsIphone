# Phil's iPhone - Complete System Functionality Documentation

## Overview

Phil's iPhone is a comprehensive e-commerce and device management platform built with Flask (Python backend) and HTML/CSS/JavaScript frontend. The system combines marketplace functionality with advanced device tracking, delivery management, real-time messaging, and Apple ecosystem integration.

---

## Core System Architecture

### Technology Stack
- **Backend**: Flask (Python) with Flask-SQLAlchemy ORM
- **Database**: SQLite (instance/site.db)
- **Real-time Communication**: Flask-SocketIO for WebSocket connections
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **Authentication**: Session-based with password hashing (Werkzeug)
- **File Storage**: Local filesystem (static/uploads/)

### Database Models
1. **User** - User accounts with roles and permissions
2. **Item** - Marketplace listings (phones, laptops)
3. **Message** - WhatsApp-style messaging system
4. **Delivery** - Comprehensive delivery tracking system
5. **DeliveryUpdate** - Real-time delivery location updates
6. **News** - Apple news feed articles
7. **CallLog** - Audio/Video call history
8. **Request** - User permission requests
9. **TrackedDevice** - Find My Phone device registration
10. **DeviceShare** - Device sharing permissions
11. **LocationHistory** - GPS location tracking history

---

## 1. USER MANAGEMENT & AUTHENTICATION

### User Registration & Login
- **Registration**: Username, email, password with confirmation
- **Role Selection**: Users can register as "Rider" (delivery driver) or "Customer"
- **Login**: Secure authentication with password hashing
- **Session Management**: Persistent sessions with user metadata
- **Logout**: Clear session and redirect to home

### User Roles & Permissions
- **Customer**: Basic user, can browse and purchase items
- **Rider**: Delivery driver, can accept delivery jobs
- **Admin**: Can approve user posting requests, manage users
- **Almighty**: Super-admin with full system control
- **Can Post**: Permission flag for approved sellers

### User Profile
- View personal information
- Track user activity
- Manage account settings

---

## 2. MARKETPLACE & E-COMMERCE

### Item Listings
- **Categories**: Phones, Laptops, Other
- **Conditions**: New, Like-New, Used
- **Features**:
  - Image upload with automatic filename sanitization
  - Price display in Ghana Cedis (₵)
  - Seller information display
  - Item detail pages with full descriptions
  - Filter by category

### Item Management
- **Post Items**: Approved users can list items for sale
- **Edit/Delete**: Sellers can manage their own listings
- **Admin Override**: Admins can delete any listing
- **Image Handling**: Support for PNG, JPG, JPEG, GIF, WebP formats

### Featured Deals Section
- Curated promotional cards for:
  - Best Value iPhones
  - Latest iPhones
  - Pro Models
  - Budget Laptops

### Trade-In Service
- **Device Valuation**: Automatic pricing based on:
  - Device type (iPhone, iPad, MacBook)
  - Model and storage capacity
  - Condition (New, Like-New, Good, Fair, Poor)
  - Accessories included (+$25 per accessory)
- **Supported Devices**:
  - iPhones (15 series down to 11 series)
  - iPads (Pro, Air, Mini, standard)
  - MacBooks (Pro, Air models)

---

## 3. DELIVERY MANAGEMENT SYSTEM

### Delivery Workflow
Complete end-to-end delivery tracking with status progression:

1. **Requested** → Sender creates delivery request
2. **Pending Recipient** → Awaits recipient approval (if recipient specified)
3. **Requested** → Available for riders to accept
4. **Accepted** → Rider accepts the job
5. **Arrived at Pickup** → Rider arrives at pickup location
6. **Picked Up** → Package collected
7. **En Route** → Rider traveling to destination
8. **Arrived at Dropoff** → Rider at delivery location
9. **Roadside Handover** → Package handed to recipient
10. **Paid** → Delivery complete and paid

### Delivery Features

#### For Senders
- Create delivery requests with:
  - Pickup/dropoff coordinates and addresses
  - Contact information
  - Package details (type, size, handling requirements)
  - Timing preferences
  - Payment method selection
- Real-time tracking of delivery status
- Automatic rider matching based on proximity

#### For Recipients
- Receive delivery notifications
- Approve incoming deliveries with approval code
- Confirm handover completion
- Track delivery progress in real-time

#### For Riders
- View available delivery offers
- Accept delivery jobs
- Update delivery status at each stage
- GPS location tracking during active deliveries
- Online/offline availability toggle

### Pricing System (Bolt-Style)
- **0-1.5 km**: Base ₵2.00 + (distance × ₵20.0)
- **1.5-4 km**: Base ₵2.00 + (distance × ₵40.0)
- **5+ km**: Base ₵2.00 + (distance × ₵10.0)
- Distance calculated using Haversine formula
- Prices stored in cents for precision

### Real-Time Features
- Live rider location updates via Socket.IO
- Status change notifications to all parties
- System notifications for key events
- Delivery room for multi-user tracking

---

## 4. REAL-TIME MESSAGING (WhatsApp-Style)

### Messaging Features
- **Private Messaging**: One-to-one conversations
- **Real-Time Delivery**: Instant message delivery via WebSocket
- **Typing Indicators**: Show when other user is typing
- **Read Receipts**: Mark messages as read
- **Message Deletion**: Soft delete (is_deleted flag)
- **Media Support**: Send images, videos, audio files
- **Unread Count**: Badge showing unread message count

### Conversation Management
- **Contact List**: Sidebar showing all conversations
- **User Search**: Find new people to chat with
- **Active Conversations**: Only shows users you've chatted with
- **Message History**: Full conversation history per user

### Media Upload
- Supported formats: PNG, JPG, JPEG, GIF, WebP, MP4, AVI, MOV, MP3, WAV, OGG, M4A, WEBM
- Files stored in `static/uploads/messages/`
- Automatic file type detection

---

## 5. AUDIO/VIDEO CALLING (WebRTC)

### Call Features
- **Audio Calls**: Voice-only communication
- **Video Calls**: Face-to-face video calling
- **Call Initiation**: From messaging interface
- **Call Management**:
  - Incoming call notifications
  - Accept/Reject options
  - Call duration tracking
  - Call end confirmation

### Call Logging
- Persistent call records in database
- Track caller, receiver, type, status, duration
- Status tracking: Missed, Answered, Rejected, Ended
- Admin view of all call logs

### WebRTC Implementation
- **Signaling**: Server relays SDP offers/answers
- **ICE Candidates**: Peer connection establishment
- **Direct P2P**: Media streams don't pass through server
- **Room-based**: Users join per-user rooms for signaling

---

## 6. FIND MY PHONE (Apple-Style Tracking)

### Device Tracking System

#### For Device Owners
- **Register Devices**: Add phones/tablets to track
- **Device Management**:
  - Device label and type (iPhone, iPad, Mac)
  - Device token for authentication
  - Active/inactive status
- **Location Tracking**: Real-time GPS coordinates
- **Location History**: View historical locations
- **Remote Actions**:
  - Trigger alarm on device
  - Remote lock with custom message
  - Remote unlock

#### For Device Agents (on tracked device)
- **Location Reporting**: Send GPS coordinates to server
- **Receive Commands**: Alarm, lock, unlock via Socket.IO
- **Authentication**: Device token validation
- **Real-Time Updates**: Instant command execution

### Device Sharing System
- **Share Codes**: Human-readable sharing codes
- **Share Tokens**: Secure URL-based access
- **Permission Levels**:
  - **View Only**: See location on map
  - **View & Alert**: View + trigger alarm
  - **Full Control**: View + alarm + lock/unlock
- **Share Management**:
  - Expiration dates
  - Password protection
  - Private/public sharing
  - Active/inactive status

### Viewer Interface
- **Public Share Access**: View shared device location
- **Real-Time Updates**: Live location via WebSocket
- **Map Integration**: Visual location display
- **Action Buttons**: Trigger allowed actions

---

## 7. IMEI CHECKER

### Device Verification
- **IMEI Validation**: 15-digit format check
- **Luhn Algorithm**: Mathematical validation
- **API Integration**: IMEI.info API for real lookups
- **Device Information**:
  - Brand and model
  - Release year
  - Chipset information
  - Device status (Clean/Blacklisted)
  - TAC (Type Allocation Code) extraction

### Local Database
- TAC database in multiple formats (CSV, TSV, JSON)
- Fallback validation when API unavailable
- Debug mode for API response inspection

---

## 8. REPAIRS & DECODING SERVICES

### Repair Requests
- Submit repair requests
- Track repair status
- Communication with repair technicians

### Device Decoding
- IMEI-based device identification
- Model and specification lookup
- Authenticity verification

---

## 9. APPLE NEWS FEED

### Live News Integration
- **RSS Feed Parsing**: Fetch from Apple Newsroom
- **Categories**:
  - General Apple news
  - iPhone-specific news
  - iPad news
  - Mac news
- **Automatic Updates**: Background fetch every 30 minutes
- **Real-Time Push**: New articles pushed via Socket.IO

### News Features
- **Media Support**: Images and videos from Apple
- **Content Extraction**: Parse HTML for media URLs
- **Categorization**: Auto-categorize by feed source
- **Author Attribution**: Credit to Apple Newsroom

### News Display
- Grid layout on homepage
- Video playback support
- Image galleries
- Category badges
- Timestamp display

---

## 10. ADMIN PANELS

### Standard Admin Panel
- **User Management**:
  - View pending posting requests
  - Approve/revoke posting permissions
  - View all users (pending, approved)
- **Call Logs**: View personal call history
- **Quick Actions**: Approve users, manage requests

### Almighty Panel (Super Admin)
- **Complete System Overview**:
  - All users
  - All items/listings
  - All deliveries
  - All permission requests
  - All messages
  - All call logs (latest 100)
- **Management Actions**:
  - Delete users (except other almighty users)
  - Toggle admin status
  - Delete deliveries
  - Delete items
  - Delete requests
  - Delete messages (hard delete)
  - Delete call logs
- **Redirect Logic**: Almighty users auto-redirected from admin panel

---

## 11. REAL-TIME FEATURES (Socket.IO)

### Connection Management
- **User Rooms**: Per-user rooms for targeted messaging
- **Delivery Rooms**: Multi-user rooms for delivery tracking
- **FindMy Rooms**: Device and share-specific rooms
- **Auto-Join**: Users join rooms on connection

### Real-Time Events

#### Messaging Events
- `join_user` - Join user's personal room
- `new_message` - Receive new message
- `typing` / `typing_on` / `typing_off` - Typing indicators
- `mark_read_thread` - Mark messages as read
- `read_updated` - Read receipt confirmation

#### Delivery Events
- `join_delivery` - Join delivery tracking room
- `delivery_status_update` - Status change notification
- `delivery_offer` - New delivery available for riders
- `rider_location` - Rider GPS update
- `rider_location_update` - Broadcast rider location
- `join_rider_portal` - Rider-specific room

#### Call Events
- `call_initiate` - Start a call
- `call_incoming` - Receive incoming call
- `call_accept` - Accept call
- `call_reject` - Reject call
- `call_accepted` - Call accepted notification
- `call_rejected` - Call rejected notification
- `call_end` - End active call
- `call_ended` - Call ended notification

#### WebRTC Signaling
- `webrtc_offer` - Send SDP offer
- `webrtc_answer` - Send SDP answer
- `webrtc_ice_candidate` - Exchange ICE candidates

#### FindMy Events
- `join_findmy_device` - Device joins its room
- `join_findmy_share` - Viewer joins share room
- `device_location_update` - Location update
- `device_trigger_alarm` - Trigger device alarm
- `device_remote_lock` - Lock device remotely
- `device_remote_unlock` - Unlock device remotely

#### System Notifications
- `system_notification` - Push notification with sound
- `news_update` - New Apple news article

---

## 12. GEOLOCATION SERVICES

### Geocoding API
- **Nominatim Proxy**: Server-side geocoding
- **Address to Coordinates**: Convert addresses to lat/lon
- **CORS Handling**: Avoid browser restrictions
- **Error Handling**: Graceful fallbacks

### Routing API
- **OSRM Proxy**: Open Source Routing Machine
- **Route Calculation**: Driving directions
- **Distance Matrix**: Point-to-point distances
- **GeoJSON Output**: Route geometry for map display

### Location Tracking
- **User Location**: Track user's phone location
- **Device Location**: Track registered devices
- **Location History**: Store historical positions
- **Real-Time Updates**: WebSocket-based live tracking

---

## 13. UI/UX FEATURES

### Responsive Design
- Mobile-first approach
- Hamburger menu for mobile navigation
- Adaptive layouts for all screen sizes

### Visual Enhancements
- **Dark Mode**: Toggle between light/dark themes
- **Hero Section**: Animated gradient with floating particles
- **3D Parallax**: Mouse-move parallax effects
- **Fade-In Animations**: Scroll-triggered animations
- **Skeleton Loading**: Placeholder loading states

### Interactive Elements
- **File Upload**: Click-to-upload with preview
- **Form Validation**: Real-time input validation
- **Auto-Hide Alerts**: Dismiss notifications after 5 seconds
- **Dropdown Menus**: User menu interactions
- **Filter Buttons**: Category filtering with active states

### Navigation
- **User Menu**: Profile, settings, logout
- **Feature Tiles**: Quick access to major features
- **Breadcrumbs**: Navigation context
- **Search**: User and item search functionality

---

## 14. SECURITY FEATURES

### Authentication Security
- **Password Hashing**: Werkzeug secure hashing
- **Session Management**: Secure cookie-based sessions
- **CSRF Protection**: Flask built-in protection
- **Input Sanitization**: Secure filename handling

### Authorization
- **Role-Based Access**: Different permissions per role
- **Ownership Checks**: Users can only modify own content
- **Admin Verification**: Admin-only routes protected
- **Almighty Checks**: Super-admin exclusive actions

### Data Protection
- **Soft Deletes**: Messages marked as deleted, not removed
- **Approval Codes**: Secure delivery confirmation
- **Token Authentication**: Device tokens for FindMy
- **Share Permissions**: Granular access control

---

## 15. API ENDPOINTS

### Authentication
- `POST /register` - User registration
- `POST /login` - User login
- `GET /logout` - User logout

### Items/Marketplace
- `GET /` - Homepage with items
- `GET /item/<id>` - Item detail page
- `POST /post_item` - Create new listing
- `GET /delete_item/<id>` - Delete listing
- `GET /api/items` - JSON item list

### Messaging
- `GET /messages` - Messaging interface
- `POST /send_message` - Send message
- `GET /get_messages/<user_id>` - Get conversation
- `POST /delete_message/<id>` - Delete message
- `GET /api/unread_messages_count` - Unread count
- `GET /api/search_users` - Search users

### Delivery
- `GET /delivery/sender` - Sender dashboard
- `GET /delivery/recipient` - Recipient dashboard
- `GET /delivery_admin` - Rider portal
- `POST /api/request_delivery` - Create delivery
- `POST /api/recipient_approve_delivery` - Approve delivery
- `POST /api/rider_accept_delivery` - Rider accepts job
- `POST /api/rider_arrive_pickup` - Arrive at pickup
- `POST /api/rider_picked_up` - Package picked up
- `POST /api/rider_arrive_dropoff` - Arrive at dropoff
- `POST /api/confirm_handover` - Confirm handover
- `POST /api/process_payment` - Complete payment
- `GET /api/rider/active_offers` - Available jobs
- `POST /api/rider/update_status` - Toggle online status

### FindMy Phone
- `GET /find-my-phone` - Tracking interface
- `GET /findmy/owner` - Owner dashboard
- `GET /findmy/viewer` - Viewer interface
- `GET /findmy/agent` - Device agent page
- `POST /api/device/update_location` - Device location update
- `GET /api/device/current_location` - Get device location
- `POST /api/device/trigger_alarm` - Trigger alarm
- `POST /api/device/remote_lock` - Lock device
- `POST /api/device/remote_unlock` - Unlock device

### IMEI Checker
- `GET /imei-checker` - Checker interface
- `POST /api/check_imei` - Check IMEI

### News
- `GET /api/news` - Get news articles
- `GET /api/news/<id>` - Get single article
- `POST /api/post_news` - Post news (admin)

### Geolocation
- `GET /api/geocode` - Address to coordinates
- `GET /api/route` - Get driving route

### Trade-In
- `GET /trade-in` - Trade-in calculator
- `POST /trade-in` - Calculate device value

### Admin
- `GET /admin_panel` - Admin dashboard
- `GET /almighty_panel` - Super admin dashboard
- `GET /approve_request/<id>` - Approve posting request
- `GET /approve_user/<id>` - Grant posting permission
- `GET /revoke_user/<id>` - Revoke posting permission

---

## 16. FILE STRUCTURE

```
phils iphone/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── delivery_models.py     # Delivery-specific models
│   ├── findmy_api.py          # FindMy phone API routes
│   ├── findmy_socketio.py     # FindMy Socket.IO events
│   ├── requirements.txt        # Python dependencies
│   ├── tac_db.csv             # IMEI TAC database
│   └── instance/
│       └── site.db            # SQLite database
├── templates/
│   ├── base.html              # Base template
│   ├── index.html             # Homepage
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── messages.html          # Messaging interface
│   ├── profile.html           # User profile
│   ├── delivery_*.html        # Delivery pages
│   ├── findmy_*.html          # FindMy pages
│   ├── imei_checker.html      # IMEI checker
│   ├── trade_in.html          # Trade-in calculator
│   └── [other templates]
├── static/
│   ├── css/
│   │   └── style.css          # Main stylesheet
│   ├── js/
│   │   ├── main.js            # Main JavaScript
│   │   └── helpBot.js         # Help bot functionality
│   ├── images/                # Static images
│   ├── uploads/               # User uploads
│   └── videos/                # Video files
└── instance/
    └── site.db                # Database file
```

---

## 17. DEFAULT ACCOUNTS

### Admin Account
- **Username**: phil
- **Password**: admin123
- **Role**: Admin + Can Post

### Almighty Account
- **Username**: almighty
- **Password**: almighty123
- **Role**: Almighty + Admin + Can Post

---

## 18. CONFIGURATION

### Environment Variables
- `SECRET_KEY` - Flask session secret (hardcoded in dev)
- `IMEIINFO_API_KEY` - IMEI.info API key (optional)
- `ENABLE_APPLE_NEWS` - Toggle news fetching (default: true)
- `IMEICHECK_DEBUG` - Debug mode for IMEI API

### Database Configuration
- **Engine**: SQLite
- **Path**: instance/site.db
- **Auto-Migration**: Automatic column additions on startup

### Upload Configuration
- **Max File Size**: 16MB
- **Allowed Image Formats**: PNG, JPG, JPEG, GIF, WebP
- **Allowed Media Formats**: Images + MP4, AVI, MOV, MP3, WAV, OGG, M4A, WEBM

---

## 19. BACKGROUND PROCESSES

### Apple News Scheduler
- **Thread**: Daemon thread running in background
- **Frequency**: Fetches news every 30 minutes
- **Eager Loading**: Immediate fetch on startup with retries
- **Feed Sources**: 4 Apple RSS feeds (general, iPhone, iPad, Mac)
- **Real-Time Push**: New articles pushed to connected clients

---

## 20. ERROR HANDLING

### Graceful Degradation
- IMEI checker works without API key (local validation only)
- News fetcher retries on failure
- File uploads handle missing/invalid files
- Geocoding provides detailed error messages

### User Feedback
- Form validation with visual indicators
- Alert messages for success/error states
- Auto-hiding notifications
- Detailed error responses from APIs

---

## Summary

Phil's iPhone is a feature-rich platform combining:
- **E-commerce marketplace** for phones and laptops
- **Real-time delivery tracking** with Bolt-style pricing
- **WhatsApp-style messaging** with media support
- **WebRTC audio/video calling**
- **Apple Find My-style device tracking**
- **IMEI verification** with live API integration
- **Apple news aggregation** with real-time updates
- **Comprehensive admin controls** with role-based permissions
- **Responsive UI** with dark mode and modern animations

The system is designed for scalability, security, and user experience, with real-time features powered by WebSocket connections and a robust database backend.