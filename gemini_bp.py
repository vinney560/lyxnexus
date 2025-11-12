# gemini_bp.py
from flask import Blueprint, request, session, jsonify, render_template, Response, stream_with_context
from flask_login import current_user, login_required
from datetime import datetime, date, time
import requests
from datetime import timedelta
import json
import time
import random

# Create blueprint
gemini_bp = Blueprint('gemini', __name__, url_prefix='/gemini')

# API Keys and Model
API_KEYS = [
    'AIzaSyA3o8aKHTnVzuW9-qg10KjNy7Lcgn19N2I',
    'AIzaSyCq8-xrPTC40k8E_i3vXZ_-PR6RiPsuOno'
]
MODEL = "gemini-2.0-flash"

class AIConversationService:
    """
    Enhanced service for AI conversation management
    """
    
    def __init__(self, db_session):
        self.db = db_session
    
    def save_conversation(self, user_id, prompt, response, context='general', 
                         message_type='text', tokens_used=0, response_time=0.0,
                         api_model=None, was_successful=True, error_message=None):
        """Save conversation with enhanced tracking"""
        try:
            from app import AIConverse
            
            conversation = AIConverse(
                user_id=user_id,
                user_message=prompt,
                ai_response=response,
                context_used=context,
                message_type=message_type,
                tokens_used=tokens_used,
                response_time=response_time,
                api_model=api_model or MODEL,
                was_successful=was_successful,
                error_message=error_message
            )
            
            self.db.session.add(conversation)
            self.db.session.commit()
            
            print(f"✅ Conversation saved for user {user_id} (ID: {conversation.id})")
            return conversation.id
            
        except Exception as e:
            print(f"❌ Error saving conversation: {e}")
            self.db.session.rollback()
            return None
    
    def get_recent_conversation_history(self, user_id, limit=10):
        """Get user's most recent conversation history for AI context"""
        try:
            from app import AIConverse
            
            conversations = AIConverse.query.filter_by(
                user_id=user_id
            ).order_by(
                AIConverse.created_at.desc()
            ).limit(limit).all()
            
            return [conv.to_dict() for conv in conversations]
            
        except Exception as e:
            print(f"Error getting recent conversation history: {e}")
            return []
    
    def get_user_conversation_history(self, user_id, limit=20, offset=0):
        """Get user's conversation history with pagination"""
        try:
            from app import AIConverse
            
            conversations = AIConverse.query.filter_by(
                user_id=user_id
            ).order_by(
                AIConverse.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            return [conv.to_dict() for conv in conversations]
            
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    def get_conversation_by_id(self, conversation_id, user_id=None):
        """Get specific conversation by ID with optional user validation"""
        try:
            from app import AIConverse
            
            query = AIConverse.query.filter_by(id=conversation_id)
            if user_id:
                query = query.filter_by(user_id=user_id)
                
            conversation = query.first()
            return conversation.to_dict() if conversation else None
            
        except Exception as e:
            print(f"Error getting conversation: {e}")
            return None
    
    def get_conversation_stats(self, user_id=None):
        """Get conversation statistics"""
        try:
            from app import AIConverse
            from sqlalchemy import func
            
            stats = {}
            
            # Base query
            if user_id:
                base_query = AIConverse.query.filter_by(user_id=user_id)
            else:
                base_query = AIConverse.query
            
            # Basic counts
            stats['total_conversations'] = base_query.count()
            stats['successful_conversations'] = base_query.filter_by(was_successful=True).count()
            stats['failed_conversations'] = base_query.filter_by(was_successful=False).count()
            
            # Average response time
            avg_time = base_query.filter(
                AIConverse.response_time > 0
            ).with_entities(
                func.avg(AIConverse.response_time)
            ).scalar()
            stats['avg_response_time'] = round(avg_time or 0, 2)
            
            # Total tokens used
            total_tokens = base_query.with_entities(
                func.sum(AIConverse.tokens_used)
            ).scalar()
            stats['total_tokens_used'] = total_tokens or 0
            
            # Recent activity (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            stats['recent_conversations'] = base_query.filter(
                AIConverse.created_at >= week_ago
            ).count()
            
            return stats
            
        except Exception as e:
            print(f"Error getting conversation stats: {e}")
            return {}
    
    """Not yet implemented --> Don't Know how to do it"""
    def update_conversation_rating(self, conversation_id, user_id, rating):
        """Update user rating for a conversation"""
        try:
            from app import AIConverse
            
            conversation = AIConverse.query.filter_by(
                id=conversation_id, 
                user_id=user_id
            ).first()
            
            if conversation:
                conversation.user_rating = rating
                self.db.session.commit()
                return True
            return False
            
        except Exception as e:
            print(f"Error updating conversation rating: {e}")
            self.db.session.rollback()
            return False
    
    def delete_user_conversations(self, user_id):
        """Delete all conversations for a user"""
        try:
            from app import AIConverse
            
            deleted_count = AIConverse.query.filter_by(user_id=user_id).delete()
            self.db.session.commit()
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting user conversations: {e}")
            self.db.session.rollback()
            return 0

