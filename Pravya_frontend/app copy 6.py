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
    
    # New session state for conversational flow
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    if 'awaiting_answer' not in st.session_state:
        st.session_state.awaiting_answer = False
    
    if 'session_complete' not in st.session_state:
        st.session_state.session_complete = False

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
                <strong style="color: #ffffff;">{member_name}</strong><br>
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
            st.session_state.awaiting_answer = True
            
            # Add narrative to conversation history
            st.session_state.conversation_history.append({
                "type": "narrative",
                "content": data['narrative'],
                "question": data['question'],
                "timestamp": time.time()
            })
            
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
        with st.spinner("🔍 Deploying solution..."):
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
            
            # Add user answer to conversation history
            st.session_state.conversation_history.append({
                "type": "user_answer",
                "content": user_answer,
                "question_id": st.session_state.current_question['id'],
                "timestamp": time.time()
            })
            
            # Add story continuation to conversation history
            st.session_state.conversation_history.append({
                "type": "story_continuation",
                "content": data['story_continuation'],
                "is_correct": data['is_correct'],
                "score": data['score'],
                "feedback": data['feedback'],
                "achievement": data.get('achievement_unlocked'),
                "timestamp": time.time()
            })
            
            # Check if session is complete
            if data.get('session_complete', False):
                st.session_state.session_complete = True
                st.session_state.awaiting_answer = False
                st.session_state.waiting_for_question = False
            else:
                # Reset for next question
                st.session_state.awaiting_answer = False
                st.session_state.waiting_for_question = True
            
            st.session_state.user_answer = ""
            
            return True
            
        else:
            st.error(f"Evaluation failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return False

def display_conversation_history():
    """Display the ongoing conversation/story"""
    
    st.markdown("### 📻 Mission Communications")
    
    if not st.session_state.conversation_history:
        st.markdown("""
        <div class="team-status">
            <p><strong>🎮 Ready to begin your mission at NeoTech Corp!</strong></p>
            <p>Click "🚨 Analyze Next System Alert" to start your first challenge.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Display conversation history
    for i, entry in enumerate(st.session_state.conversation_history):
        if entry['type'] == 'narrative':
            # Story narrative with question
            urgency_class = "urgency-critical" if st.session_state.get('urgency_level') == 'critical' else ""
            
            st.markdown(f"""
            <div class="crisis-alert {urgency_class}">
                <h4>🚨 CRISIS #{i//3 + 1}: {entry['question']['title']}</h4>
                <p>{entry['content']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display technical challenge
            question = entry['question']
            st.markdown(f"""
            <div class="mission-briefing">
                <strong>Technical Challenge ({question['mastery'].title()}, {question['difficulty'].upper()}):</strong><br>
                {question['text']}
            </div>
            """, unsafe_allow_html=True)
            
        elif entry['type'] == 'user_answer':
            # User's submitted answer
            st.markdown("**Your Solution:**")
            st.code(entry['content'], language='python' if 'def' in entry['content'] or '=' in entry['content'] else 'text')
            
        elif entry['type'] == 'story_continuation':
            # Story response based on answer
            if entry['is_correct']:
                st.markdown(f"""
                <div class="team-status">
                    <h4>✅ DEPLOYMENT SUCCESSFUL (Score: {entry['score']:.0f}/100)</h4>
                    <p>{entry['content']}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="crisis-alert">
                    <h4>❌ DEPLOYMENT FAILED (Score: {entry['score']:.0f}/100)</h4>
                    <p>{entry['content']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Show technical feedback in an expander
            with st.expander("🔍 Technical Analysis"):
                st.write(entry['feedback'])
            
            # Show achievement if any
            if entry.get('achievement'):
                st.success(f"🏆 Achievement Unlocked: {entry['achievement'].replace('_', ' ').title()}!")
            
            st.markdown("---")

def display_current_input():
    """Display input interface for current question"""
    
    if st.session_state.session_complete:
        st.markdown("""
        <div class="team-status">
            <h3>🎉 MISSION COMPLETE!</h3>
            <p>Congratulations! You've successfully completed your DevStorm demo session.</p>
            <p>You've proven your skills under pressure and helped save NeoTech Corp!</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Start New Mission", type="primary", use_container_width=True):
            # Reset session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return
    
    if st.session_state.waiting_for_question:
        questions_answered = st.session_state.game_state['session_questions_answered']
        total_questions = 5
        
        if questions_answered == 0:
            button_text = "🚨 Begin First Crisis Analysis"
        else:
            button_text = f"🚨 Analyze Next System Alert ({questions_answered}/{total_questions} complete)"
        
        if st.button(button_text, type="primary", use_container_width=True):
            if get_next_question():
                st.rerun()
        return
    
    if st.session_state.awaiting_answer:
        st.markdown("### 🛠️ Deploy Your Solution:")
        
        # Answer input based on question type
        question = st.session_state.current_question
        
        if question['mastery'] in ['python', 'react']:
            # Code editor for programming questions
            user_answer = st.text_area(
                "Enter your code solution:",
                value=st.session_state.user_answer,
                height=200,
                placeholder="# Enter your solution here...\n# This code will be deployed immediately!\n",
                key=f"code_input_{len(st.session_state.conversation_history)}"
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
                key=f"text_input_{len(st.session_state.conversation_history)}"
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
                    if submit_answer(user_answer):
                        st.rerun()
                else:
                    st.warning("Please enter a solution before deploying!")

def main():
    initialize_game_state()
    
    # Show mastery selection first
    if not display_mastery_selection():
        return
    
    display_header()
    display_stats_sidebar()
    
    # Main content area - conversational flow
    display_conversation_history()
    display_current_input()
    
    # Footer with game info
    st.markdown("---")
    
    # Progress indicator
    questions_answered = st.session_state.game_state['session_questions_answered']
    progress_text = f"Question {questions_answered}/5 complete" if questions_answered > 0 else "Ready to begin"
    
    st.markdown(f"""
    <div style="text-align: center; color: #6c757d; padding: 1rem;">
        <small>
        🎮 DevStorm v1.0 | ⚡ {progress_text} | Real-time skill assessment<br>
        Your coding decisions shape the fate of NeoTech Corp and the digital realm.
        </small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()