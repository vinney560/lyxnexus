from flask import Flask, render_template, jsonify, request, redirect, url_for
from datetime import datetime, timedelta
import random
import os

app = Flask(__name__)
app.secret_key = 'mock-secret-key-for-testing'

# Mock user class
class MockUser:
    def __init__(self, is_admin=True):
        self.is_admin = is_admin

# Mock data - only 5 files
MOCK_FILES = [
    {
        'id': 1,
        'name': 'Algorithms_Notes_ihid_JQIdh_jwdnmlweifj_kndjkwh',
        'filename': 'Algorithms_Notes_ihid_JQIdh_jwdnmlweifj_kndjkwh.pdf',
        'display_name': 'Algorithms_Notes_ihid_JQIdh_jwdnmlweifj_kndjkwh',
        'description': 'Basic algorithms and data structures',
        'file_type': 'application/pdf',
        'file_size': 1024000,  # 1 MB
        'url': '/mock-files/algo.pdf',
        'uploaded_at': (datetime.now() - timedelta(days=2)).isoformat(),
        'uploaded_by': 'Dr. Smith'
    },
    {
        'id': 2,
        'name': 'Python_Tutorial_jbdxkweh_kkqbjdjkbed_kbdkj',
        'filename': 'python_basics.py',
        'display_name': 'Python Programming Basics',
        'description': 'Introduction to Python programming',
        'file_type': 'text/x-python',
        'file_size': 512000,  # 512 KB
        'url': '/mock-files/python.py',
        'uploaded_at': (datetime.now() - timedelta(days=5)).isoformat(),
        'uploaded_by': 'Prof. Johnson'
    },
    {
        'id': 3,
        'name': 'Database_SQL_kqndkjwh_JKQDJHKWEH',
        'filename': 'sql_queries.pdf',
        'display_name': 'SQL Query Guide',
        'description': 'Common SQL queries and examples',
        'file_type': 'application/pdf',
        'file_size': 2048000,  # 2 MB
        'url': '/mock-files/sql.pdf',
        'uploaded_at': (datetime.now() - timedelta(days=3)).isoformat(),
        'uploaded_by': 'Dr. Williams'
    },
    {
        'id': 4,
        'name': 'Web_Dev_Video_wejkbfjk_welnfklj_jdklj',
        'filename': 'html_css_intro.mp4',
        'display_name': 'HTML and CSS Crash Course',
        'description': 'Video tutorial on web development basics',
        'file_type': 'video/mp4',
        'file_size': 5120000,  # 5 MB
        'url': '/mock-files/web.mp4',
        'uploaded_at': (datetime.now() - timedelta(days=1)).isoformat(),
        'uploaded_by': 'Prof. Davis'
    },
    {
        'id': 5,
        'name': 'Network_Protocols_JQDBXHUWEFHJKK_BJKawdj',
        'filename': 'tcp_ip_explained.pdf',
        'display_name': 'TCP/IP Protocol Suite',
        'description': 'Computer networking fundamentals',
        'file_type': 'application/pdf',
        'file_size': 1536000,  # 1.5 MB
        'url': '/mock-files/network.pdf',
        'uploaded_at': (datetime.now() - timedelta(days=4)).isoformat(),
        'uploaded_by': 'Dr. Brown'
    }
]

# Mock topics
MOCK_TOPICS = {
    1: {
        'id': 1,
        'name': 'CS101: Programming Fundamentals',
        'description': 'Introduction to programming concepts'
    },
    2: {
        'id': 2,
        'name': 'CS201: Data Structures',
        'description': 'Advanced data structures and algorithms'
    },
    3: {
        'id': 3,
        'name': 'CS301: Database Systems',
        'description': 'Database design and SQL'
    }
}

# Mock materials for topics - using only the 5 files
MOCK_MATERIALS = {
    1: [1, 2],      # Topic 1 has files 1-2
    2: [3, 4],      # Topic 2 has files 3-4
    3: [5, 1, 3]    # Topic 3 has files 5,1,3
}

@app.context_processor
def inject_user():
    """Make current_user available in all templates"""
    return dict(current_user=MockUser(is_admin=True))

@app.route('/')
def index():
    """Redirect to main page"""
    return redirect(url_for('main_page'))

@app.route('/main-page')
def main_page():
    """Main page with topics"""
    return render_template('main_page.html')

@app.route('/topics/<int:topic_id>')
def topic_materials(topic_id):
    """Topic materials page"""
    return render_template('material.html', topic_id=topic_id)

@app.route('/api/topics/<int:topic_id>/materials')
def get_topic_materials(topic_id):
    """Get all materials for a topic"""
    if topic_id not in MOCK_MATERIALS:
        return jsonify({
            'topic': MOCK_TOPICS.get(topic_id, {
                'id': topic_id,
                'name': f'Topic {topic_id}',
                'description': 'Sample description'
            }),
            'materials': []
        })
    
    material_ids = MOCK_MATERIALS[topic_id]
    materials = []
    
    for mid in material_ids:
        file_data = next((f for f in MOCK_FILES if f['id'] == mid), None)
        if file_data:
            material = file_data.copy()
            material['material_id'] = mid * 100 + topic_id
            materials.append(material)
    
    return jsonify({
        'topic': MOCK_TOPICS.get(topic_id, {
            'id': topic_id,
            'name': f'Topic {topic_id}',
            'description': 'Sample description'
        }),
        'materials': materials
    })

