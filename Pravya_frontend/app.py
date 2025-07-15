import streamlit as st
import requests

# --- CONFIGURATION ---
# IMPORTANT: Make sure this URL points to your deployed Render backend
# BACKEND_URL = "http://127.0.0.1:8000" # Replace with your actual Render URL
BACKEND_URL = "https://pravya-demo.onrender.com"
# --- API HELPER FUNCTIONS ---
def get_masteries_from_backend():
    try:
        response = requests.get(f"{BACKEND_URL}/masteries")
        response.raise_for_status()
        return response.json().get("masteries", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: Is the backend running at {BACKEND_URL}?", icon="🔌")
        return None

def fetch_next_question_from_backend(state):
    try:
        response = requests.post(f"{BACKEND_URL}/get-next-question", json=state)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: Could not fetch next question. {e}", icon="📡")
        return None

# --- SESSION STATE INITIALIZATION ---
def initialize_state():
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
    st.title("Pravya: The IPL Challenge 🏏")
    st.markdown("Welcome, Analyst! The IPL season is about to begin, and your team needs your strategic genius. Your skills will decide whether we lift the trophy or go home empty-handed.")
    st.markdown("#### Choose your primary area of expertise below.")
    
    masteries = get_masteries_from_backend()
    
    if masteries:
        options = ["-- Select your mastery --"] + masteries
        selected = st.selectbox("Select Your Mastery:", options=options, label_visibility="collapsed")
        
        if selected != "-- Select your mastery --" and st.button("Start Your Journey", type="primary"):
            st.session_state.selected_mastery = selected
            st.session_state.current_view = 'test'
            st.rerun()

def render_test_screen():
    st.title("Pravya: The IPL Challenge 🏏")

    with st.sidebar:
        st.header("💡 Analyst's Toolkit")
        st.markdown("**Your Earned Power-ups:**")
        if not st.session_state.power_ups:
            st.info("Answer correctly to gain a strategic edge!")
        else:
            for power in st.session_state.power_ups:
                st.success(f"✅ {power}")
        
        if st.session_state.power_ups:
            if st.button("Activate Power-up", disabled=True): # Future feature
                st.toast("Power-up activated!", icon="⚡️")

    # Initial data load
    if st.session_state.current_data is None and st.session_state.selected_mastery:
        with st.spinner("The first challenge is loading..."):
            state_payload = {
                "mastery": st.session_state.selected_mastery,
                "current_question_index": 0,
                "user_answer": None,
                "previous_story_context": None,
                "power_ups": []
            }
            st.session_state.current_data = fetch_next_question_from_backend(state_payload)

    if not st.session_state.current_data:
        st.warning("Waiting for data...")
        return

    # Check for test completion
    if st.session_state.current_data.get("status") == "completed":
        st.balloons()
        st.success("CHAMPIONS! 🏆")
        st.header("You've led the team to a glorious IPL victory!")
        if st.button("Start a New Season"):
            for key in list(st.session_state.keys()):
                del st.session_state[key] # Clear state completely
            st.rerun()
        return

    # --- Display Narrative and Question ---
    story_payload = st.session_state.current_data.get("story_payload", {})
    
    st.markdown(story_payload.get("narrative_chapter", "The story could not be loaded."), unsafe_allow_html=True)
    st.warning(f"**Your Task:** {story_payload.get('call_to_action', 'Provide your solution.')}")

    user_input = st.text_area("Enter Your Solution/Analysis:", height=150, key="user_answer_input")
    
    if st.button("Submit & Finalize Analysis 🚀", type="primary"):
        with st.spinner("Sending your analysis to the dugout..."):
            # Prepare state for the backend
            state_payload = {
                "mastery": st.session_state.selected_mastery,
                "current_question_index": st.session_state.question_index + 1,
                "user_answer": user_input,
                "previous_story_context": story_payload.get("narrative_chapter"),
                "power_ups": st.session_state.power_ups
            }

            # Fetch the next set of data
            next_data = fetch_next_question_from_backend(state_payload)

            if next_data:
                # Update state for the next turn
                st.session_state.question_index += 1
                st.session_state.current_data = next_data

                # Check for newly earned power-up from the payload
                new_power_up = next_data.get("story_payload", {}).get("earned_power_up")
                if new_power_up and new_power_up not in st.session_state.power_ups:
                    st.session_state.power_ups.append(new_power_up)
                    st.toast(f"Power-up Unlocked: {new_power_up}!", icon="🎉")
            
            st.rerun()

# --- MAIN LOGIC (VIEW ROUTER) ---
initialize_state()

if st.session_state.current_view == 'selection':
    render_selection_screen()
else:
    render_test_screen()