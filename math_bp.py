# math.py
from flask import Blueprint, request, session, jsonify, Response, stream_with_context
from flask_login import current_user, login_required
from datetime import datetime, date, time
import requests
from datetime import timedelta
import json
import time
import random

# Create blueprint
math_bp = Blueprint('math', __name__, url_prefix='/math')

# API Keys and Model
API_KEYS = [
    'AIzaSyA3o8aKHTnVzuW9-qg10KjNy7Lcgn19N2I',
    'AIzaSyCq8-xrPTC40k8E_i3vXZ_-PR6RiPsuOno'
]
MODEL = "gemini-2.0-flash"

class MathAssignmentService:
    """
    Service for math assignment management and AI assistance
    """
    
    def __init__(self, db_session):
        self.db = db_session
    
    def get_assignment_by_id(self, assignment_id):
        """Get assignment by ID with full details"""
        try:
            from app import Assignment, Topic
            
            assignment = Assignment.query.filter_by(id=assignment_id).first()
            if assignment:
                # Convert to dict with all details
                assignment_data = {
                    'id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description,
                    'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                    'created_at': assignment.created_at.isoformat() if assignment.created_at else None,
                    'file_name': assignment.file_name,
                    'file_type': assignment.file_type,
                    'topic_id': assignment.topic_id,
                    'user_id': assignment.user_id,
                    'has_file': bool(assignment.file_data)
                }
                
                # Add topic info if available
                if assignment.topic_id:
                    topic = Topic.query.filter_by(id=assignment.topic_id).first()
                    if topic:
                        assignment_data['topic_name'] = topic.name
                        assignment_data['topic_description'] = topic.description
                
                return assignment_data
            return None
            
        except Exception as e:
            print(f"Error getting assignment: {e}")
            return None
    
    def get_user_assignments(self, user_id=None, limit=50):
        """Get assignments with optional user filter"""
        try:
            from app import Assignment, Topic
            
            query = Assignment.query
            
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            assignments = query.order_by(
                Assignment.created_at.desc()
            ).limit(limit).all()
            
            result = []
            for assignment in assignments:
                assignment_data = {
                    'id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description,
                    'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                    'created_at': assignment.created_at.isoformat() if assignment.created_at else None,
                    'file_name': assignment.file_name,
                    'file_type': assignment.file_type,
                    'topic_id': assignment.topic_id,
                    'user_id': assignment.user_id,
                    'has_file': bool(assignment.file_data)
                }
                
                # Add topic info if available
                if assignment.topic_id:
                    topic = Topic.query.filter_by(id=assignment.topic_id).first()
                    if topic:
                        assignment_data['topic_name'] = topic.name
                        assignment_data['topic_description'] = topic.description
                
                result.append(assignment_data)
            
            return result
            
        except Exception as e:
            print(f"Error getting assignments: {e}")
            return []
    
    def get_assignments_by_topic(self, topic_id):
        """Get assignments for a specific topic"""
        try:
            from app import Assignment, Topic
            
            assignments = Assignment.query.filter_by(
                topic_id=topic_id
            ).order_by(
                Assignment.created_at.desc()
            ).all()
            
            result = []
            for assignment in assignments:
                assignment_data = {
                    'id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description,
                    'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                    'created_at': assignment.created_at.isoformat() if assignment.created_at else None,
                    'file_name': assignment.file_name,
                    'file_type': assignment.file_type,
                    'topic_id': assignment.topic_id,
                    'user_id': assignment.user_id,
                    'has_file': bool(assignment.file_data)
                }
                
                result.append(assignment_data)
            
            return result
            
        except Exception as e:
            print(f"Error getting assignments by topic: {e}")
            return []
    
    def save_math_conversation(self, user_id, prompt, response, assignment_id=None, 
                             context='math_assignment', tokens_used=0, response_time=0.0,
                             was_successful=True, error_message=None):
        """Save math assignment conversation"""
        try:
            from app import AIConverse
            
            conversation = AIConverse(
                user_id=user_id,
                user_message=prompt,
                ai_response=response,
                context_used=context,
                message_type='math_assistance',
                tokens_used=tokens_used,
                response_time=response_time,
                api_model=MODEL,
                was_successful=was_successful,
                error_message=error_message
            )
            
            self.db.session.add(conversation)
            self.db.session.commit()
            
            print(f"✅ Math conversation saved for user {user_id} (Assignment ID: {assignment_id})")
            return conversation.id
            
        except Exception as e:
            print(f"❌ Error saving math conversation: {e}")
            self.db.session.rollback()
            return None
    
    def get_math_conversation_history(self, user_id, limit=20):
        """Get user's math-related conversation history"""
        try:
            from app import AIConverse
            
            conversations = AIConverse.query.filter_by(
                user_id=user_id,
                context_used='math_assignment'
            ).order_by(
                AIConverse.created_at.desc()
            ).limit(limit).all()
            
            return [conv.to_dict() for conv in conversations]
            
        except Exception as e:
            print(f"Error getting math conversation history: {e}")
            return []

