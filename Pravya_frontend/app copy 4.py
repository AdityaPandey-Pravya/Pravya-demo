import streamlit as st
import requests
import json
from typing import Dict, Any, Optional
import time
from datetime import datetime
import base64

# Page configuration
st.set_page_config(
    page_title="CodeRealm Chronicles",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for immersive theme
def load_custom_css():
    st.markdown("""
    <style>
    /* Dark tech theme */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        color: #00ff88;
    }
    
    /* Main content area */
    .main-content {
        background: rgba(0, 255, 136, 0.05);
        border: 1px solid #00ff88;
        border-radius: 15px;
        padding: 25px;
        margin: 10px 0;
        box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
    }
    
    /* Story narrative box */
    .story-box {
        background: linear-gradient(145deg, #1a1a2e, #0f0f23);
        border: 2px solid #00ff88;
        border-radius: 12px;
        padding: 25px;
        margin: 15px 0;
        box-shadow: inset 0 0 15px rgba(0, 255, 136, 0.1);
        font-family: 'Courier New', monospace;
        line-height: 1.6;
    }
    
    /* Guild badge styling */
    .guild-badge {
        display: inline-block;
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        padding: 8px 16px;
        border-radius: 20px;
        color: white;
        font-weight: bold;
        margin: 5px;
        text-align: center;
    }
    
    /* Stats display */
    .stat-display {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid #00ff88;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        text-align: center;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #00ff88, #00ccff);
        color: #0f0f23;
        border: none;
        border-radius: 25px;
        padding: 12px 25px;
        font-weight: bold;
        font-size: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #00ccff, #00ff88);
        transform: scale(1.05);
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.5);
    }
    
    /* Boss battle styling */
    .boss-battle {
        background: linear-gradient(135deg, #ff4757, #2f1b14);
        border: 3px solid #ff4757;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 71, 87, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 71, 87, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 71, 87, 0); }
    }
    
    /* Code display */
    .code-display {
        background: #1e1e1e;
        border: 1px solid #00ff88;
        border-radius: 8px;
        padding: 15px;
        font-family: 'Fira Code', 'Courier New', monospace;
        color: #f8f8f2;
        margin: 10px 0;
    }
    
    /* Achievement notification */
    .achievement {
        background: linear-gradient(45deg, #ffd700, #ffed4e);
        color: #0f0f23;
        border: 2px solid #ffd700;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        text-align: center;
        font-weight: bold;
        animation: glow 1.5s ease-in-out infinite alternate;
    }
    
    @keyframes glow {
        from { box-shadow: 0 0 5px #ffd700; }
        to { box-shadow: 0 0 20px #ffd700, 0 0 30px #ffd700; }
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: rgba(0, 0, 0, 0.8);
    }
    
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if 'game_state' not in st.session_state:
        st.session_state.game_state = {
            'user_id': f"player_{int(time.time())}",
            'current_question_id': None,
            'score': 0,
            'level': 1,
            'guild': 'Frontend Mystic',
            'experience_points': 0,
            'badges': [],
            'consecutive_correct': 0,
            'team_trust': 50,
            'current_mission': None,
            'boss_battle_active': False,
            'imposter_mode_active': False
        }
    
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    
    if 'current_story' not in st.session_state:
        st.session_state.current_story = None
    
    if 'game_started' not in st.session_state:
        st.session_state.game_started = False
    
    if 'question_start_time' not in st.session_state:
        st.session_state.question_start_time = None
    
    if 'show_achievement' not in st.session_state:
        st.session_state.show_achievement = None

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"  # Replace with your backend URL

def make_api_request(endpoint: str, data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """Make API request to backend with error handling"""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        if data:
            response = requests.post(url, json=data, timeout=30)
        else:
            response = requests.get(url, timeout=30)
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            # Don't show error here, let the calling function handle it
            raise e
        else:
            st.error(f"API Error {e.response.status_code}: {e.response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

# Guild selection screen
def show_guild_selection():
    st.markdown("<h1 style='text-align: center; color: #00ff88;'>⚔️ Welcome to CodeRealm Chronicles ⚔️</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='main-content'>
    <h2 style='color: #00ccff; text-align: center;'>Choose Your Guild</h2>
    <p style='text-align: center; font-size: 18px;'>
    In the digital realm, your guild determines your specialization and the types of missions you'll encounter. 
    Each guild masters different aspects of code magic. Choose wisely, Code Architect...
    </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Guild options
    guilds = {
        "Frontend Mystic": {
            "description": "Masters of UI/UX magic and visual spells. Specializes in React, JavaScript, CSS, and user interface enchantments.",
            "icon": "🎨",
            "color": "#ff6b6b"
        },
        "Backend Paladin": {
            "description": "Defenders of data integrity and system architecture. Champions of Python, databases, APIs, and security fortifications.",
            "icon": "🛡️",
            "color": "#4ecdc4"
        },
        "Algorithm Assassin": {
            "description": "Speed and efficiency specialists. Masters of mathematics, algorithms, optimization, and computational warfare.",
            "icon": "⚡",
            "color": "#ffd93d"
        },
        "DevOps Shaman": {
            "description": "Infrastructure summoners and deployment ritualists. Experts in cloud magic, monitoring spells, and system automation.",
            "icon": "☁️",
            "color": "#6c5ce7"
        }
    }
    
    # Display guild cards
    cols = st.columns(2)
    
    guild_names = list(guilds.keys())
    for i, guild_name in enumerate(guild_names):
        guild_info = guilds[guild_name]
        col = cols[i % 2]
        
        with col:
            st.markdown(f"""
            <div class='main-content' style='border-color: {guild_info["color"]}; min-height: 200px;'>
            <h3 style='color: {guild_info["color"]}; text-align: center;'>
            {guild_info["icon"]} {guild_name}
            </h3>
            <p style='text-align: center; margin: 15px 0;'>{guild_info["description"]}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Join {guild_name}", key=f"guild_{guild_name}", use_container_width=True):
                st.session_state.game_state['guild'] = guild_name
                st.session_state.game_started = True
                st.rerun()

# Main game interface
def show_game_interface():
    # Sidebar with player stats
    with st.sidebar:
        show_player_stats()
        show_badges()
        
        # Special actions
        st.markdown("### 🎯 Quick Actions")
        
        if st.button("🆘 Ask for Hint", use_container_width=True):
            get_hint()
        
        if st.button("🔄 New Mission", use_container_width=True):
            start_new_mission()
        
        if st.session_state.game_state['level'] >= 3:
            if st.button("👹 Boss Battle", use_container_width=True):
                start_boss_battle()
        
        if st.session_state.game_state['level'] >= 5:
            if st.button("🕵️ Imposter Hunt", use_container_width=True):
                start_imposter_mode()
    
    # Main content area
    if st.session_state.show_achievement:
        show_achievement_notification()
    
    # Display current story/mission
    if st.session_state.current_story:
        show_current_mission()
    else:
        start_new_mission()

def show_player_stats():
    """Display player statistics in sidebar"""
    gs = st.session_state.game_state
    
    st.markdown(f"""
    <div class='main-content'>
    <h2 style='color: #00ff88; text-align: center;'>🧙‍♂️ Code Architect</h2>
    
    <div class='guild-badge' style='width: 100%; margin: 10px 0;'>
    {gs['guild']}
    </div>
    
    <div class='stat-display'>
    <strong>Level:</strong> {gs['level']}
    </div>
    
    <div class='stat-display'>
    <strong>Score:</strong> {gs['score']:,}
    </div>
    
    <div class='stat-display'>
    <strong>XP:</strong> {gs['experience_points']}/{gs['level'] * 100}
    </div>
    
    <div class='stat-display'>
    <strong>Team Trust:</strong> {gs['team_trust']}%
    </div>
    
    <div class='stat-display'>
    <strong>Streak:</strong> {gs['consecutive_correct']} 🔥
    </div>
    </div>
    """, unsafe_allow_html=True)

def show_badges():
    """Display earned badges"""
    badges = st.session_state.game_state['badges']
    
    if badges:
        st.markdown("### 🏆 Achievements")
        for badge in badges:
            st.markdown(f"""
            <div class='achievement' style='margin: 5px 0; padding: 8px; font-size: 14px;'>
            🏆 {badge}
            </div>
            """, unsafe_allow_html=True)

def start_new_mission():
    """Start a new regular mission"""
    question_type = "regular"
    
    # Special mode overrides
    if st.session_state.game_state['boss_battle_active']:
        question_type = "boss_battle"
    elif st.session_state.game_state['imposter_mode_active']:
        question_type = "imposter_detection"
    
    request_data = {
        "game_state": st.session_state.game_state,
        "question_type": question_type
    }
    
    with st.spinner("🔮 Consulting the digital oracle..."):
        response = make_api_request("get-question", request_data)
    
    if response:
        st.session_state.current_story = response['story_content']
        st.session_state.current_question = response['question_data']
        st.session_state.game_state = response['updated_game_state']
        st.session_state.question_start_time = time.time()
        st.rerun()

def show_current_mission():
    """Display the current mission story and question"""
    question_type = st.session_state.current_question.get('question_type', 'coding')
    
    # Story container with appropriate styling
    story_class = "boss-battle" if st.session_state.game_state['boss_battle_active'] else "story-box"
    
    st.markdown(f"""
    <div class='{story_class}'>
    {st.session_state.current_story}
    </div>
    """, unsafe_allow_html=True)
    
    # Question interface based on type
    if question_type == "multiple_choice":
        show_multiple_choice_interface()
    elif question_type == "coding":
        show_coding_interface()
    else:
        show_text_input_interface()

def show_multiple_choice_interface():
    """Display multiple choice question interface"""
    question = st.session_state.current_question
    
    st.markdown("### 🎯 Choose Your Action")
    
    options = question.get('options', [])
    if options:
        selected_option = st.radio("Select your solution:", options, key="mc_answer")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            if st.button("⚔️ Execute Solution", use_container_width=True, type="primary"):
                submit_answer(selected_option)

def show_coding_interface():
    """Display coding question interface"""
    st.markdown("### 💻 Code Your Solution")
    
    # Code editor
    user_code = st.text_area(
        "Write your code here:",
        height=200,
        placeholder="# Your solution goes here...\n",
        key="code_answer"
    )
    
    # Code execution simulation (visual feedback)
    if user_code:
        st.markdown(f"""
        <div class='code-display'>
        <strong>🔍 Code Preview:</strong><br>
        <pre><code>{user_code}</code></pre>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("🚀 Deploy Solution", use_container_width=True, type="primary"):
            if user_code.strip():
                submit_answer(user_code)
            else:
                st.error("Please write your solution first!")

def show_text_input_interface():
    """Display text input interface for short answers"""
    st.markdown("### ✍️ Your Response")
    
    user_answer = st.text_input(
        "Enter your answer:",
        placeholder="Type your solution here...",
        key="text_answer"
    )
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("📤 Submit Answer", use_container_width=True, type="primary"):
            if user_answer.strip():
                submit_answer(user_answer)
            else:
                st.error("Please enter your answer first!")

def submit_answer(user_answer: str):
    """Submit user's answer to backend"""
    time_taken = None
    if st.session_state.question_start_time:
        time_taken = int(time.time() - st.session_state.question_start_time)
    
    submission_data = {
        "game_state": st.session_state.game_state,
        "user_answer": user_answer,
        "question_id": st.session_state.current_question['id'],
        "time_taken": time_taken
    }
    
    # Debug: Show what we're sending
    with st.expander("🐛 Debug Info (Click to expand)", expanded=False):
        st.write("**Sending to backend:**")
        st.json(submission_data)
    
    with st.spinner("🔄 Processing your solution..."):
        try:
            # First try the debug endpoint to see if data is valid
            debug_response = make_api_request("debug-submit", submission_data)
            if debug_response:
                st.success("✅ Data format is valid")
            
            # Now submit the actual answer
            response = make_api_request("submit-answer", submission_data)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                st.error("❌ Data validation error (422)")
                st.error("This usually means there's a mismatch in the data format.")
                
                # Show error details
                try:
                    error_detail = e.response.json()
                    st.error(f"Error details: {error_detail}")
                except:
                    st.error(f"Raw error: {e.response.text}")
                    
                # Show what we tried to send
                st.write("**Data we tried to send:**")
                st.json(submission_data)
                return
            else:
                st.error(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
                return
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return
    
    if response:
        # Update game state
        old_level = st.session_state.game_state['level']
        st.session_state.game_state = response['updated_game_state']
        
        # Check for level up
        if st.session_state.game_state['level'] > old_level:
            st.session_state.show_achievement = f"🎉 Level Up! Welcome to Level {st.session_state.game_state['level']}!"
        
        # Check for new badges
        if len(st.session_state.game_state['badges']) > len(st.session_state.get('previous_badges', [])):
            new_badge = st.session_state.game_state['badges'][-1]
            st.session_state.show_achievement = f"🏆 New Achievement Unlocked: {new_badge}!"
        
        # Display result
        result = response['question_data'].get('result', 'unknown')
        
        if result == "correct":
            st.success("🎉 Excellent work, Code Architect!")
        else:
            st.error("⚠️ Mission incomplete. Analyze and try again!")
        
        # Show result narrative
        st.markdown(f"""
        <div class='story-box'>
        {response['story_content']}
        </div>
        """, unsafe_allow_html=True)
        
        # Reset for next question
        if st.button("➡️ Continue to Next Mission", type="primary", use_container_width=True):
            reset_current_mission()
            start_new_mission()

def get_hint():
    """Get a narrative hint for the current question"""
    if not st.session_state.current_question:
        st.warning("No active mission to provide hints for!")
        return
    
    request_data = {
        "game_state": st.session_state.game_state,
        "question_type": "regular"
    }
    
    with st.spinner("🔮 Consulting the digital mentor..."):
        response = make_api_request("get-hint", request_data)
    
    if response:
        st.info(f"💡 **Mentor's Guidance:** {response['hint']}")

def start_boss_battle():
    """Initiate boss battle mode"""
    st.session_state.game_state['boss_battle_active'] = True
    st.session_state.game_state['imposter_mode_active'] = False
    reset_current_mission()
    start_new_mission()

def start_imposter_mode():
    """Initiate imposter detection mode"""
    st.session_state.game_state['imposter_mode_active'] = True
    st.session_state.game_state['boss_battle_active'] = False
    reset_current_mission()
    start_new_mission()

def reset_current_mission():
    """Reset current mission state"""
    st.session_state.current_story = None
    st.session_state.current_question = None
    st.session_state.question_start_time = None
    st.session_state.game_state['boss_battle_active'] = False
    st.session_state.game_state['imposter_mode_active'] = False

def show_achievement_notification():
    """Display achievement notification"""
    st.markdown(f"""
    <div class='achievement'>
    {st.session_state.show_achievement}
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("✨ Awesome!", use_container_width=True):
        st.session_state.show_achievement = None
        st.rerun()

# Main app logic
def main():
    load_custom_css()
    initialize_session_state()
    
    if not st.session_state.game_started:
        show_guild_selection()
    else:
        show_game_interface()

if __name__ == "__main__":
    main()