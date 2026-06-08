"""
Phil's iPhone - Main Flask Application
A platform where main account posts phones/laptops, users can view items, 
approved users can post, and users can message each other.
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, make_response
import urllib.request as urlreq
from urllib.request import urlopen
from urllib.parse import quote_plus, urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request as URLLIBRequest
import ssl
from flask_socketio import SocketIO, join_room, emit

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect
from datetime import datetime, UTC, timedelta
import os
import math
import json
import socket
import feedparser
import threading
import time


# ── Apple RSS Feed URLs ───────────────────────────────────────────────────────
APPLE_RSS_FEEDS = [
    'https://www.apple.com/newsroom/rss-feed.rss',
    'https://www.apple.com/newsroom/iphone/rss-feed.rss',
    'https://www.apple.com/newsroom/ipad/rss-feed.rss',
    'https://www.apple.com/newsroom/mac/rss-feed.rss',
]

# Get the project root directory
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

app = Flask(__name__, 
           template_folder=os.path.join(basedir, 'templates'),
           static_folder=os.path.join(basedir, 'static'))
app.config['SECRET_KEY'] = 'phils-iphone-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'site.db')

socketio = SocketIO(app, cors_allowed_origins="*")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure required directories exist
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MEDIA_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg', 'm4a', 'webm'}

@app.before_request
def refresh_user_session_flags():
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            session['can_post'] = user.can_post
            session['is_admin'] = user.is_admin
            session['is_rider'] = user.is_rider
            session['is_almighty'] = user.is_almighty
            session['role'] = 'Rider' if user.is_rider else 'Customer'

def allowed_media_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MEDIA_EXTENSIONS

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_system_notification(user_id, title, message, type='info', url=None):
    """Utility to emit a notification with sound/note to a specific user via Socket.IO."""
    socketio.emit('system_notification', {
        'title': title,
        'message': message,
        'type': type,
        'url': url,
        'timestamp': datetime.now(UTC).strftime('%H:%M')
    }, room=f"user:{user_id}")

# Socket.IO event handlers for real-time messaging
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"Client connected: {request.sid}")
    # Join user room if authenticated
    if 'user_id' in session:
        user_id = session['user_id']
        join_room(f"user:{user_id}")
        # Mark user as online and notify peers
        user = db.session.get(User, user_id)
        if user:
            user.is_online = True
            db.session.commit()
            socketio.emit('user_status', {'user_id': user_id, 'status': 'online'}, namespace='/')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f"Client disconnected: {request.sid}")
    if 'user_id' in session:
        user_id = session['user_id']
        # Mark user as offline and notify peers
        user = db.session.get(User, user_id)
        if user:
            user.is_online = False
            user.last_seen = datetime.now(UTC)
            db.session.commit()
            socketio.emit('user_status', {
                'user_id': user_id, 
                'status': 'offline', 
                'last_seen': user.last_seen.strftime('%H:%M')
            }, namespace='/')


# --- Call signaling Socket.IO events ---
@socketio.on('call_initiate')
def handle_call_initiate(data, *args, **kwargs):
    """Initiate a call to another user and create a CallLog row."""
    if 'user_id' not in session:
        return
    other_user_id = data.get('other_user_id')
    call_type = data.get('call_type', 'video')
    if not other_user_id:
        return
    log = CallLog(caller_id=session['user_id'],
                  receiver_id=other_user_id,
                  call_type=call_type, status='started')
    db.session.add(log)
    db.session.commit()
    socketio.emit('call_incoming', {
        'from_user_id': session['user_id'],
        'from_username': session.get('username', 'Unknown'),
        'call_type': call_type,
        'log_id': log.id,
    }, room=f"user:{other_user_id}")

@socketio.on('call_accept')
def handle_call_accept(data, *args, **kwargs):
    """Accept an incoming call; update CallLog to 'answered'."""
    if 'user_id' not in session:
        return
    from_user_id = data.get('from_user_id')
    log_id = data.get('log_id')
    if from_user_id:
        if log_id:
            log = CallLog.query.get(log_id)
            if log and log.status == 'started':
                log.status = 'answered'
                db.session.commit()
        socketio.emit('call_accepted', {
            'by_user_id': session['user_id'],
            'by_username': session.get('username', 'Unknown'),
            'log_id': log_id,
        }, room=f"user:{from_user_id}")

@socketio.on('call_reject')
def handle_call_reject(data, *args, **kwargs):
    """Reject an incoming call; update CallLog to 'rejected'."""
    if 'user_id' not in session:
        return
    from_user_id = data.get('from_user_id')
    log_id = data.get('log_id')
    if from_user_id:
        if log_id:
            log = CallLog.query.get(log_id)
            if log and log.status == 'started':
                log.status = 'rejected'
                db.session.commit()
        socketio.emit('call_rejected', {}, room=f"user:{from_user_id}")

@socketio.on('call_end')
def handle_call_end(data, *args, **kwargs):
    """End an active call.

    Client wants BOTH sides to teardown (stop/close PeerConnections) reliably.
    Server therefore always emits `call_ended` to the other user.
    """
    if 'user_id' not in session:
        return

    other_user_id = data.get('other_user_id')
    log_id = data.get('log_id')
    duration = data.get('duration')

    # 1) Always notify BOTH sides to teardown UI/media.
    #    The frontend listens for `call_ended` to close the call modal.
    payload = {'log_id': log_id}

    # Notify self
    try:
        socketio.emit(
            'call_ended',
            payload,
            room=f"user:{session['user_id']}",
            namespace='/'
        )
    except Exception:
        pass


    # Notify other side
    if other_user_id is not None:
        try:
            socketio.emit('call_ended', payload, room=f"user:{other_user_id}")
        except Exception:
            # don't fail call teardown
            pass


    # 2) Update CallLog best-effort.
    try:
        if log_id:
            log = CallLog.query.get(log_id)
        else:
            # Fallback: most recent non-rejected/non-missed call involving this user.
            log = CallLog.query.filter(
                ((CallLog.caller_id == session['user_id']) | (CallLog.receiver_id == session['user_id'])),
                CallLog.status.notin_(['rejected', 'missed']),
            ).order_by(CallLog.started_at.desc()).first()

        if log and log.status not in ('rejected', 'missed'):
            log.status = 'ended'
            log.ended_at = datetime.now(UTC)
            if duration is not None:
                log.duration_seconds = int(duration)
            db.session.commit()
    except Exception:
        db.session.rollback()



# ── WebRTC SDP / ICE relay (server just forwards, no media touches the server) ──
@socketio.on('webrtc_offer')
def handle_webrtc_offer(data, *args, **kwargs):
    if 'user_id' not in session: return
    to_user_id = data.get('to_user_id')
    if not to_user_id: return
    socketio.emit('webrtc_offer', {
        'from_user_id': session['user_id'],
        'offer_sdp':    data.get('offer_sdp'),
    }, room=f"user:{to_user_id}", namespace='/')

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data, *args, **kwargs):
    if 'user_id' not in session: return
    to_user_id = data.get('to_user_id')
    if not to_user_id: return
    socketio.emit('webrtc_answer', {
        'from_user_id': session['user_id'],
        'answer_sdp':   data.get('answer_sdp'),
    }, room=f"user:{to_user_id}", namespace='/')

@socketio.on('webrtc_ice_candidate')
def handle_webrtc_ice(data, *args, **kwargs):
    if 'user_id' not in session: return
    to_user_id = data.get('to_user_id')
    if not to_user_id: return
    socketio.emit('webrtc_ice_candidate', {
        'from_user_id':  session['user_id'],
        'candidate':     data.get('candidate'),
        'sdpMid':        data.get('sdpMid'),
        'sdpMLineIndex': data.get('sdpMLineIndex'),
    }, room=f"user:{to_user_id}", namespace='/')

def extract_apple_media(entry):
    """Return (image_url, video_url) from an Apple RSS entry."""
    image_url = None
    video_url = None

    # 1. Enclosures — Apple puts both image & video here
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            href = getattr(enc, 'href', None) or (enc.get('href') if isinstance(enc, dict) else None)
            if not href:
                continue
            mtype = getattr(enc, 'type', '') or enc.get('type', '') if isinstance(enc, dict) else ''
            if mtype.startswith('video'):
                video_url = href
            elif mtype.startswith('image') or mtype in ('', 'application/octet-stream'):
                if not image_url:
                    image_url = href

    # 2. media:content array
    if hasattr(entry, 'media_content') and entry.media_content:
        for mc in entry.media_content:
            if isinstance(mc, dict):
                url = mc.get('url')
                mtype = mc.get('type', '')
                if url:
                    if mtype.startswith('video'):
                        video_url = url
                    elif mtype.startswith('image'):
                        if not image_url:
                            image_url = url

    # 3. entry.image dict
    if not image_url and hasattr(entry, 'image') and isinstance(entry.image, dict):
        image_url = entry.image.get('href')

    # 4. entry.image.href object
    if not image_url and hasattr(entry, 'image') and hasattr(entry.image, 'href'):
        image_url = entry.image.href

    # 5. image_url direct field
    if not image_url and hasattr(entry, 'image_url'):
        image_url = entry.image_url

    # 6. Scan HTML content for <img src> and <video src> tags
    content_html = ''
    if hasattr(entry, 'content') and entry.content:
        content_html = entry.content[0].get('value', '')
    if not content_html and hasattr(entry, 'summary'):
        content_html = entry.summary
    if not content_html and hasattr(entry, 'description'):
        content_html = entry.description

    if content_html:
        import re
        img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', content_html, re.IGNORECASE)
        if img_match:
            image_url = image_url or img_match.group(1)
        vid_match = re.search(r'<video[^>]+src=["\'](https?://[^"\']+)["\']', content_html, re.IGNORECASE)
        if vid_match:
            video_url = video_url or vid_match.group(1)
        # Also scan <source> tags inside <video>
        src_matches = re.findall(r'<source[^>]+src=["\'](https?://[^"\']+)["\']', content_html, re.IGNORECASE)
        for src in src_matches:
            if not video_url and any(ext in src for ext in ['.mp4', '.mov', '.m3u8', '.webm']):
                video_url = src

    return image_url, video_url


def fetch_apple_news_background():
    """Background task to fetch Apple news from RSS feeds."""
    with app.app_context():
        # Eager first pass: retry failed feeds before entering the 30-min sleep loop
        for attempt in range(3):
            print(f"[news fetch] eager pass attempt {attempt + 1}/3")
            try:
                any_added = False
                for feed_url in APPLE_RSS_FEEDS:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:3]:
                        try:
                            title_norm = (entry.title or '').strip()
                            if not title_norm:
                                continue
                            existing = News.query.filter_by(title=title_norm).first()
                            if existing:
                                continue

                            cat = 'apple'
                            url_lc = feed_url.lower()
                            if 'iphone' in url_lc:
                                cat = 'iphone'
                            elif 'ipad' in url_lc:
                                cat = 'ipad'
                            elif 'mac' in url_lc:
                                cat = 'mac'

                            content_val = ''
                            if hasattr(entry, 'content') and entry.content:
                                content_val = entry.content[0].get('value', '')
                            if not content_val:
                                content_val = entry.summary if hasattr(entry, 'summary') else entry.description or ''

                            # Best image & video
                            image_url, video_url = extract_apple_media(entry)

                            news = News(
                                title=title_norm,
                                content=content_val,
                                category=cat,
                                source='Apple Newsroom',
                                image_url=image_url,
                                video_url=video_url
                            )
                            db.session.add(news)
                            db.session.commit()
                            any_added = True

                            socketio.emit('news_update', {
                                'id': news.id,
                                'title': news.title,
                                'content': news.content[:100] + '...' if len(news.content) > 100 else news.content,
                                'category': news.category,
                                'source': news.source,
                                'image_url': news.image_url,
                                'video_url': news.video_url,
                                'created_at': news.created_at.strftime('%H:%M'),
                                'author': 'Apple News'
                            }, namespace='/')
                        except Exception as entry_e:
                            print(f"[news fetch] entry error for '{getattr(entry, 'title', '?')}': {entry_e}")
                            db.session.rollback()
                            continue

                if any_added:
                    print("[news fetch] eager pass completed — articles stored from startup")
                    break   # success — no need to retry
                else:
                    print("[news fetch] eager pass completed — no new articles found")
            except Exception as e:
                print(f"[news fetch] eager pass attempt {attempt + 1} failed: {e}")
            time.sleep(5)   # short back-off before retry

        print("[news fetch] entering 30-minute poll loop")
        while True:
            try:
                any_added = False
                for feed_url in APPLE_RSS_FEEDS:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:3]:
                        try:
                            title_norm = (entry.title or '').strip()
                            if not title_norm:
                                continue
                            existing = News.query.filter_by(title=title_norm).first()
                            if existing:
                                continue

                            cat = 'apple'
                            url_lc = feed_url.lower()
                            if 'iphone' in url_lc:
                                cat = 'iphone'
                            elif 'ipad' in url_lc:
                                cat = 'ipad'
                            elif 'mac' in url_lc:
                                cat = 'mac'

                            content_val = ''
                            if hasattr(entry, 'content') and entry.content:
                                content_val = entry.content[0].get('value', '')
                            if not content_val:
                                content_val = entry.summary if hasattr(entry, 'summary') else entry.description or ''

                            # Best image & video
                            image_url, video_url = extract_apple_media(entry)

                            news = News(
                                title=title_norm,
                                content=content_val,
                                category=cat,
                                source='Apple Newsroom',
                                image_url=image_url,
                                video_url=video_url
                            )
                            db.session.add(news)
                            db.session.commit()
                            any_added = True

                            socketio.emit('news_update', {
                                'id': news.id,
                                'title': news.title,
                                'content': news.content[:100] + '...' if len(news.content) > 100 else news.content,
                                'category': news.category,
                                'source': news.source,
                                'image_url': news.image_url,
                                'video_url': news.video_url,
                                'created_at': news.created_at.strftime('%H:%M'),
                                'author': 'Apple News'
                            }, namespace='/')
                        except Exception as entry_e:
                            print(f"[news fetch] entry error for '{getattr(entry, 'title', '?')}': {entry_e}")
                            db.session.rollback()
                            continue

                if any_added:
                    print(f"[news fetch] stored articles at {__import__('datetime').datetime.now().isoformat()}")
            except Exception as e:
                print(f"[news fetch loop error] {e}")

            time.sleep(1800)

def start_news_scheduler():
    """Start the background news fetching thread."""
    if os.environ.get('ENABLE_APPLE_NEWS', 'true').lower() == 'true':
        thread = threading.Thread(target=fetch_apple_news_background, daemon=True)
        thread.start()

def get_lan_ip():
    """Get the local network IP address for easier mobile testing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# Warn at startup if IMEI API key is missing
