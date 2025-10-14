#==========================================
import eventlet
eventlet.monkey_patch()
#==========================================

from flask_socketio import SocketIO, emit, join_room, leave_room

import os
from flask import Flask, jsonify, request, abort, send_from_directory, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import jsonify, request, send_file
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, ArgumentError
from sqlalchemy.orm import sessionmaker
from flask_cors import CORS
from datetime import timedelta, datetime, date
from flask_compress import Compress
from dotenv import load_dotenv
import traceback
import logging
import re
from flask_jwt_extended import JWTManager
from functools import wraps

#==========================================

app = Flask(__name__)
load_dotenv()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

def database_url():
    db_1 = os.getenv('DATABASE_URL')
    db_2 = os.getenv('DATABASE_URL_2')
    db_3 = os.getenv('DATABASE_FALLBACK_URL')

    print(f"DB_1: {db_1}")
    print(f"DB_2: {db_2}")
    print(f"DB_3: {db_3}")

    for name, db_url in [("Render New DB", db_1), ("Render Old DB", db_2)]:
        if db_url:
            try:
                engine = create_engine(db_url)
                engine.connect().close()
                print("=" * 70)
                print(f"✅ Connected to {name}")
                return db_url
            except OperationalError as e:
                print(f"❌ Failed to connect to {name}: {e}")
            except ArgumentError as e:
                print(f"⚠️ Invalid {name} URL: {e}")

    # Fallback to SQLite
    if db_3:
        if db_3.startswith("sqlite:///"):
            print("=" * 70)
            print("✅ Using local SQLite fallback database.")
            # No need to connect immediately; SQLAlchemy will create file if missing
            return db_3
        else:
            print("⚠️ Fallback DB URL invalid (should start with sqlite:///).")

    print("❌ All database connections failed!")
    return None

    
app.config['SQLALCHEMY_DATABASE_URI'] = database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "4321REWQ")
CORS(app, resources={
    r'/*': {
        'origins': [
            r'https://*.onrender.com',
            r'http://viewtv.viewtv.gt.tc',
            f'http://localhost:47947'
        ]
    }
})
app.logger.setLevel(logging.INFO)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
app.permanent_session_lifetime = timedelta(hours=732)
app.config["SESSION_TYPE"] = "filesystem"
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
login_manager = LoginManager()
login_manager.init_app(app)
jwt = JWTManager(app)
login_manager.login_view = 'login'
Compress(app)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

db = SQLAlchemy(app)

def nairobi_time():
    return datetime.utcnow() + timedelta(hours=3)

# =========================================
# USER MODEL
# =========================================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), default='User V', nullable=True)
    mobile = db.Column(db.String(20), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationships
    announcements = db.relationship('Announcement', backref='author', lazy=True)
    assignments = db.relationship('Assignment', backref='creator', lazy=True)

    def validate_mobile(self, mobile):
        """Validate mobile number format"""
        if not mobile:
            return True
        mobile_regex = r'^(07|01)[0-9]{8}$'
        return re.match(mobile_regex, mobile) is not None

    def set_mobile(self, mobile):
        """Set mobile with validation"""
        if mobile and not self.validate_mobile(mobile):
            raise ValueError("Mobile number must be 10 digits starting with 07 or 01")
        self.mobile = mobile

# ========================================
# ANNOUNCEMENT MODEL
# ========================================
class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)
    
    # Foreign key to user who posted
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

# =========================================
# TOPIC / THEME MODEL
# =========================================
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)

    # Relationship: a topic can have many assignments
    assignments = db.relationship('Assignment', backref='topic', lazy=True)

# =========================================
# ASSIGNMENT MODEL
# =========================================
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True) # Short title(e.g. "Math 112")
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True) # When to submit
    created_at = db.Column(db.DateTime, default=nairobi_time)

    # Store the actual uploaded file
    file_data = db.Column(db.LargeBinary, nullable=True)   # actual file content (bytes)
    file_name = db.Column(db.String(1255), nullable=True)   # original filename
    file_type = db.Column(db.String(100), nullable=True)   # MIME type (e.g. 'application/pdf')

    # Foreign keys
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # creator
# =========================================
# TIMETABLE MODEL
# =========================================
class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    room = db.Column(db.String(100), nullable=True)
    teacher = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)
    updated_at = db.Column(db.DateTime, default=nairobi_time, onupdate=nairobi_time)

    # Foreign key to topic (optional)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=True)
    
    # Relationship
    topic = db.relationship('Topic', backref='timetable_slots', lazy=True)

# =========================================
# MESSAGE MODELS
# ========================================

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room = db.Column(db.String(100), default='general')
    is_admin_message = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)  # For replies
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('messages', lazy=True))
    parent = db.relationship('Message', remote_side=[id], backref=db.backref('replies', lazy=True))

class MessageRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=nairobi_time)
    
    # Relationships
    message = db.relationship('Message', backref=db.backref('read_records', lazy=True))
    user = db.relationship('User', backref=db.backref('read_messages', lazy=True))    
#==========================================
# FILES MODEL
#==========================================
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    file_data = db.Column(db.LargeBinary, nullable=False)  # Actual file data
    description = db.Column(db.Text)
    category = db.Column(db.String(100), default='general')
    uploaded_at = db.Column(db.DateTime, default=nairobi_time)
    updated_at = db.Column(db.DateTime, default=nairobi_time, onupdate=nairobi_time)
    
    # Foreign Keys
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    uploader = db.relationship('User', backref=db.backref('uploaded_files', lazy=True))
    
    def __repr__(self):
        return f'<File {self.name}>'
