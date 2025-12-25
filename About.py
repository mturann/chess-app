import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.session_manager import init_session_state

st.set_page_config(
    page_title="Chess Analytics Hub",
    page_icon="♟️",
    layout="wide"
)

# Initialize session state
init_session_state()

# Custom CSS for better styling
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1a1a2e;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 0;
    }
    .subtitle {
        text-align: center;
        color: #4a4a6a;
        font-size: 1.2rem;
        margin-top: 0;
    }
    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .feature-title {
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .stat-box {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Header with logo
col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    st.markdown('''
    <div style="text-align: center;">
        <h1 style="font-size: 4rem; margin-bottom: 0; display: inline-flex; align-items: center; justify-content: center; gap: 15px;">
            <span>♟️</span>
            <span>Chess Analytics Hub</span>
        </h1>
        <p style="color: #4a4a6a; font-size: 1.5rem; margin-top: 10px;">Analyze your Lichess games, discover patterns, and improve your chess</p>
    </div>
    ''', unsafe_allow_html=True)

st.markdown("---")

# GIF Section - Chess animation
gif_url = "https://images.chesscomfiles.com/uploads/game-gifs/90px/green/neo/0/cc/0/0/5fc9a99d27bedb41a7abfdd3a0761870f31c1356848335c11558914aa0ee1fd0.gif"

st.markdown(f'''
<div style="display: flex; justify-content: center;">
    <img src="{gif_url}" width="350">
</div>
''', unsafe_allow_html=True)

st.markdown("---")

# What is this app section
st.header("🎯 What is Chess Analytics Hub?")
st.markdown("""
This is a comprehensive analytics platform designed to help chess players of all levels understand their 
game better. By connecting to the **Lichess API**, we fetch your game data and provide deep insights 
into your playing patterns, strengths, and areas for improvement.

Whether you're a beginner trying to understand basic patterns or an advanced player looking to fine-tune 
your opening repertoire, this tool has something for everyone.
""")

st.markdown("---")

# Features Section
st.header("✨ Features")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">📊 Profile Analysis</div>
        View your complete Lichess profile, ratings across all game types, win/loss statistics, and account history.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">📚 Opening Repertoire</div>
        Discover which openings you play most frequently, your win rates with each, and identify weak spots in your repertoire.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">⏱️ Time Management</div>
        Analyze how you use your clock, identify time trouble patterns, and see how time pressure affects your results.
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">📈 Rating Prediction</div>
        Use machine learning to forecast your future rating based on your recent performance and trends.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">🤖 AI Chess Coach</div>
        Get personalized coaching advice from an AI that understands your specific weaknesses and playing style.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">🎯 Win Probability</div>
        Predict match outcomes between any two players using advanced ML models trained on thousands of games.
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# How to use section
st.header("🚀 How to Get Started")

st.markdown("""
1. **Navigate** to any page using the sidebar on the left
2. **Enter** your Lichess username when prompted
3. **Analyze** your games and discover insights about your play
4. **Improve** based on the recommendations and data

> 💡 **Tip:** Your username is saved across pages during your session, so you only need to enter it once!
""")

st.markdown("---")

# Pages overview
st.header("📑 Available Pages")

pages_info = {
    "👤 Profile": "View your complete Lichess profile with ratings, game statistics, and account information",
    "📕 Rating History": "Track your rating progress over time with interactive charts",
    "📚 Opening Repertoire": "Analyze your most played openings and their success rates",
    "📚 Opening Coach": "Get detailed coaching on your opening weaknesses with study resources",
    "🔮 Rating Prediction": "ML-powered rating forecasts based on your recent performance",
    "⏱️ Time Management": "Understand your clock usage patterns and time trouble frequency",
    "🤖 Chess Coach": "AI-powered personalized coaching based on your game data",
    "🎯 Win Probability": "Predict match outcomes between two players",
    "👑 Top Players": "See the highest-rated players on Lichess",
    "🎮 Ongoing Game": "View your current live game"
}

for page, description in pages_info.items():
    with st.expander(page):
        st.write(description)

st.markdown("---")

# Chess Quote
st.markdown("---")

col1, col2, col3 = st.columns([1, 4, 1])
with col2:
    st.markdown("""
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 15px; margin: 20px 0;">
        <p style="font-size: 1.5rem; font-style: italic; color: #f0f0f0; margin-bottom: 15px;">
            "The beauty of a move lies not in its appearance but in the thought behind it."
        </p>
        <p style="color: #a0a0a0; font-size: 1.1rem;">
            — Aaron Nimzowitsch
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Footer
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    <p>Made with ❤️ for chess enthusiasts</p>
    <p><small>Data powered by <a href="https://lichess.org" target="_blank">Lichess.org</a> API</small></p>
</div>
""", unsafe_allow_html=True)

# Sidebar info
with st.sidebar:
    st.info("👈 Select a page from the sidebar to start analyzing your games!")
    st.markdown("---")
    st.markdown("### Quick Links")
    st.markdown("[🔗 Lichess.org](https://lichess.org)")
    st.markdown("[📖 Lichess API Docs](https://lichess.org/api)")