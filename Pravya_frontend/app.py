import streamlit as st
import requests

# --- CONFIGURATION ---
BACKEND_URL = "https://pravya-demo.onrender.com" # REPLACE WITH YOUR RENDER URL

# --- API HELPERS ---
def get_api_data(endpoint, payload=None):
    try:
        url = f"{BACKEND_URL}/{endpoint}"
        if payload is None:
            response = requests.get(url)
        else:
            response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}", icon="📡")
        return None

# --- UI RENDERING ---
def render_selection_screen():
    st.title("Pravya: The IPL Challenge 🏏")
    st.markdown("Welcome, Analyst! Your strategic genius will decide if we lift the trophy.")
    masteries = get_api_data("masteries")
    if masteries:
        options = ["-- Select your mastery --"] + masteries.get("masteries", [])
        selected = st.selectbox("Select Your Mastery:", options=options)
        if selected != "-- Select your mastery --" and st.button("Start Your Journey", type="primary"):
            st.session_state.clear() # Clear state for a new game
            st.session_state.view = 'test'
            st.session_state.mastery = selected
            st.rerun()

def render_test_screen():
    # Initialize state on first run of the test screen
    if 'current_data' not in st.session_state:
        with st.spinner("Setting up the first challenge..."):
            initial_state = {"mastery": st.session_state.mastery}
            response = get_api_data("get-next-question", initial_state)
            if response:
                st.session_state.current_data = response
                st.session_state.update(response.get("updated_state", {}))

    if 'current_data' not in st.session_state:
        st.error("Could not load game data. Please refresh and try again.")
        return

    # Check for game completion
    if st.session_state.current_data.get("status") == "completed":
        st.balloons()
        st.success("CHAMPIONS! 🏆")
        st.header("You've led the team to a glorious IPL victory!")
        st.subheader("Final Achievements:")
        for badge in st.session_state.get("badges", []):
            st.markdown(f"🏅 **{badge}**")
        if st.button("Start a New Season"):
            st.session_state.clear()
            st.rerun()
        return

    # --- MAIN UI LAYOUT ---
    st.title("Pravya: The IPL Challenge 🏏")
    col1, col2 = st.columns([2, 1.2])
    story_payload = st.session_state.current_data.get("story_payload", {})
    character = "Captain Vik" if st.session_state.get('performance_score', 0) >= 0 else "Coach Ravi"

    # --- Column 1: Story and Interaction ---
    with col1:
        st.markdown(story_payload.get("narrative_chapter", "Loading story..."), unsafe_allow_html=True)
        st.warning(f"**Your Task:** {story_payload.get('call_to_action', 'Provide your solution.')}")
        user_input = st.text_area("Enter Your Solution/Analysis:", height=150, key="user_answer_input")

        if st.button("Submit & Finalize Analysis 🚀", type="primary"):
            with st.spinner("Sending your analysis to the dugout..."):
                # Construct the complete current state to send to the backend
                state_to_send = {key: st.session_state[key] for key in ['mastery', 'current_question_index', 'power_ups', 'badges', 'performance_score', 'correct_streak']}
                state_to_send['user_answer'] = user_input
                state_to_send['previous_story_context'] = story_payload.get("narrative_chapter")
                state_to_send['current_question_index'] += 1

                response = get_api_data("get-next-question", state_to_send)
                if response:
                    # Announce new badges with a toast
                    new_badges = response.get("updated_state", {}).get("badges", [])
                    old_badges = st.session_state.get("badges", [])
                    for badge in new_badges:
                        if badge not in old_badges:
                            st.toast(f"Achievement Unlocked: {badge}!", icon="🏅")
                    
                    # Master update of state
                    st.session_state.current_data = response
                    st.session_state.update(response.get("updated_state", {}))
                st.rerun()

    # --- Column 2: Dashboard ---
    with col2:
        st.subheader("Dashboard")
        st.metric("Performance Score", st.session_state.get('performance_score', 0))
        st.markdown(f"**In the Dugout:** {character}")
        
        st.markdown("**Achievements:**")
        badges = st.session_state.get('badges', [])
        if not badges:
            st.info("No badges yet.")
        else:
            for badge in badges:
                st.markdown(f"🏅 **{badge}**")
        
        st.markdown("---")
        if st.button("🤔 Ask the Dugout for a Hint"):
            question_details = story_payload.get("question_details", {})
            if question_details:
                with st.spinner("Getting tactical advice..."):
                    hint_payload = {"question_text": question_details.get("question_text", ""), "character_to_use": character}
                    hint_response = get_api_data("get-narrative-hint", hint_payload)
                    if hint_response:
                        st.info(f"**{character} says:** \"{hint_response.get('hint_text')}\"")
            else:
                st.error("No question data available for a hint.")

# --- MAIN ROUTER ---
if 'view' not in st.session_state:
    st.session_state.view = 'selection'

if st.session_state.view == 'selection':
    render_selection_screen()
else:
    render_test_screen()