#==========================================    
with app.app_context():
    try:
        db.create_all()

        # Create admin user if not exists
        admin = User.query.filter_by(mobile="0740694312").first()
        if not admin:
            admin = User(
                username="Administrator",
                mobile="0740694312",
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created.")
        else:
            print("ℹ️ Admin already exists.")
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Database initialization error: {e}")
#==========================================
# User Loader Helper
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        print(f'⚠️ Error loading user {user_id}: {e}')
        db.session.rollback()  # ✅ reset failed transaction
        return None

@app.teardown_request
def teardown_request(exception):
    if exception:
        db.session.rollback()
    db.session.remove()

def _year():
    return datetime.now().strftime('%Y')

ALLOWED_KEYWORDS = [
    "mozilla",      # Chrome, Firefox, Edge, Safari all contain this
    "applewebkit",  # Chrome, Safari
    "chrome",       
    "safari",
    "firefox",
    "edge",
]

@app.before_request
def allow_only_known_browsers():
    ua = request.headers.get("User-Agent", "").lower()

    # No User-Agent? Probably a script or bot
    if not ua:
        abort(403)

    # If none of the allowed patterns appear → block
    if not any(kw in ua for kw in ALLOWED_KEYWORDS):
        abort(403)

    # Optionally: require some common browser headers
    required_headers = ["accept", "accept-language"]
    for h in required_headers:
        if h not in {k.lower() for k in request.headers.keys()}:
            abort(403)

def admin_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if not current_user.is_authenticated:
            # If AJAX/API request, return JSON error
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Login first to access the page', 'error')
            return redirect(url_for('login'))
        if not current_user.is_admin:
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Access denied.'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorator
    
#==========================================
#                   Routes
#==========================================
@app.route('/login', methods=['POST', 'GET'])
def login():
    next_page = request.args.get("next") or request.form.get("next")
    if current_user.is_authenticated:
        return redirect(next_page or url_for('admin_page') if current_user.is_admin else url_for('main_page'))
    if request.method == 'POST':
        username = request.form.get('username', '')[:50]
        mobile = request.form.get('mobile')
        admin_secret = request.form.get('admin_secret')  # For admin login

        # Validate mobile
        if not mobile or len(mobile) != 10:
            flash('Invalid mobile number')
            return render_template('login.html', username=username, mobile=mobile, year=_year())
        
        user = User.query.filter_by(mobile=mobile).first()
        
        # Admin login attempt
        if admin_secret:
            if not user or not user.is_admin:
                flash('Invalid admin credentials')
                return render_template('login.html', username=username, mobile=mobile, year=_year())
            login_user(user)
            return redirect(url_for('admin_page'))
        
        # Student login
        if not user:
            new_user = User(
                username=username,
                mobile=mobile
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
        else:
            login_user(user)
        # Redirect to appropriate dashboard
        if user and user.is_admin:
            return redirect(next_page or url_for('admin_page'))
        else:
            return redirect(next_page or url_for('main_page'))
    
    return render_template('login.html', year=_year())

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout Successfully!', 'sucess')
    return redirect(url_for('home'))

#===================================================
@app.route('/')
def home():
    return render_template('index.html', year=_year())

@app.route('/main-page')
@login_required
def main_page():
    return render_template('main_page.html', year=_year())

@app.route('/admin')
@login_required
@admin_required
def admin_page():
    return render_template('admin.html', year=_year())

# User management route
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    return render_template('admin_users.html')

@app.route('/profile')
@login_required
def profile():
    """Render the profile edit page"""
    return render_template('edit_profile.html')

# routes.py - Add these routes

@app.route('/files')
@login_required
def files():
    """Render the file management page"""
    return render_template('files.html')

# =========================================
# MESSAGES ROUTES
# =========================================

@app.route('/messages')
@login_required
def messages():
    """Render the messages page with initial data"""
    try:
        # Get the room from query parameter or default to 'general'
        room = request.args.get('room', 'general')
        
        # Get recent messages for the room (last 50 messages)
        messages = Message.query.filter_by(
            room=room, 
            is_deleted=False
        ).order_by(Message.created_at.desc()).limit(50).all()
        
        # Reverse to show oldest first in the UI
        messages.reverse()
        
        # Get unread count for the current user
        unread_count = get_unread_count(current_user.id)
        
        # Update user's current room in the database if you have that field
        # This helps with reconnection and room persistence
        if hasattr(current_user, 'current_room'):
            current_user.current_room = room
            db.session.commit()
        
        return render_template(
            'messages.html',
            messages=messages,
            current_user=current_user,
            unread_count=unread_count,
            room=room
        )
        
    except Exception as e:
        print(f"Error loading messages page: {e}")
        # Fallback: return basic page without messages
        return render_template(
            'messages.html',
            messages=[],
            current_user=current_user,
            unread_count=0,
            room='general'
        )

@app.route('/messages/<room_name>')
@login_required
def messages_room(room_name):
    """Render messages page for a specific room"""
    try:
        # Validate room name
        valid_rooms = ['general', 'help', 'announcements']
        if room_name not in valid_rooms:
            room_name = 'general'
        
        # Get recent messages for the room
        messages = Message.query.filter_by(
            room=room_name, 
            is_deleted=False
        ).order_by(Message.created_at.desc()).limit(50).all()
        
        messages.reverse()
        
        # Get unread count
        unread_count = get_unread_count(current_user.id)
        
        # Update user's current room
        if hasattr(current_user, 'current_room'):
            current_user.current_room = room_name
            db.session.commit()
        
        return render_template(
            'messages.html',
            messages=messages,
            current_user=current_user,
            unread_count=unread_count,
            room=room_name
        )
        
    except Exception as e:
        print(f"Error loading messages room {room_name}: {e}")
        return render_template(
            'messages.html',
            messages=[],
            current_user=current_user,
            unread_count=0,
            room=room_name
        )

def get_unread_count(user_id):
    """Get count of unread messages for a user"""
    try:
        # Count messages that haven't been read by this user
        # This is a simplified version - you might need to adjust based on your exact logic
        
        # Get all message IDs that the user has read
        read_message_ids = db.session.query(MessageRead.message_id).filter_by(
            user_id=user_id
        ).subquery()
        
        # Count messages that are not in the read list and not deleted
        unread_count = Message.query.filter(
            Message.id.notin_(read_message_ids),
            Message.is_deleted == False,
            Message.user_id != user_id  # Don't count user's own messages
        ).count()
        
        return unread_count
        
    except Exception as e:
        print(f"Error getting unread count: {e}")
        return 0
#--------------------------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.config['UPLOAD_FOLDER'], 'favicon.ico')
#--------------------------------------------------------------------
@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'manifest.json', mimetype='application/manifest+json')
#--------------------------------------------------------------------
@app.route("/offline.html")
def offline_html():
    return render_template("offline.html")
#-------------------------------------------------------------------
@app.route('/service-worker.js')
def sw():
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')
#-------------------------------------------------------------------
@app.route('/is_authenticated')
def is_authenticated():
    return jsonify({'authenticated': current_user.is_authenticated})
#-------------------------------------------------------------------
#==========================================
# FILE API
#==========================================
@app.route('/api/files')
@login_required
def get_files():
    """Get all files with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    # Build query
    query = File.query
    
    if category:
        query = query.filter(File.category == category)
    
    if search:
        query = query.filter(
            db.or_(
                File.name.ilike(f'%{search}%'),
                File.description.ilike(f'%{search}%'),
                File.filename.ilike(f'%{search}%')
            )
        )
    
    # Get paginated results
    files_pagination = query.order_by(File.uploaded_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    files_data = []
    for file in files_pagination.items:
        files_data.append({
            'id': file.id,
            'name': file.name,
            'filename': file.filename,
            'file_type': file.file_type,
            'file_size': file.file_size,
            'description': file.description,
            'category': file.category,
            'uploaded_at': file.uploaded_at.isoformat(),
            'updated_at': file.updated_at.isoformat(),
            'uploaded_by': file.uploader.username if file.uploader else 'Unknown',
            'can_delete': current_user.is_admin or current_user.id == file.uploaded_by
        })
    
    return jsonify({
        'files': files_data,
        'total': files_pagination.total,
        'pages': files_pagination.pages,
        'current_page': page,
        'has_next': files_pagination.has_next,
        'has_prev': files_pagination.has_prev
    })

def shorten_filename(filename, length=15):
    name, ext = os.path.splitext(filename)
    return f"{name[:length]}...{ext}" if len(name) > length else filename

@app.route('/api/files/upload', methods=['POST'])
@login_required
def upload_file():
    """Upload a new file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get form data
    name = request.form.get('name', file.filename)[:25]
    filename = shorten_filename(file.filename)
    description = request.form.get('description', '')[:100]
    category = request.form.get('category', 'general')
    
    # Validate file size (10MB limit)
    file_data = file.read()
    if len(file_data) > 10 * 1024 * 1024:  # 10MB
        return jsonify({'error': 'File size exceeds 10MB limit'}), 400
    
    # Check if filename already exists
    existing_file = File.query.filter_by(filename=file.filename).first()
    if existing_file:
        return jsonify({'error': 'A file with this name already exists'}), 400
    
    try:
        new_file = File(
            name=name,
            filename=filename,
            file_type=file.content_type,
            file_size=len(file_data),
            file_data=file_data,
            description=description,
            category=category,
            uploaded_by=current_user.id
        )
        
        db.session.add(new_file)
        db.session.commit()
        
        return jsonify({
            'message': 'File uploaded successfully',
            'file': {
                'id': new_file.id,
                'name': new_file.name,
                'filename': new_file.filename,
                'file_type': new_file.file_type,
                'file_size': new_file.file_size
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to upload file'}), 500

@app.route('/api/files/<int:id>/download')
@login_required
def download_file(id):
    """Download a file"""
    file = File.query.get_or_404(id)
    
    return send_file(
        BytesIO(file.file_data),
        download_name=file.filename,
        as_attachment=True,
        mimetype=file.file_type
    )

@app.route('/api/files/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_file(id):
    """Delete a file"""
    file = File.query.get_or_404(id)
    
    # Check permissions (admin or uploader)
    if not current_user.is_admin and current_user.id != file.uploaded_by:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(file)
        db.session.commit()
        
        return jsonify({'message': 'File deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete file'}), 500

@app.route('/api/files/categories')
@login_required
def get_file_categories():
    """Get all file categories"""
    categories = db.session.query(File.category).distinct().all()
    category_list = [cat[0] for cat in categories if cat[0]]
    
    return jsonify({'categories': category_list})

#==========================================
#   UPDATE USER API ROUTES
#==========================================
@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_user_profile():
    """Get current user's profile data"""
    user_data = {
        'id': current_user.id,
        'username': current_user.username,
        'mobile': current_user.mobile,
        'created_at': current_user.created_at.isoformat(),
        'is_admin': current_user.is_admin,
        'announcements_count': len(current_user.announcements),
        'assignments_count': len(current_user.assignments)
    }
    return jsonify(user_data)

@app.route('/api/user/profile', methods=['PUT'])
@login_required
def update_user_profile():
    """Update current user's profile"""
    data = request.get_json()
    
    # Validate input
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    mobile = data.get('mobile', '').strip()
    
    # Validate username
    if not username or len(username) > 200:
        return jsonify({'error': 'Username must be between 1 and 200 characters'}), 400
    
    # Validate mobile format
    mobile_regex = r'^(07|01)[0-9]{8}$'
    if not re.match(mobile_regex, mobile):
        return jsonify({'error': 'Mobile number must be 10 digits starting with 07 or 01'}), 400
    
    # Check if mobile is already taken by another user
    existing_user = User.query.filter(
        User.mobile == mobile, 
        User.id != current_user.id
    ).first()
    
    if existing_user:
        return jsonify({'error': 'Mobile number is already registered'}), 400
    
    try:
        # Update user data
        current_user.username = username
        current_user.mobile = mobile
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'mobile': current_user.mobile
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500


# =========================================
# MESSAGES BACKEND ROUTES & SOCKET HANDLERS
# =========================================

# Global dictionary to track online users
online_users = {}

# =========================================
# HTTP ROUTES
# =========================================

@app.route('/api/online-users')
@login_required
def get_online_users():
    """Get currently online users"""
    cleanup_disconnected_users()
    
    users = []
    for user_id, user_data in online_users.items():
        if user_data and 'user_id' in user_data:
            users.append({
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'is_admin': user_data.get('is_admin', False),
                'last_seen': user_data.get('last_seen'),
                'room': user_data.get('current_room', 'general')
            })
    
    return jsonify(users)

@app.route('/api/messages')
@login_required
def get_messages():
    """Get messages for a room with optional filtering"""
    room = request.args.get('room', 'general')
    since_id = request.args.get('since_id', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    
    try:
        # Base query - exclude deleted messages
        query = Message.query.filter_by(room=room, is_deleted=False)
        
        # Filter messages newer than since_id if provided
        if since_id > 0:
            query = query.filter(Message.id > since_id)
        
        # Get messages ordered by creation time
        messages = query.order_by(Message.created_at.asc()).limit(limit).all()
        
        # Get read status for current user
        read_message_ids = set()
        if current_user.is_authenticated:
            read_records = MessageRead.query.filter_by(user_id=current_user.id).all()
            read_message_ids = {record.message_id for record in read_records}
        
        # Format response
        messages_data = []
        for message in messages:
            message_data = {
                'id': message.id,
                'content': message.content,
                'user_id': message.user_id,
                'username': message.user.username,
                'is_admin': message.user.is_admin,
                'is_admin_message': message.is_admin_message,
                'created_at': message.created_at.isoformat(),
                'room': message.room,
                'is_read': message.id in read_message_ids,
                'parent_id': message.parent_id,
                'has_replies': len(message.replies) > 0 if message.replies else False
            }
            
            # Include reply data if it's a reply
            if message.parent_id:
                parent_message = Message.query.get(message.parent_id)
                if parent_message and not parent_message.is_deleted:
                    message_data['parent'] = {
                        'id': parent_message.id,
                        'content': parent_message.content,
                        'username': parent_message.user.username,
                        'user_id': parent_message.user_id
                    }
            
            messages_data.append(message_data)
        
        return jsonify({
            'success': True,
            'messages': messages_data,
            'room': room,
            'total': len(messages_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/messages/read', methods=['POST'])
@login_required
def mark_messages_read():
    """Mark messages as read for current user"""
    try:
        data = request.get_json()
        message_ids = data.get('message_ids', [])
        
        if not message_ids:
            return jsonify({'success': False, 'error': 'No message IDs provided'}), 400
        
        # Mark each message as read
        for message_id in message_ids:
            # Check if already marked as read
            existing_read = MessageRead.query.filter_by(
                message_id=message_id, 
                user_id=current_user.id
            ).first()
            
            if not existing_read:
                message_read = MessageRead(
                    message_id=message_id,
                    user_id=current_user.id
                )
                db.session.add(message_read)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Marked {len(message_ids)} messages as read',
            'read_count': len(message_ids)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    """Send a message via HTTP API (fallback)"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        room = data.get('room', 'general')
        parent_id = data.get('parent_id')  # For replies
        
        if not content:
            return jsonify({'success': False, 'error': 'Message content is required'}), 400
        
        # Validate parent message if replying
        if parent_id:
            parent_message = Message.query.get(parent_id)
            if not parent_message or parent_message.is_deleted:
                return jsonify({'success': False, 'error': 'Parent message not found'}), 404
        
        # Create message
        message = Message(
            content=content,
            user_id=current_user.id,
            room=room,
            is_admin_message=current_user.is_admin,
            parent_id=parent_id
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Prepare response
        message_data = {
            'id': message.id,
            'content': message.content,
            'user_id': message.user_id,
            'username': current_user.username,
            'is_admin': current_user.is_admin,
            'is_admin_message': current_user.is_admin,
            'created_at': message.created_at.isoformat(),
            'room': room,
            'parent_id': parent_id,
            'is_read': False
        }
        
        # Include parent data if it's a reply
        if parent_id:
            parent_message = Message.query.get(parent_id)
            if parent_message and not parent_message.is_deleted:
                message_data['parent'] = {
                    'id': parent_message.id,
                    'content': parent_message.content,
                    'username': parent_message.user.username
                }
        
        # Emit to Socket.IO clients in the room
        socketio.emit('new_message', message_data, room=room)
        
        return jsonify({
            'success': True,
            'message': message_data
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/messages/<int:message_id>/reply', methods=['POST'])
@login_required
def reply_to_message(message_id):
    """Reply to a specific message"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'success': False, 'error': 'Reply content is required'}), 400
        
        # Get parent message
        parent_message = Message.query.get(message_id)
        if not parent_message or parent_message.is_deleted:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Create reply
        reply = Message(
            content=content,
            user_id=current_user.id,
            room=parent_message.room,
            is_admin_message=current_user.is_admin,
            parent_id=message_id
        )
        
        db.session.add(reply)
        db.session.commit()
        
        # Prepare response
        reply_data = {
            'id': reply.id,
            'content': reply.content,
            'user_id': reply.user_id,
            'username': current_user.username,
            'is_admin': current_user.is_admin,
            'is_admin_message': current_user.is_admin,
            'created_at': reply.created_at.isoformat(),
            'room': parent_message.room,
            'parent_id': message_id,
            'is_read': False,
            'parent': {
                'id': parent_message.id,
                'content': parent_message.content,
                'username': parent_message.user.username
            }
        }
        
        # Emit to Socket.IO clients in the room
        socketio.emit('new_message', reply_data, room=parent_message.room)
        
        return jsonify({
            'success': True,
            'message': reply_data
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """Delete a message (soft delete)"""
    try:
        message = Message.query.get(message_id)
        
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Check permissions - user can delete their own messages or admin can delete any
        if message.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        # Soft delete the message
        message.is_deleted = True
        message.deleted_at = nairobi_time()
        message.content = "[This message was deleted]"
        
        db.session.commit()
        
        # Emit deletion event
        socketio.emit('message_deleted', {
            'message_id': message_id,
            'room': message.room,
            'deleted_by': current_user.id,
            'is_admin_action': current_user.is_admin
        }, room=message.room)
        
        return jsonify({
            'success': True,
            'message': 'Message deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/messages/<int:message_id>/replies')
@login_required
def get_message_replies(message_id):
    """Get replies for a specific message"""
    try:
        message = Message.query.get(message_id)
        
        if not message or message.is_deleted:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Get replies
        replies = Message.query.filter_by(
            parent_id=message_id, 
            is_deleted=False
        ).order_by(Message.created_at.asc()).all()
        
        # Get read status for current user
        read_message_ids = set()
        if current_user.is_authenticated:
            read_records = MessageRead.query.filter_by(user_id=current_user.id).all()
            read_message_ids = {record.message_id for record in read_records}
        
        replies_data = []
        for reply in replies:
            reply_data = {
                'id': reply.id,
                'content': reply.content,
                'user_id': reply.user_id,
                'username': reply.user.username,
                'is_admin': reply.user.is_admin,
                'is_admin_message': reply.is_admin_message,
                'created_at': reply.created_at.isoformat(),
                'room': reply.room,
                'parent_id': reply.parent_id,
                'is_read': reply.id in read_message_ids
            }
            replies_data.append(reply_data)
        
        return jsonify({
            'success': True,
            'replies': replies_data,
            'parent_message': {
                'id': message.id,
                'content': message.content,
                'username': message.user.username
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =========================================
# UTILITY FUNCTIONS
# =========================================

def cleanup_disconnected_users():
    """Remove users who haven't been seen for more than 30 seconds"""
    current_time = datetime.utcnow()
    disconnected_users = []
    
    for user_id, user_data in online_users.items():
        if user_data and 'last_seen' in user_data:
            last_seen = user_data['last_seen']
            if isinstance(last_seen, str):
                try:
                    last_seen = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                except:
                    continue
            
            if current_time - last_seen > timedelta(seconds=30):
                disconnected_users.append(user_id)
    
    for user_id in disconnected_users:
        user_data = online_users.pop(user_id, None)
        if user_data:
            room = user_data.get('current_room', 'general')
            emit('user_left', {
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'message': f'{user_data["username"]} left the chat'
            }, room=room, include_self=False)

def update_user_presence(user_id, username, is_admin=False, room='general'):
    """Update user's online status and room"""
    online_users[user_id] = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin,
        'current_room': room,
        'last_seen': datetime.utcnow().isoformat()
    }
    
    # Broadcast updated online users list to the room
    room_users = []
    for uid, user_data in online_users.items():
        if user_data and user_data.get('current_room') == room:
            room_users.append({
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'is_admin': user_data.get('is_admin', False)
            })
    
    emit('online_users_update', {'users': room_users}, room=room)

def broadcast_online_users():
    """Broadcast updated online users list to all rooms"""
    cleanup_disconnected_users()
    
    # Group users by room
    room_users = {}
    for user_id, user_data in online_users.items():
        if user_data and 'user_id' in user_data:
            room = user_data.get('current_room', 'general')
            if room not in room_users:
                room_users[room] = []
            
            room_users[room].append({
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'is_admin': user_data.get('is_admin', False)
            })
    
    # Emit to each room
    for room, users in room_users.items():
        emit('online_users_update', {'users': users}, room=room)

# =========================================
# SOCKET.IO HANDLERS
# =========================================

@socketio.on('connect')
def handle_connect():
    """Handle user connection"""
    if current_user.is_authenticated:
        # Add user to online users
        update_user_presence(
            user_id=current_user.id,
            username=current_user.username,
            is_admin=current_user.is_admin,
            room='general'
        )
        
        # Join general room by default
        join_room('general')
        
        # Notify others in the general room
        emit('user_joined', {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin,
            'message': f'{current_user.username} joined the chat'
        }, room='general', include_self=False)
        
        # Send current user their own user info
        emit('user_info', {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin
        })
        
        print(f"User {current_user.username} connected. Online users: {len(online_users)}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection"""
    if current_user.is_authenticated:
        user_data = online_users.get(current_user.id)
        
        if user_data:
            room = user_data.get('current_room', 'general')
            
            # Remove user from online users
            online_users.pop(current_user.id, None)
            
            # Notify others
            emit('user_left', {
                'user_id': current_user.id,
                'username': current_user.username,
                'message': f'{current_user.username} left the chat'
            }, room=room, include_self=False)
            
            # Broadcast updated online users list
            broadcast_online_users()
        
        print(f"User {current_user.username} disconnected. Online users: {len(online_users)}")

@socketio.on('join_room')
def handle_join_room(data):
    """Handle joining a room"""
    if current_user.is_authenticated:
        room = data.get('room', 'general')
        previous_room = online_users.get(current_user.id, {}).get('current_room', 'general')
        
        # Leave previous room if different
        if previous_room != room:
            leave_room(previous_room)
            emit('user_left', {
                'user_id': current_user.id,
                'username': current_user.username,
                'message': f'{current_user.username} left {previous_room}'
            }, room=previous_room, include_self=False)
        
        # Join new room
        join_room(room)
        
        # Update user presence
        update_user_presence(
            user_id=current_user.id,
            username=current_user.username,
            is_admin=current_user.is_admin,
            room=room
        )
        
        # Notify room
        emit('user_joined', {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin,
            'message': f'{current_user.username} joined {room}'
        }, room=room, include_self=False)
        
        # Send room history to the user
        messages = Message.query.filter_by(room=room, is_deleted=False).order_by(Message.created_at.asc()).limit(50).all()
        
        # Get read status for current user
        read_message_ids = set()
        if current_user.is_authenticated:
            read_records = MessageRead.query.filter_by(user_id=current_user.id).all()
            read_message_ids = {record.message_id for record in read_records}
        
        for message in messages:
            message_data = {
                'id': message.id,
                'content': message.content,
                'user_id': message.user_id,
                'username': message.user.username,
                'is_admin': message.user.is_admin,
                'is_admin_message': message.is_admin_message,
                'created_at': message.created_at.isoformat(),
                'room': room,
                'is_read': message.id in read_message_ids,
                'parent_id': message.parent_id
            }
            
            # Include parent data if it's a reply
            if message.parent_id:
                parent_message = Message.query.get(message.parent_id)
                if parent_message and not parent_message.is_deleted:
                    message_data['parent'] = {
                        'id': parent_message.id,
                        'content': parent_message.content,
                        'username': parent_message.user.username
                    }
            
            emit('new_message', message_data)

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle leaving a room"""
    if current_user.is_authenticated:
        room = data.get('room', 'general')
        leave_room(room)
        
        # Update user presence (set to general room)
        update_user_presence(
            user_id=current_user.id,
            username=current_user.username,
            is_admin=current_user.is_admin,
            room='general'
        )
        
        # Notify room
        emit('user_left', {
            'user_id': current_user.id,
            'username': current_user.username,
            'message': f'{current_user.username} left {room}'
        }, room=room, include_self=False)
        
        # Join general room
        join_room('general')
        
        emit('room_left', {
            'room': room,
            'user_id': current_user.id,
            'username': current_user.username
        })

@socketio.on('send_message')
def handle_send_message(data):
    """Handle new message"""
    if not current_user.is_authenticated:
        return {'success': False, 'error': 'Not authenticated'}
    
    content = data.get('content', '').strip()
    room = data.get('room', 'general')
    parent_id = data.get('parent_id')
    
    if not content:
        return {'success': False, 'error': 'Empty message'}
    
    # Validate parent message if replying
    if parent_id:
        parent_message = Message.query.get(parent_id)
        if not parent_message or parent_message.is_deleted:
            return {'success': False, 'error': 'Parent message not found'}
    
    # Update user presence (keep them in current room)
    update_user_presence(
        user_id=current_user.id,
        username=current_user.username,
        is_admin=current_user.is_admin,
        room=room
    )
    
    # Create message
    message = Message(
        content=content,
        user_id=current_user.id,
        room=room,
        is_admin_message=current_user.is_admin,
        parent_id=parent_id
    )
    
    try:
        db.session.add(message)
        db.session.commit()
        
        # Prepare response data
        message_data = {
            'id': message.id,
            'content': message.content,
            'user_id': message.user_id,
            'username': current_user.username,
            'is_admin': current_user.is_admin,
            'is_admin_message': current_user.is_admin,
            'created_at': message.created_at.isoformat(),
            'room': room,
            'parent_id': parent_id,
            'is_read': False
        }
        
        # Include parent data if it's a reply
        if parent_id:
            parent_message = Message.query.get(parent_id)
            if parent_message and not parent_message.is_deleted:
                message_data['parent'] = {
                    'id': parent_message.id,
                    'content': parent_message.content,
                    'username': parent_message.user.username
                }
        
        # Broadcast to room
        emit('new_message', message_data, room=room)
        
        return {'success': True, 'message': message_data}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}

@socketio.on('delete_message')
def handle_delete_message(data):
    """Handle message deletion via WebSocket"""
    if not current_user.is_authenticated:
        return {'success': False, 'error': 'Not authenticated'}
    
    message_id = data.get('message_id')
    
    if not message_id:
        return {'success': False, 'error': 'Message ID required'}
    
    try:
        message = Message.query.get(message_id)
        
        if not message:
            return {'success': False, 'error': 'Message not found'}
        
        # Check permissions
        if message.user_id != current_user.id and not current_user.is_admin:
            return {'success': False, 'error': 'Permission denied'}
        
        # Soft delete the message
        message.is_deleted = True
        message.deleted_at = nairobi_time()
        message.content = "[This message was deleted]"
        
        db.session.commit()
        
        # Emit deletion event
        emit('message_deleted', {
            'message_id': message_id,
            'room': message.room,
            'deleted_by': current_user.id,
            'is_admin_action': current_user.is_admin
        }, room=message.room)
        
        return {'success': True, 'message': 'Message deleted successfully'}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    if current_user.is_authenticated:
        room = data.get('room', 'general')
        emit('user_typing', {
            'user_id': current_user.id,
            'username': current_user.username,
            'room': room
        }, room=room, include_self=False)

@socketio.on('ping')
def handle_ping(data):
    """Handle ping for connection health check"""
    if current_user.is_authenticated:
        # Get the current room from online_users or use default
        user_room = online_users.get(current_user.id, {}).get('current_room', 'general')
        
        # Update user presence
        update_user_presence(
            user_id=current_user.id,
            username=current_user.username,
            is_admin=current_user.is_admin,
            room=user_room
        )
        
        # Return the timestamp for latency calculation
        emit('pong', {'timestamp': data.get('timestamp')})

@socketio.on('get_messages')
def handle_get_messages(data):
    """Handle request for messages via WebSocket"""
    if current_user.is_authenticated:
        room = data.get('room', 'general')
        since_id = data.get('since_id', 0)
        limit = data.get('limit', 100)
        
        try:
            query = Message.query.filter_by(room=room, is_deleted=False)
            if since_id > 0:
                query = query.filter(Message.id > since_id)
            
            messages = query.order_by(Message.created_at.asc()).limit(limit).all()
            
            # Get read status for current user
            read_message_ids = set()
            if current_user.is_authenticated:
                read_records = MessageRead.query.filter_by(user_id=current_user.id).all()
                read_message_ids = {record.message_id for record in read_records}
            
            messages_data = []
            for message in messages:
                message_data = {
                    'id': message.id,
                    'content': message.content,
                    'user_id': message.user_id,
                    'username': message.user.username,
                    'is_admin': message.user.is_admin,
                    'is_admin_message': message.is_admin_message,
                    'created_at': message.created_at.isoformat(),
                    'room': room,
                    'is_read': message.id in read_message_ids,
                    'parent_id': message.parent_id
                }
                
                if message.parent_id:
                    parent_message = Message.query.get(message.parent_id)
                    if parent_message and not parent_message.is_deleted:
                        message_data['parent'] = {
                            'id': parent_message.id,
                            'content': parent_message.content,
                            'username': parent_message.user.username
                        }
                
                messages_data.append(message_data)
            
            emit('messages_batch', {
                'room': room,
                'messages': messages_data,
                'since_id': since_id,
                'total': len(messages_data)
            })
            
        except Exception as e:
            emit('messages_error', {
                'error': str(e),
                'room': room
            })

@socketio.on('mark_read')
def handle_mark_read(data):
    """Handle marking messages as read via WebSocket"""
    if not current_user.is_authenticated:
        return
    
    message_ids = data.get('message_ids', [])
    
    if not message_ids:
        return
    
    try:
        for message_id in message_ids:
            existing_read = MessageRead.query.filter_by(
                message_id=message_id, 
                user_id=current_user.id
            ).first()
            
            if not existing_read:
                message_read = MessageRead(
                    message_id=message_id,
                    user_id=current_user.id
                )
                db.session.add(message_read)
        
        db.session.commit()
        
        # Emit read receipt
        emit('messages_read', {
            'message_ids': message_ids,
            'user_id': current_user.id,
            'username': current_user.username
        }, broadcast=True)
        
    except Exception as e:
        db.session.rollback()
        print(f"Error marking messages as read: {e}")

# =========================================
# PERIODIC TASKS
# =========================================

from apscheduler.schedulers.background import BackgroundScheduler

def periodic_cleanup():
    """Periodically clean up disconnected users"""
    with app.app_context():
        cleanup_disconnected_users()

# Schedule periodic cleanup (run every minute)
scheduler = BackgroundScheduler()
scheduler.add_job(func=periodic_cleanup, trigger="interval", seconds=60)
scheduler.start()
# https://lyxspace.onrender.com/files
import atexit
import requests

TARGET_URLS = [
    "https://lyxspace.onrender.com/files",
    "https://lyxnexus.onrender.com/"
]

def ping_urls():
    for url in TARGET_URLS:
        try:
            response = requests.get(url, timeout=5)
            print(f"Pinged {url} | Status: {response.status_code}")
        except requests.RequestException as e:
            print(f"Failed to ping {url}: {e}")

# Setup scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=ping_urls, trigger="interval", minutes=3)
scheduler.start()

# Ensure scheduler shuts down cleanly
atexit.register(lambda: scheduler.shutdown())

TARGET_URL = 'https://lyxspace.onrender.com/files'
# manual ping route
@app.route("/ping-lyx")
def manual_ping():
    try:
        response = requests.get(TARGET_URL, timeout=5)
        return {
            "url": TARGET_URL,
            "status_code": response.status_code,
            "success": response.ok
        }
    except requests.RequestException as e:
        return {
            "url": TARGET_URL,
            "error": str(e),
            "success": False
        }

#===========================================
@app.route('/api/users')
@login_required
@admin_required
def get_users():
    
    users = User.query.all()
    users_data = []
    
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'mobile': user.mobile,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'is_admin': user.is_admin,
            'announcements_count': len(user.announcements),
            'assignments_count': len(user.assignments)
        })
    
    return jsonify(users_data)

# API endpoint to delete user
@app.route('/api/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    try:
        # Delete dependent records in correct order
        message_ids = [m.id for m in Message.query.filter_by(user_id=user.id).all()]
        if message_ids:
            db.session.query(MessageRead).filter(MessageRead.message_id.in_(message_ids)).delete(synchronize_session=False)

        db.session.query(Message).filter_by(user_id=user.id).delete(synchronize_session=False)
        db.session.query(MessageRead).filter_by(user_id=user.id).delete(synchronize_session=False)
        db.session.query(Announcement).filter_by(user_id=user.id).delete(synchronize_session=False)
        db.session.query(Assignment).filter_by(user_id=user.id).delete(synchronize_session=False)

        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API endpoint to toggle admin status
@app.route('/api/users/<int:user_id>/toggle-admin', methods=['PUT'])
@login_required
@admin_required
def toggle_admin(user_id):
    
    user = User.query.get_or_404(user_id)
    
    # Prevent modifying your own admin status
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot modify your own admin status'}), 400
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    return jsonify({
        'message': 'Admin status updated successfully',
        'is_admin': user.is_admin
    })

# =========================================
# ANNOUNCEMENT API ROUTES
# =========================================

@app.route('/api/announcements')
def get_announcements():
    """Get all announcements"""
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    result = []
    for announcement in announcements:
        result.append({
            'id': announcement.id,
            'title': announcement.title,
            'content': announcement.content,
            'created_at': announcement.created_at.isoformat(),
            'author': {
                'id': announcement.author.id,
                'username': announcement.author.username
            } if announcement.author else None
        })
    return jsonify(result)

@app.route('/api/announcements', methods=['POST'])
@login_required
@admin_required
def create_announcement():
    """Create a new announcement (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    announcement = Announcement(
        title=data.get('title'),
        content=data.get('content'),
        user_id=current_user.id
    )
    db.session.add(announcement)
    db.session.commit()
    
    return jsonify({'message': 'Announcement created successfully', 'id': announcement.id}), 201

@app.route('/api/announcements/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_announcement(id):
    """Update an announcement (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    announcement = Announcement.query.get_or_404(id)
    data = request.get_json()
    
    announcement.title = data.get('title', announcement.title)
    announcement.content = data.get('content', announcement.content)
    db.session.commit()
    
    return jsonify({'message': 'Announcement updated successfully'})

@app.route('/api/announcements/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_announcement(id):
    """Delete an announcement (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    
    return jsonify({'message': 'Announcement deleted successfully'})

# =========================================
# ASSIGNMENT API ROUTES
# =========================================

@app.route('/api/assignments')
def get_assignments():
    """Get all assignments"""
    assignments = Assignment.query.order_by(Assignment.due_date.asc()).all()
    result = []
    for assignment in assignments:
        result.append({
            'id': assignment.id,
            'title': assignment.title,
            'description': assignment.description,
            'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
            'created_at': assignment.created_at.isoformat(),
            'file_name': assignment.file_name,
            'file_type': assignment.file_type,
            'topic': {
                'id': assignment.topic.id,
                'name': assignment.topic.name
            } if assignment.topic else None,
            'creator': {
                'id': assignment.creator.id,
                'username': assignment.creator.username
            } if assignment.creator else None
        })
    return jsonify(result)

@app.route('/api/assignments', methods=['POST'])
@login_required
@admin_required
def create_assignment():
    """Create a new assignment (Admin/Teacher only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    assignment = Assignment(
        title=data.get('title'),
        description=data.get('description'),
        due_date=datetime.fromisoformat(data.get('due_date')) if data.get('due_date') else None,
        topic_id=data.get('topic_id'),
        user_id=current_user.id
    )
    db.session.add(assignment)
    db.session.commit()
    
    return jsonify({'message': 'Assignment created successfully', 'id': assignment.id}), 201

@app.route('/api/assignments/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_assignment(id):
    """Update an assignment (Admin/Teacher only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    assignment = Assignment.query.get_or_404(id)
    data = request.get_json()
    
    assignment.title = data.get('title', assignment.title)
    assignment.description = data.get('description', assignment.description)
    if data.get('due_date'):
        assignment.due_date = datetime.fromisoformat(data.get('due_date'))
    assignment.topic_id = data.get('topic_id', assignment.topic_id)
    
    db.session.commit()
    
    return jsonify({'message': 'Assignment updated successfully'})

@app.route('/api/assignments/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_assignment(id):
    """Delete an assignment (Admin/Teacher only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    assignment = Assignment.query.get_or_404(id)
    db.session.delete(assignment)
    db.session.commit()
    
    return jsonify({'message': 'Assignment deleted successfully'})

@app.route('/api/assignments/<int:id>/upload', methods=['POST'])
@login_required
@admin_required
def upload_assignment_file(id):
    """Upload file for assignment (Admin/Teacher only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    assignment = Assignment.query.get_or_404(id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    assignment.file_data = file.read()
    assignment.file_name = file.filename
    assignment.file_type = file.content_type
    
    db.session.commit()
    
    return jsonify({'message': 'File uploaded successfully'})

@app.route('/api/assignments/<int:id>/download')
def download_assignment_file(id):
    """Download assignment file"""
    assignment = Assignment.query.get_or_404(id)
    
    if not assignment.file_data:
        return jsonify({'error': 'No file available'}), 404
    
    return send_file(
        BytesIO(assignment.file_data),
        download_name=assignment.file_name,
        as_attachment=True,
        mimetype=assignment.file_type
    )
@app.route('/assignment/<int:id>')
@login_required
def assignment_page(id):
    """Serve the assignment file view and download page"""
    assignment = Assignment.query.get_or_404(id)
    return render_template('assignment.html', assignment=assignment)
# =========================================
# TOPIC API ROUTES
# =========================================

@app.route('/api/topics')
def get_topics():
    """Get all topics"""
    topics = Topic.query.all()
    result = []
    for topic in topics:
        result.append({
            'id': topic.id,
            'name': topic.name,
            'description': topic.description,
            'created_at': topic.created_at.isoformat()
        })
    return jsonify(result)

@app.route('/api/topics', methods=['POST'])
@login_required
@admin_required
def create_topic():
    """Create a new topic (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    topic = Topic(
        name=data.get('name'),
        description=data.get('description')
    )
    db.session.add(topic)
    db.session.commit()
    
    return jsonify({'message': 'Topic created successfully', 'id': topic.id}), 201

@app.route('/api/topics/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_topic(id):
    """Update a topic (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    topic = Topic.query.get_or_404(id)
    data = request.get_json()
    
    topic.name = data.get('name', topic.name)
    topic.description = data.get('description', topic.description)
    db.session.commit()
    
    return jsonify({'message': 'Topic updated successfully'})

@app.route('/api/topics/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_topic(id):
    """Delete a topic (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    topic = Topic.query.get_or_404(id)
    db.session.delete(topic)
    db.session.commit()
    
    return jsonify({'message': 'Topic deleted successfully'})

#==========================================
#  TIMETABLE API ROUTES
#==========================================
@app.route('/api/timetable/grouped', methods=['GET'])
def get_timetable():
    """Get timetable grouped by day"""
    print("\n[DEBUG] Fetching grouped timetable...")

    try:
        # Fetch and order slots
        timetable_slots = Timetable.query.order_by(
            Timetable.day_of_week, 
            Timetable.start_time
        ).all()

        print(f"[DEBUG] Retrieved {len(timetable_slots)} timetable slots from DB")

        # Define day order
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        timetable_by_day = {day: [] for day in days_order}

        # Group by day
        for slot in timetable_slots:
            print(f"[DEBUG] Processing slot ID {slot.id} ({slot.subject}) on {slot.day_of_week}")
            timetable_by_day[slot.day_of_week].append({
                'id': slot.id,
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'time': f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}",
                'subject': slot.subject,
                'room': slot.room,
                'teacher': slot.teacher,
                'topic': {
                    'id': slot.topic.id,
                    'name': slot.topic.name
                } if slot.topic else None
            })

        # Convert to list format (only include days that have slots)
        result = [
            {'day': day, 'slots': timetable_by_day[day]}
            for day in days_order if timetable_by_day[day]
        ]

        print(f"[DEBUG] Sending grouped timetable response with {len(result)} days")
        return jsonify(result), 200

    except Exception as e:
        print("[ERROR] Failed to get timetable:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/timetable', methods=['GET', 'POST'])
def handle_timetable():
    # ================================
    # GET — Fetch all timetable slots
    # ================================
    if request.method == 'GET':
        timetable_slots = Timetable.query.order_by(
            Timetable.day_of_week,
            Timetable.start_time
        ).all()
        
        result = []
        for slot in timetable_slots:
            result.append({
                'id': slot.id,
                'day_of_week': slot.day_of_week,
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'subject': slot.subject,
                'room': slot.room,
                'teacher': slot.teacher,
                'topic': {
                    'id': slot.topic.id,
                    'name': slot.topic.name
                } if slot.topic else None
            })
        return jsonify(result)

    # ================================
    # POST — Create new timetable slot
    # ================================
    if request.method == 'POST':
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        try:
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')

            # Parse times
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()

            # Validate time order
            if start_time >= end_time:
                return jsonify({'error': 'End time must be after start time'}), 400

        except ValueError:
            return jsonify({'error': 'Invalid time format. Use HH:MM format'}), 400
        except Exception as e:
            return jsonify({'error': f'Time parsing error: {str(e)}'}), 400

        # Create new timetable slot
        timetable_slot = Timetable(
            day_of_week=data.get('day_of_week'),
            start_time=start_time,
            end_time=end_time,
            subject=data.get('subject'),
            room=data.get('room'),
            teacher=data.get('teacher'),
            topic_id=data.get('topic_id')
        )

        db.session.add(timetable_slot)
        db.session.commit()

        return jsonify({
            'message': 'Timetable slot created successfully',
            'id': timetable_slot.id
        }), 201

@app.route('/api/timetable/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_timetable_slot(id):
    """Update a timetable slot (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    timetable_slot = Timetable.query.get_or_404(id)
    data = request.get_json()
    
    timetable_slot.day_of_week = data.get('day_of_week', timetable_slot.day_of_week)
    
    if data.get('start_time'):
        timetable_slot.start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
    if data.get('end_time'):
        timetable_slot.end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
    
    timetable_slot.subject = data.get('subject', timetable_slot.subject)
    timetable_slot.room = data.get('room', timetable_slot.room)
    timetable_slot.teacher = data.get('teacher', timetable_slot.teacher)
    timetable_slot.topic_id = data.get('topic_id', timetable_slot.topic_id)
    
    db.session.commit()
    
    return jsonify({'message': 'Timetable slot updated successfully'})

@app.route('/api/timetable/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_timetable_slot(id):
    """Delete a timetable slot (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    timetable_slot = Timetable.query.get_or_404(id)
    db.session.delete(timetable_slot)
    db.session.commit()
    
    return jsonify({'message': 'Timetable slot deleted successfully'})

@app.route('/api/timetable/day/<day>')
def get_timetable_by_day(day):
    """Get timetable for a specific day"""
    timetable_slots = Timetable.query.filter_by(day_of_week=day)\
        .order_by(Timetable.start_time).all()
    
    result = []
    for slot in timetable_slots:
        result.append({
            'id': slot.id,
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M'),
            'time': f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}",
            'subject': slot.subject,
            'room': slot.room,
            'teacher': slot.teacher,
            'topic': {
                'id': slot.topic.id,
                'name': slot.topic.name
            } if slot.topic else None
        })
    
    return jsonify(result)
#==========================================
#           REGISTERING ADMIN API
#==========================================
MASTER_ADMIN_KEY = "lyxnexus_2025"

@app.route('/api/register-admin', methods=['POST'])
def register_admin():
    """Register a new admin user via API"""
    data = request.get_json()
    
    mobile = data.get('mobile')
    username = data.get('username')
    master_key = data.get('master_key')
    
    # Validate master key
    if master_key != MASTER_ADMIN_KEY:
        return jsonify({'error': 'Invalid master authorization key'}), 403
    
    # Validate mobile
    if not mobile or len(mobile) != 10:
        return jsonify({'error': 'Invalid mobile number'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(mobile=mobile).first()
    if existing_user:
        return jsonify({'error': 'User exists'}), 409
    
    # Create new admin user
    new_admin = User(
        username=username,
        mobile=mobile,
        is_admin=True
    )
    
    db.session.add(new_admin)
    db.session.commit()
    
    return jsonify({
        'message': 'Admin user created successfully',
        'user_id': new_admin.id,
        'username': new_admin.username
    }), 201

@app.route('/api/promote-to-admin', methods=['POST'])
@login_required
@admin_required
def promote_to_admin():
    """Promote an existing user to admin via API"""
    data = request.get_json()
    
    mobile = data.get('mobile')
    master_key = data.get('master_key')
    
    # Validate master key
    if master_key != MASTER_ADMIN_KEY:
        return jsonify({'error': 'Invalid master authorization key'}), 403
    
    # Find user
    user = User.query.filter_by(mobile=mobile).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Promote to admin
    user.is_admin = True
    db.session.commit()
    
    return jsonify({
        'message': 'User promoted to admin successfully',
        'user_id': user.id,
        'username': user.username
    })

@app.route('/api/check-admin', methods=['POST'])
def check_admin():
    """Check if a user is admin via API"""
    data = request.get_json()
    mobile = data.get('mobile')
    
    user = User.query.filter_by(mobile=mobile).first()
    if not user:
        return jsonify({'is_admin': False}), 404
    
    return jsonify({
        'is_admin': user.is_admin,
        'username': user.username
    })

# =========================================
# USER API ROUTES (Basic)
# =========================================

@app.route('/api/users/me')
@login_required
def get_current_user():
    """Get current user info"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'mobile': current_user.mobile,
        'is_admin': current_user.is_admin,
        'created_at': current_user.created_at.isoformat()
    })

@app.route('/api/users/<int:id>')
@login_required
def get_user(id):
    """Get user by ID (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get_or_404(id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'mobile': user.mobile,
        'is_admin': user.is_admin,
        'created_at': user.created_at.isoformat()
    })

@app.route('/api/user')
@login_required
def current_user_info():
    """Get current user information"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'mobile': current_user.mobile,
        'is_admin': current_user.is_admin,
        'created_at': current_user.created_at.isoformat()
    })
#==========================================
# Error Handlers
#==========================================

@app.errorhandler(404)

def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(403)

def forbidden_error(error):
    return render_template('403.html'), 403

@app.errorhandler(500)

def internal_error(error):
    app.logger.error(f'Internal Server Error: {error}', exc_info=True)
    flash('Oops! Something went wrong. Try again.', 'error')

    # Fallback to home if referrer is not available
    referrer = request.referrer
    if referrer:
        return redirect(referrer), 302
    else:
        return redirect(url_for('home')), 302

# ==========================================
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=47947, debug=True)
