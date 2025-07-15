# main.py (Updated Version)

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel

# --- NEW: Import our story generator function ---
from story_generator import generate_story_for_question

# --- INITIALIZATION ---
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
app = FastAPI()

# --- MIDDLEWARE (No changes here) ---
origins = [
    "http://localhost",
    "http://localhost:8501",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PYDANTIC MODELS (No changes here) ---
class TestState(BaseModel):
    mastery: str
    current_question_index: int
    previous_story_context: str | None = None
    power_ups: list[str] | None = []


# --- API ENDPOINTS ---

@app.get("/masteries")
def get_masteries():
    try:
        response = supabase.table('questions').select('mastery', count='exact').execute()
        masteries = list(set(item['mastery'] for item in response.data))
        return {"masteries": masteries}
    except Exception as e:
        print(f"Error fetching masteries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# In pravya_backend/main.py

@app.post("/get-next-question")
def get_next_question(state: TestState):
    """
    Fetches the next question, starting from 'medium' difficulty,
    and then uses the LLM to wrap it in a story.
    """
    # --- START DEBUGGING ---
    print("\n" + "="*50)
    print(f"Received request for mastery: '{state.mastery}'")
    print(f"Requesting question at index (offset): {state.current_question_index}")
    print(f"Previous story context provided: {isinstance(state.previous_story_context, str)}")
    # --- END DEBUGGING ---

    try:
        # Query the 'questions' table
        response = supabase.table('questions') \
            .select('*') \
            .eq('mastery', state.mastery) \
            .gte('difficulty_rating', 8) \
            .order('difficulty_rating', desc=False) \
            .order('id', desc=False) \
            .limit(1) \
            .offset(state.current_question_index) \
            .execute()
        
        # --- START DEBUGGING ---
        print(f"Database query found {len(response.data)} records.")
        if response.data:
            print(f"Found question ID: {response.data[0].get('id')}")
        else:
            print("No more questions found with the current criteria.")
        print("="*50 + "\n")
        # --- END DEBUGGING ---

        if not response.data:
            return {"status": "completed", "message": "The season is over! What a victory!"}

        question_data = response.data[0]

        story_payload = generate_story_for_question(
            mastery=state.mastery,
            question=question_data,
            previous_context=state.previous_story_context,
            power_ups=state.power_ups
        )

        return {
            "status": "in_progress",
            "story_payload": story_payload
        }

    except Exception as e:
        print(f"Error in get-next-question endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))