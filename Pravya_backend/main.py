from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import google.generativeai as genai
import os
from supabase import create_client, Client
import json
import random
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="DevStorm Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

logger.info(f"Initializing Supabase connection...")
logger.info(f"Supabase URL configured: {'Yes' if SUPABASE_URL else 'No'}")
logger.info(f"Supabase Key configured: {'Yes' if SUPABASE_KEY else 'No'}")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Supabase: {str(e)}")
    supabase = None

# Initialize Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
logger.info(f"Gemini API Key configured: {'Yes' if GOOGLE_API_KEY else 'No'}")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    logger.info("✅ Gemini AI client initialized successfully")
    
    # Test Gemini connection
    test_response = model.generate_content("Hello")
    logger.info("✅ Gemini API connection test successful")
except Exception as e:
    logger.error(f"❌ Failed to initialize Gemini: {str(e)}")
    model = None

# Pydantic models
class GameState(BaseModel):
    player_level: int = 1
    experience_points: int = 0
    current_question_index: int = 0
    performance_score: float = 100.0
    streak_count: int = 0
    badges: List[str] = []
    team_trust: Dict[str, float] = {"senior_dev": 100.0, "security_lead": 100.0, "junior_dev": 100.0}
    story_path: str = "normal"
    boss_battle_ready: bool = False
    session_questions_answered: int = 0
    selected_mastery: str = "python"  # New field for user's subject choice

class QuestionRequest(BaseModel):
    game_state: GameState
    
class AnswerSubmission(BaseModel):
    game_state: GameState
    user_answer: str
    question_id: str
    time_taken: Optional[int] = None

class StoryResponse(BaseModel):
    narrative: str
    question: Dict[str, Any]
    updated_game_state: GameState
    is_boss_battle: bool = False
    urgency_level: str = "medium"
    time_limit: Optional[int] = None

class HintRequest(BaseModel):
    game_state: GameState
    question_id: str

class HintResponse(BaseModel):
    hints: List[Dict[str, Any]]  # List of hints from each teammate
    updated_game_state: GameState

class TrustDecision(BaseModel):
    game_state: GameState
    question_id: str
    trusted_teammate: str  # Which teammate's advice they trust
    
class TrustDecisionResponse(BaseModel):
    is_correct_trust: bool
    consequences: str
    updated_game_state: GameState

class EvaluationResponse(BaseModel):
    is_correct: bool
    score: float
    feedback: str
    story_continuation: str  # New field for story response
    updated_game_state: GameState
    achievement_unlocked: Optional[str] = None
    session_complete: bool = False  # New field to indicate if demo is complete

# Character personas and team dynamics
CHARACTERS = {
    "senior_dev": {
        "name": "Alex Chen",
        "role": "Senior Backend Developer",
        "personality": "analytical, mentoring, prefers efficiency"
    },
    "security_lead": {
        "name": "Maya Rodriguez", 
        "role": "Cybersecurity Lead",
        "personality": "vigilant, direct, security-focused"
    },
    "junior_dev": {
        "name": "Jordan Kim",
        "role": "Junior Frontend Developer", 
        "personality": "eager, asks questions, learns from you"
    }
}

# Story scenarios based on tech concepts
SCENARIO_TEMPLATES = {
    "inheritance": "The legacy authentication system needs urgent refactoring. The old UserAccount class is being inherited by multiple subclasses, but they're not properly calling parent initialization.",
    "virtual_env": "A critical deployment failed because of dependency conflicts. The DevOps team needs you to explain proper environment isolation to prevent future disasters.",
    "algorithms": "The customer database is responding slowly during peak hours. We need to optimize the search algorithm before the next traffic surge.",
    "react_hooks": "The user interface is experiencing state management issues causing data loss. The frontend team needs immediate guidance on proper React patterns.",
    "data_structures": "Memory usage is spiking on our main servers. We need to restructure how we're storing and accessing user data."
}

