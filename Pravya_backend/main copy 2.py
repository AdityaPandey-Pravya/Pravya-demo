# --- START OF FILE main.py ---

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from story_generator import generate_story_for_question, generate_narrative_hint

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
    current_question_index: int = 0
    user_answer: str | None = None
    previous_story_context: str | None = None
    power_ups: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    agent_sanity: int = 100 # New core metric, starts high and decreases.
    correct_streak: int = 0

class HintRequest(BaseModel):
    question_text: str
    character_to_use: str

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

@app.post("/get-narrative-hint")
def get_hint(req: HintRequest):
    try:
        hint_text = generate_narrative_hint(req.question_text, req.character_to_use)
        return {"hint_text": hint_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating hint: {e}")

@app.post("/get-next-question")
def get_next_question(state: TestState):
    try:
        was_previous_answer_correct = None
        
        # --- 1. CHECK PREVIOUS ANSWER & UPDATE SANITY ---
        if state.current_question_index > 0 and state.user_answer is not None:
            previous_question_index = state.current_question_index - 1
            prev_q_res = supabase.table('questions').select('expected_outcome').eq('mastery', state.mastery).gte('difficulty_rating', 8).order('difficulty_rating').order('id').limit(1).offset(previous_question_index).execute()
            
            if prev_q_res.data:
                expected_outcome = prev_q_res.data[0]['expected_outcome']
                if expected_outcome.lower().strip() in state.user_answer.lower().strip():
                    was_previous_answer_correct = True
                    state.agent_sanity = min(100, state.agent_sanity + 5) # Regain a little sanity
                    state.correct_streak += 1
                else:
                    was_previous_answer_correct = False
                    state.agent_sanity = max(0, state.agent_sanity - 20) # Sanity loss is severe
                    state.correct_streak = 0
        
        # --- 2. CHECK FOR NEWLY SECURED ARTIFACTS ---
        earned_artifact = check_for_achievements(state)
        if earned_artifact and earned_artifact not in state.artifacts:
            state.artifacts.append(earned_artifact)

        # --- 3. FETCH NEW ANOMALY (QUESTION) ---
        new_question_res = supabase.table('questions').select('*').eq('mastery', state.mastery).gte('difficulty_rating', 8).order('difficulty_rating').order('id').limit(1).offset(state.current_question_index).execute()
        
        if not new_question_res.data or state.agent_sanity <= 0:
            status = "completed"
            if state.agent_sanity <= 0 and "Lost to Madness" not in state.artifacts:
                state.artifacts.append("Lost to Madness")
            elif "The Unseen Truth" not in state.artifacts:
                state.artifacts.append("The Unseen Truth") # Final achievement for success
            return {"status": status, "updated_state": state.dict()}

        question_data = new_question_res.data[0]
        
        # --- 4. GENERATE THE STORY ---
        story_payload = generate_story_for_question(
            question=question_data,
            mastery=state.mastery,
            agent_sanity=state.agent_sanity,
            was_correct=was_previous_answer_correct,
            earned_artifact=earned_artifact
        )

        # Update state object to be sent back
        updated_state = state.dict()
        updated_state['artifacts'] = state.artifacts

        return {
            "status": "in_progress",
            "story_payload": story_payload,
            "updated_state": updated_state
        }
    except Exception as e:
        print(f"!!! MASTER ERROR in /get-next-question: {e} !!!")
        raise HTTPException(status_code=500, detail="An unexpected error occurred on the backend.")
# --- END OF FILE main.py ---