from flask import Flask, render_template, redirect, url_for, jsonify, request
from datetime import datetime, timedelta, time
from flask_login import current_user

app = Flask(__name__)

@app.route('/main-page')
def main_page():
    return render_template('main_page.html', current_user=current_user)

@app.route('/')
def main():
    
    return render_template('admin_notifications.html', current_user=current_user)

# =========================================
# MOCK DATA ROUTES FOR TESTING
# =========================================

@app.route('/api/mock/notify')

def mock_get_notifications():
    """Mock notifications for testing"""
    import random
    from datetime import datetime, timedelta
    
    # Generate mock notifications
    mock_notifications = [
        {
            'id': 1,
            'title': 'System Maintenance',
            'message': 'The system will undergo maintenance this Saturday from 2-4 AM. Please save your work.',
            'created_at': (datetime.now() - timedelta(hours=2)).isoformat(),
            'unread': True
        },
        {
            'id': 2,
            'title': 'New Assignment Posted',
            'message': 'A new assignment "Web Development Project" has been posted. Due date: Next Friday.',
            'created_at': (datetime.now() - timedelta(days=1)).isoformat(),
            'unread': True
        },
        {
            'id': 3,
            'title': 'Welcome to LyxNexus!',
            'message': 'Welcome to our learning platform! Explore the features and let us know if you need help.',
            'created_at': (datetime.now() - timedelta(days=3)).isoformat(),
            'unread': False
        },
        {
            'id': 4,
            'title': 'Holiday Schedule',
            'message': 'Classes will be suspended next week for the mid-term break. Enjoy your holiday!',
            'created_at': (datetime.now() - timedelta(days=5)).isoformat(),
            'unread': False
        },
        {
            'id': 5,
            'title': 'Urgent: Server Update',
            'message': 'Critical security update will be deployed tonight at 11 PM. System will be unavailable for 30 minutes.',
            'created_at': (datetime.now() - timedelta(hours=6)).isoformat(),
            'unread': True
        }
    ]
    
    # Randomize unread status for testing
    for notification in mock_notifications:
        if random.random() > 0.6:  # 40% chance to be unread
            notification['unread'] = True
    
    unread_count = sum(1 for n in mock_notifications if n['unread'])
    
    return jsonify({
        'notifications': mock_notifications,
        'unread_count': unread_count
    })

@app.route('/api/mock/notify/read-all', methods=['POST'])

def mock_mark_all_read():
    """Mock mark all as read"""
    return jsonify({
        'success': True,
        'message': 'All notifications marked as read (Mock)'
    })

@app.route('/admin/mock/notifications')

def mock_admin_notifications():
    """Mock admin notifications page"""
    
    # Generate mock notifications for admin
    mock_notifications = [
        {
            'id': 1,
            'title': 'System Maintenance Announcement',
            'message': 'The system will undergo maintenance this Saturday from 2-4 AM.',
            'target_audience': 'all',
            'is_active': True,
            'created_at': (datetime.now() - timedelta(hours=2)),
            'expires_at': (datetime.now() + timedelta(days=7))
        },
        {
            'id': 2,
            'title': 'Admin Meeting Reminder',
            'message': 'Monthly admin meeting scheduled for tomorrow at 10 AM in the conference room.',
            'target_audience': 'admins',
            'is_active': True,
            'created_at': (datetime.now() - timedelta(days=1)),
            'expires_at': (datetime.now() + timedelta(days=1))
        },
        {
            'id': 3,
            'title': 'Student Welcome Message',
            'message': 'Welcome new students to the platform! Please complete your profile setup.',
            'target_audience': 'students',
            'is_active': True,
            'created_at': (datetime.now() - timedelta(days=3)),
            'expires_at': (datetime.now() + timedelta(days=30))
        },
        {
            'id': 4,
            'title': 'Specific User Alert',
            'message': 'This is a test notification for specific users only.',
            'target_audience': 'specific',
            'is_active': True,
            'created_at': (datetime.now() - timedelta(days=2)),
            'expires_at': None
        },
        {
            'id': 5,
            'title': 'Expired Notification',
            'message': 'This notification has expired and should not be visible to users.',
            'target_audience': 'all',
            'is_active': False,
            'created_at': (datetime.now() - timedelta(days=10)),
            'expires_at': (datetime.now() - timedelta(days=1))
        }
    ]
    
    return render_template('admin_notifications.html', notifications=mock_notifications)