@app.route('/api/archieves/available')
def get_available_files():
    """Get available files for adding to topic"""
    search = request.args.get('search', '').lower()
    
    available = []
    for file in MOCK_FILES:
        if search:
            if (search in file['name'].lower() or 
                search in file['filename'].lower() or 
                (file.get('description') and search in file['description'].lower())):
                available.append(file)
        else:
            available.append(file)  # Return all files when no search
    
    return jsonify({'files': available})

@app.route('/api/topics/<int:topic_id>/materials', methods=['POST'])
def add_materials(topic_id):
    """Add materials to topic"""
    data = request.get_json()
    file_ids = data.get('file_ids', [])
    
    return jsonify({
        'message': f'Successfully added {len(file_ids)} material(s)',
        'warning': None
    })

@app.route('/api/topics/<int:topic_id>/materials/<int:material_id>', methods=['DELETE'])
def remove_material(topic_id, material_id):
    """Remove material from topic"""
    return jsonify({'message': 'Material removed successfully'})

@app.route('/api/topics/<int:topic_id>/materials/reorder', methods=['POST'])
def reorder_materials(topic_id):
    """Reorder materials in topic"""
    return jsonify({'message': 'Order updated successfully'})

@app.route('/store/api/files/<int:file_id>/download')
def download_file(file_id):
    """Mock file download"""
    return jsonify({'message': f'Downloading file {file_id}'})

@app.route('/store/play/<int:file_id>')
def play_media(file_id):
    """Mock media playback"""
    file_info = next((f for f in MOCK_FILES if f['id'] == file_id), None)
    filename = file_info['filename'] if file_info else f'file_{file_id}'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Media Player</title>
        <style>
            body {{ 
                background: #111827; 
                color: white; 
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .player-container {{
                text-align: center;
                padding: 20px;
                background: rgba(30,30,40,0.9);
                border-radius: 15px;
                border: 2px dotted #3B82F6;
            }}
            .mock-player {{
                width: 600px;
                height: 300px;
                background: #1a1a2e;
                border-radius: 10px;
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
                gap: 20px;
                margin: 20px 0;
            }}
            .mock-player i {{
                font-size: 60px;
                color: #3B82F6;
            }}
            .btn {{
                background: linear-gradient(90deg, #3B82F6, #8B5CF6);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
            }}
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div class="player-container">
            <h2>Media Player</h2>
            <div class="mock-player">
                <i class="fas fa-play-circle"></i>
                <p>Playing: {filename}</p>
                <p class="text-sm text-gray-500">Mock media player for testing</p>
            </div>
            <button class="btn" onclick="window.close()">
                <i class="fas fa-times mr-2"></i> Close
            </button>
        </div>
    </body>
    </html>
    '''

@app.route('/mock-files/<path:filename>')
def mock_files(filename):
    """Serve mock files"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Preview</title>
        <style>
            body {{ 
                background: #111827; 
                color: white; 
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .preview-container {{
                text-align: center;
                padding: 30px;
                background: rgba(30,30,40,0.9);
                border-radius: 15px;
                border: 2px dotted #3B82F6;
                max-width: 500px;
            }}
            .preview-icon {{
                font-size: 60px;
                color: #3B82F6;
                margin-bottom: 20px;
            }}
            .filename {{
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 10px;
                word-break: break-word;
            }}
            .btn {{
                background: linear-gradient(90deg, #3B82F6, #8B5CF6);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                margin-top: 20px;
            }}
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div class="preview-container">
            <div class="preview-icon">
                <i class="fas fa-file"></i>
            </div>
            <div class="filename">{filename}</div>
            <p class="text-gray-400 mb-4">Mock file preview for testing</p>
            <button class="btn" onclick="window.close()">
                <i class="fas fa-times mr-2"></i> Close
            </button>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    
    print("="*60)
    print("MOCK FLASK APP READY!")
    print("="*60)
    print("\n📁 Setup Instructions:")
    print("1. Save your HTML as: templates/topic_materials.html")
    print("2. Run: python app.py")
    print("3. Open: http://localhost:5000/main-page")
    print("\n📊 Mock Data:")
    print("- 3 Topics available")
    print("- 5 Files to test with")
    print("- Admin features: ENABLED")
    print("\n🎯 Test these features:")
    print("✓ View materials")
    print("✓ Add materials (multi-select)")
    print("✓ Remove materials")
    print("✓ Drag & drop reordering")
    print("✓ File previews")
    print("✓ Media player")
    print("="*60)
    
    app.run(debug=True, port=5000)