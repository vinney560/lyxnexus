# quizAI.py
from flask import Flask, request, jsonify, render_template, Blueprint
import google.generativeai as genai
import os
import json
import re
import requests
from datetime import datetime

_quiz_AI = Blueprint('quizAI', __name__, url_prefix='/quiz')

class QuizGenerator:
    def __init__(self):
        self.api_keys = [
            'AIzaSyA3o8aKHTnVzuW9-qg10KjNy7Lcgn19N2I',
            'AIzaSyCq8-xrPTC40k8E_i3vXZ_-PR6RiPsuOno'
        ]
        self.current_key_index = 0
        self.model_name = "gemini-2.5-flash-lite"
        
        # Comprehensive University Course Database
        self.university_courses = {
            'ZOOL 143': {
                'name': 'BIOLOGY OF HIV/AIDS',
                'department': 'Zoology',
                'level': 'First Year University',
                'description': 'Comprehensive study of HIV virology, immunology, transmission, prevention, and global impact',
                'topics': ['HIV structure', 'viral replication', 'immune response', 'ART therapy', 'epidemiology'],
                'sources': ['Open University', 'Medical textbooks', 'WHO guidelines', 'Academic research papers']
            },
            'MATH 112': {
                'name': 'COLLEGE ALGEBRA', 
                'department': 'Mathematics',
                'level': 'First Year University',
                'description': 'Fundamental algebraic concepts, functions, equations, and mathematical modeling',
                'topics': ['linear equations', 'quadratic functions', 'polynomials', 'exponents', 'matrices'],
                'sources': ['Reed College', 'OpenStax Algebra', 'Khan Academy', 'University curriculum']
            },
            'PHIL 104': {
                'name': 'INTRODUCTION TO PHILOSOPHY',
                'department': 'Philosophy', 
                'level': 'First Year University',
                'description': 'Foundational philosophical concepts, ethics, logic, and major philosophical traditions',
                'topics': ['metaphysics', 'epistemology', 'ethics', 'logic', 'political philosophy'],
                'sources': ['Chuka University', 'Stanford Encyclopedia', 'Philosophy textbooks', 'Classical works']
            },
            'COMS 101': {
                'name': 'INTRODUCTION TO COMMUNICATION STUDIES',
                'department': 'Communication',
                'level': 'First Year University', 
                'description': 'Principles of human communication, media studies, and interpersonal interaction',
                'topics': ['communication models', 'verbal/nonverbal', 'public speaking', 'media literacy'],
                'sources': ['Chuka University', 'Communication theory texts', 'Academic journals', 'Case studies']
            },
            'BIT 100': {
                'name': 'INTRODUCTION TO INFORMATION TECHNOLOGY',
                'department': 'Business Information Technology',
                'level': 'First Year University',
                'description': 'Fundamentals of computer systems, networking, databases, and IT infrastructure',
                'topics': ['computer hardware', 'software systems', 'networking', 'databases', 'cybersecurity'],
                'sources': ['IT textbooks', 'Industry standards', 'Technical documentation']
            },
            'COMP 107': {
                'name': 'INTRODUCTION TO COMPUTER PROGRAMMING',
                'department': 'Computer Science',
                'level': 'First Year University',
                'description': 'Basic programming concepts, algorithm development, and problem-solving techniques',
                'topics': ['programming basics', 'algorithms', 'data types', 'control structures', 'debugging'],
                'sources': ['Programming textbooks', 'Online courses', 'Coding standards']
            },
            'CUSTOM': {
                'name': 'CUSTOM TOPIC',
                'department': 'General',
                'level': 'Variable',
                'description': 'User-defined topic with AI-powered quiz generation',
                'topics': ['user-specified content'],
                'sources': ['AI-generated', 'Educational databases']
            }
        }

        # Answer method configurations
        self.answer_methods = {
            'multiple_choice': {
                'name': 'Multiple Choice',
                'options_count': 4,
                'description': 'Choose one correct answer from several options'
            },
            'true_false': {
                'name': 'True/False', 
                'options_count': 2,
                'description': 'Determine if statement is true or false'
            },
            'fill_blank': {
                'name': 'Fill in the Blank',
                'options_count': 0,
                'description': 'Provide the exact answer for blank spaces'
            },
            'short_answer': {
                'name': 'Short Answer',
                'options_count': 0,
                'description': 'Brief written responses to questions'
            }
        }

        # Difficulty levels
        self.difficulty_levels = {
            'easy': {
                'name': 'Easy',
                'description': 'Basic concepts and fundamental knowledge',
                'complexity': 'Recall and understanding'
            },
            'medium': {
                'name': 'Medium', 
                'description': 'Application and analysis of concepts',
                'complexity': 'Application and analysis'
            },
            'hard': {
                'name': 'Hard',
                'description': 'Complex problems and critical thinking',
                'complexity': 'Evaluation and synthesis'
            }
        }
        
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
    
    def get_course_prompt_context(self, course_code, custom_topic=None):
        """Get detailed context for course-specific prompts"""
        if course_code in self.university_courses:
            course = self.university_courses[course_code]
            return {
                'course_name': course['name'],
                'department': course['department'], 
                'level': course['level'],
                'topics': course['topics'],
                'sources': course['sources'],
                'description': course['description']
            }
        else:
            return {
                'course_name': custom_topic or 'General Knowledge',
                'department': 'Various',
                'level': 'Adaptive',
                'topics': ['user-defined content'],
                'sources': ['AI-generated content', 'Educational databases'],
                'description': f'Custom topic: {custom_topic}'
            }
    
    def build_advanced_prompt(self, course_context, num_questions, difficulty, answer_method, custom_topic=None):
        """Build sophisticated prompt with course context and educational standards"""
        
        difficulty_info = self.difficulty_levels.get(difficulty.lower(), self.difficulty_levels['medium'])
        method_info = self.answer_methods.get(answer_method.lower(), self.answer_methods['multiple_choice'])
        
        prompt = f"""
        ACADEMIC QUIZ GENERATION PROTOCOL - LyxNexus University System
        ==============================================================

        COURSE CONTEXT:
        - Course: {course_context['course_name']}
        - Department: {course_context['department']}
        - Academic Level: {course_context['level']}
        - Key Topics: {', '.join(course_context['topics'])}
        - Primary Sources: {', '.join(course_context['sources'])}

        GENERATION PARAMETERS:
        - Number of Questions: {num_questions}
        - Difficulty: {difficulty_info['name']} ({difficulty_info['description']})
        - Cognitive Level: {difficulty_info['complexity']}
        - Answer Method: {method_info['name']}
        - Options per Question: {method_info['options_count']}

        CONTENT REQUIREMENTS:
        1. ALIGNMENT: Questions must align with standard university curriculum
        2. ACCURACY: Use only verified academic information
        3. DEPTH: Match {difficulty} difficulty cognitive demands
        4. RELEVANCE: Focus on {course_context['course_name']} core concepts
        5. DIVERSITY: Cover multiple aspects of the subject

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

        FORMAT REQUIREMENTS:
        Return ONLY valid JSON in this exact structure:
        [
          {{
            "question": "Clear, academically rigorous question",
            "options": ["Option1", "Option2", ...] // {method_info['options_count']} options for multiple choice, empty for others
            "correct": "Exactly correct answer",
            "explanation": "Comprehensive academic explanation with source references",
            "source": "Primary academic source or reference",
            "difficulty": "{difficulty}",
            "concept": "Specific concept being tested",
            "bloom_level": "Appropriate Bloom's taxonomy level"
          }}
        ]

        SPECIAL FORMATS:
        - Multiple Choice: Provide {method_info['options_count']} plausible options
        - True/False: Use options ["True", "False"] 
        - Fill-in-Blank: Include exact expected answer in "correct"
        - Short Answer: Focus on concise, precise responses

        QUALITY ASSURANCE:
        - All content must be academically verifiable
        - Explanations should cite established knowledge
        - Questions should promote critical thinking
        - Maintain {course_context['level']} appropriateness

        Return ONLY the JSON array, no additional text or commentary.
        """
        
        return prompt
    
    def academic_content_validator(self, quiz_data, course_context, difficulty):
        """Enhanced validation for academic quality and course alignment"""
        validated_questions = []
        
        for question in quiz_data:
            # Basic field validation
            required_fields = ['question', 'correct', 'explanation']
            if not all(field in question for field in required_fields):
                continue
            
            # Academic quality checks
            if self._meets_academic_standards(question, course_context, difficulty):
                # Enhance with missing fields
                question = self._enhance_question_quality(question, course_context)
                validated_questions.append(question)
        
        return validated_questions if validated_questions else self._create_course_specific_fallback(course_context)
    
    def _meets_academic_standards(self, question, course_context, difficulty):
        """Check if question meets academic standards"""
        # Check for non-academic content
        non_academic_indicators = [
            'celebrity', 'gossip', 'entertainment', 'sports trivia',
            'personal opinion', 'social media', 'viral trend'
        ]
        
        question_text = (question.get('question', '') + ' ' + 
                        question.get('explanation', '')).lower()
        
        if any(indicator in question_text for indicator in non_academic_indicators):
            return False
        
        # Check for sufficient academic rigor
        academic_indicators = [
            'research', 'study', 'according to', 'academic',
            'theory', 'concept', 'principle', 'analysis'
        ]
        
        academic_score = sum(1 for indicator in academic_indicators if indicator in question_text)
        return academic_score >= 2  # At least 2 academic indicators
    
    def _enhance_question_quality(self, question, course_context):
        """Enhance question with academic metadata"""
        # Add source if missing
        if 'source' not in question:
            question['source'] = course_context['sources'][0] if course_context['sources'] else 'Academic curriculum'
        
        # Add concept if missing
        if 'concept' not in question:
            question['concept'] = course_context['topics'][0] if course_context['topics'] else 'Core concept'
        
        # Add Bloom's taxonomy level
        if 'bloom_level' not in question:
            question['bloom_level'] = self._infer_blooms_level(question)
        
        # Enhance explanation with academic references
        if 'explanation' in question and not any(source in question['explanation'] for source in course_context['sources']):
            question['explanation'] = f"Based on {course_context['sources'][0] if course_context['sources'] else 'academic research'}: {question['explanation']}"
        
        return question
    
    def _infer_blooms_level(self, question):
        """Infer Bloom's taxonomy level from question content"""
        question_text = question.get('question', '').lower()
        explanation = question.get('explanation', '').lower()
        
        text = question_text + ' ' + explanation
        
        # Bloom's taxonomy keywords
        levels = {
            'remember': ['define', 'list', 'recall', 'identify', 'what is'],
            'understand': ['explain', 'describe', 'interpret', 'summarize'],
            'apply': ['use', 'apply', 'solve', 'demonstrate', 'how would'],
            'analyze': ['analyze', 'compare', 'contrast', 'differentiate'],
            'evaluate': ['evaluate', 'judge', 'critique', 'defend'],
            'create': ['create', 'design', 'develop', 'propose']
        }
        
        for level, keywords in levels.items():
            if any(keyword in text for keyword in keywords):
                return level
        
        return 'understand'  # Default level
    
    def _create_course_specific_fallback(self, course_context):
        """Create course-specific fallback questions"""
        fallback_templates = {
            'BIOLOGY OF HIV/AIDS': [
                {
                    "question": "What is the primary function of reverse transcriptase in the HIV replication cycle?",
                    "options": ["DNA to RNA transcription", "RNA to DNA transcription", "Protein synthesis", "Viral entry"],
                    "correct": "RNA to DNA transcription",
                    "explanation": "Reverse transcriptase converts viral RNA into DNA, a crucial step in HIV replication according to virology textbooks.",
                    "source": "Medical virology curriculum",
                    "difficulty": "medium",
                    "concept": "Viral replication",
                    "bloom_level": "understand"
                }
            ],
            'COLLEGE ALGEBRA': [
                {
                    "question": "What is the solution to the quadratic equation x² - 5x + 6 = 0?",
                    "options": ["x = 2, 3", "x = 1, 6", "x = -2, -3", "x = -1, -6"],
                    "correct": "x = 2, 3", 
                    "explanation": "The equation factors to (x-2)(x-3)=0, giving solutions x=2 and x=3, as per algebraic principles.",
                    "source": "Algebra textbooks",
                    "difficulty": "easy",
                    "concept": "Quadratic equations",
                    "bloom_level": "apply"
                }
            ],
            # Add templates for other courses...
        }
        
        course_name = course_context['course_name']
        if course_name in fallback_templates:
            return fallback_templates[course_name]
        else:
            return [{
                "question": f"What is a fundamental concept in {course_name}?",
                "options": ["Core principle A", "Basic concept B", "Fundamental theory C", "Essential method D"],
                "correct": "Core principle A",
                "explanation": f"This represents a key concept in {course_name} based on standard curriculum.",
                "source": "Academic sources",
                "difficulty": "medium",
                "concept": "Fundamentals",
                "bloom_level": "remember"
            }]
    
    def generate_advanced_quiz(self, course_code, custom_topic, num_questions, difficulty, answer_method):
        """Generate quiz with advanced academic controls"""
        try:
            if self.api_keys[0] == '':
                course_context = self.get_course_prompt_context(course_code, custom_topic)
                return self._create_course_specific_fallback(course_context)
            
            # Get course context
            course_context = self.get_course_prompt_context(course_code, custom_topic)
            
            model = genai.GenerativeModel(self.model_name)
            prompt = self.build_advanced_prompt(
                course_context, num_questions, difficulty, answer_method, custom_topic
            )
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2500,
                )
            )
            
            # Parse and validate response
            quiz_data = self._parse_advanced_response(response.text)
            
            # Apply academic validation
            validated_quiz = self.academic_content_validator(quiz_data, course_context, difficulty)
            
            return validated_quiz[:num_questions]  # Ensure exact number
            
        except Exception as e:
            print(f"Advanced Quiz Generation Error: {e}")
            self.switch_api_key()
            course_context = self.get_course_prompt_context(course_code, custom_topic)
            return self._create_course_specific_fallback(course_context)
    
    def _parse_advanced_response(self, response_text):
        """Parse AI response with enhanced error handling"""
        try:
            cleaned_text = response_text.strip()
            
            # Extract JSON from code blocks
            if '```json' in cleaned_text:
                cleaned_text = cleaned_text.split('```json')[1].split('```')[0]
            elif '```' in cleaned_text:
                cleaned_text = cleaned_text.split('```')[1]
            
            quiz_data = json.loads(cleaned_text)
            
            if not isinstance(quiz_data, list):
                raise ValueError("Expected list of questions")
            
            return quiz_data
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Parse error: {e}")
            return []