def get_question_from_db(difficulty_level: str, mastery: str) -> Dict[str, Any]:
    """Fetch question from Supabase based on difficulty and mastery"""
    logger.info(f"🔍 Fetching question: difficulty={difficulty_level}, mastery={mastery}")
    
    # Handle boss battles
    if difficulty_level == "boss":
        return generate_boss_battle_question(mastery)
    
    try:
        if not supabase:
            logger.error("❌ Supabase client not initialized")
            raise HTTPException(status_code=500, detail="Database connection not available")
            
        result = supabase.table("questions").select("*").eq("mastery", mastery).eq("difficulty_level", difficulty_level).execute()
        logger.info(f"📊 Database query result: {len(result.data) if result.data else 0} questions found")
        
        if result.data:
            selected_question = random.choice(result.data)
            logger.info(f"✅ Selected question: {selected_question['id']}")
            return selected_question
        else:
            # Fallback to any question of that mastery
            logger.warning(f"⚠️ No questions found for {difficulty_level}-{mastery}, trying fallback")
            result = supabase.table("questions").select("*").eq("mastery", mastery).execute()
            if result.data:
                selected_question = random.choice(result.data)
                logger.info(f"✅ Fallback question selected: {selected_question['id']}")
                return selected_question
            else:
                logger.error(f"❌ No questions found for mastery: {mastery}")
                return None
            
    except Exception as e:
        logger.error(f"❌ Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def generate_boss_battle_question(mastery: str) -> Dict[str, Any]:
    """Generate a boss battle question for the final challenge"""
    
    boss_questions = {
        "python": {
            "id": "boss-python-1",
            "mastery": "python",
            "difficulty_level": "boss",
            "difficulty_rating": 95,
            "title": "The Null Pointer Phantom - Final Confrontation",
            "question_text": "The rogue AI has corrupted our core authentication system with subtle vulnerabilities. Design a secure authentication function that properly handles edge cases, validates input, and prevents common security flaws like SQL injection, timing attacks, and null pointer exceptions.",
            "expected_outcome": "A robust authentication function that: 1) Validates all inputs, 2) Uses secure password comparison (constant-time), 3) Handles null/empty inputs gracefully, 4) Prevents injection attacks, 5) Implements proper error handling without information leakage"
        },
        "react": {
            "id": "boss-react-1", 
            "mastery": "react",
            "difficulty_level": "boss", 
            "difficulty_rating": 95,
            "title": "The State Corruption Demon - Component Crisis",
            "question_text": "The AI has injected malicious state mutations into our React application, causing memory leaks and infinite re-renders. Create a secure, optimized React component that handles complex state updates, prevents unnecessary re-renders, and implements proper cleanup to defeat the corruption.",
            "expected_outcome": "A React component that: 1) Uses proper hooks (useState, useEffect, useMemo), 2) Implements cleanup in useEffect, 3) Prevents infinite re-render loops, 4) Optimizes performance with proper dependencies, 5) Handles error boundaries"
        },
        "mathematics": {
            "id": "boss-math-1",
            "mastery": "mathematics", 
            "difficulty_level": "boss",
            "difficulty_rating": 95,
            "title": "The Algorithm Overlord - Complexity Chaos", 
            "question_text": "The AI is overwhelming our systems with exponential-time algorithms disguised as efficient solutions. Design an optimal algorithm that solves a complex problem (like finding shortest paths in a weighted graph) with the best possible time complexity while proving your solution is mathematically sound.",
            "expected_outcome": "An optimal algorithm that: 1) Achieves the theoretical best time complexity, 2) Includes mathematical proof of correctness, 3) Handles edge cases properly, 4) Demonstrates understanding of algorithmic trade-offs, 5) Shows space complexity analysis"
        }
    }
    
    return boss_questions.get(mastery, boss_questions["python"])

def determine_difficulty_progression(game_state: GameState) -> tuple:
    """Determine next question difficulty and use user's selected mastery"""
    
    # New progression: 2 medium, then 2 hard, then 1 boss battle
    questions_answered = game_state.session_questions_answered
    
    if questions_answered < 2:
        difficulty = "medium"
    elif questions_answered < 4:
        difficulty = "hard"
    else:
        # Question 5 is always a boss battle
        difficulty = "boss"
    
    # Use user's selected mastery instead of rotating
    mastery = game_state.selected_mastery
    
    logger.info(f"🎯 Difficulty progression: question #{questions_answered + 1}, level={game_state.player_level}, performance={game_state.performance_score:.1f}% -> {difficulty}/{mastery}")
    
    return difficulty, mastery

def generate_story_continuation(is_correct: bool, question_data: Dict[str, Any], game_state: GameState, user_answer: str, score: float) -> str:
    """Generate story continuation based on user's answer performance"""
    
    logger.info(f"🎭 Generating story continuation: correct={is_correct}, score={score}")
    
    # Determine story outcome and team reactions
    if is_correct:
        if score >= 90:
            outcome_type = "exceptional"
        elif score >= 75:
            outcome_type = "success"
        else:
            outcome_type = "partial_success"
    else:
        if score >= 50:
            outcome_type = "near_miss"
        else:
            outcome_type = "failure"
    
    # Character reactions based on trust levels and outcome
    character_reactions = []
    for char_id, trust in game_state.team_trust.items():
        char = CHARACTERS[char_id]
        if trust > 80:
            character_reactions.append(f"{char['name']} (trusted ally)")
        elif trust < 50:
            character_reactions.append(f"{char['name']} (suspicious)")
        else:
            character_reactions.append(f"{char['name']} (neutral)")
    
    prompt = f"""
You are continuing an immersive tech thriller story. Generate a realistic immediate reaction/consequence to the developer's solution attempt.

CONTEXT:
- Question: {question_data['title']} ({question_data['mastery']})
- User's Performance: {outcome_type} (score: {score}/100)
- Session Progress: {game_state.session_questions_answered + 1}/5 questions
- Team Trust Levels: {', '.join(character_reactions)}
- Current Streak: {game_state.streak_count}

STORY REQUIREMENTS:
1. Write immediate consequence of the solution deployment (2-3 sentences max)
2. Include realistic team member reactions based on outcome
3. Show system status change (success/failure indicators)
4. Build tension for next challenge if continuing
5. If this was question 5/5, provide a satisfying session conclusion

OUTCOME SCENARIOS:
- exceptional: "System secured! Outstanding implementation!"
- success: "Solution deployed successfully. Crisis contained."
- partial_success: "Solution works but has minor issues. Monitoring required."
- near_miss: "Solution partially failed. Quick patch needed."
- failure: "Critical failure! System still compromised!"

TONE: Immediate, realistic tech team communication during crisis

Generate the story continuation (max 150 words):
"""

    try:
        logger.info("🤖 Calling Gemini API for story continuation...")
        if not model:
            logger.error("❌ Gemini model not initialized for story continuation")
            return generate_fallback_story_continuation(is_correct, outcome_type, game_state)
            
        response = model.generate_content(prompt)
        logger.info("✅ Story continuation generated successfully")
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"❌ Story continuation generation failed: {str(e)}")
        return generate_fallback_story_continuation(is_correct, outcome_type, game_state)

