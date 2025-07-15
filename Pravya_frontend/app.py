import streamlit as st
import requests

# --- CONFIGURATION ---
# This is the address of our FastAPI backend.
BACKEND_URL = "https://pravya-demo.onrender.com"

# --- API HELPER FUNCTIONS ---

def get_masteries_from_backend():
    """Fetches the list of available masteries from the backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/masteries")
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        return response.json().get("masteries", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {e}")
        st.warning("Please make sure the FastAPI backend is running.")
        return None

def fetch_next_question_from_backend(mastery, index, context, power_ups):
    """Fetches the next question wrapped in its story from the backend."""
    try:
        payload = {
            "mastery": mastery,
            "current_question_index": index,
            "previous_story_context": context,
            "power_ups": power_ups
        }
        response = requests.post(f"{BACKEND_URL}/get-next-question", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching next question: {e}")
        return None

# --- SESSION STATE INITIALIZATION ---
# Using st.session_state to store variables that need to persist across reruns.

if 'current_view' not in st.session_state:
    st.session_state.current_view = 'selection'
if 'selected_mastery' not in st.session_state:
    st.session_state.selected_mastery = None
if 'question_index' not in st.session_state:
    st.session_state.question_index = 0
if 'narrative_context' not in st.session_state:
    st.session_state.narrative_context = None
if 'power_ups' not in st.session_state:
    st.session_state.power_ups = []
if 'current_data' not in st.session_state:
    st.session_state.current_data = None
if 'test_complete' not in st.session_state:
    st.session_state.test_complete = False

# --- UI RENDERING FUNCTIONS ---

def render_selection_screen():
    """Displays the initial screen for the user to select their mastery."""
    st.title("Pravya: The IPL Challenge 🏏")
    st.markdown("Welcome, Analyst! The IPL season is about to begin, and your team needs your strategic genius. Your skills will decide whether we lift the trophy or go home empty-handed.")
    st.markdown("Choose your primary area of expertise below. This will be your core strength throughout the season.")
    
    masteries = get_masteries_from_backend()
    
    if masteries:
        options = ["-- Select your mastery --"] + masteries
        selected = st.selectbox("Select Your Mastery:", options=options)
        
        # Make the button clickable only if a valid mastery is chosen
        if selected != "-- Select your mastery --" and st.button("Start Your Journey"):
            st.session_state.selected_mastery = selected
            st.session_state.current_view = 'test'
            st.rerun()

def render_test_screen():
    """Displays the main test screen with the story and question."""
    
    # Fetch the very first question if we don't have any data yet
    if st.session_state.current_data is None:
        with st.spinner("The first challenge is loading..."):
            st.session_state.current_data = fetch_next_question_from_backend(
                st.session_state.selected_mastery,
                st.session_state.question_index,
                st.session_state.narrative_context,
                st.session_state.power_ups
            )

    if not st.session_state.current_data:
        st.error("Could not load data from the backend. Please ensure it's running correctly.")
        return

    # Check if the test is completed
    if st.session_state.current_data.get("status") == "completed":
        st.balloons()
        st.success("CHAMPIONS! 🏆")
        st.header("You've led the team to a glorious IPL victory!")
        st.markdown(st.session_state.current_data.get("message", "Your brilliant strategies throughout the season were the key to our success. Well done!"))
        st.session_state.test_complete = True
        
        if st.button("Start a New Season"):
            # Reset all state variables to go back to the beginning
            st.session_state.current_view = 'selection'
            st.session_state.selected_mastery = None
            st.session_state.question_index = 0
            st.session_state.narrative_context = None
            st.session_state.power_ups = []
            st.session_state.current_data = None
            st.session_state.test_complete = False
            st.rerun()
        return

    # Display the story and user input elements
    if st.session_state.current_data:
        story_payload = st.session_state.current_data.get("story_payload", {})
        
        # Display the narrative from the LLM
        st.markdown(story_payload.get("narrative_chapter", "The story could not be loaded."), unsafe_allow_html=True)
        st.warning(f"**Your Task:** {story_payload.get('call_to_action', 'Provide your solution.')}")
        
        # NOTE: The raw question block is intentionally omitted for narrative immersion.
        
        st.text_area("Enter Your Solution/Analysis:", height=200, key="user_answer")
        
        # Handle the submission button
        if st.button("Submit & Continue to Next Challenge", disabled=st.session_state.test_complete):
            # Update state for the next question
            st.session_state.question_index += 1
            st.session_state.narrative_context = story_payload.get("narrative_chapter")
            
            # TODO: Implement logic to evaluate the answer and award power-ups
            
            # Fetch the next story/question from the backend
            with st.spinner("The next situation is unfolding..."):
                st.session_state.current_data = fetch_next_question_from_backend(
                    st.session_state.selected_mastery,
                    st.session_state.question_index,
                    st.session_state.narrative_context,
                    st.session_state.power_ups
                )
            
            st.rerun()

# --- MAIN LOGIC (VIEW ROUTER) ---
if st.session_state.current_view == 'selection':
    render_selection_screen()
else:
    render_test_screen()