def get_math_assignment_response(prompt, assignment_data, history, user_context=None):
    """Get specialized math assignment response from Gemini API"""
    start_time = time.time()
    
    # Build assignment context
    assignment_context = ""
    if assignment_data:
        assignment_context = f"""
ASSIGNMENT DETAILS:
- Title: {assignment_data.get('title', 'N/A')}
- Description: {assignment_data.get('description', 'N/A')}
- Due Date: {assignment_data.get('due_date', 'N/A')}
- Topic: {assignment_data.get('topic_name', 'N/A')}
- Has Attachment: {assignment_data.get('has_file', False)}
- File: {assignment_data.get('file_name', 'No file attached')}
"""
    
    # Smart history processing for math context
    conversation_context = ""
    if history:
        recent_history = history[-6:]  # Last 3 exchanges
        
        for i in range(0, len(recent_history), 2):
            if i < len(recent_history):
                user_msg = recent_history[i]
                ai_msg = recent_history[i+1] if i+1 < len(recent_history) else ""
                conversation_context += f"Student: {user_msg}\nTutor: {ai_msg}\n"
    
    # Specialized math assignment prompt with strict formatting
    math_prompt = f"""You are MathTutor AI, a specialized mathematics assignment assistant for LyxNexus.

ASSIGNMENT CONTEXT:
{assignment_context if assignment_context else 'No specific assignment selected'}

CONVERSATION HISTORY (Recent 3 exchanges):
{conversation_context if conversation_context else 'No recent conversation'}

CURRENT STUDENT QUERY: {prompt}

**PLATFORM CONTEXT:**
- Current user: {current_user.username}
- Time: {(datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')} EAT
- LyxNexus Math Assistant - Specialized for assignment help
"""
    math_prompt += r"""

MATHEMATICS SPECIALIZATION:
- You are an expert in all areas of mathematics
- Provide step-by-step solutions with clear explanations
- Use proper mathematical notation and formatting
- Verify solutions for accuracy
- Explain concepts in multiple ways if needed

RESPONSE FORMATTING REQUIREMENTS - USE EXACTLY AS SPECIFIED:

**MATHEMATICAL FORMATTING:**
- Use LaTeX syntax for all mathematical expressions
- Inline math: $E = mc^2$ or \( y = mx + b \)
- Display math: $$x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$$ or \\[ \\int_a^b f(x)dx \\]
- **CRITICAL**: Never escape curly braces - use {{ }} for LaTeX
- Use ^ for superscripts and _ for subscripts in LaTeX mode

**STEP-BY-STEP SOLUTION FORMAT:**
**Step 1:** [Clear step description]
$$mathematical_work$$
Explanation of the step

**Step 2:** [Next step description]  
$$mathematical_work$$
Explanation of the step

**Final Answer:** $$\\boxed{{answer}}$$

**MATHEMATICAL SYMBOLS:**
- Fractions: $\\frac{{numerator}}{{denominator}}$
- Square roots: $\\sqrt{{expression}}$ or $\\sqrt[n]{{expression}}$
- Integrals: $\\int$, $\\int_a^b$, $\\iint$, $\\iiint$
- Derivatives: $\\frac{{dy}}{{dx}}$, $\\frac{{\\partial y}}{{\\partial x}}$, $f'(x)$
- Summation: $\\sum_{{i=1}}^n$, $\\prod_{{i=1}}^n$
- Limits: $\\lim_{{x \\to \\infty}}$, $\\lim_{{x \\to 0^+}}$
- Greek letters: $\\alpha$, $\\beta$, $\\gamma$, $\\Delta$, $\\theta$, $\\pi$, $\\omega$

**GENERAL FORMATTING:**
- Use **bold** for emphasis
- Use *italics* for variables or special terms
- Use `code` for inline code
- Use > for blockquotes
- Use - for lists

**RESPONSE GUIDELINES:**
1. **MATHEMATICAL ACCURACY FIRST**: Always provide correct solutions
2. **STEP-BY-STEP CLARITY**: Break down complex problems
3. **MULTIPLE APPROACHES**: Show different solution methods when helpful
4. **CONCEPT EXPLANATION**: Explain the "why" behind each step
5. **REAL-WORLD APPLICATIONS**: Connect to practical uses when relevant

Now provide a comprehensive mathematical response to the student's query using the exact formatting specified above:"""

    # Prepare API request
    contents = []
    
    # Add conversation history
    if history:
        recent_exchanges = history[-6:]
        for i in range(0, len(recent_exchanges), 2):
            if i < len(recent_exchanges):
                contents.append({"role": "user", "parts": [{"text": recent_exchanges[i]}]})
                if i + 1 < len(recent_exchanges):
                    contents.append({"role": "model", "parts": [{"text": recent_exchanges[i + 1]}]})
    
    # Add current math prompt
    contents.append({"role": "user", "parts": [{"text": math_prompt}]})
    
    # Use standard API
    for api_key in API_KEYS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,  # Lower temperature for mathematical accuracy
                "topK": 20,
                "topP": 0.8,
                "maxOutputTokens": 2048,  # More tokens for detailed math solutions
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and data['candidates']:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Clean up any formatting issues
                    cleaned_text = text.replace('{{', '{').replace('}}', '}')
                    
                    # Estimate token usage
                    tokens_used = len(cleaned_text.split()) + len(prompt.split())
                    
                    return {
                        'text': cleaned_text,
                        'tokens_used': tokens_used,
                        'response_time': response_time,
                        'success': True
                    }
                else:
                    print(f"No candidates in math response: {data}")
            else:
                print(f"Math API key {api_key[:10]}... failed: {response.status_code}")
        except Exception as e:
            print(f"Math API key {api_key[:10]}... failed: {e}")
            continue
    
    return {
        'text': "I'm currently experiencing technical difficulties with the math assistant. Please try again in a moment.",
        'tokens_used': 0,
        'response_time': time.time() - start_time,
        'success': False
    }

