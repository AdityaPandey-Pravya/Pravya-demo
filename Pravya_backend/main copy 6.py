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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
logger.info(f"Gemini API Key configured: {'Yes' if GEMINI_API_KEY else 'No'}")

try:
    genai.configure(api_key=GEMINI_API_KEY)
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

def determine_difficulty_progression(game_state: GameState) -> tuple:
    """Determine next question difficulty and use user's selected mastery"""
    
    # New progression: 2 medium, then 3 hard questions
    questions_answered = game_state.session_questions_answered
    
    if questions_answered < 2:
        difficulty = "medium"
    else:
        difficulty = "hard"
    
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
    
    # Update experience and streak
    if is_correct:
        game_state.experience_points += int(score)
        game_state.streak_count += 1
        # Boost team trust slightly
        for char in game_state.team_trust:
            game_state.team_trust[char] = min(100, game_state.team_trust[char] + 2)
    else:
        game_state.streak_count = 0
        # Decrease team trust slightly
        for char in game_state.team_trust:
            game_state.team_trust[char] = max(0, game_state.team_trust[char] - 5)
    
    # Update performance score (rolling average)
    game_state.performance_score = (game_state.performance_score * 0.8) + (score * 0.2)
    
    # Level progression
    xp_for_next_level = game_state.player_level * 200
    if game_state.experience_points >= xp_for_next_level:
        game_state.player_level += 1
        game_state.boss_battle_ready = True
    
    # Badge system
    new_badges = []
    if game_state.streak_count == 3 and "code_warrior" not in game_state.badges:
        new_badges.append("code_warrior")
    if game_state.streak_count == 5 and "debugging_master" not in game_state.badges:
        new_badges.append("debugging_master")
    if score >= 95 and "perfectionist" not in game_state.badges:
        new_badges.append("perfectionist")
    if game_state.performance_score >= 90 and "elite_developer" not in game_state.badges:
        new_badges.append("elite_developer")
    
    game_state.badges.extend(new_badges)
    game_state.current_question_index += 1
    game_state.session_questions_answered += 1
    
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
        if game_state.boss_battle_ready and game_state.player_level % 3 == 0:
            # TODO: Implement boss battle logic
            is_boss_battle = True
            urgency_level = "critical"
            time_limit = 300  # 5 minutes for boss battles
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
        # Get question data for evaluation
        question_data = supabase.table("questions").select("*").eq("id", submission.question_id).execute()
        
        if not question_data.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
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
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            story_continuation=story_continuation,
            updated_game_state=updated_game_state,
            achievement_unlocked=achievement_unlocked,
            session_complete=session_complete
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating answer: {str(e)}")

@app.get("/player_stats/{player_id}")
async def get_player_stats(player_id: str):
    """Get player statistics and progress"""
    # TODO: Implement player persistence
    return {"message": "Player stats endpoint - to be implemented"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)