@app.route('/admin/mock/notifications/stats')

def mock_notification_stats():
    """Mock notification statistics"""
    
    return jsonify({
        'total_notifications': 15,
        'active_notifications': 8,
        'total_users': 124,
        'latest_stats': [
            {
                'id': 1,
                'title': 'System Maintenance',
                'total_receivers': 124,
                'read_count': 89,
                'read_percentage': 71.8
            },
            {
                'id': 2,
                'title': 'New Assignment Posted',
                'total_receivers': 115,
                'read_count': 102,
                'read_percentage': 88.7
            },
            {
                'id': 3,
                'title': 'Welcome Message',
                'total_receivers': 124,
                'read_count': 124,
                'read_percentage': 100.0
            },
            {
                'id': 4,
                'title': 'Holiday Schedule',
                'total_receivers': 124,
                'read_count': 67,
                'read_percentage': 54.0
            },
            {
                'id': 5,
                'title': 'Admin Meeting',
                'total_receivers': 8,
                'read_count': 6,
                'read_percentage': 75.0
            }
        ]
    })

@app.route('/api/mock/users/search')

def mock_search_users():
    """Mock user search for testing"""
    query = request.args.get('q', '').lower()
    
    # Mock user database
    mock_users = [
        {'id': 1, 'username': 'John Doe', 'mobile': '0712345678', 'is_admin': False, 'status': True},
        {'id': 2, 'username': 'Jane Smith', 'mobile': '0723456789', 'is_admin': False, 'status': True},
        {'id': 3, 'username': 'Mike Johnson', 'mobile': '0734567890', 'is_admin': True, 'status': True},
        {'id': 4, 'username': 'Sarah Wilson', 'mobile': '0745678901', 'is_admin': False, 'status': True},
        {'id': 5, 'username': 'David Brown', 'mobile': '0756789012', 'is_admin': False, 'status': False},
        {'id': 6, 'username': 'Emily Davis', 'mobile': '0767890123', 'is_admin': False, 'status': True},
        {'id': 7, 'username': 'Robert Miller', 'mobile': '0778901234', 'is_admin': True, 'status': True},
        {'id': 8, 'username': 'Lisa Garcia', 'mobile': '0789012345', 'is_admin': False, 'status': True},
        {'id': 9, 'username': 'James Wilson', 'mobile': '0790123456', 'is_admin': False, 'status': True},
        {'id': 10, 'username': 'Maria Martinez', 'mobile': '0701234567', 'is_admin': False, 'status': True}
    ]
    
    # Filter users based on query
    filtered_users = [
        user for user in mock_users 
        if query in user['username'].lower() or query in user['mobile']
    ][:10]  # Limit to 10 results
    
    return jsonify({'users': filtered_users})

# Mock CRUD operations
@app.route('/admin/mock/notifications/create', methods=['POST'])

def mock_create_notification():
    """Mock create notification"""
   
    
    data = request.get_json()
    
    # Simulate processing delay
    import time
    time.sleep(1)
    
    return jsonify({
        'success': True,
        'message': 'Notification created successfully (Mock)',
        'notification': {
            'id': 999,
            'title': data['title'],
            'message': data['message'],
            'target_audience': data.get('target_audience', 'all'),
            'is_active': data.get('is_active', True),
            'created_at': datetime.now().isoformat(),
            'expires_at': data.get('expires_at')
        }
    })

@app.route('/admin/mock/notifications/<int:notification_id>/update', methods=['POST'])

def mock_update_notification(notification_id):
    """Mock update notification"""
    
    return jsonify({
        'success': True,
        'message': f'Notification {notification_id} updated successfully (Mock)'
    })

@app.route('/admin/mock/notifications/<int:notification_id>/delete', methods=['POST'])
def mock_delete_notification(notification_id):
    """Mock delete notification"""
    
    return jsonify({
        'success': True,
        'message': f'Notification {notification_id} deleted successfully (Mock)'
    })

if __name__ == '__main__':
    app.run()