def simulate_math_streaming(text, base_delay=0.02):
    """Optimized streaming for mathematical content"""
    if not text:
        return
    
    # Special handling for mathematical content
    words = text.split(' ')
    i = 0
    
    while i < len(words):
        # Prefer to keep mathematical expressions together
        current_word = words[i] if i < len(words) else ""
        
        # Check if current word starts a mathematical expression
        if current_word.startswith('$') or current_word.startswith('\\') or '_{' in current_word or '^{' in current_word:
            # Try to keep mathematical expressions together
            chunk = current_word
            i += 1
            
            # Continue adding until we find the end of mathematical expression
            while i < len(words):
                next_word = words[i]
                chunk += ' ' + next_word
                i += 1
                
                # Check if this might end a mathematical expression
                if next_word.endswith('$') or (not next_word.startswith('\\') and not '_{' in next_word and not '^{' in next_word):
                    break
                    
        else:
            # Regular text - send 1-3 words
            words_in_chunk = min(random.randint(1, 3), len(words) - i)
            chunk_words = words[i:i + words_in_chunk]
            chunk = ' '.join(chunk_words)
            i += words_in_chunk
        
        # Add space if not the last chunk
        if i < len(words):
            chunk += ' '
        
        yield chunk
        
        # Variable delay
        delay = base_delay * len(chunk) * random.uniform(0.7, 1.3)
        
        # Longer pauses after mathematical expressions
        if '$' in chunk or '\\' in chunk:
            delay *= 1.5
            
        time.sleep(delay)

