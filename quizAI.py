# guizAI.py
from flask import Flask, request, jsonify, render_template, Blueprint
import google.generativeai as genai
import os
import json

_quiz_AI = Blueprint('quizAI', __name__, url_prefix='/quiz')

class QuizGenerator:
    def __init__(self):
        self.api_keys = [
            'I will add when done updating',
            'I will add when done updating'
        ]
        self.current_key_index = 0
        self.model_name = "gemini-2.5-flash-lite"
        self.setup_genai()
    
    def setup_genai(self):
        """Configure Gemini AI with current API key"""
        current_key = self.api_keys[self.current_key_index]
        if current_key and current_key != 'your_fallback_key_here':
            genai.configure(api_key=current_key)
        else:
            print("Warning: Using fallback mode - no valid API keys found")
    
    def switch_api_key(self):
        """Switch to next API key if available"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.setup_genai()
    
    def generate_quiz_stream(self, topic, num_questions=5, difficulty="Medium", style="Multiple Choice"):
        """Generate quiz using Gemini AI"""
        try:
            if self.api_keys[0] == '':
                return self._create_fallback_quiz(num_questions)
            
            model = genai.GenerativeModel(self.model_name)
            prompt = self._build_prompt(topic, num_questions, difficulty, style)
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000,
                )
            )
            
            return self._parse_response(response.text)
            
        except Exception as e:
            print(f"API Error: {e}")
            # Try switching API key on error, or return fallback --> not included
            self.switch_api_key()
            return self._create_fallback_quiz(num_questions)
    
    def _build_prompt(self, topic, num_questions, difficulty, style):
        """Build the prompt for quiz generation"""
        return f"""
        Generate exactly {num_questions} {style.lower()} questions about: "{topic}"
        Difficulty: {difficulty}
        
        Return ONLY valid JSON in this exact format:
        [
          {{
            "question": "Question text here",
            "options": ["Option1", "Option2", "Option3", "Option4"],
            "correct": "Correct answer text",
            "explanation": "Clear and Brief explanation"
          }}
        ]
        
        Important:
        You are an intelligent academic topic evaluator within LyxNexus — a learning and collaboration hub designed for structured educational use.
        - For True/False: use options ["True", "False"]
        - For Fill-in-the-Blank: include "correct" with exact expected answer
        - Ensure ALL questions have all required fields
        - Return ONLY the JSON array, no other text
        - Use mostly internet accessible resources to generate first year level questions and answers
        
        SOURCES AND RESOURCES OF ACADEMICS ONLINE:
        - WHO HIV/AIDS Fact Sheets, CDC HIV Guidelines, Medical Microbiology by Murray et al., The Lancet HIV Journal, OpenStax College Algebra, Khan Academy Algebra, Schaum's Outline of College Algebra, University Math Curriculum, Stanford Encyclopedia of Philosophy, Introduction to Philosophy by John Perry, Philosophy: The Basics by Nigel Warburton, University Philosophy Curriculum, University Communication Textbooks, Communication Theory by F. Jablin, APA Communication Guidelines, Chuka University Lecture Notes, MIT OpenCourseWare – Introduction to Computer Science, NIST Computer Science Resources, OpenStax Introduction to Computer Science, Python.org Documentation, Computer Science: An Overview by J. Glenn Brookshear, IT Fundamentals by Pearson, Online IT Courses (Coursera, edX), Industry Coding Standards, AI-generated, Educational databases
        
        CONTENT REQUIREMENTS:
        1. ALIGNMENT: Questions must align with standard university curriculum
        2. ACCURACY: Use only verified academic information
        3. DIVERSITY: Cover multiple aspects of the subject
        
        SOURCE INTEGRATION:
        - Reference established academic sources
        - Use textbook-accurate terminology
        - Include real-world applications where appropriate
        - Maintain academic rigor and precision
        
        QUESTION STRUCTURE:
        - Each question must test meaningful understanding
        - Avoid trivial or overly simple questions
        - Ensure logical progression of difficulty
        - Include practical applications when possible
        
        QUALITY ASSURANCE FOR ACCADEMICS:
        - All content must be academically verifiable
        - Explanations should cite established knowledge
        - Questions should promote critical thinking

        Your responsibility:
        Determine whether the given topic is academic or school-related. An educational topic refers to any subject or theme that could logically belong in a formal learning environment, such as a classroom, college, university, or academic curriculum.

        Educational topics typically fall under categories like:
        - Science (Physics, Chemistry, Biology, Environmental Studies)
        - Technology (Computer Science, AI, Robotics, Data Structures)
        - Mathematics (Algebra, Calculus, Statistics)
        - Humanities (History, Philosophy, Literature, Psychology)
        - Social Sciences (Economics, Political Science, Sociology)
        - Languages and Communication (English, Linguistics, Grammar, communication skills)
        - Professional Studies (Engineering, Business, Education, Medicine)

        A non-educational topic includes:
        - Entertainment, media, and pop culture (movies, celebrities, music)
        - Internet trends or memes
        - Sports and games (unless being studied academically, e.g., sports science)
        - Personal or informal lifestyle topics

        Carefully analyze the provided topic.  
        If it can reasonably be studied, taught, or analyzed in an academic context, classify it as educational and use the SOURCES AND RESOURCES OF ACADEMICS ONLINE above to source correct information then generate first year level questions and answers.  
        If it primarily belongs to casual, entertainment, or social contexts, classify it as non-educational.

        NOTICE & TOPIC BREAKDOWN:
        * These are the common Topic students will ask, understand the meaning of the unit code and then source correct academic resources for any when asked.
        - ZOOL 143 is Biology of HIV & AIDS.
        - COMP 107 is Fundation of computing delaing with Introduction to 
