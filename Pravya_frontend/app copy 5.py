import streamlit as st
import requests
import json
from typing import Dict, Any
import time

# Page configuration
st.set_page_config(
    page_title="DevStorm: The Code Uprising",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend URL (adjust for your deployment)
BACKEND_URL = "http://localhost:8000"  # Change to your Render URL when deployed

# Custom CSS for immersive UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .crisis-alert {
        background: linear-gradient(90deg, #ff416c 0%, #ff4b2b 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        border-left: 5px solid #ff0000;
        margin: 1rem 0;
    }
    
    .team-status {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
        color: #212529;
    }
    
    .mission-briefing {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #2196f3;
        margin: 1rem 0;
        color: #0d47a1;
    }
    
    .code-submission {
        background: #1e1e1e;
        color: #f8f8f2;
        padding: 1rem;
        border-radius: 10px;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    }
    
    .achievement-badge {
        background: linear-gradient(45deg, #ffd700, #ffed4e);
        color: #000;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.25rem;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .urgency-critical {
        animation: pulse 1s infinite;
        border: 2px solid #ff0000;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .stat-card {
        background: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        margin: 0.5rem 0;
        color: #212529;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_game_state():
    if 'game_state' not in st.session_state:
        st.session_state.game_state = {
            "player_level": 1,
            "experience_points": 0,
            "current_question_index": 0,
            "performance_score": 100.0,
            "streak_count": 0,
            "badges": [],
            "team_trust": {
                "senior_dev": 100.0,
                "security_lead": 100.0,
                "junior_dev": 100.0
            },
            "story_path": "normal",
            "boss_battle_ready": False,
            "session_questions_answered": 0,
            "selected_mastery": "python"  # Default selection
        }
    
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    
    if 'current_narrative' not in st.session_state:
        st.session_state.current_narrative = None
    
    if 'waiting_for_question' not in st.session_state:
        st.session_state.waiting_for_question = True
    
    if 'user_answer' not in st.session_state:
        st.session_state.user_answer = ""
    
    if 'mastery_selected' not in st.session_state:
        st.session_state.mastery_selected = False

def display_header():
    st.markdown("""
    <div class="main-header">
        <h1>⚡ DevStorm: The Code Uprising ⚡</h1>
        <p>NeoTech Corp is under siege. Your coding skills are humanity's last defense.</p>
    </div>
    """, unsafe_allow_html=True)

def display_stats_sidebar():
    with st.sidebar:
        st.markdown("### 📊 Mission Status")
        
        game_state = st.session_state.game_state
        
        # Player stats
        st.markdown(f"""
        <div class="stat-card">
            <h4 style="color: #212529;">Developer Level: {game_state['player_level']}</h4>
            <p style="color: #6c757d;">XP: {game_state['experience_points']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Performance indicator
        performance_color = "#28a745" if game_state['performance_score'] >= 70 else "#ffc107" if game_state['performance_score'] >= 50 else "#dc3545"
        st.markdown(f"""
        <div class="stat-card">
            <h4 style="color: {performance_color}">Performance: {game_state['performance_score']:.1f}%</h4>
            <p style="color: #6c757d;">Current Streak: {game_state['streak_count']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Selected mastery
        mastery_display = {
            "python": "🐍 Python",
            "react": "⚛️ React",
            "mathematics": "📐 Mathematics"
        }.get(game_state['selected_mastery'], game_state['selected_mastery'])
        
        st.markdown(f"""
        <div class="stat-card">
            <h4 style="color: #2196f3;">Specialization</h4>
            <p style="color: #6c757d;">{mastery_display}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Team trust levels
        st.markdown("### 🤝 Team Trust")
        for member, trust in game_state['team_trust'].items():
            trust_color = "#28a745" if trust >= 80 else "#ffc107" if trust >= 60 else "#dc3545"
            member_name = {
                "senior_dev": "Alex Chen",
                "security_lead": "Maya Rodriguez", 
                "junior_dev": "Jordan Kim"
            }.get(member, member)
            
            st.markdown(f"""
            <div style="margin: 0.5rem 0;">
                <strong style="color: #212529;">{member_name}</strong><br>
                <div style="background: #e9ecef; border-radius: 10px; height: 20px; overflow: hidden;">
                    <div style="background: {trust_color}; height: 100%; width: {trust}%; transition: width 0.3s;"></div>
                </div>
                <small style="color: #6c757d;">{trust:.0f}% trust</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Badges
        if game_state['badges']:
            st.markdown("### 🏆 Achievements")
            badge_names = {
                "code_warrior": "Code Warrior",
                "debugging_master": "Debug Master",
                "perfectionist": "Perfectionist",
                "elite_developer": "Elite Dev"
            }
            
            for badge in game_state['badges']:
                badge_display = badge_names.get(badge, badge.replace('_', ' ').title())
                st.markdown(f'<span class="achievement-badge">{badge_display}</span>', unsafe_allow_html=True)

def display_mastery_selection():
    """Display subject selection interface"""
    if st.session_state.mastery_selected:
        return True
    
    st.markdown("""
    <div class="main-header">
        <h2>🎯 Choose Your Tech Specialization</h2>
        <p>Select your focus area for this mission. This will determine the type of challenges you face.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="stat-card">
            <h3>🐍 Python Development</h3>
            <p>Master Python programming, algorithms, data structures, and backend development challenges.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Python", use_container_width=True, type="primary"):
            st.session_state.game_state['selected_mastery'] = "python"
            st.session_state.mastery_selected = True
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="stat-card">
            <h3>⚛️ React Development</h3>
            <p>Tackle React components, state management, hooks, and frontend architecture problems.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose React", use_container_width=True, type="primary"):
            st.session_state.game_state['selected_mastery'] = "react"
            st.session_state.mastery_selected = True
            st.rerun()
    
    with col3:
        st.markdown("""
        <div class="stat-card">
            <h3>📐 Mathematics</h3>
            <p>Solve complex mathematical problems, algorithms, statistics, and computational challenges.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Mathematics", use_container_width=True, type="primary"):
            st.session_state.game_state['selected_mastery'] = "mathematics"
            st.session_state.mastery_selected = True
            st.rerun()
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6c757d; padding: 1rem;">
        <small>
        ⚠️ Choose wisely! Your specialization will shape the entire mission storyline.<br>
        You can change this in future sessions, but for now, pick your strongest area.
        </small>
    </div>
    """, unsafe_allow_html=True)
    
    return False

def get_next_question():
    """Fetch next question from backend"""
    try:
        with st.spinner("🔄 Analyzing system breach..."):
            response = requests.post(
                f"{BACKEND_URL}/get_next_question",
                json={"game_state": st.session_state.game_state},
                timeout=30
            )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.current_question = data['question']
            st.session_state.current_narrative = data['narrative']
            st.session_state.urgency_level = data.get('urgency_level', 'medium')
            st.session_state.is_boss_battle = data.get('is_boss_battle', False)
            st.session_state.time_limit = data.get('time_limit')
            st.session_state.waiting_for_question = False
            return True
        else:
            st.error(f"Failed to get question: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return False

def submit_answer(user_answer: str):
    """Submit user's answer for evaluation"""
    try:
        with st.spinner("🔍 Analyzing your solution..."):
            response = requests.post(
                f"{BACKEND_URL}/submit_answer",
                json={
                    "game_state": st.session_state.game_state,
                    "user_answer": user_answer,
                    "question_id": st.session_state.current_question['id']
                },
                timeout=30
            )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.game_state = data['updated_game_state']
            
            # Display evaluation results
            if data['is_correct']:
                st.success(f"✅ Solution Deployed Successfully! Score: {data['score']:.0f}/100")
            else:
                st.error(f"❌ Solution Failed Deployment. Score: {data['score']:.0f}/100")
            
            st.info(f"**Team Feedback:** {data['feedback']}")
            
            # Show achievement if unlocked
            if data['achievement_unlocked']:
                st.balloons()
                st.success(f"🏆 Achievement Unlocked: {data['achievement_unlocked'].replace('_', ' ').title()}!")
            
            # Reset for next question
            st.session_state.waiting_for_question = True
            st.session_state.user_answer = ""
            time.sleep(2)
            st.rerun()
            
        else:
            st.error(f"Evaluation failed: {response.text}")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")

def display_current_scenario():
    """Display current crisis scenario and question"""
    
    if st.session_state.waiting_for_question:
        if st.button("🚨 Analyze Next System Alert", type="primary", use_container_width=True):
            if get_next_question():
                st.rerun()
        return
    
    # Display narrative with urgency styling
    urgency_class = "urgency-critical" if st.session_state.get('urgency_level') == 'critical' else ""
    
    if st.session_state.get('is_boss_battle'):
        st.markdown(f"""
        <div class="crisis-alert {urgency_class}">
            <h3>🔥 BOSS BATTLE: AI INFILTRATION DETECTED 🔥</h3>
            <p>{st.session_state.current_narrative}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="crisis-alert {urgency_class}">
            <h3>🚨 SYSTEM ALERT: {st.session_state.current_question['title']}</h3>
            <p>{st.session_state.current_narrative}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Display question details
    question = st.session_state.current_question
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 💻 Technical Implementation Required:")
        st.markdown(f"**Severity Level:** {question['difficulty'].upper()}")
        st.markdown(f"**System Component:** {question['mastery'].title()}")
        
        # Question text in a code-like container
        st.markdown(f"""
        <div class="mission-briefing">
            <strong>Mission Briefing:</strong><br>
            {question['text']}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Time pressure indicator
        if st.session_state.get('time_limit'):
            st.markdown(f"""
            <div class="crisis-alert">
                <h4>⏰ Time Limit</h4>
                <p>{st.session_state.time_limit // 60}:{st.session_state.time_limit % 60:02d}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Difficulty indicator
        difficulty_colors = {"easy": "#28a745", "medium": "#ffc107", "hard": "#dc3545"}
        difficulty_color = difficulty_colors.get(question['difficulty'], "#6c757d")
        st.markdown(f"""
        <div class="stat-card">
            <h4 style="color: {difficulty_color}">Threat Level</h4>
            <p style="color: #6c757d;">{question['difficulty_rating']}/100</p>
        </div>
        """, unsafe_allow_html=True)

def display_answer_interface():
    """Display code/answer submission interface"""
    
    if st.session_state.waiting_for_question:
        return
    
    st.markdown("### 🛠️ Deploy Your Solution:")
    
    # Answer input based on question type
    question = st.session_state.current_question
    
    if question['mastery'] in ['python', 'react']:
        # Code editor for programming questions
        user_answer = st.text_area(
            "Enter your code solution:",
            value=st.session_state.user_answer,
            height=200,
            placeholder="# Enter your solution here...\n# Remember: This code will be deployed to production!\n",
            key="code_input"
        )
        
        # Add syntax highlighting preview
        if user_answer:
            st.markdown("**Code Preview:**")
            st.code(user_answer, language='python' if question['mastery'] == 'python' else 'javascript')
    
    else:
        # Text input for mathematics/theory questions
        user_answer = st.text_area(
            "Enter your solution:",
            value=st.session_state.user_answer,
            height=150,
            placeholder="Provide your detailed solution and explanation...",
            key="text_input"
        )
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💾 Save Draft", use_container_width=True):
            st.session_state.user_answer = user_answer
            st.success("Draft saved!")
    
    with col2:
        if st.button("🔍 Ask Team for Hint", use_container_width=True):
            # Generate a contextual hint
            st.info("💬 **Alex Chen:** Think about the specific requirements mentioned in the briefing. What's the most critical aspect we need to address first?")
    
    with col3:
        if st.button("🚀 Deploy Solution", type="primary", use_container_width=True):
            if user_answer.strip():
                submit_answer(user_answer)
            else:
                st.warning("Please enter a solution before deploying!")

def main():
    initialize_game_state()
    
    # Show mastery selection first
    if not display_mastery_selection():
        return
    
    display_header()
    display_stats_sidebar()
    
    # Main content area
    display_current_scenario()
    display_answer_interface()
    
    # Footer with game info
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6c757d; padding: 1rem;">
        <small>
        🎮 DevStorm v1.0 | ⚡ Real-time skill assessment in an immersive tech crisis simulation<br>
        Your performance determines the fate of NeoTech Corp and the digital realm.
        </small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()