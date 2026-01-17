from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import datetime
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Mock user data
MOCK_USERS = {
    'students': [
        {'username': 'john_doe', 'mobile': '0712345678', 'user_id': 1},
        {'username': 'jane_smith', 'mobile': '0723456789', 'user_id': 2},
        {'username': 'mike_wilson', 'mobile': '0734567890', 'user_id': 3},
        {'username': 'sarah_jones', 'mobile': '0745678901', 'user_id': 4},
        {'username': 'alex_brown', 'mobile': '0756789012', 'user_id': 5}
    ],
    'admins': [
        {'username': 'admin1', 'mobile': '0767890123', 'user_id': 101, 'role': 'super_admin'},
        {'username': 'admin2', 'mobile': '0778901234', 'user_id': 102, 'role': 'course_admin'},
        {'username': 'vincent', 'mobile': '0740694312', 'user_id': 103, 'role': 'super_admin'}
    ]
}

# Mock master key
MASTER_KEY = "LyxNexus2024!"

# Mock courses data
MOCK_COURSES = [
    {'id': 1, 'name': 'Web Development Fundamentals', 'code': 'WEB101'},
    {'id': 2, 'name': 'Python Programming', 'code': 'PYTHON102'},
    {'id': 3, 'name': 'Data Structures & Algorithms', 'code': 'DSA201'},
    {'id': 4, 'name': 'Database Management', 'code': 'DB301'},
    {'id': 5, 'name': 'Mobile App Development', 'code': 'MOBILE202'}
]

@app.route('/')
def home():
    """Home page route"""
    return render_template('index.html', year=datetime.datetime.now().year)