Computers, Introduction to Computer Software , Operating System, SpreadSheet, Word Processing, Networking, Computer Classification & Harware considerations, .
        - PHIL 104 is Philosophy & Society.
        - BIT 100 is Barchelor in Information Technology dealing with INTRODUCTION TO PROGRAMMING, VARIABLES IN PROGRAMMING LANGUAGES, EXPRESSIONS & OPERATORS, PROGRAMMING CONCEPTS, PROBLEM-SOLVING ALGORITHMS 1 & 2.
        - COMS 101 is Communication Skills.
        - MATH 112 is College/University Mathematics.
        ## Use online tool to source information online for this Topics and generate first year level questions and Answers.
        """
    
    def _parse_response(self, response_text):
        """Parse and validate the AI response"""
        try:
            
            cleaned_text = response_text.strip()
            if '```json' in cleaned_text:
                cleaned_text = cleaned_text.split('```json')[1].split('```')[0]
            elif '```' in cleaned_text:
                cleaned_text = cleaned_text.split('```')[1]
            
            quiz_data = json.loads(cleaned_text)
            
            if not isinstance(quiz_data, list):
                raise ValueError("Expected list of questions")
            
            for question in quiz_data:
                if not all(key in question for key in ['question', 'correct']):
                    raise ValueError("Missing required fields in question")
                if 'options' not in question:
                    question['options'] = []
            
            return quiz_data
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Parse error: {e}, Response: {response_text[:200]}...")
            return self._create_fallback_quiz(3)
    
    def _create_fallback_quiz(self, num_questions=3):
        """Create a fallback quiz when AI fails or on error"""
        fallback_questions = [
            {
                "question": "What is the capital of France?",
                "options": ["London", "Berlin", "Paris", "Madrid"],
                "correct": "Paris",
                "explanation": "Paris is the capital and most populous city of France."
            },
            {
                "question": "Which planet is known as the Red Planet?",
                "options": ["Venus", "Mars", "Jupiter", "Saturn"],
                "correct": "Mars",
                "explanation": "Mars _quiz_AIears red due to iron oxide (rust) on its surface."
            },
            {
                "question": "What is 2 + 2?",
                "options": ["3", "4", "5", "6"],
                "correct": "4",
                "explanation": "Basic arithmetic: 2 + 2 = 4"
            }
        ]
        return fallback_questions[:num_questions]

quiz_gen = QuizGenerator()

@_quiz_AI.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    """Endpoint to generate quiz"""
    try:
        data = request.json
        topic = data.get('topic', '')
        num_questions = data.get('num_questions', 5)
        difficulty = data.get('difficulty', 'Medium')
        style = data.get('style', 'Multiple Choice')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        quiz_data = quiz_gen.generate_quiz_stream(
            topic, num_questions, difficulty, style
        )
        
        return jsonify({'quiz': quiz_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rendering the interface
@_quiz_AI.route('/')
def quiz():
    return render_template('quizAI.html')

# Test connection btwn frontend and backend
@_quiz_AI.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Quiz Generator API'})

print("✅ Nova AI Quiz Generator Initiated Successfully!!!!")
print("Ready to GIVE QUIZ & ANSWERS!!")