if not os.environ.get('IMEIINFO_API_KEY'):
    print("=" * 60)
    print("  IMEI API KEY NOT SET (IMEIINFO_API_KEY)")
    print("  Live IMEI lookups will use IMEI.info API (key is hardcoded).")
    print("  For full support, get a free key at https://imei.info/api/")
    print("=" * 60)


# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    can_post = db.Column(db.Boolean, default=False)
    is_rider = db.Column(db.Boolean, default=False)
    is_almighty = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    # Legacy tracking fields (will be deprecated for Find My)
    last_lat = db.Column(db.Float, nullable=True)
    last_lon = db.Column(db.Float, nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)


class TrackedDevice(db.Model):
    """A device (phone) registered for Apple-style Find My.

    Phones update their location using `device_token`.
    Viewers access location and can request actions via `share_code`/`share_token`.
    """

    id = db.Column(db.Integer, primary_key=True)

    owner_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', lazy=True)

    device_label = db.Column(db.String(100), nullable=True)
    device_type = db.Column(db.String(50), default='iPhone', nullable=False)  # iPhone, iPad, Mac, etc.

    # Auth token used by the phone agent
    device_token = db.Column(db.String(64), unique=True, nullable=False)

    # Optional “lock” permission PIN (hashed in production)
    lock_pin_hash = db.Column(db.String(255), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    last_lat = db.Column(db.Float, nullable=True)
    last_lon = db.Column(db.Float, nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    is_erased = db.Column(db.Boolean, default=False, nullable=False)
    erased_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))


class DeviceShare(db.Model):
    """A share session that viewers use to track a specific TrackedDevice.
    
    Permission levels:
    - 'view_only': Can only see location on map
    - 'view_and_alert': Can view location + trigger alarm
    - 'full_control': Can view location + alarm + lock/unlock device
    """

    id = db.Column(db.Integer, primary_key=True)

    device_id = db.Column(db.Integer, db.ForeignKey('tracked_device.id'), nullable=False)
    device = db.relationship('TrackedDevice', lazy=True)

    # If you want private shares, you can store viewer_user_id.
    viewer_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Human-friendly code (for UI)
    share_code = db.Column(db.String(16), unique=True, nullable=False)

    # Token for secure URL access
    share_token = db.Column(db.String(64), unique=True, nullable=False)

    # Permission level: 'view_only' | 'view_and_alert' | 'full_control'
    permission_level = db.Column(db.String(20), default='view_only', nullable=False)

    # Optional expiration for shares
    expires_at = db.Column(db.DateTime, nullable=True)

    # Optional password for public shares
    password_hash = db.Column(db.String(255), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    last_seen_at = db.Column(db.DateTime, nullable=True)


class LocationHistory(db.Model):
    """Historical GPS location tracking for each device.
    
    Enables viewing location history and "Recently Seen" feature.
    """

    id = db.Column(db.Integer, primary_key=True)

    device_id = db.Column(db.Integer, db.ForeignKey('tracked_device.id'), nullable=False)
    device = db.relationship('TrackedDevice', lazy=True)

    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    # GPS accuracy in meters
    accuracy = db.Column(db.Float, nullable=True)

    # Timestamp when location was recorded
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    # Index for fast queries
    __table_args__ = (
        db.Index('idx_device_timestamp', 'device_id', 'timestamp'),
    )


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'phone' or 'laptop'
    condition = db.Column(db.String(50), nullable=False)  # 'new', 'like-new', 'used'
    image_url = db.Column(db.String(200), nullable=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    seller = db.relationship('User', backref='items', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    is_read = db.Column(db.Boolean, default=False)
    media_url = db.Column(db.String(300), nullable=True)
    media_type = db.Column(db.String(20), default='text')
    is_deleted = db.Column(db.Boolean, default=False)
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages', lazy=True)
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages', lazy=True)


class DeliveryMessage(db.Model):
    """Delivery-scoped chat with 3 parties (sender, recipient, rider).

    Unlock rule: messages are allowed only after recipient approves AND rider accepts.
    We gate on Delivery.status.
    """

    id = db.Column(db.Integer, primary_key=True)

    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)  # who sent

    # The target participant within this delivery (one of the other 2 parties).
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)  # who receives

    content = db.Column(db.Text, nullable=False, default='')
    media_url = db.Column(db.String(300), nullable=True)
    media_type = db.Column(db.String(20), default='text')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id], lazy=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], lazy=True)


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user = db.relationship('User', backref='requests', lazy=True)

# Debug startup paths (helps confirm correct DB/paths are used)
with app.app_context():
    print("[startup] DB path:", app.config['SQLALCHEMY_DATABASE_URI'])
    print("[startup] Upload folder:", app.config['UPLOAD_FOLDER'])

# Delivery workflow models (MVP)
# Status flow:
# requested -> matched -> accepted -> arrived_at_pickup -> picked_up -> en_route -> roadside_handover -> paid
class Delivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Participants
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Matching/acceptance
    matched_rider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    accepted_rider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    status = db.Column(db.String(40), default='requested', nullable=False)

    # Route
    pickup_lat = db.Column(db.Float, nullable=False)
    pickup_lon = db.Column(db.Float, nullable=False)
    dropoff_lat = db.Column(db.Float, nullable=False)
    dropoff_lon = db.Column(db.Float, nullable=False)

    # 1. Pickup Details
    pickup_address = db.Column(db.Text, nullable=True)
    pickup_contact_name = db.Column(db.String(100), nullable=True)
    pickup_contact_phone = db.Column(db.String(20), nullable=True)
    pickup_instructions = db.Column(db.Text, nullable=True)

    # 2. Drop-off Details
    dropoff_address = db.Column(db.Text, nullable=True)
    recipient_name = db.Column(db.String(100), nullable=True)
    recipient_phone = db.Column(db.String(20), nullable=True)
    dropoff_instructions = db.Column(db.Text, nullable=True)

    # 3. Package Information
    package_type = db.Column(db.String(50), nullable=True)
    package_size = db.Column(db.String(50), nullable=True)
    handling_requirements = db.Column(db.Text, nullable=True)

    # 4. Timing
    preferred_pickup_time = db.Column(db.String(100), nullable=True)
    preferred_delivery_time = db.Column(db.String(100), nullable=True)
    urgency_level = db.Column(db.String(20), nullable=True)

    # 5. Payment
    payment_method = db.Column(db.String(50), nullable=True)

    # Bolt Pricing logic
    price_cents = db.Column(db.Integer, nullable=False, default=0)
    distance_km = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(10), nullable=False, default='USD')
    payment_status = db.Column(db.String(20), default='unpaid', nullable=False)  # unpaid/paid
    payment_reference = db.Column(db.String(80), nullable=True)

    # Security: recipient must enter the correct code to approve the delivery.
    # Code is generated when sender requests a delivery with a recipient_id.
    approval_code = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    matched_at = db.Column(db.DateTime, nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)
    en_route_at = db.Column(db.DateTime, nullable=True)
    arrived_at_pickup_at = db.Column(db.DateTime, nullable=True)
    picked_up_at = db.Column(db.DateTime, nullable=True)
    arrived_at_dropoff_at = db.Column(db.DateTime, nullable=True)
    handover_confirmed_at = db.Column(db.DateTime, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], lazy=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], lazy=True)
    matched_rider = db.relationship('User', foreign_keys=[matched_rider_id], lazy=True)
    accepted_rider = db.relationship('User', foreign_keys=[accepted_rider_id], lazy=True)

    # NOTE: Do NOT define properties named `accepted_rider` or `matched_rider` here.
    # The ORM relationship attributes above return User objects; defining properties
    # with the same names would shadow those relationship objects and cause
    # templates/Socket.IO handlers to receive integer IDs instead of User instances.
    # Use the *_id fields (`accepted_rider_id`, `matched_rider_id`) when you need IDs.



class DeliveryUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=False)
    rider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='apple')  # apple, iphone, ipad, mac, general
    image_url = db.Column(db.String(300), nullable=True)
    video_url = db.Column(db.String(300), nullable=True)
    source = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    author = db.relationship('User', backref='news_posts', lazy=True)

class CallLog(db.Model):
    """Persistent log of all call activity across the platform."""
    id = db.Column(db.Integer, primary_key=True)
    caller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    call_type = db.Column(db.String(10), nullable=False)  # 'audio' or 'video'
    status = db.Column(db.String(20), nullable=False)     # 'missed' | 'answered' | 'rejected'
    duration_seconds = db.Column(db.Integer, nullable=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    ended_at = db.Column(db.DateTime, nullable=True)
    caller = db.relationship('User', foreign_keys=[caller_id], backref='outgoing_calls', lazy=True)
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='incoming_calls', lazy=True)


def initialize_database():
    """Initialize database and run migrations safely."""
    with app.app_context():
        db.create_all()

        # 1. Robust Migration: Add missing columns to Delivery table
        inspector = inspect(db.engine)
        if 'delivery' in inspector.get_table_names():
            existing_cols = [c['name'] for c in inspector.get_columns('delivery')]
            required_cols = [
                ("pickup_address", "TEXT"), ("pickup_contact_name", "VARCHAR(100)"),
                ("pickup_contact_phone", "VARCHAR(20)"), ("pickup_instructions", "TEXT"),
                ("dropoff_address", "TEXT"), ("recipient_name", "VARCHAR(100)"),
                ("recipient_phone", "VARCHAR(20)"), ("dropoff_instructions", "TEXT"),
                ("package_type", "VARCHAR(50)"), ("package_size", "VARCHAR(50)"),
                ("handling_requirements", "TEXT"), ("preferred_pickup_time", "VARCHAR(100)"),
                ("preferred_delivery_time", "VARCHAR(100)"), ("urgency_level", "VARCHAR(20)"),
                ("payment_method", "VARCHAR(50)"), ("distance_km", "FLOAT"),
                ("approval_code", "VARCHAR(20)"),
                ("matched_at", "DATETIME"), ("accepted_at", "DATETIME"),
                ("en_route_at", "DATETIME"), ("handover_confirmed_at", "DATETIME"),
                ("paid_at", "DATETIME"),
                ("arrived_at_pickup_at", "DATETIME"),
                ("picked_up_at", "DATETIME"),
                ("arrived_at_dropoff_at", "DATETIME")
            ]
            
            with db.engine.begin() as conn:
                for col_name, col_type in required_cols:
                    if col_name not in existing_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE delivery ADD COLUMN {col_name} {col_type}"))
                            print(f"[migration] Added column '{col_name}' to 'delivery' table.")
                        except Exception as e:
                            print(f"[migration] Error adding '{col_name}': {e}")

        # 1b. Migration for User table
        if 'user' in inspector.get_table_names():
            user_cols = [c['name'] for c in inspector.get_columns('user')]
            if 'is_rider' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN is_rider BOOLEAN DEFAULT 0"))
                    print("[migration] Added column 'is_rider' to 'user' table.")
            if 'is_almighty' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN is_almighty BOOLEAN DEFAULT 0"))
                    print("[migration] Added column 'is_almighty' to 'user' table.")
            if 'is_online' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN is_online BOOLEAN DEFAULT 0"))
                    print("[migration] Added column 'is_online' to 'user' table.")
            if 'last_lat' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN last_lat FLOAT"))
                    conn.execute(text("ALTER TABLE user ADD COLUMN last_lon FLOAT"))
                    conn.execute(text("ALTER TABLE user ADD COLUMN last_seen DATETIME"))
                    print("[migration] Added tracking columns to 'user' table.")

        # 1c. Migration for News table – video_url column
        if 'news' in inspector.get_table_names():
            news_cols = [c['name'] for c in inspector.get_columns('news')]
            if 'video_url' not in news_cols:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE news ADD COLUMN video_url VARCHAR(300)"))
                    print("[migration] Added column 'video_url' to 'news' table.")
        
        # 1d. Migration for TrackedDevice table - is_erased and erased_at
        if 'tracked_device' in inspector.get_table_names():
            tracked_device_cols = [c['name'] for c in inspector.get_columns('tracked_device')]
            if 'is_erased' not in tracked_device_cols:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE tracked_device ADD COLUMN is_erased BOOLEAN DEFAULT 0"))
                    conn.execute(text("ALTER TABLE tracked_device ADD COLUMN erased_at DATETIME"))
                    print("[migration] Added columns 'is_erased' and 'erased_at' to 'tracked_device' table.")


        # 2. Create admin account if not exists
        if not User.query.filter_by(username='phil').first():
            admin = User(
                username='phil', email='phil@philsiphone.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True, can_post=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin account created: username='phil', password='admin123'")

        # 3. Create almighty account if not exists
        if not User.query.filter_by(username='almighty').first():
            almighty = User(
                username='almighty', email='almighty@philsiphone.com',
                password_hash=generate_password_hash('almighty123'),
                is_admin=True, can_post=True, is_almighty=True
            )
            db.session.add(almighty)
            db.session.commit()
            print("Almighty account created: username='almighty', password='almighty123'")



# Routes

# Initialize Find My Phone API / Socket.IO.
# Fix import robustness when running as: python backend/app.py
# (In that case, "backend" package may not be discoverable on sys.path.)
try:
    from backend.findmy_api import init_findmy_routes  # type: ignore
    from backend.findmy_socketio import init_findmy_socketio  # type: ignore
except Exception:
    # If executed directly, add project root to sys.path then retry absolute imports.
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from backend.findmy_api import init_findmy_routes  # type: ignore
    from backend.findmy_socketio import init_findmy_socketio  # type: ignore

init_findmy_routes(app, db, socketio)
init_findmy_socketio(socketio, db)


@app.route('/')
@app.route('/splash')
def splash():
    return render_template('splash.html')



@app.route('/home')
def index():
    category = request.args.get('category')

    query = Item.query
    if category:
        query = query.filter(Item.category == category)

    items = query.order_by(Item.created_at.desc()).all()
    return render_template('index.html', items=items, category=category)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already exists')
        
        is_rider = (role == 'rider')
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_rider=is_rider
        )
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        session['can_post'] = user.can_post
        session['is_rider'] = user.is_rider
        session['is_almighty'] = user.is_almighty
        session['role'] = 'Rider' if user.is_rider else 'Customer'
        
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            session['can_post'] = user.can_post
            session['is_rider'] = user.is_rider
            session['is_almighty'] = user.is_almighty
            session['role'] = 'Rider' if user.is_rider else 'Customer'

            return redirect(url_for('index'))
        
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# =====================================================================
# FIND MY PHONE ROUTES
# =====================================================================