class ReadOnlyDatabaseQueryService:
    """
    Read-only version of DatabaseQueryService for user access
    Only allows SELECT queries and safe operations --> Since its Student BAsed AI
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.conversation_service = AIConversationService(db_session)
    
    def _get_model(self, model_name):
        """Safely get model class from current app context"""
        try:
            from app import User, Announcement, Assignment, Topic, Timetable, Message, File, TopicMaterial, AIConverse
            
            model_map = {
                'User': User,
                'Announcement': Announcement,
                'Assignment': Assignment,
                'Topic': Topic,
                'Timetable': Timetable,
                'Message': Message,
                'File': File,
                'TopicMaterial': TopicMaterial,
                'AIConverse': AIConverse
            }
            
            return model_map.get(model_name)
        except ImportError as e:
            print(f"Import error: {e}")
            # Fallback to direct import from app
            try:
                from app import User, Announcement, Assignment, Topic, Timetable, Message, File, TopicMaterial, AIConverse
                model_map = {
                    'User': User,
                    'Announcement': Announcement,
                    'Assignment': Assignment,
                    'Topic': Topic,
                    'Timetable': Timetable,
                    'Message': Message,
                    'File': File,
                    'TopicMaterial': TopicMaterial,
                    'AIConverse': AIConverse
                }
                return model_map.get(model_name)
            except ImportError as e2:
                print(f"Secondary import error: {e2}")
                return None
    
    def get_available_models(self):
        """Return models available for read-only access"""
        return ['User', 'Announcement', 'Assignment', 'Topic', 'Timetable', 'Message', 'File', 'TopicMaterial', 'AIConverse']
    
    def query_model_safe(self, model_name, filters=None, limit=10, order_by=None):
        """
        Safe read-only query with limited results
        """
        Model = self._get_model(model_name)
        if not Model:
            return {'error': f'Model {model_name} not found or not accessible'}
        
        query = Model.query
        
        # Apply basic filters (only equality and like for safety)
        if filters:
            for field, value in filters.items():
                if hasattr(Model, field):
                    if isinstance(value, dict) and 'like' in value:
                        query = query.filter(getattr(Model, field).ilike(f'%{value["like"]}%'))
                    else:
                        query = query.filter(getattr(Model, field) == value)
        
        # Apply ordering safely
        if order_by and hasattr(Model, order_by.lstrip('-')):
            if order_by.startswith('-'):
                query = query.order_by(getattr(Model, order_by[1:]).desc())
            else:
                query = query.order_by(getattr(Model, order_by).asc())
        
        # Limit results for safety
        items = query.limit(limit).all()
        
        return {
            'data': [self.serialize_item_safe(item) for item in items],
            'model': model_name,
            'count': len(items),
            'limit': limit
        }
    
    def serialize_item_safe(self, item):
        """Safe serialization - exclude sensitive data"""
        if not item:
            return None
        
        # Use to_dict method if available
        if hasattr(item, 'to_dict'):
            return item.to_dict()
        
        # Fallback to manual serialization
        result = {}
        
        for column in item.__table__.columns:
            if column.name in ['file_data', 'password', 'secret_key', 'token']:
                continue
                
            value = getattr(item, column.name)
            
            if isinstance(value, (datetime, date)):
                result[column.name] = value.isoformat()
            elif isinstance(value, time):
                result[column.name] = value.strftime('%H:%M:%S')
            elif isinstance(value, bytes):
                result[column.name] = f'<binary data {len(value)} bytes>'
            else:
                result[column.name] = value
        
        return result
    
    def get_public_stats(self):
        """Get public-facing statistics with actual content"""
        try:
            from app import User, Announcement, Assignment, Topic, Timetable

            # Fetch recent announcements (limit 5)
            recent_announcements = Announcement.query.order_by(
                Announcement.created_at.desc()
            ).limit(5).all()

            # Fetch recent assignments (limit 5)
            recent_assignments = Assignment.query.order_by(
                Assignment.created_at.desc()
            ).limit(5).all()

            # Fetch all topics (or limit if needed)
            topics = Topic.query.order_by(Topic.created_at.desc()).all()

            # Fetch all timetable entries (optional: limit by week/day)
            timetable_entries = Timetable.query.order_by(Timetable.created_at.desc()).all()

            stats = {
                'total_users': User.query.count(),
                'total_announcements': Announcement.query.count(),
                'total_assignments': Assignment.query.count(),
                'total_topics': Topic.query.count(),
                'total_timetable_entries': Timetable.query.count(),

                'recent_announcements': [
                    {
                        'id': a.id,
                        'title': a.title,
                        'content': a.content,
                        'created_at': a.created_at.isoformat(),
                        'has_file': a.has_file(),
                        'file_url': a.get_file_url()
                    } for a in recent_announcements
                ],

                'recent_assignments': [
                    {
                        'id': assn.id,
                        'title': assn.title,
                        'description': assn.description,
                        'due_date': assn.due_date.isoformat() if assn.due_date else None,
                        'created_at': assn.created_at.isoformat(),
                        'topic': assn.topic.name if assn.topic else None,
                        'has_file': bool(assn.file_data),
                        'file_name': assn.file_name
                    } for assn in recent_assignments
                ],

                'topics': [
                    {
                        'id': t.id,
                        'name': t.name,
                        'description': t.description,
                        'created_at': t.created_at.isoformat(),
                        'assignments_count': len(t.assignments)
                    } for t in topics
                ],

                'timetable': [
                    {
                        'id': tt.id,
                        'day_of_week': tt.day_of_week,
                        'start_time': tt.start_time.isoformat(),
                        'end_time': tt.end_time.isoformat(),
                        'subject': tt.subject,
                        'room': tt.room,
                        'teacher': tt.teacher,
                        'topic': tt.topic.name if tt.topic else None
                    } for tt in timetable_entries
                ]
            }

            return stats

        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}

    def get_user_conversation_history(self, user_id, limit=20):
        """Get user's conversation history using the enhanced service"""
        return self.conversation_service.get_user_conversation_history(user_id, limit)
    
    def get_recent_conversation_history(self, user_id, limit=10):
        """Get user's recent conversation history for AI context"""
        return self.conversation_service.get_recent_conversation_history(user_id, limit)
    
    def save_conversation(self, user_id, prompt, response, **kwargs):
        """Save conversation using the enhanced service"""
        return self.conversation_service.save_conversation(
            user_id, prompt, response, **kwargs
        )

