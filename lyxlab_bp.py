from flask import Blueprint, render_template, jsonify

# Use Blueprint, not Flask
lyxlab_bp = Blueprint('lyxlab', __name__, url_prefix='/lyx-lab')

# Fixed projects dictionary with unique keys
projects = {
    'https://t-give-3.onrender.com/': {
        'name': 'T-Give Nexus',
        'credentials': {
            'mobile': '0795073922',
            'password': '1234'
        },
        'status': 'active'
    },
    'https://viewtv.viewtv.gt.tc': {
        'name': 'View Tv',
        'credentials': {
            'email': 'vinneyjoy1@gmail.com',
            'password': '2007'
        },
        'status': 'active'
    },
    'https://lyxspace.onrender.com': {
        'name': 'LyxSpace',
        'credentials': {
            'username': 'Lyxin',
            'mobile': '0112167195'
        },
        'status': 'active'
    },
    'https://lyxnexus.xo.je': {
        'name': 'LyxNexus',
        'credentials': {
            'username': 'LyxNexus',
            'mobile': '0795959595'
        },
        'status': 'active'
    },
    'https://lyxnexus.onrender.com/gemini/': {
        'name': 'LyxAI',
        'credentials': {
            'username': 'LyxNexus',
            'mobile': '0740694311'
        },
        'status': 'active'
    },
    'tonnymusic': {  
        'name': 'TonnyMusic',
        'credentials': None,
        'status': 'planned',
        'description': 'Music streaming platform - Owned now by a friend'
    },
    'examroom': {  
        'name': 'Exam Room',
        'credentials': None,
        'status': 'planned',
        'description': 'Sophisticated and Comprehensive Test platform!'
    },
    'lyxwifi': {  
        'name': 'LyxWifi',
        'credentials': None,
        'status': 'development',
        'description': 'Local WiFi management system - Currently in development & Private'
    },
    'https://lyxnexus.onrender.com/lyxpinger/': {  
        'name': 'LyxPinger',
        'credentials': None,
        'status': 'active',
        'description': 'Currently being integrated with LyxLab - LyxPinger'
    },
    'https://lyxnexus.onrender.com/test/web-scraper': {  
        'name': 'LyxWebScraper',
        'credentials': None,
        'status': 'active',
        'description': 'Currently being integrated with LyxLab - LyxWebScraper'
    },
}

@lyxlab_bp.route('/')
def lyxlab_home():
    """
    Returns the LyxLab homepage
    """
    return render_template('lyxlab.html')

@lyxlab_bp.route('/data/projects')
def data_projects():
    """
    API endpoint to get projects data as JSON
    """
    return jsonify(projects)