@app.route('/findmy')
@app.route('/findmy/owner')
def findmy_owner():
    """Find My Phone owner dashboard."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('findmy_owner.html')

@app.route('/findmy/viewer')
def findmy_viewer():
    """Find My Phone shared device viewer."""
    share_token = request.args.get('token')
    device_id = request.args.get('device_id')
    
    if not share_token and not device_id:
        return redirect(url_for('index'))
    
    return render_template('findmy_viewer.html', share_token=share_token, device_id=device_id)

@app.route('/findmy/agent')
def findmy_agent():
    """Find My Phone device agent (runs on device)."""
    return render_template('findmy_device_agent.html')

@app.route('/findmy/share')
def findmy_public_share():
    """Find My Phone public share access page."""
    return render_template('findmy_public_share.html')

@app.route('/post_item', methods=['GET', 'POST'])
def post_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if not session.get('can_post') and not session.get('is_admin'):
        return render_template('post_item.html', error='You need approval to post items')
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        condition = request.form.get('condition')
        
        # Handle image upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            print(f"[post_item] upload field image present. raw filename={getattr(file, 'filename', None)!r}")

            # Ensure we only accept a real filename
            print(
                f"[post_item] filename raw={getattr(file, 'filename', None)!r} "
                f"size={getattr(file, 'content_length', None)} "
                f"type={getattr(file, 'content_type', None)!r}"
            )

            if file and file.filename:
                # Always log extension and allowed result
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                allowed = allowed_file(file.filename)
                print(f"[post_item] upload filename_ext={ext!r} allowed={allowed}")

                # Use secure_filename regardless so we can verify rendering end-to-end
                filename = secure_filename(file.filename)

                # Add unique identifier to filename
                timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S_%f')
                filename = f"{timestamp}_{filename}"

                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(save_path)
                    image_url = filename
                    print(f"[post_item] saved upload (even if extension validation fails): image_url={image_url!r} save_path={save_path!r}")
                except Exception as e:
                    print(f"[post_item] save failed: {e!r}")
            else:
                print(f"[post_item] upload missing/empty filename: {getattr(file,'filename',None)!r}")



        item = Item(
            title=title,
            description=description,
            price=price,
            category=category,
            condition=condition,
            image_url=image_url,
            seller_id=session['user_id']
        )
        db.session.add(item)
        db.session.commit()
        
        return redirect(url_for('index'))
    
    return render_template('post_item.html')

# Route to serve uploaded images
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    item = Item.query.get_or_404(item_id)
    
    if item.seller_id != session['user_id'] and not session.get('is_admin'):
        return redirect(url_for('index'))
    
    db.session.delete(item)
    db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/request_access', methods=['POST'])
def request_access():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('is_admin'):
        return redirect(url_for('index'))
    
    # Check if user already has pending request
    existing = Request.query.filter_by(user_id=session['user_id'], status='pending').first()
    if existing:
        return render_template('post_item.html', error='Request already pending')
    
    request_obj = Request(user_id=session['user_id'])
    db.session.add(request_obj)
    db.session.commit()
    
    return redirect(url_for('post_item'))

@app.route('/approve_request/<int:request_id>')
def approve_request(request_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    req = Request.query.get_or_404(request_id)
    req.status = 'approved'
    req.user.can_post = True
    db.session.commit()
    
    return redirect(url_for('admin_panel'))

@app.route('/approve_user/<int:user_id>')
def approve_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    user.can_post = True
    db.session.commit()
    
    return redirect(url_for('admin_panel'))

@app.route('/revoke_user/<int:user_id>')
def revoke_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    user.can_post = False
    db.session.commit()
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_call/<int:call_id>')
def admin_delete_call(call_id):
    if not session.get('is_admin') and not session.get('is_almighty'):
        return redirect(url_for('index'))
    call = CallLog.query.get_or_404(call_id)
    db.session.delete(call)
    db.session.commit()
    return redirect(request.referrer or url_for('admin_panel'))

@app.route('/admin_panel')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('index'))

    # Automatically redirect almighty users to their superior panel
    if session.get('is_almighty'):
        return redirect(url_for('almighty_panel'))

    pending_requests = Request.query.filter_by(status='pending').all()
    pending_users   = User.query.filter_by(can_post=False, is_admin=False).all()
    approved_users  = User.query.filter_by(can_post=True, is_admin=False).all()
    all_users       = User.query.filter(User.id != session['user_id']).all()
    my_call_logs    = CallLog.query.filter(
        (CallLog.caller_id == session['user_id']) |
        (CallLog.receiver_id == session['user_id'])
    ).order_by(CallLog.started_at.desc()).limit(50).all()
    return render_template('admin_panel.html',
                           requests=pending_requests,
                           pending_users=pending_users,
                           approved_users=approved_users,
                           all_users=all_users,
                           my_call_logs=my_call_logs)

@app.route('/almighty_panel')
def almighty_panel():
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    
    all_users = User.query.all()
    all_items = Item.query.all()
    all_deliveries = Delivery.query.all()
    all_requests = Request.query.all()
    all_messages = Message.query.all()
    all_call_logs = CallLog.query.order_by(CallLog.started_at.desc()).limit(100).all()
    
    return render_template('almighty_panel.html', 
                         users=all_users, 
                         items=all_items, 
                         deliveries=all_deliveries, 
                         requests=all_requests,
                         messages=all_messages,
                         call_logs=all_call_logs)

@app.route('/almighty/delete_user/<int:user_id>')
def almighty_delete_user(user_id):
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    if not user.is_almighty:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/toggle_admin/<int:user_id>')
def almighty_toggle_admin(user_id):
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    if not user.is_almighty:
        user.is_admin = not user.is_admin
        db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_delivery/<int:delivery_id>')
def almighty_delete_delivery(delivery_id):
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    delivery = Delivery.query.get_or_404(delivery_id)
    db.session.delete(delivery)
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_item/<int:item_id>')
def almighty_delete_item(item_id):
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_request/<int:request_id>')
def almighty_delete_request(request_id):
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    req = Request.query.get_or_404(request_id)
    db.session.delete(req)
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_message/<int:msg_id>')
def almighty_delete_message(msg_id):
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    msg = Message.query.get_or_404(msg_id)
    db.session.delete(msg) # Hard delete for almighty
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_call/<int:call_id>')
def almighty_delete_call(call_id):
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    call = CallLog.query.get_or_404(call_id)
    db.session.delete(call)
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_all_users')
def almighty_delete_all_users():
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    # Delete all users except almighty ones to prevent lockout
    User.query.filter(User.is_almighty == False).delete()
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_all_items')
def almighty_delete_all_items():
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    Item.query.delete()
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_all_deliveries')
def almighty_delete_all_deliveries():
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    # Clear updates and messages first if foreign keys are enforced
    DeliveryUpdate.query.delete()
    DeliveryMessage.query.delete()
    Delivery.query.delete()
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_all_requests')
def almighty_delete_all_requests():
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    Request.query.delete()
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_all_messages')
def almighty_delete_all_messages():
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    Message.query.delete()
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/almighty/delete_all_calls')
def almighty_delete_all_calls():
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    CallLog.query.delete()
    db.session.commit()
    return redirect(url_for('almighty_panel'))

@app.route('/delivery_admin')
def delivery_admin():
    if not session.get('is_rider') and not session.get('is_admin'):
        return redirect(url_for('index'))
    # Find the job this rider has currently accepted
    active = Delivery.query.filter(
        Delivery.accepted_rider_id == session.get('user_id'),
        Delivery.status != 'paid'
    ).order_by(Delivery.created_at.desc()).first()
    return render_template('delivery_admin.html', active_delivery=active)
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('profile.html', user=user)


# Delivery Pages (role separated)
@app.route('/delivery')
def delivery():
    # Backward-compatible redirect to sender view
    return redirect(url_for('delivery_sender'))

@app.route('/delivery/sender')
def delivery_sender():
    if 'user_id' not in session: return redirect(url_for('login'))
    # Find the most recent active delivery for this sender
    active = Delivery.query.filter(
        Delivery.sender_id == session['user_id'], 
        Delivery.status != 'paid'
    ).order_by(Delivery.created_at.desc()).first()
    # Render the newer Bolt-style sender page instead of the legacy sender UI.
    return render_template('delivery.html', active_delivery=active)

@app.route('/delivery/recipient')
def delivery_recipient():
    if 'user_id' not in session: return redirect(url_for('login'))
    # Find the most recent active delivery for this recipient
    active = Delivery.query.filter(
        Delivery.recipient_id == session['user_id'],
        Delivery.status.in_(['pending_recipient', 'accepted', 'arrived_at_pickup', 'picked_up', 'arrived_at_dropoff', 'roadside_handover'])
    ).order_by(Delivery.created_at.desc()).first()
    return render_template('delivery_recipient.html', active_delivery=active)

@app.route('/api/geocode')
def api_geocode():
    """Server-side proxy for Nominatim geocoding to avoid browser CORS / DNS issues."""
    query = request.args.get('q', '').strip()
    print(f"[GEOCODE] Received query: {query}")
    if not query:
        return jsonify({'error': 'Missing q parameter'}), 400
    print(f"[GEOCODE] Proceeding with query: {query}")

    # NOTE: we intentionally keep it simple (no auth) and rely on Nominatim throttling.

    nominatim_url = (

        'https://nominatim.openstreetmap.org/search?format=json&limit=1&q='
        + quote_plus(query)
    )
    # urllib.request.Request signature is Request(url, headers={...})
    # (some Python/OS combinations are picky, so keep it minimal)
    # urllib.request.Request signature is Request(url, data=None, headers={}, method=None)
    # Using positional url + keyword headers to avoid platform-specific argument parsing.
    # Avoid passing `method=`; older urllib.request.Request implementations can
    # raise TypeError for unexpected argument positions.
    # Use simplest possible urllib Request signature to avoid Python/OS-specific Request() issues.
    req = urlreq.Request(nominatim_url, headers={
        'Accept': 'application/json',
        'User-Agent': 'PhilsiPhoneApp/1.0 (https://philsiphone.example.com/contact)',
    })
    # (No method= argument here.)






    try:
        # Create SSL context without certificate verification
        # (necessary for macOS development environment where certificate store may be missing)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        print("[GEOCODE] SSL context configured (verification disabled for development)")
        
        with urlopen(req, timeout=10, context=ssl_context) as resp:
            print(f"[GEOCODE] Response status: {resp.status}")
            raw = resp.read()
            # resp.read() returns bytes; json.loads accepts str/bytes in py3.
            try:
                payload = json.loads(raw)
                print(f"[GEOCODE] Successfully parsed response: {len(payload)} results")
            except TypeError:
                # Some environments are picky: decode bytes explicitly.
                payload = json.loads(raw.decode('utf-8', errors='replace'))
                print(f"[GEOCODE] Successfully parsed response (after decode)")

    except HTTPError as exc:
        # HTTPError is a subclass of URLError but we want the status code.
        try:
            body = exc.read().decode('utf-8', errors='replace')
        except Exception:
            body = ''
        print(f'[GEOCODE] HTTPError {exc.code}: {body[:100]}')
        return (
            jsonify({
                'error': 'Geocoding service returned an HTTP error',
                'query': query,
                'status': getattr(exc, 'code', None),
                'detail': body[:300] if body else str(exc),
            }),
            getattr(exc, 'code', 502) or 502,
        )
    except URLError as exc:
        print(f'[GEOCODE] URLError: {str(exc)}')
        return jsonify({'error': 'Geocoding service unavailable. Check your internet connection or try a more specific address.', 'query': query, 'detail': str(exc)}), 502
    except TimeoutError as exc:
        print(f'[GEOCODE] TimeoutError: {str(exc)}')
        return jsonify({'error': 'Geocoding service timed out. Please try again.', 'query': query, 'detail': str(exc)}), 504
    except Exception as exc:
        # Catch JSON decode errors and any other unexpected failures.
        print(f'[GEOCODE] Exception {type(exc).__name__}: {str(exc)}')
        return jsonify({'error': 'Geocoding failed. Please try a more specific address.', 'query': query, 'detail': str(exc)}), 500

    if not payload:
        return jsonify({'error': f'No results found for "{query}"'}), 404

    # Be defensive about the payload shape.
    first = payload[0] if isinstance(payload, list) and payload else None
    if not first or 'lat' not in first or 'lon' not in first:
        return jsonify({'error': 'Unexpected geocoding response', 'query': query}), 502

    return jsonify({
        'lat': float(first['lat']),
        'lon': float(first['lon']),
        'display_name': first.get('display_name', query),
    }), 200




@app.route('/api/route')
def api_route():
    """Server-side proxy for the OSRM routing API to avoid browser CORS/DNS issues."""
    src_lat = request.args.get('src_lat')
    src_lon = request.args.get('src_lon')
    dst_lat = request.args.get('dst_lat')
    dst_lon = request.args.get('dst_lon')

    if not all([src_lat, src_lon, dst_lat, dst_lon]):
        return jsonify({'error': 'Missing coordinates'}), 400

    osrm_url = (
        f'https://router.project-osrm.org/route/v1/driving/'
        f'{src_lon},{src_lat};{dst_lon},{dst_lat}'
        f'?overview=full&geometries=geojson&steps=false'
    )
    req = urlreq.Request(osrm_url, headers={'Accept': 'application/json'})
    req = urlreq.Request(osrm_url, headers={
        'Accept': 'application/json',
        'User-Agent': 'PhilsiPhoneApp/1.0'
    })
    try:
        with urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except (HTTPError, URLError) as exc:
        return jsonify({'error': f'Routing service unavailable: {exc}'}), 502

    routes = payload.get('routes', [])
    if not routes:
        return jsonify({'routes': []}), 200

    return jsonify(payload)


@app.route('/api/recipient_pending_delivery')
def api_recipient_pending_delivery():
    """Return the latest delivery waiting for this recipient's approval (or any active delivery),
    used by the recipient page on reconnect / page load to re-sync deliveryId."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    active = Delivery.query.filter(
        Delivery.recipient_id == session['user_id'],
        Delivery.status.in_(['pending_recipient', 'accepted', 'arrived_at_pickup', 'picked_up', 'arrived_at_dropoff', 'roadside_handover'])
    ).order_by(Delivery.created_at.desc()).first()

    if not active:
        return jsonify({'delivery_id': None})

    return jsonify({
        'delivery_id': active.id,
        'status': active.status,
        'approval_code': active.approval_code
    })


