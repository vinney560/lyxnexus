from flask import Blueprint, jsonify, render_template, redirect, url_for, request, flash
from app import User, UserActivity, db, File
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from functools import wraps # Wraps a function to a decorator
import datetime

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

"""
profile --> Id, Username, status, Admin status, created_at, announcements, assignment, activity, 
"""

""" Restrict Users who are banned! """
def not_banned(f): # @not_banned
    @wraps(f)
    def decor(*args, **kwargs):
        if not current_user.status:
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Banned User Not Allowed'}), 401
            referrer = request.referrer
            if referrer:
                return redirect(referrer), 302
            else:
                return redirect(url_for('main_page', message='Banned User Not Allowed!', message_type='warning')), 302
        return f(*args, **kwargs)
    return decor

@dashboard_bp.route('/')
@login_required
@not_banned
def dashboard():
    return render_template('dashboard.html')

@dashboard_bp.route('/api/data')
@login_required
@not_banned
def user_data():
    # Auxiliary features for moer data tod dahboard
    available_files = File.query.count() # Never use .all().count()
    all_users = User.query.count()
    # Get counts for announcements and assignments --> len() --> not count()
    announcements_count = len(current_user.announcements) if current_user.announcements else 0
    assignments_count = len(current_user.assignments) if current_user.assignments else 0
    
    return jsonify(
        _data = {
            'id': current_user.id,
            'username': current_user.username,
            'mobile': current_user.mobile,
            'status': current_user.status, # True or False
            'is_admin': current_user.is_admin, # True or False
            'created_at': current_user.created_at.strftime('%Y-%m-%d %H:%M:%S') if current_user.created_at else 'Unknown',
            'announcements': announcements_count,
            'assignment': assignments_count,
            'available_files': available_files,
            'all_students': all_users
        }
    )

@dashboard_bp.route('/api/activity')
@login_required
@not_banned
def activities():
    try:
        # Retrieve user activity count
        user_activity_count = UserActivity.query.filter_by(user_id=current_user.id).count()
        
        # Get recent activities with proper error handling
        recent_activities = UserActivity.query.filter_by(
            user_id=current_user.id
        ).order_by(
            desc(UserActivity.timestamp)
        ).limit(150).all()
        
        # Format activities for JSON response
        activities_data = []
        for activity in recent_activities:
            activity_data = {
                'id': activity.id,
                'action': activity.action or 'view',
                'target': activity.target or 'dashboard',
                'timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S') if activity.timestamp else 'Unknown',
                'duration': activity.duration or 0
            }
            activities_data.append(activity_data)
        
        return jsonify({
            'success': True,
            'visits': user_activity_count, 
            'visited_page': activities_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'visits': 0,
            'visited_page': []
        }), 500

@dashboard_bp.route('/api/stats')
@login_required
@not_banned
def user_stats():
    """Additional stats endpoint for charts and analytics"""
    try:
        # Get today's activities count
        today = datetime.datetime.now().date()
        today_activities = UserActivity.query.filter(
            UserActivity.user_id == current_user.id,
            func.date(UserActivity.timestamp) == today
        ).count()
        
        # Get activities by action type
        action_stats = db.session.query(
            UserActivity.action,
            func.count(UserActivity.id)
        ).filter(
            UserActivity.user_id == current_user.id
        ).group_by(UserActivity.action).all()
        
        # Format action stats
        action_data = {action: count for action, count in action_stats}
        
        # Get weekly
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        weekly_activity = db.session.query(
            func.date(UserActivity.timestamp),
            func.count(UserActivity.id)
        ).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.timestamp >= week_ago
        ).group_by(func.date(UserActivity.timestamp)).all()
        
        weekly_data = [{'date': date.strftime('%Y-%m-%d'), 'count': count} for date, count in weekly_activity]
        
        return jsonify({
            'success': True,
            'today_activities': today_activities,
            'action_stats': action_data,
            'weekly_activity': weekly_data,
            'total_announcements': len(current_user.announcements) if current_user.announcements else 0,
            'total_assignments': len(current_user.assignments) if current_user.assignments else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/api/log_activity', methods=['POST'])
@login_required
@not_banned
def log_activity():
    """Endpoint to log user activity from frontend"""
    try:
        from flask import request
        
        data = request.get_json()
        action = data.get('action', 'view')
        target = data.get('target', 'dashboard')
        duration = data.get('duration', 0)
        
        # Create new activity log --> inplace of Main-page
        new_activity = UserActivity(
            user_id=current_user.id,
            action=action,
            target=target,
            duration=duration
        )
        
        db.session.add(new_activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Activity logged successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

print("Dashboard Registered Successfully!")
print("✅ Dashboard Initialized!")