@app.route('/api/notify')
def mock_notifications():
    """Mock notifications that work with your main_page.html template"""
    from datetime import datetime, timedelta
    import random
    
    # Generate 3-6 random notifications
    notification_count = random.randint(3, 6)
    mock_notifications = []
    
    notification_templates = [
        {
            'title': 'System Maintenance Scheduled',
            'message': 'The platform will undergo maintenance on Saturday from 2-4 AM. Please save your work.',
            'hours_ago': 2
        },
        {
            'title': 'New Assignment Posted', 
            'message': 'A new assignment "Web Development Project" has been posted. Due next Friday.',
            'hours_ago': 24
        },
        {
            'title': 'Welcome to LyxNexus!',
            'message': 'Welcome to our learning platform! Explore features and let us know if you need help.',
            'hours_ago': 72
        },
        {
            'title': 'Holiday Schedule',
            'message': 'Classes suspended next week for mid-term break. Enjoy your holiday!',
            'hours_ago': 120
        },
        {
            'title': 'Urgent: Server Update', 
            'message': 'Critical security update tonight at 11 PM. System unavailable for 30 minutes.',
            'hours_ago': 6
        },
        {
            'title': 'Assignment Deadline Reminder',
            'message': 'Mathematics Quiz 3 due tomorrow. Submit before deadline to avoid penalties.',
            'hours_ago': 12
        }
    ]
    
    # Select random templates
    selected_templates = random.sample(notification_templates, notification_count)
    
    for i, template in enumerate(selected_templates):
        mock_notifications.append({
            'id': i + 1,
            'title': template['title'],
            'message': template['message'],
            'created_at': (datetime.now() - timedelta(hours=template['hours_ago'])).isoformat(),
            'unread': random.choice([True, False])  # Random read status
        })
    
    # Count unread notifications
    unread_count = sum(1 for n in mock_notifications if n['unread'])
    
    return jsonify({
        'notifications': mock_notifications,
        'unread_count': unread_count
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page route - handles both GET and POST requests"""
    if request.method == 'POST':
        login_type = request.form.get('login_type')
        login_subtype = request.form.get('login_subtype', 'login')  # Default to login
        
        username = request.form.get('username', '').strip()
        mobile = request.form.get('mobile', '').strip()
        
        print(f"Login attempt - Type: {login_type}, Subtype: {login_subtype}, Username: {username}, Mobile: {mobile}")
        
        if login_type == 'student':
            return handle_student_login(username, mobile, login_subtype)
        elif login_type == 'admin':
            return handle_admin_login(username, mobile)
    
    # GET request - render login page
    return render_template('login.html', 
                         year=datetime.now().year,
                         username=request.args.get('username', ''),
                         mobile=request.args.get('mobile', ''))

def handle_student_login(username, mobile, login_subtype):
    """Handle student login/registration"""
    # Find existing student
    existing_student = next((s for s in MOCK_USERS['students'] 
                           if s['username'] == username and s['mobile'] == mobile), None)
    
    if login_subtype == 'login':
        if existing_student:
            # Successful login
            session['user_id'] = existing_student['user_id']
            session['username'] = existing_student['username']
            session['user_type'] = 'student'
            session['mobile'] = existing_student['mobile']
            
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('student_dashboard'))
        else:
            # Student not found
            flash('Invalid username or mobile number. Please try again or register as a new student.', 'error')
            return redirect(url_for('login', username=username, mobile=mobile))
    
    elif login_subtype == 'register':
        if existing_student:
            # Student already exists
            flash('An account with this username and mobile number already exists. Please login instead.', 'warning')
            return redirect(url_for('login', username=username, mobile=mobile))
        else:
            # Register new student
            new_user_id = max([s['user_id'] for s in MOCK_USERS['students']]) + 1 if MOCK_USERS['students'] else 1
            new_student = {
                'username': username,
                'mobile': mobile,
                'user_id': new_user_id
            }
            MOCK_USERS['students'].append(new_student)
            
            session['user_id'] = new_user_id
            session['username'] = username
            session['user_type'] = 'student'
            session['mobile'] = mobile
            session['new_user'] = True
            
            flash(f'Account created successfully! Welcome to LyxNexus, {username}!', 'success')
            return redirect(url_for('student_dashboard'))

def handle_admin_login(username, mobile):
    """Handle admin login"""
    existing_admin = next((a for a in MOCK_USERS['admins'] 
                          if a['username'] == username and a['mobile'] == mobile), None)
    
    if existing_admin:
        # Successful admin login
        session['user_id'] = existing_admin['user_id']
        session['username'] = existing_admin['username']
        session['user_type'] = 'admin'
        session['mobile'] = existing_admin['mobile']
        session['role'] = existing_admin.get('role', 'admin')
        
        flash(f'Admin access granted. Welcome, {username}!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        # Admin not found
        flash('Invalid admin credentials. Please check your username and mobile number.', 'error')
        return redirect(url_for('login'))

@app.route('/api/register-admin', methods=['POST'])
def register_admin():
    """API endpoint for registering new admin with master key"""
    data = request.get_json()
    
    username = data.get('username', '').strip()
    mobile = data.get('mobile', '').strip()
    master_key = data.get('master_key', '').strip()
    
    # Validate master key
    if master_key != MASTER_KEY:
        return jsonify({'error': 'Invalid master authorization key'}), 401
    
    # Check if admin already exists
    existing_admin = next((a for a in MOCK_USERS['admins'] 
                          if a['username'] == username or a['mobile'] == mobile), None)
    
    if existing_admin:
        return jsonify({'error': 'Admin with this username or mobile already exists'}), 400
    
    # Create new admin
    new_admin_id = max([a['user_id'] for a in MOCK_USERS['admins']]) + 1 if MOCK_USERS['admins'] else 101
    new_admin = {
        'username': username,
        'mobile': mobile,
        'user_id': new_admin_id,
        'role': 'course_admin'
    }
    MOCK_USERS['admins'].append(new_admin)
    
    return jsonify({
        'success': True,
        'message': 'Admin account created successfully',
        'user_id': new_admin_id,
        'username': username
    })

@app.route('/api/promote-to-admin', methods=['POST'])
def promote_to_admin():
    """API endpoint for promoting existing user to admin with master key"""
    data = request.get_json()
    
    username = data.get('username', '').strip()
    mobile = data.get('mobile', '').strip()
    master_key = data.get('master_key', '').strip()
    
    # Validate master key
    if master_key != MASTER_KEY:
        return jsonify({'error': 'Invalid master authorization key'}), 401
    
    # Check if user exists as student
    existing_student = next((s for s in MOCK_USERS['students'] 
                           if s['username'] == username and s['mobile'] == mobile), None)
    
    if not existing_student:
        return jsonify({'error': 'No student found with these credentials'}), 404
    
    # Check if already an admin
    existing_admin = next((a for a in MOCK_USERS['admins'] 
                          if a['username'] == username or a['mobile'] == mobile), None)
    
    if existing_admin:
        return jsonify({'error': 'User is already an admin'}), 400
    
    # Promote to admin
    new_admin = {
        'username': username,
        'mobile': mobile,
        'user_id': existing_student['user_id'],
        'role': 'course_admin'
    }
    MOCK_USERS['admins'].append(new_admin)
    
    # Remove from students (optional - depending on your logic)
    MOCK_USERS['students'] = [s for s in MOCK_USERS['students'] if s['user_id'] != existing_student['user_id']]
    
    return jsonify({
        'success': True,
        'message': 'User promoted to admin successfully',
        'user_id': existing_student['user_id'],
        'username': username
    })

@app.route('/api/check-admin', methods=['POST'])
def check_admin():
    """API endpoint to check if user is admin"""
    data = request.get_json()
    
    username = data.get('username', '').strip()
    mobile = data.get('mobile', '').strip()
    
    existing_admin = next((a for a in MOCK_USERS['admins'] 
                          if a['username'] == username and a['mobile'] == mobile), None)
    
    return jsonify({
        'is_admin': existing_admin is not None,
        'role': existing_admin.get('role', '') if existing_admin else ''
    })

@app.route('/login-check')
def login_check():
    """Auto-authentication check route"""
    # Check if user is already logged in
    if 'user_id' in session:
        user_type = session.get('user_type')
        if user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    # Mock auto-authentication failure
    flash('Auto-authentication failed. Please login manually.', 'error')
    return redirect(url_for('login'))

@app.route('/student/dashboard')
def student_dashboard():
    """Student dashboard route"""
    if 'user_id' not in session or session.get('user_type') != 'student':
        flash('Please login as student to access dashboard', 'error')
        return redirect(url_for('login'))
    
    user_courses = random.sample(MOCK_COURSES, min(3, len(MOCK_COURSES)))
    
    return render_template('student_dashboard.html',
                         username=session.get('username'),
                         mobile=session.get('mobile'),
                         user_id=session.get('user_id'),
                         courses=user_courses,
                         year=datetime.datetime.now().year,
                         is_new_user=session.pop('new_user', False))

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard route"""
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Please login as admin to access dashboard', 'error')
        return redirect(url_for('login'))
    
    return render_template('admin_dashboard.html',
                         username=session.get('username'),
                         mobile=session.get('mobile'),
                         user_id=session.get('user_id'),
                         role=session.get('role'),
                         total_students=len(MOCK_USERS['students']),
                         total_courses=len(MOCK_COURSES),
                         year=datetime.datetime.now().year)

@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/terms')
def terms():
    """Terms and conditions page"""
    return render_template('terms.html', year=datetime.datetime.now().year)

@app.route('/navigation-guide')
def navigation_guide():
    """Navigation guide page"""
    return render_template('navigation_guide.html', year=datetime.datetime.now().year)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', year=datetime.now().year), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html', year=datetime.now().year), 500

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

from flask import jsonify
from datetime import datetime

@app.route('/dashboard/api/data')
def user_data():
    available_files = 788  # Mock: File.query.count()
    all_students = 198
    announcements_count = 12  # Mock: current_user.announcements.count()
    assignments_count = 8    # Mock: current_user.assignments.count()
    
    return jsonify(
        _data={
            'id': 12345,
            'username': 'john_doe',
            'mobile': '+254712345678',
            'status': True,
            'is_admin': True,
            'created_at': '2024-01-15 14:30:00',
            'announcements': announcements_count,
            'assignments': assignments_count,
            'available_files': available_files,
            'all_students': all_students
        }
    )

from flask import jsonify
import datetime
import random

@app.route('/dashboard/api/activity')
def activities():
    try:
        # Mock user activity count
        user_activity_count = random.randint(50, 200)
        
        # Generate mock recent activities
        activities_data = []
        actions = ['view', 'click', 'download', 'submit', 'login', 'search']
        targets = ['dashboard', 'announcements', 'assignments', 'profile', 'materials', 'timetable']
        
        for i in range(150):
            # Generate random timestamp within last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            timestamp = datetime.datetime.now() - datetime.timedelta(
                days=days_ago, 
                hours=hours_ago, 
                minutes=minutes_ago
            )
            
            activity_data = {
                'id': i + 1,
                'action': random.choice(actions),
                'target': random.choice(targets),
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': random.randint(5, 300)  # 5 seconds to 5 minutes
            }
            activities_data.append(activity_data)
        
        # Sort by timestamp (most recent first)
        activities_data.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'visits': user_activity_count, 
            'visited_page': activities_data[:50]  # Return only 50 most recent
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'visits': 0,
            'visited_page': []
        }), 500

