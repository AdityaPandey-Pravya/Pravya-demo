# --- START OF FILE main.py ---

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from story_generator import (
    generate_story_for_question,
    generate_imposter_challenge,
    generate_boss_battle_turn
)

# --- INITIALIZATION ---
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
app = FastAPI()

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
class TestState(BaseModel):
    mastery: str
    game_mode: str = "story" # 'story', 'imposter', or 'boss_battle'
    current_question_index: int = 0
    user_answer: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    agent_sanity: int = 100
    correct_streak: int = 0

# --- HELPER FUNCTIONS ---
def check_for_achievements(state: TestState) -> str | None:
    if state.correct_streak == 1 and "First Contact" not in state.artifacts:
        return "First Contact"
    if state.correct_streak == 3 and "Ritualistic Precision" not in state.artifacts:
        return "Ritualistic Precision"
    return None

# --- API ENDPOINTS ---
@app.get("/masteries")
def get_masteries():
    try:
        response = supabase.table('questions').select('mastery', count='exact').execute()
        masteries = list(set(item['mastery'] for item in response.data))
        return {"masteries": masteries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-next-question")
def get_next_question(state: TestState):
    try:
        was_previous_answer_correct = None
        
        # --- 1. CHECK PREVIOUS ANSWER & UPDATE SANITY (shared logic) ---
        if state.current_question_index > 0 and state.user_answer is not None:
            previous_question_index = state.current_question_index - 1
            prev_q_res = supabase.table('questions').select('expected_outcome').eq('mastery', state.mastery).gte('difficulty_rating', 8).order('difficulty_rating').order('id').limit(1).offset(previous_question_index).execute()
            
            if prev_q_res.data:
                expected_outcome = prev_q_res.data[0]['expected_outcome']
                if expected_outcome.lower().strip() in state.user_answer.lower().strip():
                    was_previous_answer_correct = True
                    state.agent_sanity = min(100, state.agent_sanity + 5)
                    state.correct_streak += 1
                else:
                    was_previous_answer_correct = False
                    state.agent_sanity = max(0, state.agent_sanity - 20)
                    state.correct_streak = 0
        
        earned_artifact = check_for_achievements(state)
        if earned_artifact and earned_artifact not in state.artifacts:
            state.artifacts.append(earned_artifact)

        # --- 2. FETCH NEW QUESTION (shared logic) ---
        question_res = supabase.table('questions').select('*').eq('mastery', state.mastery).gte('difficulty_rating', 60).order('difficulty_rating').order('id').limit(1).offset(state.current_question_index).execute()
        
        if not question_res.data or state.agent_sanity <= 0:
            status = "completed" # Can mean success or failure (madness)
            # Add final achievement based on outcome
            return {"status": status, "updated_state": state.dict()}

        question_data = question_res.data[0]
        
        # --- 3. GAME MODE ROUTER ---
        # Call the appropriate generator based on the selected game mode.
        if state.game_mode == 'imposter':
            story_payload = generate_imposter_challenge(question_data, state)
        elif state.game_mode == 'boss_battle':
            story_payload = generate_boss_battle_turn(question_data, state)
        else: # Default to 'story' mode
            story_payload = generate_story_for_question(
                question=question_data,
                mastery=state.mastery,
                agent_sanity=state.agent_sanity,
                was_correct=was_previous_answer_correct,
                earned_artifact=earned_artifact
            )
        
        return {
            "status": "in_progress",
            "story_payload": story_payload,
            "updated_state": state.dict()
        }
    except Exception as e:
        print(f"!!! MASTER ERROR in /get-next-question: {e} !!!")
        raise HTTPException(status_code=500, detail="An unexpected error occurred on the backend.")
# --- END OF FILE main.py ---