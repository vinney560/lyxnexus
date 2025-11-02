# gemini_bp.py — Updated for Intelligent Context & Chronological Memory
# Author: Vincent (Optimized for LyxNexus)
# Version: Context-Stable | Topic-Aware | Chronological Memory

from flask import Blueprint, request, session, jsonify, render_template, Response, stream_with_context
from flask_login import current_user, login_required
from datetime import datetime, timedelta, date, time
import requests
import random
import time as systime
import json

# Create blueprint
gemini_bp = Blueprint('gemini', __name__, url_prefix='/gemini')

# Gemini API Config
API_KEYS = [
    'AIzaSyA3o8aKHTnVzuW9-qg10KjNy7Lcgn19N2I',
    'AIzaSyCq8-xrPTC40k8E_i3vXZ_-PR6RiPsuOno'
]
MODEL = "gemini-2.0-flash"


# =====================================================================
# Core Services
# =====================================================================
class AIConversationService:
    """Handles conversation persistence and history retrieval."""
    def __init__(self, db_session):
        self.db = db_session

    def save_conversation(self, user_id, prompt, response, context='general',
                         message_type='text', tokens_used=0, response_time=0.0,
                         api_model=None, was_successful=True, error_message=None):
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
            return conversation.id
        except Exception as e:
            print(f"❌ Error saving conversation: {e}")
            self.db.session.rollback()
            return None

    def get_user_conversation_history(self, user_id, limit=20, offset=0):
        """Return user's conversations chronologically (oldest → newest)."""
        try:
            from app import AIConverse
            conversations = (
                AIConverse.query.filter_by(user_id=user_id)
                .order_by(AIConverse.created_at.asc())  # chronological
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [conv.to_dict() for conv in conversations]
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []


# =====================================================================
# ReadOnly Query Service
# =====================================================================
class ReadOnlyDatabaseQueryService:
    """Provides safe read-only access to platform data."""
    def __init__(self, db_session):
        self.db = db_session
        self.conversation_service = AIConversationService(db_session)

    def get_public_stats(self):
        """Return latest platform info: announcements, assignments, timetable."""
        try:
            from app import Announcement, Assignment, Timetable, Topic

            recent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
            recent_assignments = Assignment.query.order_by(Assignment.created_at.desc()).limit(5).all()
            timetable_entries = Timetable.query.order_by(Timetable.created_at.desc()).limit(5).all()
            topics = Topic.query.order_by(Topic.created_at.desc()).limit(5).all()

            return {
                "announcements": [
                    {"title": a.title, "content": a.content, "created_at": a.created_at.isoformat()}
                    for a in recent_announcements
                ],
                "assignments": [
                    {"title": a.title, "description": a.description, "due_date": a.due_date.isoformat() if a.due_date else None}
                    for a in recent_assignments
                ],
                "timetable": [
                    {"day": t.day_of_week, "subject": t.subject, "start": t.start_time.isoformat(), "end": t.end_time.isoformat()}
                    for t in timetable_entries
                ],
                "topics": [{"name": tp.name, "description": tp.description} for tp in topics]
            }
        except Exception as e:
            print(f"Error loading public stats: {e}")
            return {}

    def get_user_conversation_history(self, user_id, limit=20):
        return self.conversation_service.get_user_conversation_history(user_id, limit)

    def save_conversation(self, user_id, prompt, response, **kwargs):
        return self.conversation_service.save_conversation(user_id, prompt, response, **kwargs)


# =====================================================================
# Intelligent Response System
# =====================================================================
def detect_topic_from_text(text):
    """Identify main topic from text content."""
    text = text.lower()
    if any(k in text for k in ["assignment", "due", "submit", "homework"]):
        return "assignments"
    elif any(k in text for k in ["announcement", "news", "update"]):
        return "announcements"
    elif any(k in text for k in ["timetable", "schedule", "class"]):
        return "timetable"
    elif any(k in text for k in ["topic", "course", "lesson"]):
        return "topics"
    else:
        return "general"


def build_conversation_context(history):
    """Build context from chronological history for natural continuity."""
    context = ""
    if not history:
        return "No previous conversation."

    # use only last 6 exchanges (3 user-AI pairs)
    limited = history[-6:]
    for i in range(0, len(limited), 2):
        user_msg = limited[i]
        ai_msg = limited[i + 1] if i + 1 < len(limited) else ""
        context += f"User: {user_msg}\nAssistant: {ai_msg}\n"
    return context.strip()


def get_gemini_response(prompt, history, user_context=None):
    """Enhanced Gemini API integration with topic stability and continuity."""
    start_time = systime.time()

    # Build chronological context
    conversation_context = build_conversation_context(history)
    topic = detect_topic_from_text(" ".join(history[-4:]) + " " + prompt)

    # Fetch platform data when relevant
    platform_context = ""
    try:
        from app import db
        db_service = ReadOnlyDatabaseQueryService(db)
        stats = db_service.get_public_stats()

        if topic == "assignments" and stats.get("assignments"):
            recent = stats["assignments"][:2]
            platform_context += "\nRecent Assignments:\n"
            for a in recent:
                platform_context += f"- {a['title']} (Due: {a['due_date']})\n"
        elif topic == "announcements" and stats.get("announcements"):
            recent = stats["announcements"][:2]
            platform_context += "\nRecent Announcements:\n"
            for a in recent:
                platform_context += f"- {a['title']}\n"
        elif topic == "timetable" and stats.get("timetable"):
            platform_context += "\nUpcoming Classes:\n"
            for t in stats["timetable"][:2]:
                platform_context += f"- {t['day']} {t['subject']} ({t['start']} - {t['end']})\n"
    except Exception as e:
        print(f"Context data load error: {e}")

    # Smart prompt
    smart_prompt = f"""
You are Marion, a wise and friendly AI assistant on the LyxNexus educational platform.

Platform Context:
{platform_context if platform_context else '(No specific platform data relevant right now)'}

Recent Conversation (chronological):
{conversation_context}

Current User Message: {prompt}

Rules:
1. Maintain context naturally. Don't jump between topics.
2. If user continues same topic, keep flow smooth.
3. If user switches to new topic, transition silently and respond relevantly.
4. Treat short replies like 'yes', 'no', 'continue' as follow-ups to the last exchange.
5. Be concise, clear, and natural — avoid overexplaining.
6. Never mention “previous messages” or “context.”

Time: {(datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')} EAT
User: {current_user.username}
    """.strip()

    # Prepare payload
    contents = [{"role": "user", "parts": [{"text": smart_prompt}]}]
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        }
    }

    # Try Gemini keys sequentially
    for key in API_KEYS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
            r = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
            response_time = systime.time() - start_time

            if r.status_code == 200:
                data = r.json()
                if "candidates" in data and data["candidates"]:
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return {
                        "text": text,
                        "tokens_used": len(text.split()) + len(prompt.split()),
                        "response_time": round(response_time, 2),
                        "success": True,
                        "context_used": topic,
                    }
            else:
                print(f"Gemini API error {r.status_code}: {r.text}")
        except Exception as e:
            print(f"Gemini API key {key[:10]}... failed: {e}")

    # fallback
    return {
        "text": "I'm experiencing a temporary issue. Please try again shortly.",
        "tokens_used": 0,
        "response_time": systime.time() - start_time,
        "success": False,
        "context_used": "general"
    }