def generate_fallback_story_continuation(is_correct: bool, outcome_type: str, game_state: GameState) -> str:
    """Fallback story continuation when LLM fails"""
    
    if is_correct:
        success_messages = [
            "✅ **Alex Chen:** 'Excellent work! System stabilizing... threat neutralized for now.'",
            "✅ **Maya Rodriguez:** 'Clean implementation. Security protocols holding steady.'",
            "✅ **Jordan Kim:** 'Wow, that actually worked! Learning so much from your approach.'"
        ]
        return f"{success_messages[game_state.session_questions_answered % len(success_messages)]}\n\n*System status: SECURED* 🛡️"
    else:
        failure_messages = [
            "❌ **Alex Chen:** 'That's not going to work! We need a different approach, fast!'",
            "❌ **Maya Rodriguez:** 'Still seeing intrusion patterns. Try again!'",
            "❌ **Jordan Kim:** 'The system rejected that solution. What are we missing?'"
        ]
        return f"{failure_messages[game_state.session_questions_answered % len(failure_messages)]}\n\n*System status: STILL COMPROMISED* ⚠️"

def generate_immersive_narrative(question_data: Dict[str, Any], game_state: GameState) -> str:
    """Generate story narrative that naturally integrates the technical question"""
    
    logger.info(f"🎭 Generating narrative for question: {question_data['id']}")
    
    # Determine current scenario context
    story_tension = "high" if game_state.performance_score < 60 else "medium"
    team_morale = "concerned" if any(trust < 70 for trust in game_state.team_trust.values()) else "confident"
    
    # Build character context based on trust levels
    character_context = ""
    for char_id, trust in game_state.team_trust.items():
        char = CHARACTERS[char_id]
        if trust < 50:
            character_context += f"{char['name']} ({char['role']}) seems suspicious lately. "
        elif trust > 90:
            character_context += f"{char['name']} ({char['role']}) has your complete trust. "
    
    prompt = f"""
You are a master storyteller creating an immersive tech thriller narrative. Generate a compelling scenario for this coding challenge:

CONTEXT:
- Player Level: {game_state.player_level}
- Performance Score: {game_state.performance_score}%
- Story Tension: {story_tension}
- Team Morale: {team_morale}
- Current Streak: {game_state.streak_count}
- Questions Answered: {game_state.session_questions_answered}

TECHNICAL CHALLENGE:
- Title: {question_data['title']}
- Mastery: {question_data['mastery']}
- Difficulty: {question_data['difficulty_level']}
- Original Question: {question_data['question_text']}

TEAM DYNAMICS:
{character_context}

STORY REQUIREMENTS:
1. Create a urgent, realistic development crisis at NeoTech Corp
2. The technical question must feel like a natural solution to the crisis
3. Integrate team members naturally - make their dialogue feel authentic
4. Adapt the original question terminology to fit the story (change generic examples to story-relevant ones)
**For Mathematical quesiton, you can change the terminologies, but keep the numeric value same as the original question**
**For example : You bought a book for $15, which was 75% of its original price. What was the original price?(original Question) to make it fit in story you can change book to petawatts of charge but keep the numeric value of 15 and 75%
5. Build suspense about potential system infiltration by rogue AIs
6. Keep narrative concise but engaging (max 200 words)
7. End with the technical challenge that needs immediate solution
** You should never ask the question in a direct way or at the end of your story narration, the question should be blended with the story narration, So that user have to read the story and find the question within it.**
** Question information should be scattered in the entire narration, so that it does not feel like the story narration is useless, and the user simply reads the last paragraph of the narration to solve the question.**
TONE: Professional but urgent, with underlying tension about AI threats

Generate the narrative that leads naturally to the technical question:
"""

    try:
        logger.info("🤖 Calling Gemini API for narrative generation...")
        if not model:
            logger.error("❌ Gemini model not initialized")
    except Exception as e:
        print(e)
    def generate_boss_battle_narrative(question_data: Dict[str, Any], game_state: GameState) -> str:
        """Generate epic boss battle narrative"""

        logger.info(f"🔥 Generating boss battle narrative for: {question_data['id']}")

        boss_names = {
            "python": "The Null Pointer Phantom",
            "react": "The State Corruption Demon", 
            "mathematics": "The Algorithm Overlord"
        }

        boss_name = boss_names.get(question_data['mastery'], "The Code Destroyer")

        prompt = f"""
You are crafting the climactic boss battle scene of a tech thriller. This is the final confrontation!

CONTEXT:
- Player has completed 4 challenges and proven their skills
- Performance Score: {game_state.performance_score}%
- Team Trust: {"High" if all(trust > 70 for trust in game_state.team_trust.values()) else "Mixed"}
- Final Boss: {boss_name}

BOSS BATTLE SCENARIO:
- Title: {question_data['title']}
- The AI has revealed its true form and is making its final assault
- This is a direct confrontation between human ingenuity and artificial corruption
- The fate of NeoTech Corp and the digital realm hangs in the balance

STORY REQUIREMENTS:
1. Create an epic, cinematic opening to the boss battle (max 30 words)
2. Show the boss AI taunting the player with corrupted code/logic
3. Build maximum tension - this is the final showdown
4. Include dramatic team support and rallying 
5. End with the ultimate technical challenge that will determine victory

TONE: Epic, high-stakes, cinematic boss battle with tech terminology

Generate the boss battle introduction:
"""

    try:
        if not model:
            return f"🔥 **FINAL BOSS BATTLE!** {boss_name} emerges from the corrupted systems! This is your ultimate test - defeat the AI corruption with perfect code!"
            
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"❌ Boss battle narrative generation failed: {str(e)}")
        return f"🔥 **FINAL BOSS BATTLE!** {boss_name} has taken control of the core systems! Only flawless implementation can stop the digital apocalypse!"
            
        response = model.generate_content(prompt)
        logger.info("✅ Gemini API call successful")
        logger.info(f"📝 Generated narrative length: {len(response.text)} characters")
        return response.text
    except Exception as e:
        logger.error(f"❌ Gemini API call failed: {str(e)}")
        return f"URGENT: System crisis detected! {question_data['title']} requires immediate attention. {question_data['question_text']}"
    """Generate story narrative that naturally integrates the technical question"""
    
    logger.info(f"🎭 Generating narrative for question: {question_data['id']}")
    
    # Determine current scenario context
    story_tension = "high" if game_state.performance_score < 60 else "medium"
    team_morale = "concerned" if any(trust < 70 for trust in game_state.team_trust.values()) else "confident"
    
    # Build character context based on trust levels
    character_context = ""
    for char_id, trust in game_state.team_trust.items():
        char = CHARACTERS[char_id]
        if trust < 50:
            character_context += f"{char['name']} ({char['role']}) seems suspicious lately. "
        elif trust > 90:
            character_context += f"{char['name']} ({char['role']}) has your complete trust. "
    
    prompt = f"""
You are a master storyteller creating an immersive tech thriller narrative. Generate a compelling scenario for this coding challenge:

CONTEXT:
- Player Level: {game_state.player_level}
- Performance Score: {game_state.performance_score}%
- Story Tension: {story_tension}
- Team Morale: {team_morale}
- Current Streak: {game_state.streak_count}
- Questions Answered: {game_state.session_questions_answered}

TECHNICAL CHALLENGE:
- Title: {question_data['title']}
- Mastery: {question_data['mastery']}
- Difficulty: {question_data['difficulty_level']}
- Original Question: {question_data['question_text']}

TEAM DYNAMICS:
{character_context}

STORY REQUIREMENTS:
1. Create a urgent, realistic development crisis at NeoTech Corp
2. The technical question must feel like a natural solution to the crisis
3. Integrate team members naturally - make their dialogue feel authentic
4. Adapt the original question terminology to fit the story (change generic examples to story-relevant ones)
   **For Mathematical quesiton, you can change the terminologies, but keep the numeric value same as the original question**
5. Build suspense about potential system infiltration by rogue AIs
6. Keep narrative concise but engaging (max 200 words)
7. End with the technical challenge that needs immediate solution

TONE: Professional but urgent, with underlying tension about AI threats

Generate the narrative that leads naturally to the technical question:
"""

    try:
        logger.info("🤖 Calling Gemini API for narrative generation...")
        if not model:
            logger.error("❌ Gemini model not initialized")
            return f"URGENT: System crisis detected! {question_data['title']} requires immediate attention. {question_data['question_text']}"
            
        response = model.generate_content(prompt)
        logger.info("✅ Gemini API call successful")
        logger.info(f"📝 Generated narrative length: {len(response.text)} characters")
        return response.text
    except Exception as e:
        logger.error(f"❌ Gemini API call failed: {str(e)}")
        return f"URGENT: System crisis detected! {question_data['title']} requires immediate attention. {question_data['question_text']}"