@app.route('/dashboard/api/stats')
def user_stats():
    """Additional stats endpoint for charts and analytics"""
    try:
        # Mock today's activities count
        today_activities = random.randint(5, 25)
        
        # Mock action stats
        actions = ['view', 'click', 'download', 'submit', 'login', 'search']
        action_data = {}
        for action in actions:
            action_data[action] = random.randint(10, 100)
        
        # Mock weekly activity data
        weekly_data = []
        for i in range(7):
            date = datetime.datetime.now() - datetime.timedelta(days=6-i)
            weekly_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': random.randint(5, 20)
            })
        
        return jsonify({
            'success': True,
            'today_activities': today_activities,
            'action_stats': action_data,
            'weekly_activity': weekly_data,
            'total_announcements': random.randint(5, 15),
            'total_assignments': random.randint(3, 10),
            'total_files': random.randint(50, 150),
            'completion_rate': random.randint(60, 95),
            'average_session': random.randint(15, 45)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/dashboard/api/log_activity', methods=['POST'])
def log_activity():
    """Endpoint to log user activity from frontend"""
    try:
        from flask import request
        
        data = request.get_json()
        action = data.get('action', 'view')
        target = data.get('target', 'dashboard')
        duration = data.get('duration', 0)
        
        # Mock successful activity logging
        print(f"Mock: Logged activity - Action: {action}, Target: {target}, Duration: {duration}s")
        
        return jsonify({
            'success': True,
            'message': 'Activity logged successfully (mock)',
            'logged_data': {
                'action': action,
                'target': target,
                'duration': duration,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/dashboard/api/user-summary')
def user_summary():
    """Comprehensive user summary with all stats"""
    try:
        # Generate comprehensive mock data
        summary_data = {
            'user': {
                'id': current_user.id if current_user else 12345,
                'username': getattr(current_user, 'username', 'demo_user'),
                'status': 'active',
                'member_since': '2024-01-15'
            },
            'stats': {
                'total_visits': random.randint(100, 500),
                'today_visits': random.randint(5, 25),
                'announcements': random.randint(5, 15),
                'assignments': random.randint(3, 10),
                'files_accessed': random.randint(50, 150),
                'completion_rate': random.randint(60, 95),
                'avg_session_duration': random.randint(15, 45)
            },
            'recent_activity': [
                {
                    'action': 'view',
                    'target': 'dashboard', 
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': 120
                },
                {
                    'action': 'download',
                    'target': 'assignment_1',
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': 45
                },
                {
                    'action': 'submit',
                    'target': 'quiz_1',
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': 300
                }
            ],
            'weekly_trend': [
                {'day': 'Mon', 'activity': random.randint(10, 20)},
                {'day': 'Tue', 'activity': random.randint(10, 20)},
                {'day': 'Wed', 'activity': random.randint(10, 20)},
                {'day': 'Thu', 'activity': random.randint(10, 20)},
                {'day': 'Fri', 'activity': random.randint(10, 20)},
                {'day': 'Sat', 'activity': random.randint(5, 15)},
                {'day': 'Sun', 'activity': random.randint(5, 15)}
            ]
        }
        
        return jsonify({
            'success': True,
            'summary': summary_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import json
import random
from datetime import datetime, timedelta
from faker import Faker
import os

class MockDataGenerator:
    def __init__(self):
        self.fake = Faker()
        self.data = {}
        
    def generate_data(self):
        # Generate users
        users = [
            {
                'id': 1,
                'username': 'vincent',
                'mobile': '+254740694312',
                'is_admin': True,
                'status': True,
                'created_at': '2024-01-15T10:30:00',
                'email': 'vincent@lyxnexus.com'
            }
        ]
        
        # Add more users
        for i in range(2, 6):
            users.append({
                'id': i,
                'username': self.fake.user_name(),
                'mobile': self.fake.phone_number(),
                'is_admin': False,
                'status': random.choice([True, False]),
                'created_at': self.fake.date_time_this_year().isoformat(),
                'email': self.fake.email()
            })
        
        # Generate topics
        tech_topics = [
            "Web Development", "Data Structures", "Algorithms", "Database Systems",
            "Machine Learning", "Network Security", "Mobile Development", "Cloud Computing"
        ]
        
        topics = []
        for i, topic_name in enumerate(tech_topics, 1):
            topics.append({
                'id': i,
                'name': topic_name,
                'description': f"Comprehensive course covering {topic_name} fundamentals and advanced concepts.",
                'created_at': self.fake.date_time_this_year().isoformat(),
                'material_count': random.randint(3, 12)
            })
        
        # Generate announcements
        announcements = []
        announcement_titles = [
            "",
            "",
            "",
            "Holiday Announcement",
            "Workshop Opportunity",
            "Exam Schedule Released",
            "New Learning Materials",
            "Maintenance Notice"
        ]
        
        for i in range(1, 16):
            has_file = random.choice([True, False, False])
            file_type = None
            file_url = None
            file_name = None
            
            if has_file:
                file_type = random.choice(['image/png', 'image/png', 'application/pdf'])
                file_name = f"navmmbm-{i}.{file_type.split('/')[-1]}"
                file_url = f"/uploads/{file_name}"
            
            content = self.fake.paragraph(nb_sentences=random.randint(2, 4))
            if random.choice([True, False]):
                content = f"**Important Update**: {content}"
            if random.choice([True, False]):
                content += f"\n\nCheck out this resource: {self.fake.url()}"
            
            announcements.append({
                'id': i,
                'title': random.choice(announcement_titles),
                'content': content,
                'author': random.choice(users),
                'has_file': has_file,
                'file_type': file_type,
                'file_url': file_url,
                'file_name': file_name,
                'created_at': self.fake.date_time_this_month().isoformat(),
                'is_pinned': random.choice([True, False, False, False])
            })
        
        # Generate assignments
        assignments = []
        assignment_titles = [
            "Data Structures Programming Assignment",
            "Web Development Project",
            "Algorithm Analysis Report",
            "Database Design Exercise",
            "Machine Learning Implementation",
            "Network Security Lab"
        ]
        
        for i in range(1, 13):
            due_date = self.fake.future_datetime(end_date="+30d")
            
            descriptions = [
                f"Complete the exercises on {random.choice(['arrays', 'linked lists', 'trees', 'graphs'])}.",
                f"Read chapter {random.randint(1, 12)} and solve the problems at the end.",
                f"Research and write a report about {self.fake.catch_phrase()}.",
                f"Solve the equation: $x^{random.randint(2, 3)} + {random.randint(1, 5)}x + {random.randint(1, 10)} = 0$",
                f"Implement a {random.choice(['sorting algorithm', 'search algorithm', 'data structure'])} in your preferred language.",
                f"Calculate the integral: $\\int_{random.randint(0, 2)}^{random.randint(3, 5)} x^{random.randint(1, 2)} dx$"
            ]
            
            assignments.append({
                'id': i,
                'title': f"{random.choice(assignment_titles)} {i}",
                'description': random.choice(descriptions),
                'due_date': due_date.isoformat(),
                'topic': random.choice(topics),
                'status': 'active',
                'points': random.randint(10, 100),
                'created_at': self.fake.past_datetime(start_date="-30d").isoformat()
            })
        
        # Generate timetable
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        time_slots = ['08:00-09:30', '09:45-11:15', '11:30-13:00', '14:00-15:30', '15:45-17:15']
        subjects = ['Mathematics', 'Physics', 'Computer Science', 'Web Development', 'Data Structures']
        rooms = ['Lab 101', 'Room 201', 'Room 305', 'Lab 402', 'Virtual']
        
        timetable = []
        for day in days:
            day_slots = []
            slots_count = random.randint(3, 4)
            
            used_times = set()
            for _ in range(slots_count):
                time_slot = random.choice([ts for ts in time_slots if ts not in used_times])
                used_times.add(time_slot)
                
                slot = {
                    'subject': random.choice(subjects),
                    'teacher': self.fake.name(),
                    'time': time_slot,
                    'room': random.choice(rooms),
                    'type': random.choice(['Lecture', 'Lab', 'Tutorial'])
                }
                day_slots.append(slot)
            
            # Sort by time
            day_slots.sort(key=lambda x: x['time'])
            
            timetable.append({
                'day': day,
                'slots': day_slots
            })
        
        self.data = {
            'users': users,
            'topics': topics,
            'announcements': announcements,
            'assignments': assignments,
            'timetable': timetable
        }
        
        return self.data

# Initialize mock data generator
mock_generator = MockDataGenerator()
mock_data = mock_generator.generate_data()

# Mock current user (for session)
current_user = mock_data['users'][0]

@app.route('/main-page')
def main_page():
    return render_template('main_page.html', current_user=current_user)

@app.route('/api/user')
def get_current_user():
    """Get current user data"""
    return jsonify(current_user)

@app.route('/api/announcements/specified')
def get_announcements():
    """Get all announcements"""
    return jsonify(mock_data['announcements'])

@app.route('/api/assignments')
def get_assignments():
    """Get all assignments"""
    return jsonify(mock_data['assignments'])

@app.route('/api/topics')
def get_topics():
    """Get all topics/units"""
    return jsonify(mock_data['topics'])

@app.route('/api/timetable')
def get_timetable():
    """Get timetable (flat structure)"""
    flat_slots = []
    for day in mock_data['timetable']:
        for slot in day['slots']:
            flat_slots.append({**slot, 'day': day['day']})
    return jsonify(flat_slots)

@app.route('/api/timetable/grouped')
def get_timetable_grouped():
    """Get timetable grouped by days"""
    return jsonify(mock_data['timetable'])

@app.route('/api/track-visit', methods=['POST'])
def track_visit():
    """Track user visit (analytics)"""
    data = request.get_json()
    print(f"Visit tracked: {data}")
    return jsonify({'status': 'success'})

@app.route('/api/track-activity', methods=['POST'])
def track_activity():
    """Track user activity"""
    data = request.get_json()
    print(f"Activity tracked: {data}")
    return jsonify({'status': 'success'})

@app.route('/api/preview')
def get_link_preview():
    """Generate OG preview data"""
    url = request.args.get('url', '')
    return jsonify({
        'title': 'Sample Website - ' + random.choice(['Technology', 'Education', 'News', 'Blog']),
        'description': 'This is a sample description for the website preview.',
        'image': 'https://picsum.photos/200/100?random=' + str(random.randint(1, 100)),
        'url': url
    })


@app.route('/files')
def files():
    return render_template('main_page.html', current_user=current_user)

@app.route('/messages')
def messages():
    return render_template('main_page.html', current_user=current_user)


@app.route('/lyx-lab')
def lyx_lab():
    return render_template('main_page.html', current_user=current_user)

@app.route('/profile')
def profile():
    return render_template('main_page.html', current_user=current_user)

@app.route('/assignment/<int:assignment_id>')
def assignment_detail(assignment_id):
    return render_template('main_page.html', current_user=current_user)

@app.route('/material/<int:topic_id>')
def material_detail(topic_id):
    return render_template('main_page.html', current_user=current_user)

@app.route('/gemini')
def gemini_ai():
    return render_template('main_page.html', current_user=current_user)

@app.route('/quiz')
def quiz():
    return render_template('main_page.html', current_user=current_user)

@app.route('/math')
def math_ai():
    return render_template('main_page.html', current_user=current_user)

# Search API endpoint
@app.route('/api/search')
def search():
    """Enhanced search endpoint"""
    query = request.args.get('q', '').lower().strip()
    section = request.args.get('section', 'announcements')
    
    if not query:
        return jsonify({'results': [], 'count': 0})
    
    results = []
    
    if section == 'announcements':
        results = [ann for ann in mock_data['announcements'] 
                  if query in ann['title'].lower() or query in ann['content'].lower()]
    elif section == 'assignments':
        results = [ass for ass in mock_data['assignments']
                  if query in ass['title'].lower() or query in ass['description'].lower()]
    elif section == 'topics':
        results = [topic for topic in mock_data['topics']
                  if query in topic['name'].lower() or query in topic['description'].lower()]
    elif section == 'timetable':
        results = []
        for day in mock_data['timetable']:
            matching_slots = [slot for slot in day['slots']
                            if query in slot['subject'].lower() or 
                               query in slot['teacher'].lower() or
                               query in slot['room'].lower()]
            if matching_slots:
                results.append({
                    'day': day['day'],
                    'slots': matching_slots
                })
    
    return jsonify({
        'results': results,
        'count': len(results),
        'query': query,
        'section': section
    })
        
if __name__ == '__main__':
    app.run()