# =====================================================================
# Streaming System
# =====================================================================
def simulate_streaming(text, base_delay=0.03):
    """Stream text gradually for live chat feel."""
    words = text.split(' ')
    i = 0
    while i < len(words):
        chunk_size = min(random.randint(1, 3), len(words) - i)
        chunk = ' '.join(words[i:i + chunk_size])
        if i + chunk_size < len(words):
            chunk += ' '
        yield f"data: {chunk}\n\n"
        delay = base_delay * len(chunk) * random.uniform(0.9, 1.3)
        if chunk.endswith(('.', '!', '?')):
            delay *= 2
        systime.sleep(delay)
        i += chunk_size


def generate_stream(prompt, history, user_context):
    """Generate and stream response with chronological, topic-aware memory."""
    try:
        from app import db
        db_service = ReadOnlyDatabaseQueryService(db)

        if not history:
            db_history = db_service.get_user_conversation_history(current_user.id, 20)
            history = []
            for h in db_history:
                history += [h["user_message"], h["ai_response"]]

        response = get_gemini_response(prompt, history, user_context)
        text = response["text"]
        context_used = response.get("context_used", "general")

        db_service.save_conversation(
            user_id=current_user.id,
            prompt=prompt,
            response=text,
            context=context_used,
            tokens_used=response["tokens_used"],
            response_time=response["response_time"],
            was_successful=response["success"]
        )

        session.setdefault("gemini_history", [])
        session["gemini_history"] += [prompt, text]
        session["gemini_history"] = session["gemini_history"][-40:]
        session.modified = True

        for chunk in simulate_streaming(text):
            yield chunk
    except Exception as e:
        print(f"Streaming error: {e}")
        yield "data: ❌ An error occurred during streaming.\n\n"


# =====================================================================
# Routes
# =====================================================================
@gemini_bp.route('/')
@login_required
def gemini_chat():
    from app import db
    db_service = ReadOnlyDatabaseQueryService(db)
    history_data = db_service.get_user_conversation_history(current_user.id, 20)

    session["gemini_history"] = []
    for h in history_data:
        session["gemini_history"] += [h["user_message"], h["ai_response"]]
    session.modified = True

    history_html = "".join(
        f"<div class='message user-message'><div class='message-content'>{h['user_message']}</div></div>"
        f"<div class='message ai-message'><div class='message-content'>{h['ai_response']}</div></div>"
        for h in history_data
    )

    return render_template("ai_assist.html", current_user=current_user, history_html=history_html, sidebar_history_html=history_html)


@gemini_bp.route('/stream')
@login_required
def gemini_stream():
    prompt = request.args.get("prompt", "").strip()
    if not prompt:
        return Response("data: ❌ Empty prompt\n\n", mimetype="text/event-stream")

    user_context = {"user_id": current_user.id, "username": current_user.username}
    history = session.get("gemini_history", [])
    return Response(
        stream_with_context(generate_stream(prompt, history, user_context)),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


print("✅ Gemini Blueprint Updated — Chronological, Topic-Aware, Context-Stable")
print("🤖 Enhanced AI memory & topic understanding active")
print("🚀 Ready to chat intelligently on LyxNexus!")