def evaluate_user_answer(user_answer: str, question_data: Dict[str, Any], game_state: GameState) -> tuple:
    """Use LLM to evaluate user's code/answer against expected outcome"""
    
    logger.info(f"🔍 Evaluating answer for question: {question_data['id']}")
    logger.info(f"📝 Answer length: {len(user_answer)} characters")
    
    prompt = f"""
You are an expert code reviewer evaluating a developer's solution during a critical system emergency.

ORIGINAL CHALLENGE:
{question_data['question_text']}

EXPECTED SOLUTION CRITERIA:
{question_data['expected_outcome']}

USER'S SUBMITTED SOLUTION:
{user_answer}

EVALUATION CRITERIA:
1. Correctness: Does the solution address the core problem?
2. Code Quality: Is it readable, efficient, and following best practices?
3. Completeness: Does it meet all requirements from expected outcome?
4. Emergency Context: Is this solution deployable in a crisis situation?

You MUST respond with ONLY a valid JSON object in this exact format (no extra text, no markdown formatting):
{{"is_correct": true, "score": 85, "feedback": "Solution correctly implements the required functionality with good coding practices."}}

The JSON must be valid and parseable. Do not include any text before or after the JSON.
"""

    try:
        logger.info("🤖 Calling Gemini API for answer evaluation...")
        if not model:
            logger.error("❌ Gemini model not initialized for evaluation")
            # Fallback evaluation
            is_correct = len(user_answer.strip()) > 10
            score = 75 if is_correct else 25
            feedback = f"Emergency evaluation complete. {'Solution accepted' if is_correct else 'Solution needs revision'} - API unavailable"
            return is_correct, score, feedback
            
        response = model.generate_content(prompt)
        logger.info("✅ Gemini evaluation API call successful")
        logger.info(f"📋 Raw response: {response.text[:200]}...")  # Log first 200 chars
        
        # Clean up the response text
        response_text = response.text.strip()
        
        # Remove any markdown formatting
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()
        
        # Find the JSON object in the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_text = response_text[start_idx:end_idx]
            logger.info(f"📊 Extracted JSON: {json_text}")
            
            try:
                evaluation = json.loads(json_text)
                logger.info(f"📊 Evaluation result: correct={evaluation.get('is_correct', False)}, score={evaluation.get('score', 0)}")
                
                # Validate required fields
                is_correct = evaluation.get('is_correct', False)
                score = evaluation.get('score', 0)
                feedback = evaluation.get('feedback', 'Evaluation completed')
                
                return is_correct, score, feedback
                
            except json.JSONDecodeError as json_error:
                logger.error(f"❌ JSON parsing failed: {str(json_error)}")
                logger.error(f"📋 Problematic JSON: {json_text}")
                
                # Try to extract basic info from text response
                is_correct = 'true' in response_text.lower() or 'correct' in response_text.lower()
                
                # Extract score if possible
                import re
                score_match = re.search(r'"score":\s*(\d+)', response_text)
                score = int(score_match.group(1)) if score_match else (80 if is_correct else 40)
                
                feedback = "Solution evaluated - see detailed analysis above"
                return is_correct, score, feedback
        else:
            logger.error("❌ No valid JSON found in response")
            # Fallback evaluation based on content analysis
            is_correct = len(user_answer.strip()) > 10 and ('=' in user_answer or 'def' in user_answer)
            score = 75 if is_correct else 25
            feedback = "Emergency evaluation: Basic syntax check completed"
            return is_correct, score, feedback
            
    except Exception as e:
        logger.error(f"❌ Gemini evaluation failed: {str(e)}")
        # Advanced fallback evaluation
        is_correct = analyze_code_quality(user_answer, question_data)
        score = 75 if is_correct else 25
        feedback = f"Emergency evaluation complete. {'Solution appears functional' if is_correct else 'Solution needs revision'}"
        return is_correct, score, feedback

