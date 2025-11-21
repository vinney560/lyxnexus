from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
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

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

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
            "Important System Update",
            "New Assignment Posted",
            "Class Schedule Changes",
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
                file_type = random.choice(['image/jpeg', 'image/png', 'application/pdf'])
                file_name = f"announcement_{i}.{file_type.split('/')[-1]}"
                file_url = f"/uploads/{file_name}"
            
            content = self.fake.paragraph(nb_sentences=random.randint(2, 4))
            if random.choice([True, False]):
                content = f"**Important Update**: {content}"
            if random.choice([True, False]):
                content += f"\n\nCheck out this resource: {self.fake.url()}"
            
            announcements.append({
                'id': i,
                'title': random.choice(announcement_titles) + f" #{i}",
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

@app.route('/')
def main_page():
    return render_template('main_page.html', current_user=current_user)

@app.route('/api/user')
def get_current_user():
    """Get current user data"""
    return jsonify(current_user)

@app.route('/api/announcements')
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

# Additional routes for navigation
@app.route('/dashboard')
def dashboard():
    return render_template('main_page.html', current_user=current_user)

@app.route('/files')
def files():
    return render_template('main_page.html', current_user=current_user)

@app.route('/messages')
def messages():
    return render_template('main_page.html', current_user=current_user)

@app.route('/terms')
def terms():
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

@app.route('/logout')
def logout():
    return redirect('/')

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