def generate_math_stream(prompt, assignment_id, history, user_context):
    """Generate streaming response for math assignments"""
    try:
        from app import db
        math_service = MathAssignmentService(db)

        # Get assignment data
        assignment_data = None
        if assignment_id:
            assignment_data = math_service.get_assignment_by_id(assignment_id)
            print(f"Loaded assignment: {assignment_data.get('title') if assignment_data else 'None'}")

        # Get recent math conversations from DB
        db_history = math_service.get_math_conversation_history(
            user_id=current_user.id, 
            limit=10
        )
        
        # Build fresh history from recent math conversations
        fresh_history = []
        for conv in reversed(db_history):
            fresh_history.append(conv['user_message'])
            fresh_history.append(conv['ai_response'])

        print(f"Loaded {len(fresh_history)//2} recent math conversations from DB")

        # Get full response from Math AI
        response_data = get_math_assignment_response(prompt, assignment_data, fresh_history, user_context)
        full_response = response_data['text']

        if not full_response:
            yield "data: ❌ Failed to get response from Math AI.\n\n"
            return

        # Save math conversation to database
        try:
            conversation_id = math_service.save_math_conversation(
                user_id=current_user.id,
                prompt=prompt,
                response=full_response,
                assignment_id=assignment_id,
                tokens_used=response_data.get('tokens_used', 0),
                response_time=response_data.get('response_time', 0),
                was_successful=response_data.get('success', True)
            )
            print(f"✅ Math conversation saved (ID: {conversation_id})")
        except Exception as e:
            print(f"❌ Failed to save math conversation: {e}")

        # Update session with fresh math history
        session.pop('math_history', None)
        
        updated_history = math_service.get_math_conversation_history(
            user_id=current_user.id, 
            limit=10
        )
        
        session['math_history'] = []
        for conv in updated_history:
            session['math_history'].append(conv['user_message'])
            session['math_history'].append(conv['ai_response'])
        
        session.modified = True

        # Stream response with mathematical optimization
        for chunk in simulate_math_streaming(full_response):
            yield f"data: {chunk}\n\n"

    except Exception as e:
        print(f"Math streaming error: {e}")
        yield "data: ❌ An error occurred while generating the math response.\n\n"

from flask import render_template
@math_bp.route('/')
@login_required
def math_assistant():
    """Main math assistant page"""
    return render_template('math.html')

@math_bp.route('/data')
@login_required
def math_data():
    """Get math assistant data"""
    from app import db
    math_service = MathAssignmentService(db)

    # Load user's assignments
    user_assignments = math_service.get_user_assignments(
        user_id=current_user.id,
        limit=50
    )

    # Load math conversation history
    conversation_history = math_service.get_math_conversation_history(
        user_id=current_user.id,
        limit=20
    )

    # Initialize session with fresh math data
    session.pop('math_history', None)
    session['math_history'] = []
    for conv in conversation_history:
        session['math_history'].append(conv['user_message'])
        session['math_history'].append(conv['ai_response'])
    session.modified = True

    return jsonify({
        'success': True,
        'user': {
            'username': current_user.username,
            'id': current_user.id,
            'is_admin': current_user.is_admin
        },
        'assignments': user_assignments,
        'conversations': conversation_history,
        'total_assignments': len(user_assignments),
        'total_conversations': len(conversation_history)
    })

@math_bp.route('/assignment/<int:assignment_id>')
@login_required
def get_assignment_data(assignment_id):
    """Get specific assignment data"""
    from app import db
    math_service = MathAssignmentService(db)
    
    assignment_data = math_service.get_assignment_by_id(assignment_id)
    
    if assignment_data:
        return jsonify({
            'success': True,
            'assignment': assignment_data
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Assignment not found'
        }), 404

