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
from bs4 import BeautifulSoup

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

    for name, db_url in [("Aiven DB", db_1), ("Render DB", db_2)]:
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

    # Fallback to SQLite to prevent Runtime errors
    if db_3:
        if db_3.startswith("sqlite:///"):
            print("=" * 70)
            print("✅ Using local SQLite fallback database.")
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
    
    #Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    file_name = db.Column(db.String(255), nullable=True)       # Original filename
    file_type = db.Column(db.String(100), nullable=True)       # MIME type
    file_data = db.Column(db.LargeBinary, nullable=True)       # Actual file content (bytes)

    def has_file(self):
        """Check if announcement has an attached file"""
        return bool(self.file_data and self.file_name)

    def get_file_url(self):
        if not self.has_file():
            return None
        return f"/announcement-file/{self.id}/{self.file_name}"

# =========================================
# TOPIC / THEME MODEL
# =========================================
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)

    # Relationship
    assignments = db.relationship('Assignment', backref='topic', lazy=True)

# =========================================
# ASSIGNMENT MODEL
# =========================================
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)

    # Store the actual uploaded file
    file_data = db.Column(db.LargeBinary, nullable=True)   # actual file content (bytes)
    file_name = db.Column(db.String(1255), nullable=True)   # original filename
    file_type = db.Column(db.String(100), nullable=True)   # MIME type

    # Foreign keys
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
# =========================================
# TIMETABLE MODEL
# =========================================
class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    room = db.Column(db.String(100), nullable=True)
    teacher = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)
    updated_at = db.Column(db.DateTime, default=nairobi_time, onupdate=nairobi_time)

    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=True)
    
    # Relationship
    topic = db.relationship('Topic', backref='timetable_slots', lazy=True)

# =========================================
# MESSAGE MODELS
# ========================================
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    room = db.Column(db.String(100), default='general')
    is_admin_message = db.Column(db.Boolean, default=False)
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('message.id', ondelete='CASCADE'),
        nullable=True
    )
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=nairobi_time)

    # Relationships
    user = db.relationship(
        'User',
        backref=db.backref('messages', lazy=True, cascade='all, delete-orphan')
    )

    parent = db.relationship(
        'Message',
        remote_side=[id],
        backref=db.backref('replies', lazy=True, cascade='all, delete-orphan')
    )

class MessageRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(
        db.Integer,
        db.ForeignKey('message.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    read_at = db.Column(db.DateTime, default=nairobi_time)

    # Relationships
    message = db.relationship(
        'Message',
        backref=db.backref('read_records', lazy=True, cascade='all, delete-orphan')
    )
    user = db.relationship(
        'User',
        backref=db.backref('read_messages', lazy=True, cascade='all, delete-orphan')
    )    

#==========================================
# FILES MODEL
#==========================================
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
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

class TopicMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    display_name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=nairobi_time)
    
    # Relationships
    topic = db.relationship('Topic', backref=db.backref('topic_materials', lazy=True))
    file = db.relationship('File', backref=db.backref('material_references', lazy=True))
    
    def __repr__(self):
        return f'<TopicMaterial {self.display_name or self.file.name}>'
#==========================================    
with app.app_context():
    try:
        db.create_all()

        # Create admin user if not exists (For easy access and testing)
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
#========================================
#          HELPERS && BACKGROUND WORKERS
#==========================================
# User Loader Helper
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        print(f'⚠️ Error loading user {user_id}: {e}')
        db.session.rollback()
        return None

@app.teardown_request
def teardown_request(exception):
    if exception:
        db.session.rollback()
    db.session.remove()

def _year():
    return datetime.now().strftime('%Y')

def send_notification(user_id, title, message):
    notification_data = {
        'title': title,
        'message': message,
        'type': 'info',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Send to specific user

    socketio.emit('push_notification', notification_data, room=f'user_{user_id}')

def admin_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if not current_user.is_authenticated:
            # for AJAX/API
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
#------------------------------------------------------------------------------
                                 # BACKGROUND WORKERS

from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy_utils import database_exists, create_database, drop_database
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

BATCH_SIZE = 500
LOG_EVERY_BATCH = True

def clone_database_robust():
    src_url = os.getenv("DATABASE_URL")
    tgt_url = os.getenv("DATABASE_URL_2")

    src_engine = create_engine(src_url)
    tgt_engine = create_engine(tgt_url)

    # Drop target tables before clone
    tgt_meta = MetaData()
    tgt_meta.reflect(bind=tgt_engine)
    tgt_meta.drop_all(bind=tgt_engine)

    # Recreate schema
    src_meta = MetaData()
    src_meta.reflect(bind=src_engine)
    src_meta.create_all(bind=tgt_engine)

    with src_engine.connect() as src_conn, tgt_engine.begin() as tgt_conn:
        for table in src_meta.sorted_tables:
            print(f"🔹 Cloning table: {table.name}")
            offset = 0
            while True:
                rows = src_conn.execute(
                    select(table).offset(offset).limit(BATCH_SIZE)
                ).mappings().all()
                if not rows:
                    break
                tgt_conn.execute(table.insert(), rows)
                offset += BATCH_SIZE
            print(f"✅ Done: {table.name}")

@app.route("/admin/clone-db")
@admin_required
def clone_db_page():
    """Render the database cloning page"""
    return render_template("clone-db.html", year=_year())

@app.route("/api/admin/clone-db", methods=["POST"])
@admin_required
def clone_db_route():
    try:
        clone_database_robust()
        return jsonify({"message": "✅ Database cloned successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# ============================================================
#  Database Keep-Alive 'n Status Logging
# ============================================================

SRC_DB_URL = os.getenv("DATABASE_URL")
TGT_DB_URL = os.getenv("DATABASE_URL_2")

src_engine = create_engine(
    SRC_DB_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5}
)
tgt_engine = create_engine(
    TGT_DB_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5}
)

LOG_FILE = "logs/db_health.log"
os.makedirs("logs", exist_ok=True)

def log_status(message: str):
    """Append timestamped messages to a local log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    print(line.strip()) 
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)

def keep_databases_alive():
    for name, engine in [("Source", src_engine), ("Target", tgt_engine)]:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log_status(f"🟢 {name} DB keep-alive OK")
        except OperationalError as e:
            log_status(f"⚠️ {name} DB unreachable: {e}")
        except Exception as e:
            log_status(f"❌ Unexpected error pinging {name} DB: {e}")

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=keep_databases_alive,
    trigger=IntervalTrigger(minutes=3),
    id="db_keep_alive_both",
    replace_existing=True
)
scheduler.start()

log_status("🕒 Keep-alive scheduler started — pinging both DBs every 3 minutes")

atexit.register(lambda: scheduler.shutdown(wait=False))
#=============================================================================

#      ANNOUNCEMENT CLEANER
def delete_old_announcements():
    """Delete announcements older than 5 days to save storage"""
    cutoff = datetime.utcnow() - timedelta(days=5)
    old_announcements = Announcement.query.filter(Announcement.created_at < cutoff).all()
    
    if not old_announcements:
        print("🗑️ No old announcements to delete.")
        return
    
    for ann in old_announcements:
        print(f"🗑️ Deleting announcement ID {ann.id} ({ann.title}) created on {ann.created_at}")
        db.session.delete(ann)
    
    db.session.commit()
    print(f"✅ Deleted {len(old_announcements)} old announcements.")

scheduler = BackgroundScheduler()

# Run the job every day
scheduler.add_job(
    func=delete_old_announcements,
    trigger=IntervalTrigger(days=1),
    id="delete_old_announcements_task",
    replace_existing=True,
)

scheduler.start()
print("🕒 APScheduler started: deleting announcements older than 5 days daily")
atexit.register(lambda: scheduler.shutdown(wait=False))

#==========================================
#                  Normal Routes
#==========================================
MASTER_ADMIN_KEY = "lyxnexus_2025"

@app.route('/login', methods=['POST', 'GET'])
def login():
    next_page = request.args.get("next") or request.form.get("next")
    login_type = request.form.get('login_type', 'student')  # 'student' or 'admin' - prevent login conflict

    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(next_page or url_for('admin_page'))
        else:
            return redirect(next_page or url_for('main_page'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()[:50]
        mobile = request.form.get('mobile')
        master_key = request.form.get('master_key')

        if (
            not mobile
            or len(mobile) != 10
            or not (mobile.startswith('07') or mobile.startswith('01'))
        ):
            flash('Invalid mobile number', 'error')
            return render_template('login.html', username=username, mobile=mobile,
                                   login_type=login_type, year=_year())

        # Admin access using master key
        if master_key:
            if master_key == MASTER_ADMIN_KEY:
                user = User.query.filter_by(mobile=mobile).first()
                if user:
                    user.is_admin = True
                    if username and user.username.lower() != username.lower():
                        user.username = username
                    db.session.commit()
                    login_user(user)
                    flash('User promoted to administrator successfully!', 'success')
                    return redirect(next_page or url_for('admin_page'))
                else:
                    new_admin = User(
                        username=username,
                        mobile=mobile,
                        is_admin=True
                    )
                    db.session.add(new_admin)
                    db.session.commit()
                    login_user(new_admin)
                    flash('Admin account created successfully!', 'success')
                    return redirect(next_page or url_for('admin_page'))
            else:
                flash('Invalid master authorization key', 'error')
                return render_template('login.html', username=username, mobile=mobile,
                                       login_type=login_type, year=_year())

        user = User.query.filter_by(mobile=mobile).first()

        # ========================
        #   ADMIN LOGIN SECTION
        # ========================
        if login_type == 'admin':
            if not user or not user.is_admin:
                flash('Invalid admin credentials', 'error')
                return render_template('login.html', username=username, mobile=mobile,
                                       login_type=login_type, year=_year())

            if user.username.lower() != username.lower():
                flash('Username does not match admin account', 'error')
                return render_template('login.html', username=username, mobile=mobile,
                                       login_type=login_type, year=_year())

            login_user(user)
            flash('Admin login successful!', 'success')
            return redirect(next_page or url_for('admin_page'))

        # ========================
        #   STUDENT LOGIN SECTION
        # ========================
        if login_type == 'student':
            if not user:
                # New student -> Create account and send to navigation guide
                new_user = User(
                    username=username,
                    mobile=mobile,
                    is_admin=False
                )
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                flash('Welcome to LyxNexus! Let’s get you started.', 'success')
                return redirect(url_for('nav_guide'))

            else:
                # Returning student
                if user.username.lower() != username.lower():
                    flash('Username does not match existing account', 'error')
                    return render_template('login.html', username=username, mobile=mobile,
                                           login_type=login_type, year=_year())

                login_user(user)
                return redirect(next_page or url_for('main_page', message='Login successfully!', message_type='success'))

    login_type = request.args.get('type', 'student')
    return render_template('login.html', login_type=login_type, year=_year())

#===================================================================
@app.route('/')
def home():
    return render_template('index.html', year=_year())
#--------------------------------------------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout Successfully!', 'sucess')
    return redirect(url_for('home'))
#--------------------------------------------------------------------
@app.route('/main-page')
@login_required
def main_page():
    return render_template('main_page.html', year=_year())
#-----------------------------------------------------------------
@app.route('/navigation-guide')
def nav_guide():
    return render_template('navigation.html')
#--------------------------------------------------------------------
@app.route('/admin')
@login_required
@admin_required
def admin_page():
    return render_template('admin.html', year=_year())
#--------------------------------------------------------------------
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    return render_template('admin_users.html')
#-----------------------------------------------------------------
@app.route('/profile')
@login_required
def profile():
    """Render the profile edit page"""
    return render_template('edit_profile.html')
#--------------------------------------------------------------------
@app.route('/files')
@login_required
def files():
    """Render the file management page"""
    return render_template('files.html')
#--------------------------------------------------------------------
@app.route('/material/<int:topic_id>')
@login_required
def topic_materials(topic_id):
    """Render the topic materials page"""
    topic = Topic.query.get_or_404(topic_id)
    return render_template('material.html', topic_id=topic_id)
#--------------------------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.config['UPLOAD_FOLDER'], 'favicon.ico')
#--------------------------------------------------------------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if '..' in filename or filename.startswith('/'):
        abort(400, "Invalid filename")
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        abort(404, "File not found")
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

#              SPECIFIED ROUTES

# =========================================
#              MESSAGES ROUTES
# =========================================

@app.route('/messages')
@login_required
def messages():
    """Render the messages page with initial data"""
    try:
        room = request.args.get('room', 'general')
        
        # (last 50 messages)
        messages = Message.query.filter_by(
            room=room, 
            is_deleted=False
        ).order_by(Message.created_at.desc()).limit(50).all()
        
        messages.reverse()
        
        unread_count = get_unread_count(current_user.id)
        
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
        # Fallback: returns page without messages
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
        valid_rooms = ['general', 'help', 'announcements']
        if room_name not in valid_rooms:
            room_name = 'general'
        
        messages = Message.query.filter_by(
            room=room_name, 
            is_deleted=False
        ).order_by(Message.created_at.desc()).limit(50).all()
        
        messages.reverse()
        
        # Get unread count - Still fixing
        unread_count = get_unread_count(current_user.id)
        
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
        read_message_ids = db.session.query(MessageRead.message_id).filter_by(
            user_id=user_id
        ).subquery()
        
        # Count messages that are not in the read list and not deleted
        unread_count = Message.query.filter(
            Message.id.notin_(read_message_ids),
            Message.is_deleted == False,
            Message.user_id != user_id
        ).count()
        
        return unread_count
        
    except Exception as e:
        print(f"Error getting unread count: {e}")
        return 0

#=================================================
#                  FILE API
#==========================================
@app.route('/api/files')
@login_required
def get_files():
    """Get all files with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
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
    
    # pagination
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

def shorten_filename(filename, length=30):
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
    
    name = request.form.get('name', file.filename)[:100]
    filename = shorten_filename(file.filename)
    description = request.form.get('description', '')[:12000]
    category = request.form.get('category', 'general')
    
    # Validate file size (10MB limit) - Memory 1GB only
    file_data = file.read()
    if len(file_data) > 10 * 1024 * 1024:
        return jsonify({'error': 'File size exceeds 10MB limit'}), 400
    
    # Check if filename already exists - No duplicates Unique Key Constrains
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

#================================================
#            UPDATE USER API ROUTES
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
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    mobile = data.get('mobile', '').strip()
    
    if not username or len(username) > 200:
        return jsonify({'error': 'Username must be between 1 and 200 characters'}), 400
    
    # Validate mobile format - For those enetering 08 ....
    mobile_regex = r'^(07|01)[0-9]{8}$'
    if not re.match(mobile_regex, mobile):
        return jsonify({'error': 'Mobile number must be 10 digits starting with 07 or 01'}), 400
    
    existing_user = User.query.filter(
        User.mobile == mobile, 
        User.id != current_user.id
    ).first()
    
    if existing_user:
        return jsonify({'error': 'Mobile number is already registered'}), 400
    
    try:
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


# ===============================================================
#          MESSAGES API ROUTES & SOCKET HANDLERS
# ===========================================================

online_users = {}

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
        query = Message.query.filter_by(room=room, is_deleted=False)
        
        if since_id > 0:
            query = query.filter(Message.id > since_id)
        
        messages = query.order_by(Message.created_at.asc()).limit(limit).all()
        
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
        parent_id = data.get('parent_id')  # To track replies
        
        if not content:
            return jsonify({'success': False, 'error': 'Message content is required'}), 400
        
        if parent_id:
            parent_message = Message.query.get(parent_id)
            if not parent_message or parent_message.is_deleted:
                return jsonify({'success': False, 'error': 'Parent message not found'}), 404
        
        message = Message(
            content=content,
            user_id=current_user.id,
            room=room,
            is_admin_message=current_user.is_admin,
            parent_id=parent_id
        )
        
        db.session.add(message)
        db.session.commit()
        
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
        
        if parent_id:
            parent_message = Message.query.get(parent_id)
            if parent_message and not parent_message.is_deleted:
                message_data['parent'] = {
                    'id': parent_message.id,
                    'content': parent_message.content,
                    'username': parent_message.user.username
                }
        
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
        
        parent_message = Message.query.get(message_id)
        if not parent_message or parent_message.is_deleted:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        reply = Message(
            content=content,
            user_id=current_user.id,
            room=parent_message.room,
            is_admin_message=current_user.is_admin,
            parent_id=message_id
        )
        
        db.session.add(reply)
        db.session.commit()
        
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
        
        if message.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        # Soft delete
        message.is_deleted = True
        message.deleted_at = nairobi_time()
        message.content = "[This message was deleted]"
        
        db.session.commit()
        
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
        
        replies = Message.query.filter_by(
            parent_id=message_id, 
            is_deleted=False
        ).order_by(Message.created_at.asc()).all()
        
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
#          EXTRA FUNCTIONS CLEAN UP - MEMORY CONSTRAIN
# ===========================================================

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
    
    for room, users in room_users.items():
        emit('online_users_update', {'users': users}, room=room)

# =========================================
#             SOCKET.IO HANDLERS
# =========================================

@socketio.on('connect')
def handle_connect():
    """Handle user connection"""
    if current_user.is_authenticated:
        update_user_presence(
            user_id=current_user.id,
            username=current_user.username,
            is_admin=current_user.is_admin,
            room='general'
        )
        
        join_room('general')
        
        emit('user_joined', {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin,
            'message': f'{current_user.username} joined the chat'
        }, room='general', include_self=False)
        
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
            
            online_users.pop(current_user.id, None)
            
            emit('user_left', {
                'user_id': current_user.id,
                'username': current_user.username,
                'message': f'{current_user.username} left the chat'
            }, room=room, include_self=False)
            
            broadcast_online_users()
        
        print(f"User {current_user.username} disconnected. Online users: {len(online_users)}")

# I'm not that good at this part
@socketio.on('join_room')
def handle_join_room(data):
    """Handle joining a room"""
    if current_user.is_authenticated:
        room = data.get('room', 'general')
        previous_room = online_users.get(current_user.id, {}).get('current_room', 'general')
        
        if previous_room != room:
            leave_room(previous_room)
            emit('user_left', {
                'user_id': current_user.id,
                'username': current_user.username,
                'message': f'{current_user.username} left {previous_room}'
            }, room=previous_room, include_self=False)
        
        join_room(room)
        
        update_user_presence(
            user_id=current_user.id,
            username=current_user.username,
            is_admin=current_user.is_admin,
            room=room
        )
        
        emit('user_joined', {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin,
            'message': f'{current_user.username} joined {room}'
        }, room=room, include_self=False)
        
        messages = Message.query.filter_by(room=room, is_deleted=False).order_by(Message.created_at.asc()).limit(50).all()
        
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
    
        update_user_presence(
            user_id=current_user.id,
            username=current_user.username,
            is_admin=current_user.is_admin,
            room='general'
        )
        
        emit('user_left', {
            'user_id': current_user.id,
            'username': current_user.username,
            'message': f'{current_user.username} left {room}'
        }, room=room, include_self=False)
        
        join_room('general')
        
        emit('room_left', {
            'room': room,
            'user_id': current_user.id,
            'username': current_user.username
        })

@socketio.on('send_message')
def handle_send_message(data):
    if not current_user.is_authenticated:
        return {'success': False, 'error': 'Not authenticated'}
    
    content = data.get('content', '').strip()
    room = data.get('room', 'general')
    parent_id = data.get('parent_id')
    
    if not content:
        return {'success': False, 'error': 'Empty message'}
    
    if parent_id:
        parent_message = Message.query.get(parent_id)
        if not parent_message or parent_message.is_deleted:
            return {'success': False, 'error': 'Parent message not found'}
    
    update_user_presence(
        user_id=current_user.id,
        username=current_user.username,
        is_admin=current_user.is_admin,
        room=room
    )
    
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
        
        if parent_id:
            parent_message = Message.query.get(parent_id)
            if parent_message and not parent_message.is_deleted:
                message_data['parent'] = {
                    'id': parent_message.id,
                    'content': parent_message.content,
                    'username': parent_message.user.username
                }
        
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
        
        if message.user_id != current_user.id and not current_user.is_admin:
            return {'success': False, 'error': 'Permission denied'}
        
        # Soft delete message
        message.is_deleted = True
        message.deleted_at = nairobi_time()
        message.content = "[This message was deleted]"
        
        db.session.commit()
        
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
        user_room = online_users.get(current_user.id, {}).get('current_room', 'general')
        
        # Update user presence
        update_user_presence(
            user_id=current_user.id,
            username=current_user.username,
            is_admin=current_user.is_admin,
            room=user_room
        )
        
        emit('pong', {'timestamp': data.get('timestamp')})

@socketio.on('get_messages')
def handle_get_messages(data):
    if current_user.is_authenticated:
        room = data.get('room', 'general')
        since_id = data.get('since_id', 0)
        limit = data.get('limit', 100)
        
        try:
            query = Message.query.filter_by(room=room, is_deleted=False)
            if since_id > 0:
                query = query.filter(Message.id > since_id)
            
            messages = query.order_by(Message.created_at.asc()).limit(limit).all()
            
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
        
        emit('messages_read', {
            'message_ids': message_ids,
            'user_id': current_user.id,
            'username': current_user.username
        }, broadcast=True)
        
    except Exception as e:
        db.session.rollback()
        print(f"Error marking messages as read: {e}")

# ================================================
        # PERIODIC TASKS FOR KEEP ALIVE THE WEBS
# ==================================================
import requests

def periodic_cleanup():
    """Periodically clean up disconnected users"""
    with app.app_context():
        cleanup_disconnected_users()

# periodic cleanup (run every minute)
scheduler = BackgroundScheduler()
scheduler.add_job(func=periodic_cleanup, trigger="interval", seconds=60)
scheduler.start()

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

scheduler = BackgroundScheduler()
scheduler.add_job(func=ping_urls, trigger="interval", minutes=3)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

TARGET_URL = 'https://lyxspace.onrender.com/files'
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

@app.route('/api/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    try:
        # =====================================================
        # 1️. Delete MessageReads for messages SENT BY this user
        # =====================================================
        user_message_ids = [m.id for m in Message.query.filter_by(user_id=user.id).all()]
        if user_message_ids:
            db.session.query(MessageRead).filter(
                MessageRead.message_id.in_(user_message_ids)
            ).delete(synchronize_session=False)

        # =========================================================
        # 2️. Delete MessageReads BY this user
        # =========================================================
        db.session.query(MessageRead).filter_by(user_id=user.id).delete(synchronize_session=False)

        # ==========================================
        # 3️. Delete Replies to user's messages FIRST
        # ==========================================
        if user_message_ids:
            db.session.query(Message).filter(
                Message.parent_id.in_(user_message_ids)
            ).delete(synchronize_session=False)

        # ==================================
        # 4️. Delete messages CREATED BY user
        # ==================================
        db.session.query(Message).filter_by(user_id=user.id).delete(synchronize_session=False)

        # =====================================
        # 5️. Delete assignments & announcements
        # =====================================
        db.session.query(Announcement).filter_by(user_id=user.id).delete(synchronize_session=False)
        db.session.query(Assignment).filter_by(user_id=user.id).delete(synchronize_session=False)

        # ================================
        # 6️. Delete files uploaded by user
        # =================================
        user_file_ids = [f.id for f in File.query.filter_by(uploaded_by=user.id).all()]
        if user_file_ids:
            db.session.query(TopicMaterial).filter(
                TopicMaterial.file_id.in_(user_file_ids)
            ).delete(synchronize_session=False)
            db.session.query(File).filter(File.id.in_(user_file_ids)).delete(synchronize_session=False)

        # ==================================
        # 7️. Delete orphaned TopicMaterials
        # ==================================
        db.session.query(TopicMaterial).filter_by(file_id=None).delete(synchronize_session=False)

        # =============================
        # 8️. Finally delete the user 😤
        # =============================
        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': f'User {user.username or user.id} deleted successfully with all related data.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500

@app.route('/api/users/<int:user_id>/toggle-admin', methods=['PUT'])
@login_required
@admin_required
def toggle_admin(user_id):
    
    user = User.query.get_or_404(user_id)
    
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
import io

@app.route('/api/announcements')
def get_announcements():
    try:
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
        result = [{
            'id': a.id,
            'title': a.title,
            'content': a.content,
            'created_at': a.created_at.isoformat(),
            'author': {'id': a.author.id, 'username': a.author.username} if a.author else None,
            'has_file': a.has_file(),
            'file_name': a.file_name,
            'file_type': a.file_type,
            'file_url': a.get_file_url()
        } for a in announcements]
        return jsonify(result)
    except Exception as e:
        app.logger.exception("Failed to fetch announcements")
        return jsonify({'error': 'Failed to fetch announcements'}), 500

from werkzeug.utils import secure_filename

@app.route('/api/announcements/create', methods=['POST'])
@login_required
@admin_required
def create_announcement():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    title = request.form.get('title')
    content = request.form.get('content')

    file = request.files.get('file')
    file_name = secure_filename(file.filename) if file else None
    file_type = file.mimetype if file else None
    file_data = file.read() if file else None

    announcement = Announcement(
        title=title,
        content=content,
        user_id=current_user.id,
        file_name=file_name,
        file_type=file_type,
        file_data=file_data
    )
    db.session.add(announcement)
    db.session.commit()

    send_notification(
        current_user.id,
        'New Announcement Created',
        f'You created: {announcement.title}'
    )
    
    # Broadcast to all users
    socketio.emit('push_notification', {
        'title': 'New Announcement',
        'message': f'New announcement: {announcement.title}',
        'type': 'announcement',
        'announcement_id': announcement.id,
        'timestamp': datetime.utcnow().isoformat()
    })
    return jsonify({'message': 'Announcement created successfully', 'id': announcement.id}), 201

@app.route('/api/announcements/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_announcement(id):
    """Update an announcement with optional file"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    announcement = Announcement.query.get_or_404(id)
    title = request.form.get('title', announcement.title)
    content = request.form.get('content', announcement.content)
    file = request.files.get('file')

    announcement.title = title
    announcement.content = content

    if file:
        announcement.file_name = secure_filename(file.filename)
        announcement.file_type = file.mimetype
        announcement.file_data = file.read()

    db.session.commit()

    send_notification(
        current_user.id,
        'Editted Announcement Created',
        f'You created: {announcement.title}'
    )
    
    # Broadcast to all users
    socketio.emit('push_notification', {
        'title': 'Announcement Editted',
        'message': f'announcement eddited: {announcement.title}',
        'type': 'announcement',
        'announcement_id': announcement.id,
        'timestamp': datetime.utcnow().isoformat()
    })    
    return jsonify({'message': 'Announcement updated successfully'})


@app.route('/api/announcements/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_announcement(id):
    """Delete an announcement (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    announcement = Announcement.query.get_or_404(id)
    send_notification(
        current_user.id,
        'Deleted Announcement',
        f'You Deleted: {announcement.title}'
    )

    socketio.emit('push_notification', {
        'title': 'Announcement Deleted', 
        'message': f'Announcement was deleted by {current_user.username}',
        'type': 'announcement',
        'announcement_id': announcement.id,
        'timestamp': datetime.utcnow().isoformat()
    })    
    db.session.delete(announcement)
    db.session.commit()
    
    return jsonify({'message': 'Announcement deleted successfully'})

@app.route('/announcement-file/<int:id>/<filename>')
def serve_announcement_file(id, filename):
    announcement = Announcement.query.get_or_404(id)
    if not announcement.has_file() or announcement.file_name != filename:
        return jsonify({'error': 'File not found'}), 404

    return send_file(
        io.BytesIO(announcement.file_data),
        download_name=announcement.file_name,
        mimetype=announcement.file_type
    )
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
    send_notification(
        current_user.id,
        'Assignment Given',
        f'You Deleted: {assignment.title}'
    )

    socketio.emit('push_notification', {
        'title': 'Assignment handed out', 
        'message': f' Assignment on: {assignment.title}',
        'type': 'assignment',
        'assignment_id': assignment.id,
        'timestamp': datetime.utcnow().isoformat()
    })    
    
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
    send_notification(
        current_user.id,
        'Assignment Updated',
        f'You updated: {assignment.title}'
    )

    socketio.emit('push_notification', {
        'title': 'Assignment Updated', 
        'message': f' Assignment {assignment.title} updated',
        'type': 'assignment',
        'assignment_id': assignment.id,
        'timestamp': datetime.utcnow().isoformat()
    })    
    
    return jsonify({'message': 'Assignment updated successfully'})

@app.route('/api/assignments/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_assignment(id):
    """Delete an assignment (Admin/Teacher only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    assignment = Assignment.query.get_or_404(id)
    send_notification(
        current_user.id,
        'Assignment Deletd',
        f'You Deleted: {assignment.title}'
    )

    socketio.emit('push_notification', {
        'title': 'Assignment Deleted', 
        'message': f' Assignment {assignment.title} deleted',
        'type': 'assignment',
        'assignment_id': assignment.id,
        'timestamp': datetime.utcnow().isoformat()
    })        
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

@app.route("/api/preview")
def preview():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "Missing URL"}), 400

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=4)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        def meta(prop):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            return tag["content"].strip() if tag and tag.get("content") else None

        title = meta("og:title") or (soup.title.string.strip() if soup.title else None)
        description = meta("og:description") or meta("description")
        image = meta("og:image")

        return jsonify({
            "title": title or "",
            "description": description or "",
            "image": image or ""
        })

    except requests.exceptions.RequestException as e:
        print("OG fetch error:", e)
        return jsonify({"title": "", "description": "", "image": ""})

# =========================================
#              TOPIC API ROUTES
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
#            TIMETABLE API ROUTES
#==========================================
@app.route('/api/timetable/grouped', methods=['GET'])
def get_timetable():
    """Get timetable grouped by day"""
    print("\n[DEBUG] Fetching grouped timetable...")

    try:
        timetable_slots = Timetable.query.order_by(
            Timetable.day_of_week, 
            Timetable.start_time
        ).all()

        print(f"[DEBUG] Retrieved {len(timetable_slots)} timetable slots from DB")

        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        timetable_by_day = {day: [] for day in days_order}

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

    if request.method == 'POST':
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        try:
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')

            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()

            if start_time >= end_time:
                return jsonify({'error': 'End time must be after start time'}), 400

        except ValueError:
            return jsonify({'error': 'Invalid time format. Use HH:MM format'}), 400
        except Exception as e:
            return jsonify({'error': f'Time parsing error: {str(e)}'}), 400

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

@app.route('/api/register-admin', methods=['POST'])
def register_admin():
    """Register a new admin user via API"""
    data = request.get_json()
    
    mobile = data.get('mobile')
    username = data.get('username')
    master_key = data.get('master_key')
    
    if master_key != MASTER_ADMIN_KEY:
        return jsonify({'error': 'Invalid master authorization key'}), 403
    
    if not mobile or len(mobile) != 10:
        return jsonify({'error': 'Invalid mobile number'}), 400
    
    existing_user = User.query.filter_by(mobile=mobile).first()
    if existing_user:
        return jsonify({'error': 'User with this mobile already exists'}), 409
    
    new_admin = User(
        username=username.strip().lower(),
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
    username = data.get('username')
    master_key = data.get('master_key')
    
    if master_key != MASTER_ADMIN_KEY:
        return jsonify({'error': 'Invalid master authorization key'}), 403
    
    user = User.query.filter_by(mobile=mobile).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.username.lower() != username.strip().lower():
        return jsonify({'error': 'Username does not match existing account'}), 400
    
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
# USER API ROUTES FOR PROFILE & ADMIN MNGMT
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
#  TOPIC API ROUTES
# =========================================

@app.route('/api/topics/<int:topic_id>/materials')
def get_topic_materials(topic_id):
    """Get all materials for a specific topic"""
    try:
        topic = Topic.query.get_or_404(topic_id)
        materials = TopicMaterial.query.filter_by(topic_id=topic_id)\
            .order_by(TopicMaterial.order_index).all()
        
        materials_data = []
        for material in materials:
            materials_data.append({
                'id': material.id,
                'display_name': material.display_name or material.file.name,
                'description': material.description or material.file.description,
                'file_id': material.file_id,
                'filename': material.file.filename,
                'file_type': material.file.file_type,
                'file_size': material.file.file_size,
                'uploaded_at': material.file.uploaded_at.isoformat(),
                'uploaded_by': material.file.uploader.username,
                'order_index': material.order_index
            })
        
        return jsonify({
            'topic': {
                'id': topic.id,
                'name': topic.name,
                'description': topic.description
            },
            'materials': materials_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics/<int:topic_id>/materials', methods=['POST'])
@login_required
def add_topic_material(topic_id):
    """Add a material to a topic"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
            
        topic = Topic.query.get_or_404(topic_id)
        data = request.get_json()
        
        file_id = data.get('file_id')
        display_name = data.get('display_name')
        description = data.get('description')
        
        if not file_id:
            return jsonify({'error': 'File ID is required'}), 400
            
        file = File.query.get(file_id)
        if not file:
            return jsonify({'error': 'File not found'}), 404
            
        existing_material = TopicMaterial.query.filter_by(
            topic_id=topic_id, file_id=file_id
        ).first()
        
        if existing_material:
            return jsonify({'error': 'Material already exists for this topic'}), 400
        
        max_order = db.session.query(db.func.max(TopicMaterial.order_index))\
            .filter_by(topic_id=topic_id).scalar() or 0
        
        material = TopicMaterial(
            topic_id=topic_id,
            file_id=file_id,
            display_name=display_name,
            description=description,
            order_index=max_order + 1
        )
        
        db.session.add(material)
        db.session.commit()
        
        return jsonify({
            'message': 'Material added successfully',
            'material': {
                'id': material.id,
                'display_name': material.display_name or file.name,
                'file_id': file.id
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics/<int:topic_id>/materials/<int:material_id>', methods=['DELETE'])
@login_required
def remove_topic_material(topic_id, material_id):
    """Remove a material from a topic"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
            
        material = TopicMaterial.query.filter_by(
            id=material_id, topic_id=topic_id
        ).first_or_404()
        
        db.session.delete(material)
        db.session.commit()
        
        return jsonify({'message': 'Material removed successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics/<int:topic_id>/materials/reorder', methods=['POST'])
@login_required
def reorder_topic_materials(topic_id):
    """Reorder materials in a topic"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
            
        data = request.get_json()
        material_order = data.get('order', [])
        
        for index, material_id in enumerate(material_order):
            material = TopicMaterial.query.filter_by(
                id=material_id, topic_id=topic_id
            ).first()
            if material:
                material.order_index = index
        
        db.session.commit()
        return jsonify({'message': 'Materials reordered successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/available')
@login_required
def get_available_files():
    """Get files that can be added to topics"""
    try:
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        query = File.query
        
        if search:
            query = query.filter(
                db.or_(
                    File.name.ilike(f'%{search}%'),
                    File.description.ilike(f'%{search}%'),
                    File.filename.ilike(f'%{search}%')
                )
            )
        
        files = query.order_by(File.uploaded_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        files_data = []
        for file in files.items:
            files_data.append({
                'id': file.id,
                'name': file.name,
                'filename': file.filename,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'description': file.description,
                'category': file.category,
                'uploaded_at': file.uploaded_at.isoformat(),
                'uploaded_by': file.uploader.username
            })
        
        return jsonify({
            'files': files_data,
            'has_next': files.has_next,
            'has_prev': files.has_prev,
            'current_page': files.page,
            'pages': files.pages,
            'total': files.total
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
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

    referrer = request.referrer
    if referrer:
        return redirect(referrer, message='Oops! Something went wrong. Try again.', message_type='error'), 302
    else:
        return redirect(url_for('main_page', message='Oops! Something went wrong. Try again.', message_type='error')), 302

# ==========================================
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=47947, debug=False)