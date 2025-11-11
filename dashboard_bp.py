from flask import Blueprint, jsonify, render_template
from app import User, UserActivity
from flask_login import login_required, current_user
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

"""
profile --> Id, Username, status, Admin status, created_at, announcements, assignment, activity, 
"""

@dashboard_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@dashboard_bp.route('/api/data')
@login_required
def user_data():
    return jsonify(
        _data = {
            'id': current_user.id,
            'username': current_user.username,
            'mobile': current_user.mobile,
            'status': current_user.status, # True or False
            'is_admin': current_user.is_admin, # True or False
            'created_at': current_user.created_at.strftime('%Y-%m-%d %H:%M:%S') if current_user.created_at else 'Unknown',
            'announcements': current_user.announcements.count() if hasattr(current_user, 'announcements') else 0,
            'assignment': current_user.assignments.count() if hasattr(current_user, 'assignments') else 0
        }
    )

@dashboard_bp.route('/api/activity')
@login_required
def activities():
    # Retrieve user activity count
    user_activity_count = UserActivity.query.filter_by(user_id=current_user.id).count()
    
    # Get recent activities
    recent_activities = UserActivity.query.filter_by(user_id=current_user.id).order_by(UserActivity.timestamp.desc()).limit(10).all()
    
    # Format activities for JSON response
    activities_data = []
    for activity in recent_activities:
        activities_data.append({
            'page': activity.page or 'dashboard',
            'section': activity.section or 'main',
            'timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S') if activity.timestamp else 'Unknown'
        })
    
    return jsonify({
        'visits': user_activity_count, 
        'visited_page': activities_data
    })

print("Dashboard Registered Successfully!")
print("✅ Dashboard Initialized!")