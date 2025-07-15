import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel

# Import our story generator function
from story_generator import generate_story_for_question

# --- INITIALIZATION ---
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
app = FastAPI()

# --- MIDDLEWARE ---
origins = [
    "http://localhost",
    "http://localhost:8501",
    # Add your Streamlit Community Cloud URL when you have it
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for simplicity, can be restricted to `origins`
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PYDANTIC MODELS ---
class TestState(BaseModel):
    """Defines the structure of the data we expect from the frontend."""
    mastery: str
    current_question_index: int
    user_answer: str | None = None  # Receives the user's answer from the frontend
    previous_story_context: str | None = None
    power_ups: list[str] = []

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

@app.post("/get-next-question")
def get_next_question(state: TestState):
    """
    Fetches the next question, checks the previous answer, and wraps it all in a story.
    """
    was_previous_answer_correct = None
    earned_power_up = None

    # --- ANSWER CHECKING LOGIC ---
    # Check the answer for the PREVIOUS question (if it's not the first turn).
    if state.current_question_index > 0 and state.user_answer:
        previous_question_index = state.current_question_index - 1
        
        try:
            prev_question_response = supabase.table('questions') \
                .select('expected_outcome') \
                .eq('mastery', state.mastery) \
                .gte('difficulty_rating', 8) \
                .order('difficulty_rating', desc=False) \
                .order('id', desc=False) \
                .limit(1) \
                .offset(previous_question_index) \
                .execute()
                
            if prev_question_response.data:
                expected_outcome = prev_question_response.data[0]['expected_outcome']
                # Simple check: Does the user's answer contain the core number from the outcome?
                correct_answer_value = ''.join(c for c in expected_outcome.split('.')[0] if c.isdigit() or c == '.')

                if correct_answer_value and correct_answer_value in state.user_answer:
                    was_previous_answer_correct = True
                    # Award a power-up!
                    power_up_options = ["Captain's Confidence", "Hawkeye Analysis", "DRS Override", "Finisher's Instinct"]
                    new_power_ups = [p for p in power_up_options if p not in state.power_ups]
                    if new_power_ups:
                        earned_power_up = new_power_ups[0]
                else:
                    was_previous_answer_correct = False
        except Exception as e:
            print(f"Error checking previous answer: {e}")
            was_previous_answer_correct = False # Default to false on error

    # --- FETCH THE NEW QUESTION ---
    try:
        response = supabase.table('questions') \
            .select('*') \
            .eq('mastery', state.mastery) \
            .gte('difficulty_rating', 8) \
            .order('difficulty_rating', desc=False) \
            .order('id', desc=False) \
            .limit(1) \
            .offset(state.current_question_index) \
            .execute()

        if not response.data:
            return {"status": "completed", "message": "The season is over! What a victory!"}

        question_data = response.data[0]

        # --- GENERATE THE STORY ---
        story_payload = generate_story_for_question(
            mastery=state.mastery,
            question=question_data,
            previous_context=state.previous_story_context,
            power_ups=state.power_ups,
            was_correct=was_previous_answer_correct,
            earned_power_up=earned_power_up
        )
        
        # Add results to the payload for the frontend
        story_payload['was_previous_answer_correct'] = was_previous_answer_correct
        story_payload['earned_power_up'] = earned_power_up

        return {
            "status": "in_progress",
            "story_payload": story_payload
        }

    except Exception as e:
        print(f"Error in get-next-question endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))