@app.route('/delivery/recipient/by-sender-id')
def delivery_recipient_by_sender_id():
    return render_template('delivery_recipient_senderid.html')




# Repairs & Decoding pages
@app.route('/repairs-decoding')
def repair_decoding():
    return render_template('repair_request.html')


@app.route('/repairs')
def repairs_home():
    return render_template('repair_home.html')


@app.route('/imei-checker')
def imei_checker():
    return redirect("https://sickw.com")


@app.route('/api/check_imei', methods=['POST'])
def api_check_imei():
    """Live IMEI lookup using IMEI.info API.

    Uses the official IMEI.info API (https://imei.info/api/) with the API key
    configured via environment variable IMEIINFO_API_KEY or hardcoded.

    Returns real-time device status, brand, model, and detailed specifications.
    """
    data = request.get_json(force=True, silent=True) or {}
    imei = data.get('imei', '').strip()

    imei_clean = ''.join(filter(str.isdigit, imei))
    if not imei_clean.isdigit() or len(imei_clean) != 15:
        return jsonify({'success': False, 'error': 'Invalid IMEI. Must be 15 digits.'}), 400

    # Local Luhn algorithm check for basic validation
    def luhn_check(digits):
        total = 0
        for i, d in enumerate(reversed(digits)):
            n = int(d)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0

    # Use environment variable or the hardcoded API key
    api_key = os.environ.get('IMEIINFO_API_KEY') or '1b9736c2-9a85-4284-92b0-40142c5c0ad1'

    # Debug visibility (so you can confirm the server runtime env received the key)
    print(f"[imeicheck] api_key_present={bool(api_key)} using IMEI.info API")

    # Always return local validation as a baseline
    local_response = {
        'imei': imei_clean,
        'tac': imei_clean[:8],
        'brand': None,
        'model': None,
        'model_info': None,
        'year': None,
        'chipset': None,
        'status': 'Local validation - IMEI format checked with Luhn algorithm',
        'is_valid_luhn': luhn_check(imei_clean),
    }

    if not api_key:
        # No external key configured; don't call any 3rd party.
        return jsonify({'success': True, 'data': local_response}), 200

    # Create SSL context without certificate verification (similar to api_geocode)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    print("[imeicheck] SSL context configured (verification disabled for development)")

    try:
        # IMEI.info API - try multiple endpoint formats
        # Some networks can’t resolve `api.imei.info` but can resolve `imei.info`.
        api_endpoints = [
            # GET (api subdomain)
            f"https://api.imei.info/v3/device/{imei_clean}?apikey={api_key}",
            # GET (base domain)
            f"https://imei.info/v3/device/{imei_clean}?apikey={api_key}",
            # POST (api subdomain)
            "https://api.imei.info/api/check.php",
            # POST (base domain)
            "https://imei.info/api/check.php",
        ]


        
        last_error = None
        payload = None
        
        for endpoint in api_endpoints:
            try:
                print(f"[imeicheck] Trying endpoint: {endpoint[:80]}...")
                
                if "check.php" in endpoint:
                    # POST method
                    post_data = urlencode({
                        'apikey': api_key,
                        'imei': imei_clean,
                    }).encode('utf-8')
                    
                    req = urlreq.Request(
                        endpoint,
                        data=post_data,
                        headers={
                            'Accept': 'application/json',
                            'User-Agent': 'PhilsiPhoneApp/1.0',
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        method='POST',
                    )
                else:
                    # GET method
                    req = urlreq.Request(
                        endpoint,
                        headers={
                            'Accept': 'application/json',
                            'User-Agent': 'PhilsiPhoneApp/1.0',
                        },
                        method='GET',
                    )
                
                with urlopen(req, timeout=15, context=ssl_context) as resp:
                    raw = resp.read()
                    payload = json.loads(raw)
                    
                if payload:
                    print(f"[imeicheck] Got response: status={payload.get('status', 'N/A')}")
                    break
                    
            except Exception as e:
                last_error = str(e)
                print(f"[imeicheck] Endpoint failed: {last_error[:100]}")
                continue
        
        if not payload:
            raise Exception(f"All API endpoints failed. Last error: {last_error}")
        
        print(f"[imeicheck] Response status: {payload.get('status', 'N/A')}")
        
        if isinstance(payload, dict):
            api_status = str(payload.get('status', ''))
            
            # Successful responses have status '0' or 'success', or contain imei data
            if api_status == '0' or api_status == 'success' or payload.get('imei') or payload.get('brand'):
                device_data = payload
                
                brand = device_data.get('brand', device_data.get('Brand', 'Unknown'))
                model = device_data.get('model', device_data.get('Model', 'Unknown'))
                year = device_data.get('releaseDate', device_data.get('year', device_data.get('ReleaseDate')))
                tac = device_data.get('tac', device_data.get('TAC', imei_clean[:8]))
                
                model_info = {
                    'image': device_data.get('image', device_data.get('Image')),
                    'release_date': year,
                    'dimensions': device_data.get('dimensions', device_data.get('Dimensions')),
                    'display': device_data.get('display', device_data.get('Display')),
                    'chipset': device_data.get('chipset', device_data.get('Chipset')),
                }
                model_info = {k: v for k, v in model_info.items() if v is not None}
                
                return jsonify({
                    'success': True,
                    'data': {
                        **local_response,
                        'imei': imei_clean,
                        'tac': tac,
                        'brand': brand,
                        'model': model,
                        'year': year,
                        'chipset': device_data.get('chipset', device_data.get('Chipset')),
                        'model_info': model_info,
                        'status': 'Verified via IMEI.info API',
                        'raw': payload if os.environ.get('IMEICHECK_DEBUG') == '1' else None,
                    }
                }), 200
            else:
                error_msg = payload.get('message', payload.get('error', 'IMEI not found or invalid'))
                return jsonify({
                    'success': True,
                    'data': {
                        **local_response,
                        'status': f'IMEI.info: {error_msg}',
                    }
                }), 200
        else:
            return jsonify({
                'success': True,
                'data': {
                    **local_response,
                    'status': 'Unexpected response format from IMEI.info',
                }
            }), 200

    except HTTPError as e:
        error_body = ''
        try:
            error_body = e.read().decode('utf-8', errors='replace')
        except:
            pass
        return jsonify({
            'success': False,
            'error': f'IMEI.info API HTTP error: {str(e)}',
            'detail': error_body[:200] if error_body else str(e)
        }), getattr(e, 'code', 502)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Could not reach IMEI.info service: {str(e)}'}), 502


@app.route('/decoding')
def decoding_home():
    return render_template('repair_home.html')



# Delivery REST APIs


@app.route('/api/recipient_lookup_delivery_by_sender', methods=['POST'])
def api_recipient_lookup_delivery_by_sender():
    """Recipient provides sender_id; we return the latest active delivery between them."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}
    try:
        sender_id = int(data.get('sender_id'))
    except Exception:
        return jsonify({'error': 'Invalid payload'}), 400

    recipient_id = session['user_id']

    # Find the most recent delivery where this recipient matched with that sender.
    delivery_obj = Delivery.query.filter(
        Delivery.sender_id == sender_id,
        Delivery.recipient_id == recipient_id
    ).order_by(Delivery.created_at.desc()).first()

    if not delivery_obj:
        return jsonify({'error': 'No delivery found'}), 404

    return jsonify({
        'success': True,
        'delivery_id': delivery_obj.id,
        'status': delivery_obj.status,
        'approval_code': delivery_obj.approval_code
    })


def _delivery_riders_queryset():
    # Dedicated query for users registered as riders
    return User.query.filter(User.is_rider == True, User.is_online == True)


def calculate_haversine(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in km."""
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def estimate_bolt_fare(distance_km):
    """Bolt-style pricing (GHC): piecewise fare based on distance.

    Requirements:
    - 0 to 1.5 km:  estimatedFare = 2.00 + (distKm * 20.0)
    - 1.5 to 4 km: estimatedFare = 2.00 + (distKm * 40.0)
    - 5+ km:       estimatedFare = 2.00 + (distKm * 10.0)

    Note: distances are in km and fare returned is in cents (int).
    """
    dist = float(distance_km or 0)
    base_fare = 2.00

    if dist <= 1.5:
        rate = 20.0
    elif dist <= 4.0:
        rate = 40.0
    elif dist >= 5.0:
        rate = 10.0
    else:
        # 4 to <5km: not specified clearly; choose the closer intended middle policy (40.0)
        rate = 40.0

    total = base_fare + (dist * rate)
    return int(total * 100)  # cents



def _find_nearest_available_rider(pickup_lat, pickup_lon, limit=1):
    riders = _delivery_riders_queryset().all()
    best = []

    for r in riders:
        # availability constraint (simple): don't match riders who already have accepted/en_route jobs.
        busy = Delivery.query.filter(
            Delivery.accepted_rider_id == r.id,
            Delivery.status.in_(['accepted', 'arrived_at_pickup', 'picked_up', 'arrived_at_dropoff', 'roadside_handover'])
        ).first()

        if busy:
            continue

        # For MVP: assume riders are nearby if no current GPS. 
        # In production, we'd use the last known lat/lon of the rider.
        dist = 0 
        best.append((dist, r))

    best.sort(key=lambda x: x[0])
    return [r for _, r in best][:limit]


@app.route('/api/delivery_guys')
def api_delivery_guys():
    riders = User.query.filter(User.is_rider == True).all()
    return jsonify({
        'delivery_guys': [{
            'id': u.id,
            'username': u.username,
            'online': u.is_online,
            'last_lat': u.last_lat,
            'last_lon': u.last_lon,
            'last_seen_at': u.last_seen.strftime('%Y-%m-%d %H:%M:%S') if u.last_seen else None
        } for u in riders]
    })

@app.route('/api/rider/update_status', methods=['POST'])
def api_rider_update_status():
    """Rider toggles their online/offline availability."""
    if 'user_id' not in session or not session.get('is_rider'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json(force=True, silent=True) or {}
    is_online = data.get('online')

    if is_online is None:
        return jsonify({'error': 'Missing online status'}), 400

    user = User.query.get(session['user_id'])
    user.is_online = bool(is_online)
    db.session.commit()

    return jsonify({'success': True, 'online': user.is_online})


@app.route('/api/rider/active_offers')
def api_rider_active_offers():
    """Endpoint for the Rider Portal to fetch available delivery jobs."""
    if 'user_id' not in session or not session.get('is_rider'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    rider_id = session['user_id']
    user = User.query.get(rider_id)

    if not user or not user.is_online:
        return jsonify({
            'error': 'You are offline',
            'message': 'Go online to view and accept delivery offers.'
        }), 403

    # Show all jobs that are officially 'requested' (available for anyone to pick up)
    offers = Delivery.query.filter(
        Delivery.status == 'requested'
    ).all()
    
    return jsonify([{
        'id': d.id,
        'pickup_address': d.pickup_address,
        'dropoff_address': d.dropoff_address,
        'price': d.price_cents / 100,
        'package_type': d.package_type,
        'status': d.status
    } for d in offers])


@app.route('/api/request_delivery', methods=['POST'])
def api_request_delivery():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}

    try:
        rid = data.get('recipient_id')
        recipient_id = int(rid) if rid else None
        pickup_lat = float(data.get('pickup_lat'))
        pickup_lon = float(data.get('pickup_lon'))
        dropoff_lat = float(data.get('dropoff_lat'))
        dropoff_lon = float(data.get('dropoff_lon'))
    except Exception:
        return jsonify({'error': 'Invalid payload'}), 400

    sender_id = session['user_id']

    if recipient_id:
        if sender_id == recipient_id:
            return jsonify({'error': 'Sender and recipient must be different'}), 400
        recipient = User.query.get(recipient_id)
        if not recipient:
            return jsonify({'error': 'Recipient not found'}), 404

    selected_rider_id = data.get('rider_id')
    matched = None
    if selected_rider_id is not None:
        try:
            selected_rider_id = int(selected_rider_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid rider selection'}), 400

        matched = User.query.get(selected_rider_id)
        if not matched or not matched.is_rider:
            return jsonify({'error': 'Selected rider not found'}), 404
        if not matched.is_online:
            return jsonify({'error': 'Selected rider is currently offline'}), 400

        busy = Delivery.query.filter(
            (Delivery.accepted_rider_id == matched.id) | (Delivery.matched_rider_id == matched.id),
            Delivery.status.in_(['accepted', 'arrived_at_pickup', 'picked_up', 'arrived_at_dropoff', 'roadside_handover'])
        ).first()
        if busy:
            return jsonify({'error': 'Selected rider is currently busy with another delivery'}), 400
    else:
        available_count = User.query.filter(User.is_rider == True, User.is_online == True).count()
        if available_count > 0:
            return jsonify({'error': 'Please choose an available rider before requesting delivery.'}), 400
        matched_riders = _find_nearest_available_rider(pickup_lat, pickup_lon, limit=1)
        matched = matched_riders[0] if matched_riders else None

    # Bolt Logic: Calculate distance and fare
    dist = calculate_haversine(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    fare_cents = estimate_bolt_fare(dist)

    # Generate a short approval code for recipient security (only when there is a recipient).
    import secrets
    approval_code = secrets.token_urlsafe(6).upper().replace('-', '')[:8] if recipient_id else None

    delivery_obj = Delivery(
        sender_id=sender_id,
        recipient_id=recipient_id,
        matched_rider_id=matched.id if matched else None,
        pickup_lat=pickup_lat,
        pickup_lon=pickup_lon,
        dropoff_lat=dropoff_lat,
        dropoff_lon=dropoff_lon,
        pickup_address=data.get('pickup_address'),
        pickup_contact_name=data.get('pickup_contact_name'),
        pickup_contact_phone=data.get('pickup_contact_phone'),
        pickup_instructions=data.get('pickup_instructions'),
        dropoff_address=data.get('dropoff_address'),
        recipient_name=data.get('recipient_name'),
        recipient_phone=data.get('recipient_phone'),
        dropoff_instructions=data.get('dropoff_instructions'),
        package_type=data.get('package_type'),
        status='pending_recipient' if recipient_id else 'requested',
        package_size=data.get('package_size'),
        handling_requirements=data.get('handling_requirements'),
        preferred_pickup_time=data.get('preferred_pickup_time'),
        preferred_delivery_time=data.get('preferred_delivery_time'),
        urgency_level=data.get('urgency_level'),
        payment_method=data.get('payment_method'),
        distance_km=round(dist, 2),
        price_cents=fare_cents,
        matched_at=datetime.now(UTC) if matched else None,
        approval_code=approval_code,
    )
    db.session.add(delivery_obj)
    db.session.commit()

    # If there is a recipient, immediately notify them so the UI can show the Approve button.
    if recipient_id:
        socketio.emit(
            'delivery_status_update',
            {
                'delivery_id': delivery_obj.id,
                'status': delivery_obj.status,
                'approval_code': delivery_obj.approval_code
            },
            room=f"user:{recipient_id}",
            namespace='/'
        )

    # Notify matched rider (offer)
    if matched:
        emit_payload = {
            'delivery_id': delivery_obj.id,
            'pickup_lat': pickup_lat,
            'pickup_lon': pickup_lon,
            'dropoff_lat': dropoff_lat,
            'dropoff_lon': dropoff_lon,
            'status': delivery_obj.status,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'pickup_address': delivery_obj.pickup_address,
            'dropoff_address': delivery_obj.dropoff_address,
            'package_type': delivery_obj.package_type,
            'urgency_level': delivery_obj.urgency_level,
            'pickup_contact_name': delivery_obj.pickup_contact_name,
            'recipient_name': delivery_obj.recipient_name,
            'price': delivery_obj.price_cents / 100
        }
        # Notify all riders that a new job is available
        socketio.emit('delivery_offer', emit_payload, namespace='/')

    return jsonify({
        'success': True,
        'delivery_id': delivery_obj.id,
        'status': delivery_obj.status,
        'approval_code': approval_code
    })


@app.route('/api/recipient_approve_delivery', methods=['POST'])
def api_recipient_approve_delivery():
    """Recipient approves the incoming delivery, making it available for riders."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}
    delivery_id = data.get('delivery_id')
    approval_code = (data.get('approval_code') or '').strip().upper()

    print(f"[approve] session={session.get('user_id')} delivery_id={delivery_id!r} approval_code={approval_code!r}")

    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj:
        print(f"[approve] delivery NOT FOUND for id={delivery_id!r}")
        return jsonify({'error': 'Delivery not found'}), 404

    if delivery_obj.recipient_id != session['user_id']:
        print(f"[approve] MISMATCH: delivery.recipient={delivery_obj.recipient_id} session={session['user_id']}")
        return jsonify({'error': 'Unauthorized'}), 403

    print(f"[approve] delivery status={delivery_obj.status!r} db_code={delivery_obj.approval_code!r}")

    if delivery_obj.status != 'pending_recipient':
        return jsonify({'error': f'Delivery status is {delivery_obj.status}, not pending_recipient'}), 400

    if not approval_code or delivery_obj.approval_code is None or approval_code != str(delivery_obj.approval_code).strip().upper():
        print(f"[approve] CODE MISMATCH: received={approval_code!r} expected={delivery_obj.approval_code!r}")
        return jsonify({'error': 'Invalid approval code'}), 403

    delivery_obj.status = 'requested'
    db.session.commit()

    # Notify riders that a new job has just become available.
    # IMPORTANT: rider/driver UI expects a `delivery_offer` event to populate the job details.
    socketio.emit(
        'delivery_status_update',
        {'delivery_id': delivery_obj.id, 'status': 'requested'},
        namespace='/'
    )

    emit_payload = {
        'delivery_id': delivery_obj.id,
        'pickup_lat': delivery_obj.pickup_lat,
        'pickup_lon': delivery_obj.pickup_lon,
        'dropoff_lat': delivery_obj.dropoff_lat,
        'dropoff_lon': delivery_obj.dropoff_lon,
        'status': delivery_obj.status,
        'sender_id': delivery_obj.sender_id,
        'recipient_id': delivery_obj.recipient_id,
        'pickup_address': delivery_obj.pickup_address,
        'dropoff_address': delivery_obj.dropoff_address,
        'package_type': delivery_obj.package_type,
        'package_size': delivery_obj.package_size,
        'urgency_level': delivery_obj.urgency_level,
        'pickup_contact_name': delivery_obj.pickup_contact_name,
        'recipient_name': delivery_obj.recipient_name,
        'price': (delivery_obj.price_cents or 0) / 100,
    }

    socketio.emit('delivery_offer', emit_payload, namespace='/')

    return jsonify({'success': True})

@app.route('/api/recipient_confirm_handover', methods=['POST'])
def api_recipient_confirm_handover():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}
    try:
        delivery_id = int(data.get('delivery_id'))
    except Exception:
        return jsonify({'error': 'Invalid payload'}), 400

    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj:
        return jsonify({'error': 'Delivery not found'}), 404

    if delivery_obj.recipient_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    if delivery_obj.status not in ['arrived_at_dropoff', 'roadside_handover']:
        return jsonify({'error': f'Cannot confirm handover in status {delivery_obj.status}'}), 400

    delivery_obj.handover_confirmed_at = datetime.now(UTC)
    delivery_obj.status = 'paid'
    delivery_obj.payment_status = 'paid'
    delivery_obj.paid_at = datetime.now(UTC)
    delivery_obj.payment_reference = delivery_obj.payment_reference or f"REC-{delivery_obj.id}-{int(datetime.now(UTC).timestamp())}"
    db.session.commit()

    payload = {
        'delivery_id': delivery_obj.id,
        'status': delivery_obj.status,
        'matched_at': delivery_obj.matched_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.matched_at else None,
        'accepted_at': delivery_obj.accepted_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.accepted_at else None,
        'arrived_at_pickup_at': delivery_obj.arrived_at_pickup_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.arrived_at_pickup_at else None,
        'picked_up_at': delivery_obj.picked_up_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.picked_up_at else None,
        'arrived_at_dropoff_at': delivery_obj.arrived_at_dropoff_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.arrived_at_dropoff_at else None,
        'handover_confirmed_at': delivery_obj.handover_confirmed_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.handover_confirmed_at else None,
        'paid_at': delivery_obj.paid_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.paid_at else None,
    }

    socketio.emit('delivery_status_update', payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    socketio.emit('delivery_status_update', payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    if delivery_obj.accepted_rider_id:
        socketio.emit('delivery_status_update', payload, room=f"rider:{delivery_obj.accepted_rider_id}", namespace='/')
    
    # Notify users with links to the delivery receipt
    send_system_notification(delivery_obj.sender_id, 'Delivery Completed', 'Your recipient has confirmed handover and delivery is complete.', type='delivery', url=url_for('delivery_sender', _external=True))
    send_system_notification(delivery_obj.recipient_id, 'Handover Confirmed', 'Thank you for confirming handover.', type='delivery', url=url_for('delivery_recipient', _external=True))
    if delivery_obj.accepted_rider_id:
        send_system_notification(delivery_obj.accepted_rider_id, 'Delivery Complete', 
                                 'Recipient has confirmed handover. Thank you.', type='delivery', url=url_for('delivery_admin', _external=True))

    return jsonify({'success': True})

@app.route('/api/rider_accept_delivery', methods=['POST'])
def api_rider_accept_delivery():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}
    try:
        delivery_id = int(data.get('delivery_id'))
    except Exception:
        return jsonify({'error': 'Invalid payload'}), 400

    rider_id = session['user_id']
    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj:
        return jsonify({'error': 'Delivery not found'}), 404

    # Allow any rider to grab a 'requested' job
    if delivery_obj.status != 'requested':
        return jsonify({'error': f'Cannot accept in status {delivery_obj.status}'}), 400

    delivery_obj.accepted_rider_id = rider_id
    delivery_obj.matched_rider_id = rider_id # Ensure match is recorded if claimed from 'requested'
    delivery_obj.status = 'accepted'
    delivery_obj.accepted_at = datetime.now(UTC)
    db.session.commit()

    # Broadcast status update to sender + recipient + rider
    status_payload = {
        'delivery_id': delivery_obj.id, 
        'status': delivery_obj.status,
        'accepted_at': delivery_obj.accepted_at.strftime('%Y-%m-%d %H:%M')
    }
    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"rider:{rider_id}", namespace='/')

    # Notify sender/recipient
    send_system_notification(delivery_obj.sender_id, "Delivery Accepted", 
                             f"Rider {session['username']} has accepted your delivery.", type='delivery', url=url_for('delivery_sender', _external=True))
    if delivery_obj.recipient_id:
        send_system_notification(delivery_obj.recipient_id, "Delivery Update", 
                                 f"A rider has accepted the delivery to you.", type='delivery', url=url_for('delivery_recipient', _external=True))

    return jsonify({'success': True})

@app.route('/api/rider_arrive_pickup', methods=['POST'])
def api_rider_arrive_pickup():
    if 'user_id' not in session: return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json(force=True, silent=True) or {}
    delivery_obj = Delivery.query.get(data.get('delivery_id'))
    if not delivery_obj or delivery_obj.accepted_rider_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    delivery_obj.status = 'arrived_at_pickup'
    delivery_obj.arrived_at_pickup_at = datetime.now(UTC)
    db.session.commit()
    
    status_payload = {'delivery_id': delivery_obj.id, 'status': delivery_obj.status, 'arrived_at_pickup_at': delivery_obj.arrived_at_pickup_at.strftime('%Y-%m-%d %H:%M')}
    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    
    # Notify sender
    send_system_notification(delivery_obj.sender_id, "Rider Arrived", "Your rider has arrived at the pickup location.", type='delivery', url=url_for('delivery_sender', _external=True))

    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"rider:{session['user_id']}", namespace='/')
    return jsonify({'success': True})

@app.route('/api/rider_go_online', methods=['POST'])
def api_rider_go_online():
    """Driver starts the trip GPS + timeline by moving delivery to en_route."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}
    try:
        delivery_id = int(data.get('delivery_id'))
    except Exception:
        return jsonify({'error': 'Invalid payload'}), 400

    driver_id = session['user_id']
    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj:
        return jsonify({'error': 'Delivery not found'}), 404

    if delivery_obj.accepted_rider_id != driver_id:
        return jsonify({'error': 'Not the accepted rider'}), 403

# Only allow transition to en_route once accepted.
    if delivery_obj.status != 'accepted':
        return jsonify({'error': f"Cannot go online in status {delivery_obj.status}"}), 400

    try:
        delivery_obj.status = 'en_route'
        delivery_obj.en_route_at = datetime.now(UTC)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error: ' + str(e)}), 500

    status_payload = {
        'delivery_id': delivery_obj.id,
        'status': delivery_obj.status,
        'en_route_at': delivery_obj.en_route_at.strftime('%Y-%m-%d %H:%M')
    }

    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"rider:{driver_id}", namespace='/')

    send_system_notification(delivery_obj.sender_id, "Trip Started", "Your rider is now en route with your package.", type='delivery', url=url_for('delivery_sender', _external=True))

    return jsonify({'success': True})


@app.route('/api/rider_picked_up', methods=['POST'])
def api_rider_picked_up():
    if 'user_id' not in session: return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json(force=True, silent=True) or {}
    delivery_obj = Delivery.query.get(data.get('delivery_id'))
    if not delivery_obj or delivery_obj.accepted_rider_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403

    delivery_obj.status = 'picked_up'
    delivery_obj.picked_up_at = datetime.now(UTC)
    delivery_obj.en_route_at = delivery_obj.picked_up_at
    db.session.commit()

    status_payload = {'delivery_id': delivery_obj.id, 'status': delivery_obj.status, 'picked_up_at': delivery_obj.picked_up_at.strftime('%Y-%m-%d %H:%M')}
    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    
    if delivery_obj.recipient_id:
        send_system_notification(delivery_obj.recipient_id, "Package Picked Up", "A package is coming your way!", type='delivery', url=url_for('delivery_recipient', _external=True))

    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"rider:{session['user_id']}", namespace='/')
    return jsonify({'success': True})


@app.route('/api/rider_arrive_dropoff', methods=['POST'])
def api_rider_arrive_dropoff():
    if 'user_id' not in session: return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json(force=True, silent=True) or {}
    delivery_obj = Delivery.query.get(data.get('delivery_id'))
    if not delivery_obj or delivery_obj.accepted_rider_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    delivery_obj.status = 'arrived_at_dropoff'
    delivery_obj.arrived_at_dropoff_at = datetime.now(UTC)
    db.session.commit()
    
    status_payload = {'delivery_id': delivery_obj.id, 'status': delivery_obj.status, 'arrived_at_dropoff_at': delivery_obj.arrived_at_dropoff_at.strftime('%Y-%m-%d %H:%M')}
    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    
    if delivery_obj.recipient_id:
        send_system_notification(delivery_obj.recipient_id, "Rider Arrived", "Your rider is at the drop-off location.", type='delivery', url=url_for('delivery_recipient', _external=True))

    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"rider:{session['user_id']}", namespace='/')
    return jsonify({'success': True})

    return jsonify({'success': True})



@app.route('/api/confirm_handover', methods=['POST'])
def api_confirm_handover():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}
    try:
        delivery_id = int(data.get('delivery_id'))
    except Exception:
        return jsonify({'error': 'Invalid payload'}), 400

    driver_id = session['user_id']
    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj:
        return jsonify({'error': 'Delivery not found'}), 404

    if delivery_obj.accepted_rider_id != driver_id:
        return jsonify({'error': 'Not the accepted rider'}), 403

    if delivery_obj.status not in ['picked_up', 'arrived_at_dropoff', 'accepted']:
        return jsonify({'error': f'Cannot confirm handover in status {delivery_obj.status}'}), 400

    delivery_obj.status = 'roadside_handover'
    delivery_obj.handover_confirmed_at = datetime.now(UTC)
    db.session.commit()

    payload = {
        'delivery_id': delivery_obj.id,
        'status': delivery_obj.status,
        'matched_at': delivery_obj.matched_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.matched_at else None,
        'accepted_at': delivery_obj.accepted_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.accepted_at else None,
        'arrived_at_pickup_at': delivery_obj.arrived_at_pickup_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.arrived_at_pickup_at else None,
        'picked_up_at': delivery_obj.picked_up_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.picked_up_at else None,
        'arrived_at_dropoff_at': delivery_obj.arrived_at_dropoff_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.arrived_at_dropoff_at else None,
        'handover_confirmed_at': delivery_obj.handover_confirmed_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.handover_confirmed_at else None,
        'paid_at': delivery_obj.paid_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.paid_at else None,
    }

    socketio.emit('delivery_status_update', payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    socketio.emit('delivery_status_update', payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    socketio.emit('delivery_status_update', payload, room=f"rider:{driver_id}", namespace='/')

    return jsonify({'success': True})


@app.route('/api/process_payment', methods=['POST'])
def api_process_payment():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}
    try:
        delivery_id = int(data.get('delivery_id'))
    except Exception:
        return jsonify({'error': 'Invalid payload'}), 400

    driver_id = session['user_id']
    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj:
        return jsonify({'error': 'Delivery not found'}), 404

    if delivery_obj.accepted_rider_id != driver_id:
        return jsonify({'error': 'Not the accepted rider'}), 403

    if delivery_obj.status not in ['roadside_handover', 'accepted', 'en_route']:
        return jsonify({'error': f'Cannot process payment in status {delivery_obj.status}'}), 400

    delivery_obj.status = 'paid'
    delivery_obj.payment_status = 'paid'
    delivery_obj.paid_at = datetime.now(UTC)
    delivery_obj.payment_reference = delivery_obj.payment_reference or f"MVP-{delivery_obj.id}-{int(datetime.now(UTC).timestamp())}"
    db.session.commit()

    payload = {
        'delivery_id': delivery_obj.id,
        'status': delivery_obj.status,
        'matched_at': delivery_obj.matched_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.matched_at else None,
        'accepted_at': delivery_obj.accepted_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.accepted_at else None,
        'arrived_at_pickup_at': delivery_obj.arrived_at_pickup_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.arrived_at_pickup_at else None,
        'picked_up_at': delivery_obj.picked_up_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.picked_up_at else None,
        'arrived_at_dropoff_at': delivery_obj.arrived_at_dropoff_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.arrived_at_dropoff_at else None,
        'handover_confirmed_at': delivery_obj.handover_confirmed_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.handover_confirmed_at else None,
        'paid_at': delivery_obj.paid_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.paid_at else None,
    }

    socketio.emit('delivery_status_update', payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    socketio.emit('delivery_status_update', payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    socketio.emit('delivery_status_update', payload, room=f"rider:{driver_id}", namespace='/')

    return jsonify({'success': True})



# News Routes
@app.route('/api/news')
def api_news():
    """Get latest news for home screen."""
    news_items = News.query.filter_by(is_active=True).order_by(News.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': n.id,
        'title': n.title,
        'content': n.content,
        'category': n.category,
        'image_url': n.image_url,
        'video_url': n.video_url,
        'source': n.source,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
        'author': n.author.username if n.author else 'Admin'
    } for n in news_items])


@app.route('/api/post_news', methods=['POST'])
def api_post_news():
    """Admin endpoint to post news."""
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json(force=True, silent=True) or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    category = data.get('category', 'apple')
    image_url = data.get('image_url', '').strip() or None
    video_url = data.get('video_url', '').strip() or None
    source = data.get('source', 'Phil\'s iPhone News').strip()

    if not title or not content:
        return jsonify({'error': 'Title and content required'}), 400

    news = News(
        title=title,
        content=content,
        category=category,
        image_url=image_url,
        video_url=video_url,
        source=source,
        author_id=session.get('user_id')
    )
    db.session.add(news)
    db.session.commit()

    # Emit real-time update to all connected clients
    socketio.emit('news_update', {
        'id': news.id,
        'title': news.title,
        'content': news.content[:100] + '...' if len(news.content) > 100 else news.content,
        'category': news.category,
        'image_url': news.image_url,
        'video_url': news.video_url,
        'source': news.source,
        'created_at': news.created_at.strftime('%H:%M'),
        'author': session.get('username', 'Admin')
    }, namespace='/')

    return jsonify({'success': True, 'news_id': news.id})


@app.route('/api/news/<int:news_id>')
def api_news_detail(news_id):
    """Get single news item."""
    news = News.query.get_or_404(news_id)
    return jsonify({
        'id': news.id,
        'title': news.title,
        'content': news.content,
        'category': news.category,
        'image_url': news.image_url,
        'video_url': news.video_url,
        'source': news.source,
        'created_at': news.created_at.strftime('%Y-%m-%d %H:%M'),
        'author': news.author.username if news.author else 'Admin'
    })


# Socket.IO Events
@socketio.on('join_delivery')
def on_join_delivery(payload):
    try:
        delivery_id = int(payload.get('delivery_id'))
    except Exception:
        return

    room = f"delivery:{delivery_id}"
    join_room(room)

    delivery_obj = db.session.get(Delivery, delivery_id)
    if not delivery_obj:
        emit('delivery_initial', {})
        return

    # Security check: User must be a participant
    user_id = session.get('user_id')
    if user_id not in [delivery_obj.sender_id, delivery_obj.recipient_id, delivery_obj.accepted_rider_id]:
        return

    emit('delivery_initial', {
        'pickup_lat': delivery_obj.pickup_lat,
        'pickup_lon': delivery_obj.pickup_lon,
        'dropoff_lat': delivery_obj.dropoff_lat,
        'dropoff_lon': delivery_obj.dropoff_lon,
        'pickup_address': delivery_obj.pickup_address,
        'dropoff_address': delivery_obj.dropoff_address,
        'package_type': delivery_obj.package_type,
        'urgency_level': delivery_obj.urgency_level,
        'status': delivery_obj.status,
        'matched_at': delivery_obj.matched_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.matched_at else None,
        'accepted_at': delivery_obj.accepted_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.accepted_at else None,
        'arrived_at_pickup_at': delivery_obj.arrived_at_pickup_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.arrived_at_pickup_at else None,
        'picked_up_at': delivery_obj.picked_up_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.picked_up_at else None,
        'arrived_at_dropoff_at': delivery_obj.arrived_at_dropoff_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.arrived_at_dropoff_at else None,
        'handover_confirmed_at': delivery_obj.handover_confirmed_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.handover_confirmed_at else None,
        'paid_at': delivery_obj.paid_at.strftime('%Y-%m-%d %H:%M') if delivery_obj.paid_at else None,
    }, room=request.sid)


@socketio.on('join_rider_portal')
def on_join_rider_portal(payload):
    """Driver portal joins rider:{user_id} room to receive delivery offers."""
    try:
        rider_id = int(payload.get('rider_id'))
    except Exception:
        return

    # Only allow logged-in drivers to join their own portal.
    if 'user_id' not in session or session['user_id'] != rider_id:
        return

    join_room(f"rider:{rider_id}")


@socketio.on('rider_location')
def on_rider_location(payload):
    # Publish rider GPS only if sender is the accepted rider for this delivery.
    try:
        delivery_id = int(payload.get('delivery_id'))
        lat = float(payload.get('lat'))
        lon = float(payload.get('lon'))
    except Exception:
        return

    if 'user_id' not in session:
        return

    rider_id = session['user_id']

    delivery_obj = db.session.get(Delivery, delivery_id)
    if not delivery_obj:
        return

    # Security/Correctness: only the assigned rider can broadcast live GPS.
    if delivery_obj.accepted_rider_id != rider_id and delivery_obj.matched_rider_id != rider_id:
        return

    # Also require the delivery to be in an active trip state.
    if delivery_obj.status not in ['accepted', 'arrived_at_pickup', 'picked_up', 'arrived_at_dropoff', 'roadside_handover', 'en_route', 'paid']:
        return

    room = f"delivery:{delivery_id}"
    payload = {'delivery_id': delivery_id, 'lat': lat, 'lon': lon}
    emit('rider_location_update', payload, room=room, namespace='/')
    if delivery_obj.sender_id:
        emit('rider_location_update', payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    if delivery_obj.recipient_id:
        emit('rider_location_update', payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')



# Messaging (WhatsApp-like) Socket.IO Events
@socketio.on('join_user')
def on_join_user(payload):
    """Client joins a per-user room so the server can push messages."""
    try:
        user_id = int(payload.get('user_id'))
    except Exception:
        return

    join_room(f"user:{user_id}")


@socketio.on('typing')
def on_typing(payload):
    """Notify the other user that someone is typing."""
    if 'user_id' not in session:
        return

    try:
        other_user_id = int(payload.get('other_user_id'))
        is_typing = bool(payload.get('is_typing'))
    except Exception:
        return

    event = 'typing_on' if is_typing else 'typing_off'

    emit(
        event,
        {
            'from_user_id': session['user_id'],
            'other_user_id': other_user_id,
            'ts': datetime.now(UTC).isoformat(),
        },
        room=f"user:{other_user_id}",
    )


@socketio.on('mark_read_thread')
def on_mark_read_thread(payload):
    """Mark messages as read for the currently viewed thread."""
    if 'user_id' not in session:
        return

    try:
        other_user_id = int(payload.get('other_user_id'))
    except Exception:
        return

    user_id = session['user_id']

    # Mark only messages in this thread where the receiver is the logged-in user.
    Message.query.filter(
        Message.receiver_id == user_id,
        Message.sender_id == other_user_id,
        Message.is_deleted == False,
        Message.is_read == False,
    ).update({Message.is_read: True})
    db.session.commit()

    emit('read_updated', {'other_user_id': other_user_id, 'viewer_user_id': user_id}, room=f"user:{user_id}")
    # Notify the sender that their messages have been read (Blue Ticks)
    socketio.emit('messages_read', {'by_user_id': user_id}, room=f"user:{other_user_id}", namespace='/')






# Feature Pages
@app.route('/fast-delivery')
def fast_delivery():
    return render_template('feature_fast_delivery.html')



@app.route('/verified-listings')
def verified_listings():
    return render_template('feature_verified_listings.html')


@app.route('/great-prices')
def great_prices():
    return render_template('feature_great_prices.html')


@app.route('/easy-returns')
def easy_returns():
    return render_template('feature_easy_returns.html')


# Messaging Routes
@app.route('/api/unread_messages_count')
def api_unread_messages_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})

    user_id = session['user_id']

    # Unread = received by me, not deleted, and not marked read.
    count = Message.query.filter(
        Message.receiver_id == user_id,
        Message.is_deleted == False,
        Message.is_read == False,
    ).count()

    return jsonify({'count': count})



@app.route('/messages')
def messages():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    # Filter sidebar to show only active conversations (users you have chatted with)
    # Use distinct to avoid duplicate user IDs if a conversation has both sent and received messages
    sent_partners = db.session.query(Message.receiver_id).filter(Message.sender_id == user_id, Message.is_deleted == False).distinct()
    received_partners = db.session.query(Message.sender_id).filter(Message.receiver_id == user_id, Message.is_deleted == False).distinct()
    partner_ids = set(r[0] for r in sent_partners.union(received_partners).all() if r[0] != user_id)
    
    users_list = []
    for p_id in partner_ids:
        p = db.session.get(User, p_id)
        if p:
            # Get the most recent message for a WhatsApp-style preview
            last_msg = Message.query.filter(
                Message.is_deleted == False,
                db.or_(
                    db.and_(Message.sender_id == user_id, Message.receiver_id == p.id),
                    db.and_(Message.sender_id == p.id, Message.receiver_id == user_id)
                )
            ).order_by(Message.created_at.desc()).first()

            # Count unread messages for the "red dot" indicator
            unread = Message.query.filter_by(
                sender_id=p.id, 
                receiver_id=user_id, 
                is_read=False, 
                is_deleted=False
            ).count()

            last_preview = last_msg.content if last_msg else ''
            if last_msg and last_msg.media_type != 'text':
                last_preview = f"[{last_msg.media_type.capitalize()}] " + last_preview

            users_list.append({
                'id': p.id, 
                'username': p.username, 
                'unread_count': unread,
                'last_message': last_preview,
                'last_message_time': last_msg.created_at if last_msg else None,
                'is_online': p.is_online
            })

    # Sort conversations by most recent message (recency sorting)
    users_list.sort(key=lambda x: x['last_message_time'] or datetime.min.replace(tzinfo=UTC), reverse=True)

    # Prepare formatting for JSON/Frontend
    for u in users_list:
        if u['last_message_time']:
            u['last_message_time_str'] = u['last_message_time'].strftime('%H:%M')
            u['last_message_time'] = u['last_message_time'].isoformat()
        else:
            u['last_message_time_str'] = ''

    import json

    users_json = json.dumps(users_list)

    return render_template('messages.html', users=users_list, users_json=users_json, current_user_id=user_id)

@app.route('/api/search_users')
def search_users():
    """API to search for new people to chat with (for the 'plus' button search)."""
    if 'user_id' not in session:
        return jsonify([]), 401
    query = request.args.get('q', '').strip()
    
    base_query = User.query.filter(User.id != session['user_id'])
    
    if query:
        base_query = base_query.filter(
            db.or_(User.username.ilike(f'%{query}%'), User.email.ilike(f'%{query}%'))
        )
        
    users = base_query.limit(15).all()
    return jsonify([{'id': u.id, 'username': u.username} for u in users])

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    receiver_username = request.form.get('receiver')
    content = request.form.get('content')
    print('[send_message] receiver=', receiver_username, 'content_len=', len(content or ''), 'files=', list(request.files.keys()))
    
    receiver = User.query.filter_by(username=receiver_username).first()
    if not receiver:
        return jsonify({'error': 'User not found'}), 404
    
    media_url = None
    media_type = 'text'
    messages_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'messages')
    os.makedirs(messages_upload_folder, exist_ok=True)
    
    if 'media_file' in request.files:
        file = request.files['media_file']
        if file and file.filename and allowed_media_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S_%f')
            name, ext = filename.rsplit('.', 1)
            filename = f"{timestamp}_{name}.{ext}"
            file.save(os.path.join(messages_upload_folder, filename))
            media_url = filename
            
            if ext.lower() in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                media_type = 'image'
            elif ext.lower() in ['mp4', 'avi', 'mov']:
                media_type = 'video'
            elif ext.lower() in ['mp3', 'wav', 'ogg', 'm4a', 'webm']:
                media_type = 'audio'
    
    print(f"Sending message from {session['user_id']} to {receiver.id}: {(content or 'media')[:50]} ({media_type})")

    message = Message(
        sender_id=session['user_id'],
        receiver_id=receiver.id,
        content=content or '',
        media_url=media_url,
        media_type=media_type
    )
    db.session.add(message)
    db.session.commit()

    # Notify receiver with sound and note
    send_system_notification(receiver.id, "New Message", 
                             f"Message from {session['username']}: {message.content[:30]}...", type='message', url=url_for('messages', _external=True))

    # Push to receiver and sender in real-time (WhatsApp-like)
    try:
        # To receiver - message is "from sender" (is_me: false)
        receiver_payload = {
            'type': 'new_message',
            'other_user_id': session['user_id'],
            'message': {
                'id': message.id,
                'sender': session.get('username', 'Unknown'),
                'content': message.content,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
                'media_url': message.media_url,
                'media_type': message.media_type,
                'is_me': False,
            }
        }
        socketio.emit('new_message', receiver_payload, room=f"user:{receiver.id}", namespace='/')

        # To sender - message is "from me" (is_me: true), other_user_id = receiver
        sender_payload = {
            'type': 'new_message',
            'other_user_id': receiver.id,
            'message': {
                'id': message.id,
                'sender': session.get('username', 'Unknown'),
                'content': message.content,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
                'media_url': message.media_url,
                'media_type': message.media_type,
                'is_me': True,
            }
        }
        socketio.emit('new_message', sender_payload, room=f"user:{session['user_id']}", namespace='/')
    except Exception as e:
        print(f"[send_message] Socket emit failed: {e!r}")

    return jsonify({'success': True})


