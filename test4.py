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
        {'username': 'alex_brown', 'mobile': '0756789012', 'user_id': 5},
        {'username': 'tech', 'mobile': '0740694312', 'user_id': '6'}
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
                         year=datetime.datetime.now().year,
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
    return render_template('404.html', year=datetime.datetime.now().year), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html', year=datetime.datetime.now().year), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)