# Initialize advanced quiz generator
quiz_gen = QuizGenerator()

@_quiz_AI.route('/generate-advanced-quiz', methods=['POST'])
def generate_advanced_quiz():
    """Enhanced quiz generation endpoint with comprehensive controls"""
    try:
        data = request.json
        course_code = data.get('course_code', 'CUSTOM')
        custom_topic = data.get('custom_topic', '')
        num_questions = min(data.get('num_questions', 5), 20)
        difficulty = data.get('difficulty', 'medium')
        answer_method = data.get('answer_method', 'multiple_choice')
        
        if not custom_topic and course_code == 'CUSTOM':
            return jsonify({'error': 'Custom topic required when no course selected'}), 400
        
        # Generate advanced quiz
        quiz_data = quiz_gen.generate_advanced_quiz(
            course_code, custom_topic, num_questions, difficulty, answer_method
        )
        
        # Get course info
        course_info = quiz_gen.get_course_prompt_context(course_code, custom_topic)
        
        response_data = {
            'quiz': quiz_data,
            'metadata': {
                'course_code': course_code,
                'course_name': course_info['course_name'],
                'department': course_info['department'],
                'academic_level': course_info['level'],
                'num_questions_generated': len(quiz_data),
                'difficulty': difficulty,
                'answer_method': answer_method,
                'timestamp': datetime.now().isoformat(),
                'sources_referenced': course_info['sources']
            },
            'quality_metrics': {
                'questions_with_sources': sum(1 for q in quiz_data if q.get('source')),
                'average_difficulty': difficulty,
                'concepts_covered': list(set(q.get('concept', 'General') for q in quiz_data)),
                'bloom_levels': list(set(q.get('bloom_level', 'understand') for q in quiz_data))
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@_quiz_AI.route('/courses', methods=['GET'])
def get_courses():
    """Get all available courses and their details"""
    return jsonify({
        'courses': quiz_gen.university_courses,
        'answer_methods': quiz_gen.answer_methods,
        'difficulty_levels': quiz_gen.difficulty_levels
    })

@_quiz_AI.route('/course-details/<course_code>', methods=['GET'])
def get_course_details(course_code):
    """Get detailed information about a specific course"""
    course_code = course_code.upper()
    if course_code in quiz_gen.university_courses:
        return jsonify(quiz_gen.university_courses[course_code])
    else:
        return jsonify({'error': 'Course not found'}), 404

# Maintain original endpoints for backward compatibility
@_quiz_AI.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    """Original quiz generation endpoint (maintained for compatibility)"""
    try:
        data = request.json
        topic = data.get('topic', '')
        num_questions = data.get('num_questions', 5)
        difficulty = data.get('difficulty', 'Medium')
        style = data.get('style', 'Multiple Choice')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        # Map to new system
        answer_method_map = {
            'Multiple Choice': 'multiple_choice',
            'True/False': 'true_false', 
            'Fill-in-the-Blank': 'fill_blank'
        }
        
        quiz_data = quiz_gen.generate_advanced_quiz(
            course_code='CUSTOM',
            custom_topic=topic,
            num_questions=num_questions,
            difficulty=difficulty.lower(),
            answer_method=answer_method_map.get(style, 'multiple_choice')
        )
        
        return jsonify({'quiz': quiz_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@_quiz_AI.route('/')
def quiz():
    return render_template('quizAI.html')

@_quiz_AI.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Super Advanced Quiz Generator API',
        'version': '3.0',
        'features': [
            'University course integration',
            'Advanced difficulty controls', 
            'Multiple answer methods',
            'Academic source tracking',
            'Quality metrics',
            'Bloom\'s taxonomy integration'
        ],
        'supported_courses': len(quiz_gen.university_courses),
        'course_codes': list(quiz_gen.university_courses.keys())
    })

print("🚀 Super Advanced Quiz Generator Initialized Successfully!")
print("🎓 Features: Course Integration, Advanced Controls, Source Tracking")
print("📊 Supported Courses:", ', '.join(quiz_gen.university_courses.keys()))
print("🎯 Ready for Advanced Academic Quiz Generation!")