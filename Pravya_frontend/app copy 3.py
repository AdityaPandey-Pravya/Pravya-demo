# --- START OF FILE app.py ---

import streamlit as st
import requests

# --- CONFIGURATION ---
BACKEND_URL = "http://127.0.0.1:8000" # Ensure this is your correct Render URL

# --- API HELPER ---
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
        st.error(f"Comms Failure: Cannot connect to the Aegis server. The connection is unstable. Error: {e}", icon="📡")
        return None

# --- UI RENDERING ---
def render_selection_screen():
    st.title("Project Umbra: The Aegis Protocol 👁️")
    st.markdown("You are a Technomancer, our last line of defense against reality-bending threats. Your code is the only thing holding back the darkness. Welcome to Project Umbra.")
    masteries = get_api_data("masteries")
    if masteries:
        options = ["-- Select your field of expertise --"] + masteries.get("masteries", [])
        selected_mastery = st.selectbox("Select Your Field of Expertise:", options=options)

        if selected_mastery != "-- Select your field of expertise --":
            st.markdown("---")
            st.subheader("Select a Simulation Protocol")

            # Store the game mode selection in a temporary key to avoid race conditions
            if 'selected_mode' not in st.session_state:
                st.session_state.selected_mode = None

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Start Story Mode", use_container_width=True):
                    st.session_state.selected_mode = 'story'
                    st.rerun()
            st.info("The standard narrative experience. Unravel a mystery through a series of connected challenges.", icon="📖")

            with col2:
                if st.button("Engage Imposter Protocol", use_container_width=True):
                    st.session_state.selected_mode = 'imposter'
                    st.rerun()
            st.info("A teammate AI will offer help, but it may be deceptive. Find the bug in their suggestion.", icon="🕵️")

            with col3:
                if st.button("Face AI Boss Battle", use_container_width=True):
                    st.session_state.selected_mode = 'boss_battle'
                    st.rerun()
            st.info("Go head-to-head with a hostile AI. It will present flawed code and taunt you.", icon="🤖")

            # --- THIS IS THE CORRECTED LOGIC BLOCK ---
            # Check if a mode has been selected to start the game.
            if st.session_state.selected_mode:
                # Store the selected mode and mastery in local variables
                # BEFORE clearing the entire session state.
                game_mode = st.session_state.selected_mode
                
                # Now we can safely clear the state for a new game
                st.session_state.clear()
                
                # And re-initialize it with the values we saved
                st.session_state.view = 'test'
                st.session_state.mastery = selected_mastery
                st.session_state.game_mode = game_mode
                st.rerun()


def render_test_screen():
    # Initialize state
    if 'current_data' not in st.session_state:
        with st.spinner("Calibrating reality anchors..."):
            initial_state = {
                "mastery": st.session_state.mastery,
                "game_mode": st.session_state.game_mode
            }
            response = get_api_data("get-next-question", initial_state)
            if response:
                st.session_state.current_data = response
                st.session_state.update(response.get("updated_state", {}))
            else:
                 st.error("Initialization failed. The frequency is unstable. Refresh to try again.")
                 return

    if 'current_data' not in st.session_state:
        st.error("Data stream corrupted by paranormal interference. Please refresh the terminal.")
        return

    # Dynamic title based on game mode
    mode = st.session_state.get('game_mode', 'story').replace('_', ' ').title()
    st.title(f"Aegis Protocol: {mode} 👁️")


    # --- MAIN UI LAYOUT ---
    col1, col2 = st.columns([2.2, 1])
    story_payload = st.session_state.current_data.get("story_payload", {})
    agent_sanity = st.session_state.get('agent_sanity', 100)
    character = "Director Thorne" if agent_sanity > 60 else "Dr. Aris Thorne"

    with col1:
        st.markdown(story_payload.get("narrative_chapter", "Receiving fragmented transmission..."), unsafe_allow_html=True)
        st.warning(f"**Implied Goal:** {story_payload.get('call_to_action', 'Decipher the anomaly.')}")
        
        user_input = st.text_area("Input your counter-ritual (code):", height=200, key="user_answer_input")

        if st.button("Execute Counter-Ritual", type="primary"):
            with st.spinner("Casting incantation..."):
                state_to_send = {
                    'mastery': st.session_state.mastery,
                    'game_mode': st.session_state.game_mode,
                    'current_question_index': st.session_state.get('current_question_index', 0),
                    'artifacts': st.session_state.get('artifacts', []),
                    'agent_sanity': agent_sanity,
                    'correct_streak': st.session_state.get('correct_streak', 0),
                    'user_answer': user_input,
                    'current_question_index': st.session_state.get('current_question_index', 0) + 1
                }

                response = get_api_data("get-next-question", state_to_send)
                if response:
                    new_artifacts = response.get("updated_state", {}).get("artifacts", [])
                    old_artifacts = st.session_state.get("artifacts", [])
                    for artifact in new_artifacts:
                        if artifact not in old_artifacts:
                            st.toast(f"Artifact Secured: {artifact}!", icon="📜")
                    
                    st.session_state.current_data = response
                    st.session_state.update(response.get("updated_state", {}))
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("Containment Status")
            st.metric("Agent Sanity", f"{agent_sanity}%")
            st.markdown(f"**Comms:** {character}")
            st.markdown(f"**Protocol:** {mode}")
            
            st.markdown("**Secured Artifacts:**")
            artifacts = st.session_state.get('artifacts', [])
            if not artifacts:
                st.caption("No artifacts secured.")
            else:
                for artifact in artifacts:
                    st.markdown(f"📜 **{artifact}**")


# --- MAIN ROUTER ---
if 'view' not in st.session_state:
    st.session_state.view = 'selection'

if st.session_state.view == 'selection':
    render_selection_screen()
else:
    render_test_screen()
# --- END OF FILE app.py ---