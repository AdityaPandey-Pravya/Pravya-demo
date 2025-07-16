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
        selected = st.selectbox("Select Your Field of Expertise:", options=options)
        if selected != "-- Select your field of expertise --" and st.button("Begin the Ritual", type="primary"):
            st.session_state.clear()
            st.session_state.view = 'test'
            st.session_state.mastery = selected
            st.rerun()

def render_test_screen():
    # Initialize state
    if 'current_data' not in st.session_state:
        with st.spinner("Calibrating reality anchors..."):
            initial_state = {"mastery": st.session_state.mastery}
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

    # Check for mission completion or failure
    agent_sanity = st.session_state.get('agent_sanity', 100)
    if st.session_state.current_data.get("status") == "completed":
        if agent_sanity <= 0:
            st.error("CONTAINMENT LOST. REALITY UNRAVELING.", icon="💀")
            st.header("You have been lost to the madness.")
        else:
            st.balloons()
            st.success("CONTAINMENT RE-ESTABLISHED ✅")
            st.header("The anomaly is stabilized. The world is safe... for now.")
        
        st.subheader("Final Log - Secured Artifacts:")
        for artifact in st.session_state.get("artifacts", []):
            st.markdown(f"📜 **{artifact}**")
        if st.button("Begin a New Protocol"):
            st.session_state.clear()
            st.rerun()
        return

    # --- MAIN UI LAYOUT ---
    st.title("Aegis Protocol Terminal 👁️")
    col1, col2 = st.columns([2.2, 1])
    story_payload = st.session_state.current_data.get("story_payload", {})
    character = "Director Thorne" if agent_sanity > 60 else "Dr. Aris Thorne"

    with col1:
        st.markdown(story_payload.get("narrative_chapter", "Receiving fragmented transmission..."), unsafe_allow_html=True)
        st.warning(f"**Implied Goal:** {story_payload.get('call_to_action', 'Decipher the anomaly.')}")
        
        user_input = st.text_area("Input your counter-ritual (code):", height=200, key="user_answer_input")

        if st.button("Execute Counter-Ritual", type="primary"):
            with st.spinner("Casting incantation..."):
                state_to_send = {
                    'mastery': st.session_state.mastery,
                    'current_question_index': st.session_state.current_question_index,
                    'power_ups': st.session_state.get('power_ups', []),
                    'artifacts': st.session_state.get('artifacts', []),
                    'agent_sanity': agent_sanity,
                    'correct_streak': st.session_state.get('correct_streak', 0),
                    'user_answer': user_input,
                    'current_question_index': st.session_state.current_question_index + 1
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
            if agent_sanity <= 60:
                 st.markdown(f"**Comms:** <span style='color: red;'>**{character} (Unstable)**</span>", unsafe_allow_html=True)
            else:
                 st.markdown(f"**Comms:** {character}")
            
            st.markdown("**Secured Artifacts:**")
            artifacts = st.session_state.get('artifacts', [])
            if not artifacts:
                st.caption("No artifacts secured.")
            else:
                for artifact in artifacts:
                    st.markdown(f"📜 **{artifact}**")
            
            st.markdown("---")
            if st.button("Consult Forbidden Lore (Hint)"):
                question_details = story_payload.get("question_details", {})
                if question_details:
                    with st.spinner("Whispers from beyond the veil..."):
                        hint_payload = {"question_text": question_details.get("question_text", ""), "character_to_use": character}
                        hint_response = get_api_data("get-narrative-hint", hint_payload)
                        if hint_response:
                            st.info(f"A voice whispers: \"*{hint_response.get('hint_text')}*\"")
                else:
                    st.error("The artifact remains silent.")

# --- MAIN ROUTER ---
if 'view' not in st.session_state:
    st.session_state.view = 'selection'

if st.session_state.view == 'selection':
    render_selection_screen()
else:
    render_test_screen()
# --- END OF FILE app.py ---