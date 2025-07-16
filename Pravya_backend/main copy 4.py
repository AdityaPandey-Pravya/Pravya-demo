from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import google.generativeai as genai
import os
from supabase import create_client, Client
import json
from datetime import datetime
import random

# Initialize FastAPI app
app = FastAPI(title="CodeRealm Chronicles API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables with validation
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Validate environment variables
if not SUPABASE_URL:
    print("ERROR: SUPABASE_URL environment variable not set")
if not SUPABASE_KEY:
    print("ERROR: SUPABASE_KEY environment variable not set")
if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY environment variable not set")

# Initialize clients with error handling
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Supabase client: {e}")
    supabase = None

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    print("✅ Gemini API configured successfully")
except Exception as e:
    print(f"❌ Failed to configure Gemini API: {e}")

# Pydantic models
class GameState(BaseModel):
    user_id: str
    current_question_id: Optional[Union[int, str]] = None  # Allow both int and string
    score: int = 0
    level: int = 1
    guild: str = "Frontend Mystic"  # Frontend Mystic, Backend Paladin, Algorithm Assassin, DevOps Shaman
    experience_points: int = 0
    badges: List[str] = []
    consecutive_correct: int = 0
    team_trust: int = 50  # 0-100 scale
    current_mission: Optional[str] = None
    boss_battle_active: bool = False
    imposter_mode_active: bool = False

class QuestionRequest(BaseModel):
    game_state: GameState
    question_type: str  # "regular", "boss_battle", "imposter_detection"

class AnswerSubmission(BaseModel):
    game_state: GameState
    user_answer: str
    question_id: Union[int, str]  # Allow both int and string IDs
    time_taken: Optional[int] = None

class NarrativeResponse(BaseModel):
    story_content: str
    question_data: Dict[str, Any]
    updated_game_state: GameState
    hint_available: bool = True
    special_actions: List[str] = []

# Game configuration - Updated for your database schema
GUILD_SPECIALIZATIONS = {
    "Frontend Mystic": ["react", "javascript", "css", "html"],
    "Backend Paladin": ["python", "databases", "apis", "security"],
    "Algorithm Assassin": ["mathematics", "algorithms", "optimization"],
    "DevOps Shaman": ["deployment", "infrastructure", "monitoring", "python"]
}

BOSS_PERSONALITIES = {
    "CorruptorAI": {
        "description": "Introduces subtle logical errors and off-by-one mistakes",
        "weakness": "debugging and edge case testing",
        "attack_pattern": "presents working code with hidden bugs"
    },
    "ChaosBot": {
        "description": "Creates intentionally messy, unreadable code",
        "weakness": "code readability and best practices",
        "attack_pattern": "shows multiple terrible solutions to choose from"
    },
    "OptimizationDevil": {
        "description": "Writes working but horribly inefficient solutions",
        "weakness": "algorithm optimization and complexity analysis",
        "attack_pattern": "challenges you to improve performance"
    },
    "SecurityShadow": {
        "description": "Adds vulnerabilities and security flaws",
        "weakness": "security best practices and vulnerability detection",
        "attack_pattern": "presents code with security holes"
    }
}

class GameEngine:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def get_next_question(self, game_state: GameState) -> Dict[str, Any]:
        """Fetch the next appropriate question from Supabase based on game state"""
        try:
            print(f"🔍 Fetching question for level {game_state.level}, guild: {game_state.guild}")
            
            if not supabase:
                print("❌ Supabase client not available")
                # Return a fallback question
                return {
                    "id": 1,
                    "mastery": "python",
                    "difficulty_level": "intermediate",
                    "difficulty_rating": 30,
                    "title": "Factorial Function",
                    "question_text": "Write a function that calculates the factorial of a number.",
                    "expected_outcome": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
                }
            
            # Determine question difficulty based on level and performance
            difficulty_range = self._calculate_difficulty_range(game_state)
            print(f"🎯 Target difficulty range: {difficulty_range}")
            
            # Get guild-specific question types
            preferred_masteries = GUILD_SPECIALIZATIONS.get(game_state.guild, ["python"])
            print(f"🎨 Preferred masteries for {game_state.guild}: {preferred_masteries}")
            
            # Query Supabase for appropriate question
            try:
                response = supabase.table("questions").select("*").in_(
                    "mastery", preferred_masteries
                ).gte("difficulty_rating", difficulty_range[0]).lte("difficulty_rating", difficulty_range[1]).execute()
                
                print(f"📊 Found {len(response.data) if response.data else 0} matching questions")
                
            except Exception as db_error:
                print(f"❌ Database query failed: {db_error}")
                # Try a simpler query
                try:
                    response = supabase.table("questions").select("*").limit(10).execute()
                    print(f"📊 Fallback query found {len(response.data) if response.data else 0} questions")
                except Exception as fallback_error:
                    print(f"❌ Fallback query also failed: {fallback_error}")
                    response = None
            
            if not response or not response.data:
                print("⚠️ No questions found, using hardcoded fallback")
                # Return a hardcoded fallback question
                return {
                    "id": 999,
                    "mastery": "python",
                    "difficulty_level": "beginner",
                    "difficulty_rating": game_state.level * 10,
                    "title": "Find Maximum Element",
                    "question_text": "Create a function that finds the maximum element in a list.",
                    "expected_outcome": "def find_max(lst): return max(lst) if lst else None"
                }
            
            # Select random question from available options
            question = random.choice(response.data)
            print(f"✅ Selected question ID: {question.get('id')}, Mastery: {question.get('mastery')}")
            
            return question
            
        except Exception as e:
            print(f"💥 Unexpected error in get_next_question: {str(e)}")
            # Return emergency fallback
            return {
                "id": 888,
                "mastery": "general",
                "difficulty_level": "beginner",
                "difficulty_rating": 25,
                "title": "Simple Addition",
                "question_text": "Write a simple function that adds two numbers.",
                "expected_outcome": "def add(a, b): return a + b"
            }
    
    def _calculate_difficulty_range(self, game_state: GameState) -> tuple:
        """Calculate appropriate difficulty range based on game state"""
        base_difficulty = min(10 + (game_state.level - 1) * 5, 90)
        
        # Adjust based on recent performance
        if game_state.consecutive_correct >= 3:
            base_difficulty += 10  # Increase difficulty for good performance
        elif game_state.consecutive_correct == 0 and game_state.score > 0:
            base_difficulty -= 10  # Decrease for struggling players
        
        return (max(1, base_difficulty - 15), min(100, base_difficulty + 15))
    
    def generate_narrative(self, game_state: GameState, question: Dict[str, Any], 
                          question_type: str = "regular") -> str:
        """Generate immersive narrative that transforms the question into CodeRealm context"""
        
        print(f"🎭 Generating {question_type} narrative for question: {question.get('id')}")
        
        # Select appropriate prompt template based on question type
        if question_type == "boss_battle":
            prompt_template = self._get_boss_battle_prompt(game_state, question)
        elif question_type == "imposter_detection":
            prompt_template = self._get_imposter_prompt(game_state, question)
        else:
            prompt_template = self._get_regular_mission_prompt(game_state, question)
        
        try:
            print("🤖 Calling Gemini API...")
            response = self.model.generate_content(prompt_template)
            print("✅ Gemini API response received")
            return response.text
        except Exception as e:
            print(f"❌ LLM generation error: {str(e)}")
            # Return a fallback narrative
            return f"""
🚨 **URGENT MISSION ALERT** 🚨

Code Architect, the digital realm needs your expertise! A critical system component has malfunctioned in the {game_state.guild} sector.

**Mission Briefing:**
Your current objective involves solving a {question.get('subject', 'programming')} challenge that will restore system stability. The team is counting on your Level {game_state.level} expertise to resolve this situation.

**Technical Challenge:**
{question.get('question_text', 'System diagnostic required.')}

Time is of the essence! The fate of the digital realm depends on your coding prowess.

🎯 **Difficulty Level:** {question.get('difficulty', 'Unknown')}
⚡ **Guild Specialization:** {game_state.guild}

Prepare your solution, Code Architect. The realm awaits your expertise!
"""
    
    def _get_regular_mission_prompt(self, game_state: GameState, question: Dict[str, Any]) -> str:
        """Generate prompt for regular mission narratives"""
        return f"""
You are the Master Storyteller for CodeRealm Chronicles. Create a CONCISE, action-packed story where the coding challenge IS the exact action needed to save the situation.

THE GOLDEN RULE: The code solution must be the EXACT action needed in the story. No academic language - only immersive action.

STORY LENGTH LIMIT: 10-15 lines maximum. Every word must serve the story.

CURRENT GAME STATE:
- Player Level: {game_state.level}
- Guild: {game_state.guild}
- Consecutive Correct: {game_state.consecutive_correct}
- Team Trust: {game_state.team_trust}%

QUESTION TO INTEGRATE:
Mastery: {question.get('mastery', 'programming')}
Title: {question.get('title', 'Crisis')}
Question: {question.get('question_text', '')}

WRITING STYLE:
- Start with immediate crisis
- Cut all unnecessary description  
- Make the coding action feel like casting a spell or operating critical systems
- End with what the character must do (the code action)
- NO "write a function" - only story actions

EXAMPLES OF CONCISE INTEGRATION:
❌ VERBOSE: "The air hummed with unsettling cadence, Elder Seraph's visage etched with concern..."
✅ CONCISE: "🚨 SYSTEM BREACH! Agent Bob's profile is corrupted during authentication. His email channel may be destroyed. Extract his contact frequency safely, or default to 'Not Provided' to prevent cascade failure."

❌ VERBOSE: "The shimmering data streams materialized, their temporal flows disrupted..."  
✅ CONCISE: "⚡ Core temperature sensors are failing! Multiple readings incoming as data packets. Identify the highest temperature to trigger emergency cooling before meltdown."

TONE BASED ON PERFORMANCE:
- High performance ({game_state.consecutive_correct} >= 3): Epic crisis, realm-wide stakes
- Struggling (consecutive_correct == 0): Personal mission, mentor support
- Balanced: Team crisis, moderate stakes

Generate a 10-15 line story where the coding task is the literal action needed to resolve the crisis:
"""

    def _get_boss_battle_prompt(self, game_state: GameState, question: Dict[str, Any]) -> str:
        """Generate prompt for boss battle scenarios"""
        boss_type = random.choice(list(BOSS_PERSONALITIES.keys()))
        boss_info = BOSS_PERSONALITIES[boss_type]
        
        return f"""
You are creating a BOSS BATTLE for CodeRealm Chronicles. Keep it concise and action-packed.

BOSS: {boss_type} - {boss_info['description']}
WEAKNESS: {boss_info['weakness']}

STORY LENGTH LIMIT: 15-20 lines maximum. Cut all fluff.

GAME STATE:
- Player Level: {game_state.level}
- Guild: {game_state.guild}
- Team Trust: {game_state.team_trust}%

QUESTION TO WEAPONIZE:
Title: {question.get('title', 'Challenge')}
Mastery: {question.get('mastery', 'programming')}
Question: {question.get('question_text', '')}

BOSS BATTLE STRUCTURE:
1. Boss is CAUSING the exact problem from the question
2. Boss taunts with their corrupted solution
3. Your code solution literally defeats them
4. Keep dialogue snappy and menacing

BOSS PERSONALITIES:
- CorruptorAI: "My bugs are features! Watch your systems crash!"
- ChaosBot: "Clean code is weakness! Embrace the chaos!"
- OptimizationDevil: "Speed is irrelevant! Function over form!"
- SecurityShadow: "These aren't flaws - they're backdoors!"

EXAMPLE STRUCTURE:
⚡ Crisis happening NOW
🤖 Boss appears, causing the problem
💬 Brief menacing dialogue
⚔️ Boss shows their flawed approach
🎯 Player must counter with correct solution

Generate a 15-20 line boss battle where the coding solution defeats {boss_type}:
"""

    def _get_imposter_prompt(self, game_state: GameState, question: Dict[str, Any]) -> str:
        """Generate prompt for imposter detection scenarios"""
        return f"""
You are creating an IMPOSTER DETECTION mission for CodeRealm Chronicles. Keep it tight and suspenseful.

STORY LENGTH LIMIT: 15-20 lines maximum. Focus on tension and choices.

GAME STATE:
- Player Level: {game_state.level}
- Guild: {game_state.guild}
- Team Trust: {game_state.team_trust}%

CRISIS TO SOLVE:
Title: {question.get('title', 'Challenge')}
Question: {question.get('question_text', '')}

IMPOSTER MISSION STRUCTURE:
1. Urgent crisis requiring the exact solution from question
2. 3-4 teammates each propose different approaches
3. ONE solution is subtly wrong and would cause disaster
4. Player must identify the corrupted teammate

TEAMMATES (pick 3-4):
- Alex: Senior dev, detailed explanations
- Sarah: Performance-focused, efficiency lover
- Ryan: Methodical debugger, step-by-step
- Maya: Creative innovator, unconventional ideas

MISSION FORMAT:
🚨 Immediate crisis
👥 Team assembles quickly  
💬 Each teammate gives their solution (1-2 lines each)
⚠️ Hint that one approach is dangerous
🎯 Player must choose wisely

EXAMPLE:
"🚨 Security breach! Agent Bob's authentication failing!
Alex: 'Extract email with user["email"]'
Sarah: 'Use user.get("email", "Not Provided")'  
Ryan: 'Check if email exists first'
One of these will crash the system..."

Generate a 15-20 line imposter detection scenario:
"""

    def evaluate_answer(self, game_state: GameState, user_answer: str, 
                       expected_outcome: str, question_id: Union[int, str], question_data: Dict[str, Any] = None) -> GameState:
        """Evaluate user's answer using LLM for intelligent code analysis"""
        
        print(f"🔍 Evaluating answer for question {question_id}")
        print(f"📝 User answer: {user_answer[:100]}...")
        
        # Use LLM to evaluate the code/answer
        is_correct = self._llm_evaluate_code(user_answer, expected_outcome, question_data)
        
        # Update game state based on answer
        updated_state = game_state.copy()
        
        if is_correct:
            # Correct answer rewards
            base_points = 10 * updated_state.level
            updated_state.score += base_points
            updated_state.consecutive_correct += 1
            updated_state.experience_points += 15
            updated_state.team_trust = min(100, updated_state.team_trust + 5)
            
            print(f"✅ Correct answer! +{base_points} points")
            
            # Level up logic
            xp_needed = updated_state.level * 100
            if updated_state.experience_points >= xp_needed:
                updated_state.level += 1
                updated_state.experience_points = 0
                print(f"🎉 Level up! Now level {updated_state.level}")
            
            # Badge logic for streaks
            if updated_state.consecutive_correct == 3:
                updated_state.badges.append("Code Streak Master")
                print("🏆 New badge: Code Streak Master")
            elif updated_state.consecutive_correct == 5:
                updated_state.badges.append("Algorithm Assassin")
                print("🏆 New badge: Algorithm Assassin")
            elif updated_state.consecutive_correct == 10:
                updated_state.badges.append("Digital Sage")
                print("🏆 New badge: Digital Sage")
            
        else:
            # Incorrect answer penalties
            updated_state.consecutive_correct = 0
            updated_state.team_trust = max(0, updated_state.team_trust - 3)
            print("❌ Incorrect answer")
        
        return updated_state
    
    def _llm_evaluate_code(self, user_answer: str, expected_outcome: str, question_data: Dict[str, Any] = None) -> bool:
        """Use LLM to intelligently evaluate if the user's code/answer is correct"""
        
        question_text = question_data.get('question_text', '') if question_data else ''
        question_type = question_data.get('question_type', 'coding') if question_data else 'coding'
        
        evaluation_prompt = f"""
You are an expert coding evaluator for CodeRealm Chronicles. Your job is to determine if a user's answer correctly solves the given problem.

EVALUATION CRITERIA:
- For coding questions: Check if the logic is correct, not just the output
- Look for proper syntax and approach
- Consider multiple valid solutions
- Be lenient with minor syntax variations but strict on logic
- Focus on whether the code would actually solve the problem

QUESTION CONTEXT:
Question: {question_text}
Expected Solution Pattern: {expected_outcome}
Question Type: {question_type}

USER'S SUBMITTED ANSWER:
{user_answer}

EVALUATION GUIDELINES:

1. CODING QUESTIONS:
   - Does the code logic match the expected approach?
   - Would this code actually solve the problem?
   - Are the core concepts (loops, conditionals, data structures) used correctly?
   - Minor syntax errors are acceptable if logic is sound

2. MULTIPLE CHOICE/SHORT ANSWER:
   - Is the answer semantically correct?
   - Consider synonyms and alternative phrasings

3. EXAMPLES OF CORRECT VARIATIONS:
   - `user_id in approved_users` ✅
   - `204 in [101, 204, 305]` ✅  
   - `if user_id in approved_users: return True` ✅
   - `approved_users.count(user_id) > 0` ✅ (less elegant but correct)

4. EXAMPLES OF INCORRECT:
   - Just writing "True" without code ❌
   - Completely wrong logic ❌
   - Syntax so broken it wouldn't run ❌

RESPONSE FORMAT:
Respond with exactly one word: "CORRECT" or "INCORRECT"

If the user's answer demonstrates they understand the problem and their solution would work (even if not identical to expected), respond "CORRECT".
If the logic is fundamentally wrong or they just guessed the output, respond "INCORRECT".

EVALUATION:
"""
        
        try:
            print("🤖 Using LLM to evaluate answer...")
            response = self.model.generate_content(evaluation_prompt)
            result = response.text.strip().upper()
            
            print(f"🎯 LLM evaluation result: {result}")
            
            # Parse LLM response
            if "CORRECT" in result:
                return True
            elif "INCORRECT" in result:
                return False
            else:
                # Fallback to basic string comparison if LLM response is unclear
                print("⚠️ LLM response unclear, falling back to basic comparison")
                return self._basic_answer_check(user_answer, expected_outcome)
                
        except Exception as e:
            print(f"❌ LLM evaluation failed: {str(e)}")
            # Fallback to basic comparison
            return self._basic_answer_check(user_answer, expected_outcome)
    
    def _basic_answer_check(self, user_answer: str, expected_outcome: str) -> bool:
        """Fallback basic answer checking method"""
        user_clean = user_answer.strip().lower()
        expected_clean = expected_outcome.strip().lower()
        
        # For coding questions, check if key elements are present
        if any(keyword in expected_clean for keyword in ['def ', 'for ', 'if ', 'in ', '==', '!=']):
            # This is likely a code question, check for key concepts
            expected_keywords = ['in', 'user_id', 'approved_users']
            return all(keyword in user_clean for keyword in expected_keywords)
        else:
            # Simple text comparison for non-code answers
            return user_clean == expected_clean
    
    def generate_result_narrative(self, game_state: GameState, is_correct: bool, 
                                time_taken: Optional[int] = None) -> str:
        """Generate narrative response based on answer result"""
        
        prompt = f"""
Generate a narrative response for CodeRealm Chronicles based on the player's answer result.

GAME STATE:
- Player Level: {game_state.level}
- Guild: {game_state.guild}
- Score: {game_state.score}
- Consecutive Correct: {game_state.consecutive_correct}
- Team Trust: {game_state.team_trust}%

RESULT: {"CORRECT" if is_correct else "INCORRECT"}
Time Taken: {time_taken or "N/A"} seconds

RESPONSE REQUIREMENTS:
1. Show immediate consequences in the digital world
2. Reflect team reactions and trust changes
3. Set up anticipation for next mission
4. Maintain immersive atmosphere

TONE GUIDELINES:
- Correct Answer: Celebration, system stabilizes, team confidence, unlock new possibilities
- Incorrect Answer: Setback but not defeat, learning opportunity, mentor support, redemption setup

Generate a 200-250 word result narrative:
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Mission {'completed successfully' if is_correct else 'requires another attempt'}. The digital realm awaits your next move."

# Initialize game engine
game_engine = GameEngine()

# API Routes
@app.get("/")
async def root():
    return {"message": "CodeRealm Chronicles API is running"}

@app.get("/test")
async def test_connections():
    """Test all connections and configurations"""
    results = {
        "api_status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "environment_variables": {
            "supabase_url": "✅ Set" if SUPABASE_URL else "❌ Missing",
            "supabase_key": "✅ Set" if SUPABASE_KEY else "❌ Missing",
            "GOOGLE_API_KEY": "✅ Set" if GOOGLE_API_KEY else "❌ Missing"
        }
    }
    
    # Test Supabase connection
    try:
        if supabase:
            test_response = supabase.table("questions").select("id").limit(1).execute()
            results["supabase_connection"] = "✅ Connected"
            results["questions_table"] = f"✅ Accessible ({len(test_response.data) if test_response.data else 0} rows found)"
            
            # Test actual column structure
            if test_response.data:
                sample_question = test_response.data[0]
                results["database_schema"] = {
                    "columns_found": list(sample_question.keys()),
                    "expected_columns": ["id", "mastery", "difficulty_level", "difficulty_rating", "title", "question_text", "expected_outcome"]
                }
        else:
            results["supabase_connection"] = "❌ Not initialized"
    except Exception as e:
        results["supabase_connection"] = f"❌ Error: {str(e)}"
    
    # Test Gemini API
    try:
        test_model = genai.GenerativeModel('gemini-pro')
        test_response = test_model.generate_content("Say 'API test successful'")
        results["gemini_api"] = "✅ Working"
    except Exception as e:
        results["gemini_api"] = f"❌ Error: {str(e)}"
    
    return results

@app.post("/get-question", response_model=NarrativeResponse)
async def get_question(request: QuestionRequest):
    """Get next question with immersive narrative"""
    try:
        print(f"📥 Received question request: {request.question_type}")
        print(f"🎮 Game state - Level: {request.game_state.level}, Guild: {request.game_state.guild}")
        
        # Get appropriate question from database
        print("🔍 Fetching question from database...")
        question = game_engine.get_next_question(request.game_state)
        print(f"✅ Question fetched: ID {question.get('id')}")
        
        # Generate immersive narrative
        print("🎭 Generating narrative...")
        story_content = game_engine.generate_narrative(
            request.game_state, question, request.question_type
        )
        print("✅ Narrative generated successfully")
        
        # Prepare question data (remove answer for frontend) - Updated for your schema
        question_data = {
            "id": question.get("id"),  # Keep original ID type (int or string)
            "mastery": question["mastery"],
            "difficulty_level": question["difficulty_level"],
            "difficulty_rating": question["difficulty_rating"],
            "title": question["title"],
            "question_text": question["question_text"],
            "question_type": "coding"  # Default since you don't have this column
        }
        
        # Determine special actions available
        special_actions = []
        if request.game_state.team_trust >= 70:
            special_actions.append("ask_mentor")
        if request.question_type == "boss_battle":
            special_actions.extend(["analyze_boss_code", "debug_battle"])
        
        print("📤 Sending response to frontend")
        
        return NarrativeResponse(
            story_content=story_content,
            question_data=question_data,
            updated_game_state=request.game_state,
            hint_available=True,
            special_actions=special_actions
        )
        
    except Exception as e:
        print(f"💥 Error in get_question endpoint: {str(e)}")
        import traceback
        print(f"📍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/submit-answer", response_model=NarrativeResponse)
async def submit_answer(submission: AnswerSubmission):
    """Submit answer and get updated game state with narrative response"""
    try:
        print(f"📥 Received answer submission for question {submission.question_id}")
        
        # Get question data including expected outcome
        question_response = supabase.table("questions").select("*").eq(
            "id", submission.question_id
        ).execute()
        
        if not question_response.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        question_data = question_response.data[0]
        expected_outcome = question_data["expected_outcome"]
        print(f"✅ Retrieved question data for question {submission.question_id}")
        
        # Evaluate answer using LLM analysis
        updated_state = game_engine.evaluate_answer(
            submission.game_state, 
            submission.user_answer, 
            expected_outcome, 
            submission.question_id,
            question_data  # Pass full question data for context
        )
        
        # Determine if answer was correct by comparing states
        is_correct = updated_state.consecutive_correct > submission.game_state.consecutive_correct or \
                    (updated_state.consecutive_correct > 0 and submission.game_state.consecutive_correct == 0)
        
        print(f"🎯 Final evaluation: {'Correct' if is_correct else 'Incorrect'}")
        
        # Generate narrative response based on result
        response_narrative = game_engine.generate_result_narrative(
            updated_state, is_correct, submission.time_taken
        )
        
        return NarrativeResponse(
            story_content=response_narrative,
            question_data={"result": "correct" if is_correct else "incorrect"},
            updated_game_state=updated_state,
            hint_available=False,
            special_actions=[]
        )
        
    except Exception as e:
        print(f"💥 Error in submit_answer endpoint: {str(e)}")
        import traceback
        print(f"📍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/get-hint")
async def get_hint(request: QuestionRequest):
    """Get narrative-based hint for current question"""
    try:
        # Generate story-based hint that doesn't reveal the answer
        hint_prompt = f"""
Generate a subtle, narrative-based hint for a CodeRealm Chronicles mission. The hint should:
1. Be delivered by a mentor NPC or teammate
2. Provide guidance without giving away the answer
3. Stay in character and maintain immersion
4. Help the player think through the problem methodology

Player Level: {request.game_state.level}
Guild: {request.game_state.guild}
Team Trust: {request.game_state.team_trust}%

Generate a 100-150 word hint response:
"""
        
        response = game_engine.model.generate_content(hint_prompt)
        return {"hint": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/leaderboard")
async def get_leaderboard():
    """Get current leaderboard (placeholder for future implementation)"""
    return {"message": "Leaderboard coming soon"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)