def analyze_code_quality(user_answer: str, question_data: Dict[str, Any]) -> bool:
    """Fallback code analysis when LLM evaluation fails"""
    try:
        # Basic quality checks
        code = user_answer.strip()
        
        # Check if it's not empty
        if len(code) < 5:
            return False
        
        # Check for basic Python syntax elements
        has_assignment = '=' in code and not code.count('=') == code.count('==')
        has_keywords = any(keyword in code for keyword in ['def', 'class', 'if', 'for', 'while', 'in', 'import'])
        has_comments = '#' in code
        
        # For the specific question type, check for relevant patterns
        question_text = question_data.get('question_text', '').lower()
        if 'list' in question_text or 'array' in question_text:
            has_list_operations = any(op in code for op in ['[', ']', 'append', 'in'])
            return has_assignment and (has_keywords or has_list_operations)
        
        return has_assignment and len(code) > 20
        
    except Exception:
        return len(user_answer.strip()) > 10

def update_game_state_after_answer(game_state: GameState, is_correct: bool, score: float) -> GameState:
    """Update game state based on answer evaluation"""
    
    try:
        # Create a new GameState object with updated values
        updated_state = GameState(
            player_level=game_state.player_level,
            experience_points=game_state.experience_points,
            current_question_index=game_state.current_question_index,
            performance_score=game_state.performance_score,
            streak_count=game_state.streak_count,
            badges=list(game_state.badges),  # Create new list
            team_trust=dict(game_state.team_trust),  # Create new dict
            story_path=game_state.story_path,
            boss_battle_ready=game_state.boss_battle_ready,
            session_questions_answered=game_state.session_questions_answered,
            selected_mastery=game_state.selected_mastery
        )
        
        # Update experience and streak
        if is_correct:
            updated_state.experience_points += int(score)
            updated_state.streak_count += 1
            # Boost team trust slightly
            for char in updated_state.team_trust:
                updated_state.team_trust[char] = min(100.0, updated_state.team_trust[char] + 2.0)
        else:
            updated_state.streak_count = 0
            # Decrease team trust slightly
            for char in updated_state.team_trust:
                updated_state.team_trust[char] = max(0.0, updated_state.team_trust[char] - 5.0)
        
        # Update performance score (rolling average)
        updated_state.performance_score = (updated_state.performance_score * 0.8) + (score * 0.2)
        
        # Level progression
        xp_for_next_level = updated_state.player_level * 200
        if updated_state.experience_points >= xp_for_next_level:
            updated_state.player_level += 1
            updated_state.boss_battle_ready = True
        
        # Badge system
        new_badges = []
        if updated_state.streak_count == 3 and "code_warrior" not in updated_state.badges:
            new_badges.append("code_warrior")
        if updated_state.streak_count == 5 and "debugging_master" not in updated_state.badges:
            new_badges.append("debugging_master")
        if score >= 95 and "perfectionist" not in updated_state.badges:
            new_badges.append("perfectionist")
        if updated_state.performance_score >= 90 and "elite_developer" not in updated_state.badges:
            new_badges.append("elite_developer")
        
        updated_state.badges.extend(new_badges)
        updated_state.current_question_index += 1
        updated_state.session_questions_answered += 1
        
        logger.info(f"🎮 Game state updated: XP={updated_state.experience_points}, Level={updated_state.player_level}, Performance={updated_state.performance_score:.1f}%")
        
        return updated_state
        
    except Exception as e:
        logger.error(f"❌ Error updating game state: {str(e)}")
        # Return original state if update fails
        return game_state