@app.route('/get_messages/<int:other_user_id>')
def get_messages(other_user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    
    messages = Message.query.filter(
        Message.is_deleted == False,
        db.or_(
            db.and_(Message.sender_id == user_id, Message.receiver_id == other_user_id),
            db.and_(Message.sender_id == other_user_id, Message.receiver_id == user_id)
        )
    ).order_by(Message.created_at).all()
    
    messages_data = []
    for msg in messages:
        messages_data.append({
            'id': msg.id, # Keep existing ID
            'sender': msg.sender.username if msg.sender else 'Deleted User', # Handle NoneType for sender
            'content': msg.content,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
            'media_url': msg.media_url,
            'media_type': msg.media_type,
            'is_me': msg.sender_id == user_id
        })
    
    return jsonify(messages_data)

@app.route('/delete_message/<int:msg_id>', methods=['POST'])
def delete_message(msg_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    msg = Message.query.get_or_404(msg_id)
    if msg.sender_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    msg.is_deleted = True
    db.session.commit()

    # Notify both participants to update UI in real-time
    payload = {'msg_id': msg_id, 'sender_id': msg.sender_id, 'receiver_id': msg.receiver_id}
    socketio.emit('message_deleted', payload, room=f"user:{msg.sender_id}", namespace='/')
    socketio.emit('message_deleted', payload, room=f"user:{msg.receiver_id}", namespace='/')

    return jsonify({'success': True})

@app.route('/messages_uploads/<path:filename>')
def messages_uploaded_file(filename):
    messages_folder = app.config['UPLOAD_FOLDER']
    return send_from_directory(messages_folder, f"messages/{filename}")

# API Routes
@app.route('/api/items')
def api_items():
    items = Item.query.order_by(Item.created_at.desc()).all()
    return jsonify([{
        'id': item.id,
        'title': item.title,
        'description': item.description,
        'price': item.price,
        'category': item.category,
        'condition': item.condition,
        'seller': item.seller.username,
        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
    } for item in items])


# --- Phone Tracking APIs ---

@app.route('/api/update_my_location', methods=['POST'])
def api_update_my_location():
    """Endpoint for the phone to report its own location."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json(force=True, silent=True) or {}
    lat = data.get('lat')
    lon = data.get('lon')
    
    try:
        lat_f = float(lat) if lat is not None else None
        lon_f = float(lon) if lon is not None else None
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid coordinates format'}), 400
    if lat_f is None or lon_f is None:
        return jsonify({'error': 'Missing coordinates'}), 400
        
    user = User.query.get(user_id)
    user.last_lat = lat_f
    user.last_lon = lon_f
    user.last_seen = datetime.now(UTC)
    db.session.commit()

    # Emit real-time update to the user's room
    socketio.emit('phone_location_update', {
        'lat': user.last_lat,
        'lon': user.last_lon,
        'last_seen': user.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC')
    }, room=f"user:{user_id}", namespace='/')
    
    return jsonify({'success': True})

@app.route('/api/get_phone_location')
def api_get_phone_location():
    """Endpoint to retrieve the current location of the user's phone."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    user = User.query.get(session['user_id'])
    
    if user.last_lat is None:
        # Return success true but null coords so the frontend can still initialize an empty map at a default center
        return jsonify({'success': True, 'lat': None, 'lon': None, 'message': 'No location data available.'})
        
    return jsonify({
        'success': True,
        'lat': user.last_lat,
        'lon': user.last_lon,
        'last_seen': user.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC') if user.last_seen else None
    })

@app.route('/api/trigger_alarm', methods=['POST'])
def api_trigger_alarm():
    """Endpoint to trigger an emergency alarm on the user's own device."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = session['user_id']
    # Emit a Socket.IO event to the user's room to trigger the alarm on their device
    socketio.emit('trigger_alarm', {
        'from_user_id': user_id,
        'message': 'Emergency alarm triggered!'
    }, room=f"user:{user_id}", namespace='/')
    return jsonify({'success': True, 'message': 'Alarm signal sent.'})

@app.route('/api/remote_lock', methods=['POST'])
def api_remote_lock():
    """Endpoint to trigger a remote lock on the user's own device."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = session['user_id']
    data = request.get_json(force=True, silent=True) or {}
    message = data.get('message', 'This device has been locked remotely. Please contact the owner.')
    contact_number = data.get('contact_number', '')

    socketio.emit('remote_lock', {
        'from_user_id': user_id,
        'message': message,
        'contact_number': contact_number
    }, room=f"user:{user_id}", namespace='/')
    return jsonify({'success': True, 'message': 'Remote lock signal sent.'})

@app.route('/api/remote_unlock', methods=['POST'])
def api_remote_unlock():
    """Endpoint to trigger a remote unlock on the user's own device."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user_id = session['user_id']
    socketio.emit('remote_unlock', {'from_user_id': user_id}, room=f"user:{user_id}", namespace='/')
    return jsonify({'success': True, 'message': 'Remote unlock signal sent.'})


@app.route('/api/device/update_location', methods=['POST'])
def api_device_update_location():
    """Phone agent reports location for a specific TrackedDevice via device_token."""
    data = request.get_json(force=True, silent=True) or {}

    device_token = (data.get('device_token') or '').strip()
    lat = data.get('lat')
    lon = data.get('lon')

    if not device_token:
        return jsonify({'error': 'Missing device_token'}), 400

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid coordinates'}), 400

    device = TrackedDevice.query.filter_by(device_token=device_token, is_active=True).first()
    if not device:
        return jsonify({'error': 'Invalid device_token'}), 403

    device.last_lat = lat_f
    device.last_lon = lon_f
    device.last_seen_at = datetime.now(UTC)
    db.session.commit()
    
    # Broadcast using the NEW event name so findmy_viewer and findmy_owner can see it
    timestamp_iso = datetime.now(UTC).isoformat()
    socketio.emit('findmy:location_update_stream', {
        'device_id': device.id,
        'latitude': lat_f,
        'longitude': lon_f,
        'accuracy': None,
        'timestamp': timestamp_iso
    }, room=f'device:{device.id}')

    # Notify all active shares for this device.
    shares = DeviceShare.query.filter_by(device_id=device.id, is_active=True).all()
    for share in shares:
        room = f"findmy:share:{share.share_token}"
        socketio.emit(
            'findmy:location_update_stream',
            {
                'share_token': share.share_token,
                'device_id': device.id, # Include device_id for consistency
                'latitude': device.last_lat,
                'longitude': device.last_lon,
                'accuracy': None, # Assuming accuracy is not stored per share, or can be derived
                'timestamp': timestamp_iso,
            },
            room=room,
            namespace='/',
        )

    return jsonify({'success': True})


@app.route('/api/device/current_location')
def api_device_current_location():
    """Viewer fetches current location using share_token."""
    share_token = (request.args.get('share_token') or '').strip()
    if not share_token:
        return jsonify({'error': 'Missing share_token'}), 400

    share = DeviceShare.query.filter_by(share_token=share_token, is_active=True).first()
    if not share:
        return jsonify({'error': 'Invalid share_token'}), 403

    device = share.device
    if not device or device.last_lat is None or device.last_lon is None:
        return jsonify({'success': True, 'lat': None, 'lon': None, 'last_seen_at': None})

    return jsonify(
        {
            'success': True,
            'lat': device.last_lat,
            'lon': device.last_lon,
            'last_seen_at': device.last_seen_at.strftime('%Y-%m-%d %H:%M:%S UTC') if device.last_seen_at else None,
        }
    )


@app.route('/api/device/trigger_alarm', methods=['POST'])
def api_device_trigger_alarm():
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get('device_id')
    share_token = (data.get('share_token') or '').strip()

    device = None
    if device_id:
        device = TrackedDevice.query.get(device_id)
        if not device or device.owner_user_id != session.get('user_id'):
            return jsonify({'error': 'Unauthorized to trigger alarm on this device'}), 403
    elif share_token:
        share = DeviceShare.query.filter_by(share_token=share_token, is_active=True).first()
        if not share:
            return jsonify({'error': 'Invalid share_token'}), 403
        # For MVP: require logged-in viewer matches stored viewer_user_id if present.
        if share.viewer_user_id and session.get('user_id') != share.viewer_user_id:
            return jsonify({'error': 'Unauthorized viewer'}), 403
        device = share.device
    else:
        return jsonify({'error': 'Missing device_id or share_token'}), 400

    if not device:
        return jsonify({'error': 'Device not found'}), 404

    socketio.emit(
        'device_trigger_alarm',
        {'share_token': share_token, 'device_id': device.id},
        room=f"findmy:device:{device.id}",
        namespace='/',
    )

    return jsonify({'success': True})


@app.route('/api/device/remote_lock', methods=['POST'])
def api_device_remote_lock():
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get('device_id')
    share_token = (data.get('share_token') or '').strip()
    message = (data.get('message') or '').strip() or 'This device has been locked remotely.'
    contact_number = (data.get('contact_number') or '').strip()

    device = None
    if device_id:
        device = TrackedDevice.query.get(device_id)
        if not device or device.owner_user_id != session.get('user_id'):
            return jsonify({'error': 'Unauthorized to lock this device'}), 403
    elif share_token:
        share = DeviceShare.query.filter_by(share_token=share_token, is_active=True).first()
        if not share:
            return jsonify({'error': 'Invalid share_token'}), 403
        if share.viewer_user_id and session.get('user_id') != share.viewer_user_id:
            return jsonify({'error': 'Unauthorized viewer'}), 403
        device = share.device
    else:
        return jsonify({'error': 'Missing device_id or share_token'}), 400

    if not device:
        return jsonify({'error': 'Device not found'}), 404

    socketio.emit(
        'device_remote_lock',
        {
            'share_token': share_token,
            'device_id': device.id,
            'message': message,
            'contact_number': contact_number,
        },
        room=f"findmy:device:{device.id}",
        namespace='/',
    )

    return jsonify({'success': True})


@app.route('/api/device/remote_unlock', methods=['POST'])
def api_device_remote_unlock():
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get('device_id')
    share_token = (data.get('share_token') or '').strip()

    device = None
    if device_id:
        device = TrackedDevice.query.get(device_id)
        if not device or device.owner_user_id != session.get('user_id'):
            return jsonify({'error': 'Unauthorized to unlock this device'}), 403
    elif share_token:
        share = DeviceShare.query.filter_by(share_token=share_token, is_active=True).first()
        if not share:
            return jsonify({'error': 'Invalid share_token'}), 403
        if share.viewer_user_id and session.get('user_id') != share.viewer_user_id:
            return jsonify({'error': 'Unauthorized viewer'}), 403
        device = share.device
    else:
        return jsonify({'error': 'Missing device_id or share_token'}), 400

    if not device:
        return jsonify({'error': 'Device not found'}), 404

    socketio.emit(
        'device_remote_unlock',
        {'share_token': share_token, 'device_id': device.id},
        room=f"findmy:device:{device.id}",
        namespace='/',
    )

    return jsonify({'success': True})


@app.route('/api/delivery_messages/send', methods=['POST'])
def api_send_delivery_message():
    """Send a message within a 3-party delivery thread."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json(force=True, silent=True) or {}
    delivery_id = data.get('delivery_id')
    content = (data.get('content') or '').strip()

    if not delivery_id or not content:
        return jsonify({'error': 'Delivery ID and content are required'}), 400

    delivery = db.session.get(Delivery, delivery_id)
    if not delivery:
        return jsonify({'error': 'Delivery not found'}), 404

    # Auth check: User must be sender, recipient, or the accepted rider
    user_id = session['user_id']
    is_sender = (delivery.sender_id == user_id)
    is_recipient = (delivery.recipient_id == user_id)
    is_rider = (delivery.accepted_rider_id == user_id)

    if not (is_sender or is_recipient or is_rider):
        return jsonify({'error': 'You are not a participant in this delivery'}), 403

    # Logic Check: Unlock only after rider accepts
    unlocked_statuses = ['accepted', 'arrived_at_pickup', 'picked_up', 'en_route', 'arrived_at_dropoff', 'roadside_handover', 'paid']
    if delivery.status not in unlocked_statuses:
        return jsonify({'error': 'Messaging is locked until the rider accepts the delivery'}), 403

    # Determine recipient_id to satisfy model FK (broadcast happens via Socket.IO room)
    # We target the 'other' primary party, but the room broadcast makes it 3-party.
    target_recipient_id = delivery.recipient_id if is_sender else delivery.sender_id

    msg = DeliveryMessage(
        delivery_id=delivery_id,
        sender_id=user_id,
        recipient_id=target_recipient_id,
        content=content
    )
    db.session.add(msg)
    db.session.commit()

    # Emit to the delivery room (all 3 parties should be joined via on_join_delivery)
    payload = {
        'id': msg.id,
        'delivery_id': delivery_id,
        'sender_id': user_id,
        'sender_username': session.get('username', 'User'),
        'content': content,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M')
    }
    # Broadcast to the shared delivery room and also to the individual participant rooms.
    socketio.emit('delivery_new_message', payload, room=f"delivery:{delivery_id}", namespace='/')
    if delivery.sender_id:
        socketio.emit('delivery_new_message', payload, room=f"user:{delivery.sender_id}", namespace='/')
    if delivery.recipient_id:
        socketio.emit('delivery_new_message', payload, room=f"user:{delivery.recipient_id}", namespace='/')
    if delivery.accepted_rider_id:
        socketio.emit('delivery_new_message', payload, room=f"user:{delivery.accepted_rider_id}", namespace='/')
        socketio.emit('delivery_new_message', payload, room=f"rider:{delivery.accepted_rider_id}", namespace='/')

    return jsonify({'success': True, 'message': payload})


@app.route('/api/delivery_messages/<int:delivery_id>')
def api_get_delivery_messages(delivery_id):
    """Retrieve chat history for a delivery."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    delivery = db.session.get(Delivery, delivery_id) or abort(404)
    user_id = session['user_id']
    if user_id not in [delivery.sender_id, delivery.recipient_id, delivery.accepted_rider_id]:
        return jsonify({'error': 'Unauthorized'}), 403

    msgs = DeliveryMessage.query.filter_by(delivery_id=delivery_id).order_by(DeliveryMessage.created_at.asc()).all()
    return jsonify([{
        'id': m.id,
        'sender_id': m.sender_id,
        'sender_username': m.sender.username,
        'content': m.content,
        'media_url': m.media_url,
        'media_type': m.media_type,
        'created_at': m.created_at.strftime('%Y-%m-%d %H:%M')
    } for m in msgs])


@app.route('/delivery/<int:delivery_id>/receipt/download')
def download_delivery_receipt(delivery_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    delivery = db.session.get(Delivery, delivery_id)
    if not delivery:
        return redirect(url_for('delivery'))

    user_id = session['user_id']
    if user_id not in [delivery.sender_id, delivery.recipient_id, delivery.accepted_rider_id]:
        return jsonify({'error': 'Unauthorized to view this receipt'}), 403

    if delivery.status not in ['paid', 'roadside_handover']:
        return jsonify({'error': 'Receipt is only available after payment or handover confirmation'}), 400

    html = render_template('delivery_receipt.html', delivery=delivery, now=datetime.now(UTC))
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="delivery_receipt_{delivery_id}.html"'
    return response


@socketio.on('join_findmy_device')
def on_join_findmy_device(payload):
    """Device agent joins its own room so it can receive alarm/lock events."""
    device_token = (payload.get('device_token') or '').strip()
    if not device_token:
        return

    device = TrackedDevice.query.filter_by(device_token=device_token, is_active=True).first()
    if not device:
        return

    join_room(f"findmy:device:{device.id}")


@socketio.on('join_findmy_share')
def on_join_findmy_share(payload):
    """Viewer joins a share room to receive live location updates."""
    share_token = (payload.get('share_token') or '').strip()
    if not share_token:
        return

    share = DeviceShare.query.filter_by(share_token=share_token, is_active=True).first()
    if not share:
        return

    # If share is private, require viewer is logged-in matching viewer_user_id.
    if share.viewer_user_id and session.get('user_id') != share.viewer_user_id:
        return

    join_room(f"findmy:share:{share_token}")


@app.route('/find-my-phone')
def find_my_phone():
    """Render the phone tracking and reporting interface (legacy viewer UI for now)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect("https://www.icloud.com/find")



# Trade-In Route
@app.route('/trade-in', methods=['GET', 'POST'])
def trade_in():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    trade_value = 0
    error = None
    success = False

    # Ensure these exist for GET requests (prevents UnboundLocalError)
    has_dent = False
    has_external_issue = False
    has_internal_issue = False
    age_years = None

    if request.method == 'POST':
        device_type = request.form.get('device_type')
        brand = request.form.get('brand') # Assuming brand is always 'iPhone' for these models
        model = request.form.get('model')
        condition = request.form.get('condition')
        storage = request.form.get('storage') # e.g., '64GB', '128GB', '256GB', '512GB', '1TB'
        age_years = request.form.get('age_years', type=int) # e.g., 1, 2, 5
        has_dent = 'has_dent' in request.form # Checkbox
        has_external_issue = 'has_external_issue' in request.form # Checkbox
        has_internal_issue = 'has_internal_issue' in request.form # Checkbox
        accessories = request.form.getlist('accessories')
        description = request.form.get('description')

        # Detailed base values including storage for iPhones
        # Prices are in local currency (e.g., GHC)
        # NOTE: Prices for iPhone 14, 15, 16, 17 series are estimated/extrapolated
        # as specific values were not provided beyond iPhone 13 Pro Max.
        base_values_detailed = {
            'iphone': {
                'iPhone XR': {'64GB': 1600, '128GB': 1700},
                'iPhone 11': {'64GB': 2000, '128GB': 2200},
                'iPhone 11 Pro': {'64GB': 2300, '256GB': 2400}, # Assuming 25gig was a typo for 256GB
                'iPhone 11 Pro Max': {'64GB': 2400, '256GB': 2700},
                'iPhone 12': {'64GB': 2200, '128GB': 2400, '256GB': 2600, '512GB': 2800},
                'iPhone 12 Pro': {'128GB': 2900, '256GB': 4000, '512GB': 4500},
                'iPhone 12 Pro Max': {'128GB': 3500, '256GB': 4200, '512GB': 4800},
                'iPhone 13': {'128GB': 3200, '256GB': 3300, '512GB': 3500},
                'iPhone 13 Pro': {'128GB': 4100, '256GB': 4200, '512GB': 4500, '1TB': 4800},
                'iPhone 13 Pro Max': {'128GB': 4800, '256GB': 5000, '512GB': 5300, '1TB': 5600},
                # Estimated prices for newer models
                'iPhone 14': {'128GB': 3800, '256GB': 3700, '512GB': 3900},
                'iPhone 14 Plus': {'128GB': 3800, '256GB': 4000, '512GB': 4200},
                'iPhone 14 Pro': {'128GB': 4500, '256GB': 4700, '512GB': 5000, '1TB': 5300},
                'iPhone 14 Pro Max': {'128GB': 5200, '256GB': 5400, '512GB': 5700, '1TB': 6000},
                'iPhone 15': {'128GB': 4100, '256GB': 4200, '512GB': 4400},
                'iPhone 15 Plus': {'128GB': 4500, '256GB': 4800, '512GB': 5000},
                'iPhone 15 Pro': {'128GB': 5500, '256GB': 5600, '512GB': 5900, '1TB': 6200},
                'iPhone 15 Pro Max': {'128GB': 6900, '256GB': 7000, '512GB': 7200, '1TB': 8000},
                'iPhone 16': {'128GB': 7100, '256GB': 7300, '512GB': 7500},
                'iPhone 16 Plus': {'128GB': 7300, '256GB': 7500, '512GB': 7700},
                'iPhone 16 Pro': {'128GB': 7300, '256GB': 7500, '512GB': 7700, '1TB': 8000},
                'iPhone 16 Pro Max': {'128GB': 8100, '256GB': 8300, '512GB': 8600, '1TB': 8900},
                'iPhone 16pro max': {'128GB': 8100, '256GB': 8300, '512GB': 8600, '1TB': 8900},
                'iPhone 17': {'128GB': 7400, '256GB': 4600, '512GB': 4800},

                'iPhone 17 Plus': {'128GB': 8400, '256GB': 8600, '512GB': 8700},

                'iPhone 17 Pro': {'128GB': 8100, '256GB': 8300, '512GB': 8400, '1TB': 6200},
                'iPhone 17 Pro Max': {'128GB': 9000, '256GB': 9200, '512GB': 9600, '1TB': 6900},
            },
            'ipad': {
                'iPad Pro 12.9-inch (6th gen)': {'128GB': 700, '256GB': 800, '512GB': 900, '1TB': 1000},
                'iPad Pro 11-inch (4th gen)': {'128GB': 500, '256GB': 600, '512GB': 700, '1TB': 800},
                'iPad Air (5th gen)': {'64GB': 400, '256GB': 500},
                'iPad (10th gen)': {'64GB': 250, '256GB': 350},
                'iPad mini (6th gen)': {'64GB': 200, '256GB': 300},
            },
            'macbook': {
                'MacBook Pro 16-inch (M2 Pro/Max)': {'512GB': 1500, '1TB': 1800, '2TB': 2200},
                'MacBook Pro 14-inch (M2 Pro/Max)': {'512GB': 1200, '1TB': 1500, '2TB': 1800},
                'MacBook Air (M2)': {'256GB': 800, '512GB': 1000, '1TB': 1200},
                'MacBook Pro 13-inch (M2)': {'256GB': 900, '512GB': 1100, '1TB': 1300},
            }
        }
        
        # Basic validation
        if not all([device_type, brand, model, condition, storage]):
            error = 'Please fill in all required fields'
        else:
            # Get base value based on device type, model, and storage
            base_value = 0
            if device_type in base_values_detailed and model in base_values_detailed[device_type]:
                if storage in base_values_detailed[device_type][model]:
                    base_value = base_values_detailed[device_type][model][storage]
                else:
                    # Fallback if specific storage not found, use lowest storage price or a default
                    # For simplicity, we'll take the first available storage price if exact match not found
                    first_storage_price = next(iter(base_values_detailed[device_type][model].values()), 0)
                    base_value = first_storage_price
                    error = f"Specific storage '{storage}' not found for '{model}'. Using base price of ${first_storage_price:.2f}."
            else:
                # Default values for unspecified models
                defaults = {
                    'iphone': 200,
                    'ipad': 150,
                    'macbook': 300,
                    'other_phone': 100,
                    'other_laptop': 150
                }
                base_value = defaults.get(device_type, 100)
                error = f"Model '{model}' not found in our database. Using default base value of ${base_value:.2f}."

            trade_value = base_value

            # Condition multipliers
            condition_multipliers = {
                'new': 1.0,
                'like-new': 0.85,
                'good': 0.65,
                'fair': 0.45,
                'poor': 0.25
            }

            # Get base value
            # This logic is now handled above with base_values_detailed

            # Apply condition multiplier
            multiplier = condition_multipliers.get(condition, 0.5)
            trade_value = base_value * multiplier

            # Apply issue deductions
            if has_dent:
                trade_value *= 0.90  # -10% for dent
            if has_external_issue:
                trade_value *= 0.80  # -20% for external issue
            if has_internal_issue:
                trade_value *= 0.70  # -30% for internal issue

            # Apply age deductions
            # Interpretation: 1 year old = -10%, 2 years old = -20%, 5+ years = -30%
            # Intermediate years (3, 4) are interpolated.
            if age_years is not None and age_years > 0:
                age_deduction_multiplier = 1.0
                if age_years == 1:
                    age_deduction_multiplier = 0.90 # -10%
                elif age_years == 2:
                    age_deduction_multiplier = 0.80 # -20%
                elif age_years == 3:
                    age_deduction_multiplier = 0.75 # -25% (example interpolation)
                elif age_years == 4:
                    age_deduction_multiplier = 0.72 # -28% (example interpolation)
                elif age_years >= 5:
                    age_deduction_multiplier = 0.70 # -30%
                
                trade_value *= age_deduction_multiplier

            # Add value for accessories
            accessory_value = len(accessories) * 25  # $25 per accessory
            trade_value += accessory_value
            
            success = True
    
    return render_template('trade_in.html',
                           trade_value=trade_value,
                           error=error,
                           success=success,
                           # Pass back form values to pre-fill if there was an error
                           device_type=request.form.get('device_type', ''),
                           brand=request.form.get('brand', ''),
                           model=request.form.get('model', ''),
                           condition=request.form.get('condition', ''),
                           storage=request.form.get('storage', ''),
                           age_years=request.form.get('age_years', type=int),
                           has_dent=has_dent,
                           has_external_issue=has_external_issue,
                           has_internal_issue=has_internal_issue)





if __name__ == '__main__':
    # Initialize database safely
    initialize_database()

    # Start background Apple news fetcher
    start_news_scheduler()

    preferred_port = os.environ.get('PORT')
    default_port = 5005
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    use_https = os.environ.get('USE_HTTPS', '0') == '1'

    if preferred_port:
        try:
            preferred_port = int(preferred_port)
        except ValueError:
            preferred_port = default_port
    else:
        preferred_port = default_port

    app.debug = debug_mode

    print("=" * 60)
    print("  Phil's iPhone Server Starting...")
    print(f"  Opening on the first available port starting at {preferred_port}...")
    if not os.environ.get('PORT'):
        print("  Port 5000 will be tried last to avoid common macOS port conflicts.")
    protocol = "https" if use_https else "http"
    lan_ip = get_lan_ip()
    print("-" * 60)
    print(f"  LOCAL: {protocol}://localhost:{preferred_port}")
    print(f"  LAN:   {protocol}://{lan_ip}:{preferred_port}")
    print("-" * 60)
    ssl_context = None
    if use_https:
        print("  SECURE CONTEXT ENABLED (Required for Microphone)")
        cert_path = os.path.join(basedir, 'cert.pem')
        key_path = os.path.join(basedir, 'key.pem')
        if os.path.exists(cert_path) and os.path.exists(key_path):
            print("  Using trusted SSL certificate (mkcert). No warnings expected!")
            ssl_context = (cert_path, key_path)
        else:
            print("  IMPORTANT: You must explicitly type 'https://' in your browser.")
            print("  Your browser will show a warning: Click 'Advanced'")
            print(f"  then 'Proceed to {lan_ip} (unsafe)'.")
            ssl_context = 'adhoc'
    else:
        print("\n" + "╔" + "═" * 58 + "╗")
        print("║" + " " * 21 + "SECURITY WARNING" + " " * 21 + "║")
        print("╠" + "═" * 58 + "╣")
        print("║  Server is running over HTTP (Insecure Context).         ║")
        print("║  Microphone access is DISABLED by browsers on non-local  ║")
        print("║  IP addresses (like your iPhone).                        ║")
        print("║                                                          ║")
        print("║  TO FIX: Restart with HTTPS enabled:                     ║")
        print("║  USE_HTTPS=1 python3 start.py                            ║")
        print("╚" + "═" * 58 + "╝\n")
    print("=" * 60)

    candidate_ports = [preferred_port]
    for fallback in (5005, 5001, 8000, 8080, 5000):
        if fallback not in candidate_ports:
            candidate_ports.append(fallback)

    for port in candidate_ports:
        try:
            print(f"Trying to start server on port {port}...")
            print(f"Server available at: {protocol}://127.0.0.1:{port}")
            print("Press Ctrl+C to stop the server.")
            socketio.run(
                app,
                debug=debug_mode,
                use_reloader=False,
                host='0.0.0.0',
                port=port,
                allow_unsafe_werkzeug=True,
                ssl_context=ssl_context
            )
            break
        except OSError as exc:
            print(f"Port {port} unavailable: {exc}")
    else:
        raise SystemExit("No available port found. Set PORT to a free port and restart.")                        