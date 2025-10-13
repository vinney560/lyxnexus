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
                with engine.connect() as conn:
                    conn.execute("SELECT 1;")
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
#==========================================
# User Loader Helper
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        print('Connection Lost on User Load')
        return None

def _year():
    """Return the current year in Nairobi time (UTC+3)."""
    return (datetime.utcnow() + timedelta(hours=3)).year

def admin_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if not current_user.is_authenticated:
            # If AJAX/API request, return JSON error
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Login first', 'error')
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
    if current_user.is_authenticated:
        return redirect(url_for('admin_page') if current_user.is_admin else url_for('main_page'))
    if request.method == 'POST':
        username = request.form.get('username', '')[:50]
        mobile = request.form.get('mobile')
        admin_secret = request.form.get('admin_secret')  # For admin login

        # Validate mobile
        if not mobile or len(mobile) != 10:
            flash('Invalid mobile number')
            return render_template('login.html', username=username, mobile=mobile, year=_year)
        
        user = User.query.filter_by(mobile=mobile).first()
        
        # Admin login attempt
        if admin_secret:
            if not user or not user.is_admin:
                flash('Invalid admin credentials')
                return render_template('login.html', username=username, mobile=mobile, year=_year)
            # For now, we're not checking the secret in this example
            # In production, you'd verify against a stored hash
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
            return redirect(url_for('admin_page'))
        else:
            return redirect(url_for('main_page'))
    
    return render_template('login.html', year=datetime.utcnow().year)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout Successfully!', 'sucess')
    return redirect(url_for('home'))

#===================================================
@app.route('/')
def home():
    return render_template('index.html', year=_year)

@app.route('/main-page')
@login_required
def main_page():
    return render_template('main_page.html', year=_year)

@app.route('/admin')
@admin_required
def admin_page():
    return render_template('admin.html', year=_year)

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
def delete_assignment(id):
    """Delete an assignment (Admin/Teacher only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    assignment = Assignment.query.get_or_404(id)
    db.session.delete(assignment)
    db.session.commit()
    
    return jsonify({'message': 'Assignment deleted successfully'})

@app.route('/api/assignments/<int:id>/upload', methods=['POST'])
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
def delete_topic(id):
    """Delete a topic (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    topic = Topic.query.get_or_404(id)
    db.session.delete(topic)
    db.session.commit()
    
    return jsonify({'message': 'Topic deleted successfully'})

# =========================================
# TIMETABLE API ROUTES
# =========================================

@app.route('/api/timetable')
def get_timetable():
    """Get timetable grouped by day"""
    timetable_slots = Timetable.query.order_by(
        Timetable.day_of_week, 
        Timetable.start_time
    ).all()
    
    # Group by day
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    timetable_by_day = {day: [] for day in days_order}
    
    for slot in timetable_slots:
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
    
    # Convert to list format expected by frontend
    result = []
    for day in days_order:
        if timetable_by_day[day]:  # Only include days with slots
            result.append({
                'day': day,
                'slots': timetable_by_day[day]
            })
    
    return jsonify(result)

@app.route('/api/timetable', methods=['POST'])
def create_timetable_slot():
    """Create a new timetable slot (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Convert time strings to time objects
    start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
    end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
    
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
    
    return jsonify({'message': 'Timetable slot created successfully', 'id': timetable_slot.id}), 201

@app.route('/api/timetable/<int:id>', methods=['PUT'])
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
#           Registering admins

# Master key for admin registration (store this securely in environment variables in production)
MASTER_ADMIN_KEY = "lyxspace_2025"

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
        return jsonify({'error': 'User with this mobile already exists'}), 409
    
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
# date_str = request.form.get("date_of_birth")  # e.g., "1990-05-12"
# 
# if date_str:
#     dob = datetime.strptime(date_str, "%Y-%m-%d").date()  # convert string to datetime.date
# else:
#     dob = None  # leave as NULL if no input
# 
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

#==========================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        admin = User.query.get(1)
        if not admin:
            admin = User(id=1, mobile="0740694312", username="Administrator", is_admin=True)
            db.session.add(admin)
            db.session.commit()    
    socketio.run(app, host='0.0.0.0', port=47947, debug=True)