@app.get("/")
async def root():
    return {"message": "DevStorm Backend API is running!"}

@app.post("/get_next_question", response_model=StoryResponse)
async def get_next_question(request: QuestionRequest):
    """Generate next question with immersive narrative"""
    
    try:
        game_state = request.game_state
        
        # Check if it's boss battle time
        if game_state.boss_battle_ready or game_state.session_questions_answered >= 4:
            is_boss_battle = True
            urgency_level = "critical"
            time_limit = 600  # 10 minutes for boss battles
        else:
            is_boss_battle = False
            urgency_level = "high" if game_state.performance_score < 60 else "medium"
            time_limit = None
        
        # Get appropriate question
        difficulty, mastery = determine_difficulty_progression(game_state)
        question_data = get_question_from_db(difficulty, mastery)
        
        if not question_data:
            raise HTTPException(status_code=404, detail="No suitable question found")
        
        # Generate immersive narrative
        if is_boss_battle:
            narrative = generate_boss_battle_narrative(question_data, game_state)
        else:
            narrative = generate_immersive_narrative(question_data, game_state)
        
        # Adapt question text to story context
        adapted_question = question_data['question_text']
        # Replace generic terms with story-specific ones
        adapted_question = adapted_question.replace("example", "NeoTech system")
        adapted_question = adapted_question.replace("Provide an example", "Show how you would implement this for our crisis")
        
        response = StoryResponse(
            narrative=narrative,
            question={
                "id": question_data["id"],
                "title": question_data["title"],
                "text": adapted_question,
                "mastery": question_data["mastery"],
                "difficulty": question_data["difficulty_level"],
                "difficulty_rating": question_data["difficulty_rating"]
            },
            updated_game_state=game_state,
            is_boss_battle=is_boss_battle,
            urgency_level=urgency_level,
            time_limit=time_limit
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")

@app.post("/submit_answer", response_model=EvaluationResponse)
async def submit_answer(submission: AnswerSubmission):
    """Evaluate user's answer and update game state"""
    
    try:
        question = None
        # Check if the question is a boss battle question
        if "boss" in submission.question_id:
            # If so, generate the question data locally instead of calling the DB
            logger.info(f"🐲 Handling boss battle question: {submission.question_id}")
            question = generate_boss_battle_question(submission.game_state.selected_mastery)
        else:
            # Otherwise, fetch the question from Supabase
            question_data = supabase.table("questions").select("*").eq("id", submission.question_id).execute()
            if not question_data.data:
                raise HTTPException(status_code=404, detail=f"Question with ID '{submission.question_id}' not found")
            question = question_data.data[0]
        
        # Evaluate answer using LLM
        is_correct, score, feedback = evaluate_user_answer(
            submission.user_answer, 
            question, 
            submission.game_state
        )
        
        # Update game state
        updated_game_state = update_game_state_after_answer(
            submission.game_state, 
            is_correct, 
            score
        )
        
        # Generate story continuation
        story_continuation = generate_story_continuation(
            is_correct,
            question,
            updated_game_state,
            submission.user_answer,
            score
        )
        
        # Check for new achievements
        achievement_unlocked = None
        if len(updated_game_state.badges) > len(submission.game_state.badges):
            new_badges = set(updated_game_state.badges) - set(submission.game_state.badges)
            achievement_unlocked = list(new_badges)[0]
        
        # Check if session is complete (5 questions answered)
        session_complete = updated_game_state.session_questions_answered >= 5
        
        response = EvaluationResponse(
            is_correct=bool(is_correct),
            score=float(score),
            feedback=str(feedback),
            story_continuation=str(story_continuation),
            updated_game_state=updated_game_state,
            achievement_unlocked=achievement_unlocked,
            session_complete=bool(session_complete)
        )
        
        return response

    # Improved exception handling
    except HTTPException as http_exc:
        # Re-raise HTTPException so FastAPI can handle it
        raise http_exc
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred in submit_answer: {str(e)}")
        # Return a proper HTTP 500 error instead of letting the function crash
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

def generate_team_hints(question_data: Dict[str, Any], game_state: GameState) -> List[Dict[str, Any]]:
    """Generate hints from all three teammates - one will be deliberately wrong"""
    
    logger.info(f"💡 Generating team hints for question: {question_data['id']}")
    
    # Determine which teammate gives wrong advice (randomly)
    wrong_advisor = random.choice(["senior_dev", "security_lead", "junior_dev"])
    logger.info(f"🎭 Wrong advisor selected: {wrong_advisor}")
    
    prompt = f"""
Generate three hints for this technical challenge. ONE hint should be subtly wrong or misleading.

QUESTION:
{question_data['question_text']}

EXPECTED SOLUTION:
{question_data['expected_outcome']}

CHARACTER PERSONAS:
- Alex Chen (Senior Developer): Analytical, focuses on efficiency and best practices
- Maya Rodriguez (Security Lead): Security-focused, thinks about vulnerabilities 
- Jordan Kim (Junior Developer): Eager but sometimes overthinks, asks questions

HINT REQUIREMENTS:
1. Generate one hint from each character's perspective
2. Two hints should be helpful and correct
3. ONE hint (from {CHARACTERS[wrong_advisor]['name']}) should be SUBTLY wrong - not obviously bad, but misleading
4. Each hint should be 1-2 sentences, in character voice
5. The wrong hint should seem plausible but lead to issues

Return as JSON array:
[
  {{"character": "alex_chen", "hint": "...", "is_correct": true}},
  {{"character": "maya_rodriguez", "hint": "...", "is_correct": true}},  
  {{"character": "jordan_kim", "hint": "...", "is_correct": false}}
]

Make the wrong hint subtle and believable!
"""

    try:
        if not model:
            return generate_fallback_hints(question_data, wrong_advisor)
            
        response = model.generate_content(prompt)
        hints_text = response.text.strip()
        
        # Clean and parse JSON
        if hints_text.startswith('```json'):
            hints_text = hints_text.replace('```json', '').replace('```', '').strip()
        
        start_idx = hints_text.find('[')
        end_idx = hints_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_text = hints_text[start_idx:end_idx]
            hints = json.loads(json_text)
            
            # Validate and ensure we have exactly one wrong hint
            wrong_count = sum(1 for hint in hints if not hint.get('is_correct', True))
            if wrong_count != 1:
                logger.warning(f"⚠️ Wrong hint count: {wrong_count}, using fallback")
                return generate_fallback_hints(question_data, wrong_advisor)
            
            logger.info(f"✅ Generated {len(hints)} hints with 1 wrong advice")
            return hints
        else:
            logger.error("❌ Invalid JSON format in hints response")
            return generate_fallback_hints(question_data, wrong_advisor)
            
    except Exception as e:
        logger.error(f"❌ Hint generation failed: {str(e)}")
        return generate_fallback_hints(question_data, wrong_advisor)

def generate_fallback_hints(question_data: Dict[str, Any], wrong_advisor: str) -> List[Dict[str, Any]]:
    """Fallback hint generation when LLM fails"""
    
    hints = [
        {
            "character": "alex_chen",
            "hint": "Focus on the core requirements first, then optimize for edge cases.",
            "is_correct": True
        },
        {
            "character": "maya_rodriguez", 
            "hint": "Don't forget to validate inputs and handle security implications.",
            "is_correct": True
        },
        {
            "character": "jordan_kim",
            "hint": "I think we should start with the most complex approach to be thorough.",
            "is_correct": False
        }
    ]
    
    # Make sure the wrong advisor gives the wrong hint
    for hint in hints:
        if hint["character"] == wrong_advisor.replace("_", "_"):
            hint["is_correct"] = False
        elif hint["is_correct"] == False and hint["character"] != wrong_advisor.replace("_", "_"):
            hint["is_correct"] = True
    
    return hints

@app.post("/get_team_hints", response_model=HintResponse)
async def get_team_hints(request: HintRequest):
    """Get hints from all three teammates"""
    
    try:
        # Get question data
        question_data = supabase.table("questions").select("*").eq("id", request.question_id).execute()
        
        if not question_data.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        question = question_data.data[0]
        
        # Generate hints
        hints = generate_team_hints(question, request.game_state)
        
        response = HintResponse(
            hints=hints,
            updated_game_state=request.game_state  # No changes for getting hints
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating hints: {str(e)}")

@app.post("/submit_trust_decision", response_model=TrustDecisionResponse)
async def submit_trust_decision(decision: TrustDecision):
    """Handle player's trust decision and apply consequences"""
    
    try:
        # Get question data
        question_data = supabase.table("questions").select("*").eq("id", decision.question_id).execute()
        
        if not question_data.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        question = question_data.data[0]
        
        # Generate hints to determine correct choice
        hints = generate_team_hints(question, decision.game_state)
        
        # Find if trusted teammate gave correct advice
        trusted_hint = None
        for hint in hints:
            if hint["character"] == decision.trusted_teammate:
                trusted_hint = hint
                break
        
        if not trusted_hint:
            raise HTTPException(status_code=400, detail="Invalid teammate selection")
        
        is_correct_trust = trusted_hint["is_correct"]
        updated_game_state = decision.game_state.copy()
        
        if is_correct_trust:
            # Trusted the right person - minor benefits
            consequences = f"✅ **Wise choice!** {CHARACTERS[decision.trusted_teammate]['name']} gives you a confident nod. The team's morale improves."
            
            # Small trust boost for chosen teammate
            if decision.trusted_teammate in updated_game_state.team_trust:
                updated_game_state.team_trust[decision.trusted_teammate] = min(100, 
                    updated_game_state.team_trust[decision.trusted_teammate] + 5)
        else:
            # Trusted the wrong person - apply repercussions
            repercussions = [
                "⚠️ **Bad Intel!** Following that advice wasted precious time. You lose 30 seconds from your submission window.",
                "💔 **Team Friction!** The other teammates notice your poor judgment. Trust levels drop across the board.", 
                "🎯 **Misdirection!** That advice sent you down the wrong path. Your confidence wavers, affecting your next solution quality."
            ]
            
            chosen_repercussion = random.choice(repercussions)
            consequences = f"❌ **Poor judgment!** {chosen_repercussion}"
            
            # Apply consequences to game state
            if "time" in chosen_repercussion.lower():
                # Time penalty (handled in frontend)
                pass
            elif "trust" in chosen_repercussion.lower():
                # Reduce all trust levels
                for teammate in updated_game_state.team_trust:
                    updated_game_state.team_trust[teammate] = max(0, 
                        updated_game_state.team_trust[teammate] - 10)
            elif "confidence" in chosen_repercussion.lower():
                # Performance penalty for next question
                updated_game_state.performance_score = max(0, 
                    updated_game_state.performance_score - 5)
        
        response = TrustDecisionResponse(
            is_correct_trust=is_correct_trust,
            consequences=consequences,
            updated_game_state=updated_game_state
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing trust decision: {str(e)}")

@app.get("/player_stats/{player_id}")
async def get_player_stats(player_id: str):
    """Get player statistics and progress"""
    # TODO: Implement player persistence
    return {"message": "Player stats endpoint - to be implemented"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)