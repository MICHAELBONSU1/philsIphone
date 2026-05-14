"""
Phil's iPhone - Main Flask Application
A platform where main account posts phones/laptops, users can view items, 
approved users can post, and users can message each other.
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory

from flask_socketio import SocketIO, join_room, emit

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect
from datetime import datetime, UTC
import os
import math

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


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MEDIA_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg', 'm4a', 'webm'}

def allowed_media_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MEDIA_EXTENSIONS

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

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


class DeliveryUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=False)
    rider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))



# Create tables
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
@app.route('/')
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

@app.route('/admin_panel')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    # Automatically redirect almighty users to their superior panel
    if session.get('is_almighty'):
        return redirect(url_for('almighty_panel'))
    
    pending_requests = Request.query.filter_by(status='pending').all()
    pending_users = User.query.filter_by(can_post=False, is_admin=False).all()
    approved_users = User.query.filter_by(can_post=True, is_admin=False).all()
    all_users = User.query.filter(User.id != session['user_id']).all()
    return render_template('admin_panel.html', requests=pending_requests, pending_users=pending_users, approved_users=approved_users, all_users=all_users)

@app.route('/almighty_panel')
def almighty_panel():
    if not session.get('is_almighty'):
        return redirect(url_for('index'))
    
    all_users = User.query.all()
    all_items = Item.query.all()
    all_deliveries = Delivery.query.all()
    all_requests = Request.query.all()
    all_messages = Message.query.all()
    
    return render_template('almighty_panel.html', 
                         users=all_users, 
                         items=all_items, 
                         deliveries=all_deliveries, 
                         requests=all_requests,
                         messages=all_messages)

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
    user = User.query.get(session['user_id'])
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
    return render_template('delivery_sender.html', active_delivery=active)

@app.route('/delivery/recipient')
def delivery_recipient():
    if 'user_id' not in session: return redirect(url_for('login'))
    # Find the most recent active delivery for this recipient
    active = Delivery.query.filter(
        Delivery.recipient_id == session['user_id'], 
        Delivery.status != 'paid'
    ).order_by(Delivery.created_at.desc()).first()
    return render_template('delivery_recipient.html', active_delivery=active)

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
    })


def _delivery_riders_queryset():
    # Dedicated query for users registered as riders
    return User.query.filter(User.is_rider == True)


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
    """Bolt-style pricing: base fare + price per km."""
    base_fare = 2.00
    price_per_km = 1.50
    total = base_fare + (distance_km * price_per_km)
    return int(total * 100) # cents

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
        'delivery_guys': [{'id': u.id, 'username': u.username} for u in riders]
    })

@app.route('/api/rider/active_offers')
def api_rider_active_offers():
    """Endpoint for the Rider Portal to fetch available delivery jobs."""
    if 'user_id' not in session or not session.get('is_rider'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    rider_id = session['user_id']
    
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

    # Bolt Logic: Calculate distance and fare
    dist = calculate_haversine(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    fare_cents = estimate_bolt_fare(dist)

    matched_riders = _find_nearest_available_rider(pickup_lat, pickup_lon, limit=1)
    matched = matched_riders[0] if matched_riders else None

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
            {'delivery_id': delivery_obj.id, 'status': delivery_obj.status},
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

    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj or delivery_obj.recipient_id != session['user_id']:
        return jsonify({'error': 'Delivery not found or unauthorized'}), 404

    if delivery_obj.status != 'pending_recipient':
        return jsonify({'error': 'Delivery is not awaiting approval'}), 400

    if not approval_code or delivery_obj.approval_code is None or approval_code != str(delivery_obj.approval_code).strip().upper():
        return jsonify({'error': 'Invalid approval code'}), 403

    delivery_obj.status = 'requested'
    db.session.commit()

    # Notify riders that a new job has just become available
    socketio.emit('delivery_status_update', {'delivery_id': delivery_obj.id, 'status': 'requested'}, namespace='/')
    
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
    if delivery_obj.status not in ['accepted', 'requested']:
        return jsonify({'error': f"Cannot go online in status {delivery_obj.status}"}), 400

    delivery_obj.status = 'en_route'
    delivery_obj.en_route_at = datetime.now(UTC)
    db.session.commit()

    status_payload = {
        'delivery_id': delivery_obj.id,
        'status': delivery_obj.status,
        'en_route_at': delivery_obj.en_route_at.strftime('%Y-%m-%d %H:%M')
    }

    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.sender_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"user:{delivery_obj.recipient_id}", namespace='/')
    socketio.emit('delivery_status_update', status_payload, room=f"rider:{driver_id}", namespace='/')

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



# Socket.IO Events
@socketio.on('join_delivery')
def on_join_delivery(payload):
    try:
        delivery_id = int(payload.get('delivery_id'))
    except Exception:
        return

    room = f"delivery:{delivery_id}"
    join_room(room)

    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj:
        emit('delivery_initial', {})
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

    delivery_obj = Delivery.query.get(delivery_id)
    if not delivery_obj:
        return

    # Security/Correctness: only the assigned rider can broadcast live GPS.
    if delivery_obj.accepted_rider_id != rider_id and delivery_obj.matched_rider_id != rider_id:
        return

    # Also require the delivery to be in an active trip state.
    if delivery_obj.status not in ['accepted', 'arrived_at_pickup', 'picked_up', 'arrived_at_dropoff', 'roadside_handover', 'en_route', 'paid']:
        return

    room = f"delivery:{delivery_id}"
    emit('rider_location_update', {'lat': lat, 'lon': lon}, room=room, namespace='/')



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

    # Keep this page lightweight; the client loads the actual thread via /get_messages/<other_user_id>
    # so these aren't used by the messages.html JS right now.
    received_messages = Message.query.filter_by(receiver_id=user_id).order_by(Message.created_at.desc()).limit(200).all()
    sent_messages = Message.query.filter_by(sender_id=user_id).order_by(Message.created_at.desc()).limit(200).all()

    # Get all users for the conversation picker
    users_list = []
    for user in User.query.filter(User.id != user_id).all():
        users_list.append({'id': user.id, 'username': user.username})

    return render_template('messages.html', received_messages=received_messages, sent_messages=sent_messages, users=users_list)

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

    # Push to receiver in real-time (WhatsApp-like)
    try:
        payload = {
            'type': 'new_message',
            'other_user_id': session['user_id'],
            'message': {
                'id': message.id,
                'sender': User.query.get(session['user_id']).username,
                'content': message.content,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
                'media_url': message.media_url,
                'media_type': message.media_type,
                'is_me': False,
            }
        }
        socketio.emit('new_message', payload, room=f"user:{receiver.id}", namespace='/')
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
            'id': msg.id,
            'sender': msg.sender.username,
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

if __name__ == '__main__':
    # Ensure Socket.IO uses an async server that can handle continuous realtime traffic.
    # eventlet is included in requirements, so this works well in dev.
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