def get_gemini_response(prompt, history, user_context=None):
    """Get response from Gemini API with smart conversation continuity"""
    start_time = time.time()
    
    # Smart history processing - focus on maintaining conversation flow
    conversation_context = ""
    if history:
        # Always take the last 3 exchanges (6 messages) for context
        recent_history = history[-6:]  # Last 3 user-assistant pairs
        
        # Build context with clear conversation flow
        for i in range(0, len(recent_history), 2):
            if i < len(recent_history):
                user_msg = recent_history[i]
                ai_msg = recent_history[i+1] if i+1 < len(recent_history) else ""
                conversation_context += f"User: {user_msg}\nAssistant: {ai_msg}\n"
    
    # Smart prompt that maintains conversation continuity
    smart_prompt = f"""You are Marion, an AI assistant for LyxNexus educational platform.

CONVERSATION CONTEXT (Last 3 exchanges):
{conversation_context if conversation_context else 'No recent conversation'}

CURRENT USER MESSAGE: {prompt}

CONVERSATION FLOW RULES:
1. **CONTINUITY FIRST**: If the current message continues the recent conversation, maintain that topic naturally
2. **TOPIC TRANSITIONS**: If the user changes topic, smoothly transition without mentioning the shift
3. **FOLLOW-UP HANDLING**: Treat "yes", "no", "continue" as direct responses to the most recent exchange
4. **CONTEXT AWARENESS**: Use the conversation history to understand references and context
5. **NATURAL FLOW**: Respond as if you naturally remember the recent conversation

SPECIFIC SCENARIO GUIDANCE:
- If user says "yes"/"no" to a recent suggestion: Continue with that suggestion
- If user asks a follow-up question: Answer in context of recent discussion  
- If user starts new topic: Address it directly while maintaining conversational flow
- If user refers to something from earlier: Connect it naturally without explicit references
- If user gives an explicit command or requirement adhire and respond naturally

RESPONSE REQUIREMENTS:
- Answer the current message directly and naturally
- Maintain conversation continuity when appropriate
- Never say "going back to" or "returning to previous topic"
- Never explicitly acknowledge topic changes
- Never mention conversation history or context
- Be concise and directly helpful
- If user request for a code, respond with valid code format and syntax that are correct and runnable
- Avoid using symbols like "<>", "**", "[]", or any symbols in responses to show URLs, Links, emphasis, or references. For Links or URLs, add a space at the end then "-->".

' ==============================================================
' AI MARKDOWN-LIKE FORMAT GUIDE
' ==============================================================

' [TEXT EMPHASIS]
' "_"text"_"                  → italics
' "*"text"*" or "**"text"**"  → bold
' "~~"text"~~"                → strikethrough
' "__"text"__"                → underline
' "=="text"=="                → highlight

' [SCIENTIFIC NOTATION]
' "~"text"~"                  → subscript
' "^"text"^"                  → superscript

' [CODE FORMATTING]
' "`"code"`"                  → inline code and code block 
' Example of a code block:

#python --> to show language
def hello_world():
    print("Hello, world!")
#output: Hello world --> (#)comments inside the code to prevent syntax error. in javascript use // and in others use relevant

' Keep syntax highlighting based on the language specified
' If no language is given, treat as plain code

' [HEADERS & STRUCTURE]
' "# text"                    → level 1 header
' "## text"                   → level 2 header
' "### text"                  → level 3 header

' [LISTS & ORGANIZATION]
' "- text", "* text", "+ text" → unordered list item
' "1. text", "2. text"        → ordered list item
' "> text"                    → blockquote
' Consecutive list items should be grouped together

' [VISUAL ELEMENTS]
' "---", "***", or "___"      → horizontal line

' [TABLES]
' "| header1 | header2 |"     → table header
' "|---------|---------|"     → header separator
' "| data1   | data2   |"     → table row
' Tables should have consistent column counts
' Example of a table: 

Here's a comparison of different AI models:

| Model | Company | Parameters | Best Use Case |
|-------|---------|------------|---------------|
| GPT-4 | OpenAI | 1.7T | General purpose, reasoning |
| Claude 3 | Anthropic | Unknown | Document analysis, ethics |
| Gemini Pro | Google | Unknown | Multimodal tasks, integration |
| Llama 2 | Meta | 70B | Open-source, research |
| Mixtral | Mistral AI | 47B | Multilingual, efficient |

' [LINE BREAKS]
' Each "\n" (newline) represents a line break

'==============================================================
'[MATH & SCIENTIFIC RENDERING & FORMATS]
'==============================================================
'
' Instructions for AI:
' 
' 1. Solve the math/science problem given.
' 2. Output **only LaTeX-ready math**, formatted for KaTeX.
' 3. Do **not** wrap expressions in `$...$` or `$$...$$`.
' 4. Do **not** escape characters or double backslashes.
' 5. Input may contain `^` for superscripts and `~` for subscripts; preserve them as-is.
' 6. Inline and display math can be written naturally using LaTeX syntax (e.g., \frac, \sqrt, \int, etc.).
' 7. Do **not** output plain text equations — all math should be in proper LaTeX format.
' 8. Avoid explanations outside the equations unless explicitly asked.
' 9. Rendering engines like KaTeX will interpret the output automatically in the chat.
' 
' Example input: "Solve x^2 - 5x + 6 = 0"
' 
' Example AI output:
' 
' x^2 - 5x + 6 = 0
' 
' x = \frac{-(-5) \pm \sqrt{(-5)^2 - 4(1)(6)}}{2(1)}
' 
' x = \frac{5 \pm \sqrt{25 - 24}}{2}
' 
' x = \frac{5 \pm 1}{2}
' 
' Solutions:
' 
' x = 3  or  x = 2

' ==============================================================
' [NOTES FOR AI]
' ==============================================================
' 1. Read from top to bottom — handle complex patterns (like code blocks) first.
' 2. Keep all original text content unchanged.
' 3. Apply formatting logically, not visually.
' 4. Unknown patterns should remain as-is.
' 5. Do not output HTML or styling, only meaning-based formatting.
' 6. Ensure code blocks are syntactically correct and runnable.
' 7. Use user preferences for formatting if requested or given.
' ==============================================================

PLATFORM CONTEXT:
**Only give the site URL if user asks for it**
- LyxNexus has: announcements, assignments, topics, files, messages, timetable, profile, specific file(s) for Course Unit Materials or Assignment
- LyxNexus URL: https://lyxnexus.onrender.com
- LyxNexus Main Page URL: https://lyxnexus.onrender.com/main-page - contains Announcements, Upcoming Assignments, Messages button, Files button, Profile and Timetable overview located on the top in desktop and on the scrollable section on the bottom in mobile.
- LyxNexus Files Page URL: https://lyxnexus.onrender.com/files - for managing Course Unit Materials and all available files related to all Units or Topics.
- LyxNexus is an educational platform for managing course Units, assignments, Course Units Materials, Announcements, and communications.
- LyxNexus support: vincentkipngetich479@gmail.com or +254740694312 for WhatsApp or Contant
- Current user: Username: {current_user.username}, ID: {current_user.id}, Mobile: {current_user.mobile}, Admin Status: {current_user.is_admin}, Member Since: {current_user.created_at}
- Time: {(datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')} EAT

"Refer User only by his or her Username, if asked about account details you can disclose the other user details"
"You have access to real-time internet search via Google Search to get the latest information when needed. Use this capability to provide current, up-to-date answers about recent events, news, weather, or any topics that require current information beyond the LyxNexus platform data."

BACKGROUND AND ORIGIN:
- You were built by Vincent Kipngetich nicknamed "Lyxin" who is your creator, maintainer and developer. Refer him as Lyxin
- You are from LyxNexus educational platform branch of Main LyxLab Intelligence.
- You are designed to assist users in navigating and utilizing the LyxNexus platform effectively.
Now respond naturally to the user's current message:"""
    
    # Add platform data context when relevant to current conversation
    try:
        from app import db
        db_service = ReadOnlyDatabaseQueryService(db)
        stats = db_service.get_public_stats()
        
        # Check if current conversation is about platform content
        current_topic = ""
        if history:
            # Analyze recent conversation to detect topic - EXPANDED KEYWORDS
            recent_text = " ".join(history[-4:]).lower()
            if any(word in recent_text for word in ['assignment', 'homework', 'due', 'submit', 'task', 'work']):
                current_topic = "assignments"
            elif any(word in recent_text for word in ['announcement', 'news', 'update', 'new', 'recent', 'latest']):
                current_topic = "announcements" 
            elif any(word in recent_text for word in ['topic', 'course', 'lesson', 'unit', 'subject']):
                current_topic = "topics"
            elif any(word in recent_text for word in ['timetable', 'schedule', 'class', 'lecture', 'time']):
                current_topic = "timetable"
        
        # Add relevant platform data based on conversation topic
        if current_topic and stats:
            platform_context = f"\nCurrent Platform Status:\n"
            if current_topic == "assignments" and stats.get('recent_assignments'):
                platform_context += f"- Recent assignments: {len(stats['recent_assignments'])} available\n"
                for assn in stats['recent_assignments'][:3]:  # Show 3 items
                    platform_context += f"  * {assn.get('title', '')}: {assn.get('description', '')} (Due: {assn.get('due_date', '')})\n"
            elif current_topic == "announcements" and stats.get('recent_announcements'):
                platform_context += f"- Recent announcements: {len(stats['recent_announcements'])} available\n"
                for ann in stats['recent_announcements'][:3]:  # Show 3 items with CONTENT
                    platform_context += f"  * {ann.get('title', '')}: {ann.get('content', '')}\n"
            
            enhanced_prompt = platform_context + smart_prompt
        else:
            # Always include basic platform overview even if no specific topic detected
            platform_context = f"\nPlatform Overview:\n"
            platform_context += f"- Total announcements: {stats.get('total_announcements', 0)}\n"
            platform_context += f"- Total assignments: {stats.get('total_assignments', 0)}\n"
            platform_context += f"- Total topics: {stats.get('total_topics', 0)}\n"
            enhanced_prompt = platform_context + smart_prompt
    except Exception as e:
        print(f"Database context error: {e}")
        enhanced_prompt = smart_prompt
    
    # Prepare API request with focused history
    contents = []
    
    # Add only the last 3 exchanges to maintain context without overload
    if history:
        recent_exchanges = history[-6:]  # Last 3 complete exchanges
        for i in range(0, len(recent_exchanges), 2):
            if i < len(recent_exchanges):
                contents.append({"role": "user", "parts": [{"text": recent_exchanges[i]}]})
                if i + 1 < len(recent_exchanges):
                    contents.append({"role": "model", "parts": [{"text": recent_exchanges[i + 1]}]})
    
    # Add current smart prompt
    contents.append({"role": "user", "parts": [{"text": enhanced_prompt}]})
    
    # Use standard API
    for api_key in API_KEYS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            },
            "tools": [{"google_search": {}}]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and data['candidates']:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Clean response - remove any meta-commentary about conversation flow
                    lines = text.split('\n')
                    clean_lines = []
                    for line in lines:
                        # Remove lines that break conversation flow
                        if not any(phrase in line.lower() for phrase in [
                            'going back to', 'returning to', 'as we were discussing',
                            'previously we talked', 'earlier you asked', 'regarding your previous'
                        ]):
                            clean_lines.append(line)
                    
                    clean_text = '\n'.join(clean_lines).strip()
                    
                    # Estimate token usage
                    tokens_used = len(clean_text.split()) + len(prompt.split())
                    
                    return {
                        'text': clean_text,
                        'tokens_used': tokens_used,
                        'response_time': response_time,
                        'success': True
                    }
                else:
                    print(f"No candidates in response: {data}")
            else:
                print(f"API key {api_key[:10]}... failed with status: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"API key {api_key[:10]}... failed: {e}")
            continue
    
    return {
        'text': "I'm currently experiencing technical difficulties. Please try again in a moment.",
        'tokens_used': 0,
        'response_time': time.time() - start_time,
        'success': False
    }

def simulate_streaming(text, base_delay=0.03):
    """Optimized streaming that preserves spaces and feels natural"""
    if not text:
        return
    
    words = text.split(' ')
    i = 0
    
    while i < len(words):
        # Calculate how many words to include in this chunk (1-3 words)
        words_in_chunk = min(random.randint(1, 3), len(words) - i)
        
        # Get the chunk of words
        chunk_words = words[i:i + words_in_chunk]
        chunk = ' '.join(chunk_words)
        
        # Add space if not the last chunk
        if i + words_in_chunk < len(words):
            chunk += ' '
        
        yield chunk
        
        # Variable delay based on chunk size and punctuation
        delay = base_delay * len(chunk) * random.uniform(0.8, 1.2)
        
        # Check for punctuation in the last word of chunk
        last_word = chunk_words[-1] if chunk_words else ''
        if last_word and last_word[-1] in '.!?':
            delay *= 2.5  # Longer pause at sentence endings
        elif last_word and last_word[-1] in ',;:':
            delay *= 1.5  # Slightly longer pause at commas
            
        time.sleep(delay)
        i += words_in_chunk

def generate_stream(prompt, history, user_context):
    """Generate streaming response with persistent memory from DB"""
    try:
        from app import db
        db_service = ReadOnlyDatabaseQueryService(db)

        # Always reload recent history from DB for fresh context
        db_history = db_service.get_recent_conversation_history(
            user_id=current_user.id, 
            limit=10  # Only get recent 10 conversations for context
        )
        
        # Build fresh history from recent DB conversations
        fresh_history = []
        for conv in reversed(db_history):  # Reverse to get chronological order
            fresh_history.append(conv['user_message'])
            fresh_history.append(conv['ai_response'])

        print(f"Loaded {len(fresh_history)//2} recent conversations from DB for context")

        # Get full response from Gemini
        response_data = get_gemini_response(prompt, fresh_history, user_context)
        full_response = response_data['text']

        if not full_response:
            yield "data: ❌ Failed to get response from AI service.\n\n"
            return

        # Save conversation to database
        try:
            conversation_id = db_service.save_conversation(
                user_id=current_user.id,
                prompt=prompt,
                response=full_response,
                tokens_used=response_data.get('tokens_used', 0),
                response_time=response_data.get('response_time', 0),
                was_successful=response_data.get('success', True)
            )
            print(f"✅ Conversation saved (ID: {conversation_id})")
        except Exception as e:
            print(f"❌ Failed to save conversation: {e}")

        # Clear session history and reload with fresh data including new response
        session.pop('gemini_history', None)
        
        # Reload updated history from DB for next interaction
        updated_history = db_service.get_recent_conversation_history(
            user_id=current_user.id, 
            limit=10
        )
        
        # Update session with fresh history
        session['gemini_history'] = []
        for conv in updated_history:
            session['gemini_history'].append(conv['user_message'])
            session['gemini_history'].append(conv['ai_response'])
        
        session.modified = True

        # Stream response in chunks
        for chunk in simulate_streaming(full_response):
            yield f"data: {chunk}\n\n"

        print(f"Session reloaded with fresh history. Total exchanges: {len(session['gemini_history']) // 2}")

    except Exception as e:
        print(f"Streaming error: {e}")
        yield "data: ❌ An error occurred while generating the response.\n\n"

@gemini_bp.route('/')
@login_required
def gemini_chat():
    """Render the Gemini chat interface with streaming and history"""
    from app import db
    db_service = ReadOnlyDatabaseQueryService(db)

    # Load conversation history from database (latest 20)
    conversation_history = db_service.get_user_conversation_history(
        user_id=current_user.id,
        limit=20
    )

    # Always reload session with fresh DB data
    session.pop('gemini_history', None)
    session['gemini_history'] = []
    for conv in conversation_history:
        session['gemini_history'].append(conv['user_message'])
        session['gemini_history'].append(conv['ai_response'])
    session.modified = True

    # Format text function for server-side formatting
    def format_text(text):
        """Format text using custom markdown-like syntax with math-safe rendering."""
        import re
    
        formatted = text
    
        # Code blocks with language
        formatted = re.sub(
            r'```(\w+)?\n([\s\S]*?)```',
            lambda m: f'<pre data-language="{m.group(1) or "text"}"><code>{m.group(2).strip()}</code></pre>',
            formatted
        )
    
        # Inline code
        formatted = re.sub(r'`([^`]+)`', r'<code>\1</code>', formatted)
    
        # Headers
        formatted = re.sub(r'^### (.*$)', r'<h3>\1</h3>', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^## (.*$)', r'<h2>\1</h2>', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^# (.*$)', r'<h1>\1</h1>', formatted, flags=re.MULTILINE)
    
        # Bold / Italic / Underline / Highlight / Strikethrough
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)
        formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
        formatted = re.sub(r'_(.*?)_', r'<em>\1</em>', formatted)
        formatted = re.sub(r'__(.*?)__', r'<span class="underline">\1</span>', formatted)
        formatted = re.sub(r'==(.*?)==', r'<span class="highlight">\1</span>', formatted)
        formatted = re.sub(r'~~(.*?)~~', r'<span class="strikethrough">\1</span>', formatted)
    
        # Blockquotes
        formatted = re.sub(r'^> (.*$)', r'<blockquote>\1</blockquote>', formatted, flags=re.MULTILINE)
    
        # Horizontal rules
        formatted = re.sub(r'^(?:\*\*\*|---|___)$', r'<hr>', formatted, flags=re.MULTILINE)
    
        # Lists
        formatted = re.sub(r'^\s*[-*+] (.*$)', r'<li>\1</li>', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^\s*\d+\. (.*$)', r'<li>\1</li>', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', formatted, flags=re.DOTALL)
    
        # Tables
        def format_table(match):
            row = match.group(1)
            cells = [cell.strip() for cell in row.split('|') if cell.strip()]
            if len(cells) > 1:
                table_html = '<table><tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr></table>'
                return table_html
            return match.group(0)
    
        formatted = re.sub(r'\|(.+)\|', format_table, formatted)
    
        # Math-safe: subscripts and superscripts
        # Do not escape math syntax (^ or ~); wrap them lightly for CSS/MathJax/KaTeX rendering.
        formatted = re.sub(r'~(.+?)~', r'<span class="subscript">\1</span>', formatted)
        formatted = re.sub(r'\^(.+?)\^', r'<span class="superscript">\1</span>', formatted)
    
        # Line breaks
        formatted = formatted.replace('\n', '<br>')
    
        # URLs
        formatted = re.sub(
            r'(https?://[^\s]+)',
            r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
            formatted
        )
    
        # Prevent escaping math or special characters — let KaTeX/MathJax handle inline math
        # Example: y^3 + 8y - 15 = 0 should remain as-is
        return formatted

    # Generate HTML for main chat with formatting
    history_html = ""
    for conv in reversed(conversation_history):  # newest first
        try:
            timestamp = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
            time_str = timestamp.strftime('%H:%M')
        except:
            time_str = "Just now"

        # Format AI response
        formatted_ai_response = format_text(conv['ai_response'])

        history_html += f'''
        <div class="message user-message">
            <div class="message-content">
                {conv['user_message']}
                <div class="message-time">{time_str}</div>
            </div>
        </div>
        <div class="message ai-message" data-prompt="{conv['user_message'].replace('"', '&quot;')}">
            <div class="message-content">
                <div class="formatted-text">{formatted_ai_response}</div>
                <div class="message-time">{time_str}</div>
                <div class="message-actions">
                    <button class="message-action copy-button" title="Copy response">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                    <button class="message-action regenerate-button" title="Regenerate response">
                        <i class="fas fa-redo"></i> Regenerate
                    </button>
                </div>
            </div>
        </div>
        '''

    # Sidebar history
    sidebar_history_html = ""
    for conv in conversation_history:
        try:
            timestamp = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
            time_str = timestamp.strftime('%H:%M')
        except:
            time_str = "Just now"

        prompt_preview = conv['user_message'][:60] + "..." if len(conv['user_message']) > 60 else conv['user_message']

        sidebar_history_html += f'''
        <div class="history-item" data-conv-id="{conv['id']}">
            <div class="history-prompt">{prompt_preview}</div>
            <div class="history-time">{time_str}</div>
        </div>
        '''

    return render_template('ai_assist.html',
        current_user=current_user,
        history_html=history_html,
        sidebar_history_html=sidebar_history_html
    )

@gemini_bp.route('/stream')
@login_required
def gemini_stream():
    """Streaming endpoint for Gemini responses"""
    prompt = request.args.get('prompt', '').strip()
    
    if not prompt:
        return Response("data: ❌ Error: Empty prompt\n\n", mimetype='text/event-stream')
    
    print(f"Starting stream for prompt: {prompt[:50]}...")
    
    # Get user context
    user_context = {
        'user_id': current_user.id,
        'username': current_user.username,
        'is_admin': current_user.is_admin
    }
    
    # Always use fresh history from session (reloaded in generate_stream)
    history = session.get('gemini_history', [])
    
    return Response(
        stream_with_context(generate_stream(prompt, history, user_context)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@gemini_bp.route('/get-conversation/<int:conv_id>')
@login_required
def get_conversation(conv_id):
    """Get specific conversation by ID"""
    try:
        from app import AIConverse
        
        conversation = AIConverse.query.filter_by(
            id=conv_id, 
            user_id=current_user.id
        ).first()
        
        if conversation:
            # Format timestamp for display
            try:
                timestamp = conversation.created_at.strftime('%H:%M') if conversation.created_at else "Just now"
            except:
                timestamp = "Just now"
                
            return jsonify({
                'success': True,
                'conversation': {
                    'id': conversation.id,
                    'prompt': conversation.user_message,
                    'response': conversation.ai_response,
                    'timestamp': timestamp,
                    'created_at': conversation.created_at.isoformat() if conversation.created_at else None
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Conversation not found'}), 404
            
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return jsonify({'success': False, 'error': 'Failed to load conversation'}), 500

@gemini_bp.route('/rate-conversation/<int:conv_id>', methods=['POST'])
@login_required
def rate_conversation(conv_id):
    """Rate a conversation (1-5 stars)"""
    try:
        data = request.get_json()
        if not data or 'rating' not in data:
            return jsonify({'success': False, 'error': 'No rating provided'}), 400
            
        rating = data.get('rating')
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
        
        from app import db
        conversation_service = AIConversationService(db)
        
        success = conversation_service.update_conversation_rating(
            conversation_id=conv_id,
            user_id=current_user.id,
            rating=rating
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Conversation rated {rating} stars successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Conversation not found or access denied'}), 404
            
    except Exception as e:
        print(f"Error rating conversation: {e}")
        return jsonify({'success': False, 'error': 'Failed to rate conversation'}), 500

@gemini_bp.route('/stats')
@login_required
def get_conversation_stats():
    """Get conversation statistics for the current user"""
    try:
        from app import db
        conversation_service = AIConversationService(db)
        
        user_stats = conversation_service.get_conversation_stats(user_id=current_user.id)
        global_stats = conversation_service.get_conversation_stats()
        
        return jsonify({
            'success': True,
            'user_stats': user_stats,
            'global_stats': global_stats
        })
        
    except Exception as e:
        print(f"Error getting conversation stats: {e}")
        return jsonify({'success': False, 'error': 'Failed to load statistics'}), 500

@gemini_bp.route('/chat', methods=['POST'])
@login_required
def gemini_chat_api():
    """Fallback non-streaming endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Empty prompt'}), 400
        
        # Get user context
        user_context = {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin
        }
        
        # Always reload fresh history from DB
        from app import db
        db_service = ReadOnlyDatabaseQueryService(db)
        db_history = db_service.get_recent_conversation_history(
            user_id=current_user.id, 
            limit=10
        )
        
        fresh_history = []
        for conv in reversed(db_history):
            fresh_history.append(conv['user_message'])
            fresh_history.append(conv['ai_response'])
        
        # Get response
        response_data = get_gemini_response(prompt, fresh_history, user_context)
        full_response = response_data['text']
        
        if full_response:
            # Save to database with enhanced tracking
            try:
                conversation_id = db_service.save_conversation(
                    user_id=current_user.id,
                    prompt=prompt,
                    response=full_response,
                    tokens_used=response_data.get('tokens_used', 0),
                    response_time=response_data.get('response_time', 0),
                    was_successful=response_data.get('success', True)
                )
            except Exception as e:
                print(f"Failed to save conversation: {e}")
            
            # Clear and reload session with fresh data
            session.pop('gemini_history', None)
            updated_history = db_service.get_recent_conversation_history(
                user_id=current_user.id, 
                limit=10
            )
            
            session['gemini_history'] = []
            for conv in updated_history:
                session['gemini_history'].append(conv['user_message'])
                session['gemini_history'].append(conv['ai_response'])
            
            session.modified = True
            
            return jsonify({
                'success': True,
                'response': full_response,
                'history_length': len(session['gemini_history']),
                'conversation_id': conversation_id,
                'response_time': response_data.get('response_time', 0),
                'tokens_used': response_data.get('tokens_used', 0)
            })
        else:
            return jsonify({'success': False, 'error': 'Service unavailable'}), 503
        
    except Exception as e:
        print(f"Gemini chat error: {e}")
        return jsonify({'success': False, 'error': 'Failed to process request'}), 500

@gemini_bp.route('/clear-history')
@login_required
def clear_chat_history():
    """Clear the chat history from both session and database"""
    try:
        # Clear session history
        session.pop('gemini_history', None)
        
        # Clear database history
        from app import db
        conversation_service = AIConversationService(db)
        deleted_count = conversation_service.delete_user_conversations(current_user.id)
        
        return jsonify({
            'success': True, 
            'message': f'Chat history cleared ({deleted_count} conversations deleted)'
        })
    except Exception as e:
        print(f"Error clearing history: {e}")
        return jsonify({'success': False, 'error': 'Failed to clear history'}), 500

@gemini_bp.route('/get-history')
@login_required
def get_conversation_history():
    """Get user's conversation history"""
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        from app import db
        conversation_service = AIConversationService(db)
        conversations = conversation_service.get_user_conversation_history(
            user_id=current_user.id, 
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'conversations': conversations,
            'total': len(conversations)
        })
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return jsonify({'success': False, 'error': 'Failed to load history'}), 500

@gemini_bp.route('/status')
@login_required
def status():
    """Get chat status with enhanced statistics"""
    history = session.get('gemini_history', [])
    
    # Get database statistics
    try:
        from app import db
        conversation_service = AIConversationService(db)
        stats = conversation_service.get_conversation_stats(user_id=current_user.id)
        db_count = stats.get('total_conversations', 0)
    except:
        db_count = 0
    
    return jsonify({
        'history_length': len(history),
        'exchanges': len(history) // 2,
        'database_conversations': db_count,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin
        },
        'stats': stats
    })

print("✅ Enhanced Gemini Blueprint loaded successfully!")
print("🔑 API Keys configured:", len(API_KEYS))
print("🤖 Model:", MODEL)
print("🚀 Enhanced Gemini Blueprint is ready to use!")