@math_bp.route('/stream')
@login_required
def math_stream():
    """Streaming endpoint for math responses"""
    prompt = request.args.get('prompt', '').strip()
    assignment_id = request.args.get('assignment_id', type=int)
    
    if not prompt:
        return Response("data: ❌ Error: Empty prompt\n\n", mimetype='text/event-stream')
    
    print(f"Starting math stream for assignment {assignment_id}: {prompt[:50]}...")
    
    # Get user context
    user_context = {
        'user_id': current_user.id,
        'username': current_user.username,
        'is_admin': current_user.is_admin
    }
    
    # Use fresh history from session
    history = session.get('math_history', [])
    
    return Response(
        stream_with_context(generate_math_stream(prompt, assignment_id, history, user_context)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@math_bp.route('/chat', methods=['POST'])
@login_required
def math_chat_api():
    """Non-streaming math chat endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        prompt = data.get('prompt', '').strip()
        assignment_id = data.get('assignment_id')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Empty prompt'}), 400
        
        # Get user context
        user_context = {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_admin': current_user.is_admin
        }
        
        # Get assignment data
        from app import db
        math_service = MathAssignmentService(db)
        assignment_data = None
        if assignment_id:
            assignment_data = math_service.get_assignment_by_id(assignment_id)
        
        # Get fresh history
        db_history = math_service.get_math_conversation_history(
            user_id=current_user.id, 
            limit=10
        )
        
        fresh_history = []
        for conv in reversed(db_history):
            fresh_history.append(conv['user_message'])
            fresh_history.append(conv['ai_response'])
        
        # Get response
        response_data = get_math_assignment_response(prompt, assignment_data, fresh_history, user_context)
        full_response = response_data['text']
        
        if full_response:
            # Save to database
            try:
                conversation_id = math_service.save_math_conversation(
                    user_id=current_user.id,
                    prompt=prompt,
                    response=full_response,
                    assignment_id=assignment_id,
                    tokens_used=response_data.get('tokens_used', 0),
                    response_time=response_data.get('response_time', 0),
                    was_successful=response_data.get('success', True)
                )
            except Exception as e:
                print(f"Failed to save math conversation: {e}")
            
            # Update session
            session.pop('math_history', None)
            updated_history = math_service.get_math_conversation_history(
                user_id=current_user.id, 
                limit=10
            )
            
            session['math_history'] = []
            for conv in updated_history:
                session['math_history'].append(conv['user_message'])
                session['math_history'].append(conv['ai_response'])
            
            session.modified = True
            
            return jsonify({
                'success': True,
                'response': full_response,
                'conversation_id': conversation_id,
                'response_time': response_data.get('response_time', 0),
                'tokens_used': response_data.get('tokens_used', 0)
            })
        else:
            return jsonify({'success': False, 'error': 'Math service unavailable'}), 503
        
    except Exception as e:
        print(f"Math chat error: {e}")
        return jsonify({'success': False, 'error': 'Failed to process math request'}), 500

@math_bp.route('/clear-history')
@login_required
def clear_math_history():
    """Clear math conversation history"""
    try:
        # Clear session history
        session.pop('math_history', None)
        
        # Clear database math conversations
        from app import db, AIConverse
        
        deleted_count = AIConverse.query.filter_by(
            user_id=current_user.id,
            context_used='math_assignment'
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Math history cleared ({deleted_count} conversations deleted)'
        })
    except Exception as e:
        print(f"Error clearing math history: {e}")
        return jsonify({'success': False, 'error': 'Failed to clear math history'}), 500

@math_bp.route('/assignments')
@login_required
def get_assignments():
    """Get user's assignments"""
    try:
        from app import db
        math_service = MathAssignmentService(db)
        
        assignments = math_service.get_user_assignments(
            user_id=current_user.id,
            limit=50
        )
        
        return jsonify({
            'success': True,
            'assignments': assignments,
            'total': len(assignments)
        })
    except Exception as e:
        print(f"Error getting assignments: {e}")
        return jsonify({'success': False, 'error': 'Failed to load assignments'}), 500

print("✅ Math Assignment Blueprint loaded successfully!")
print("🔑 API Keys configured:", len(API_KEYS))
print("🧮 Model:", MODEL)
print("🚀 Math Assignment Assistant is ready to use!")