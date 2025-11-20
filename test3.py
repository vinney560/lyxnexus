from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('dashboard.html')

from flask import jsonify
from datetime import datetime

@app.route('/dashboard/api/data')
def user_data():
    # Mock data - replace with your actual database queries
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
if __name__ == '__main__':
    app.run()