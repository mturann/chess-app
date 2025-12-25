import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(
    page_title="Chess Coach",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    /* Chat bubbles */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 20px 20px 5px 20px;
        margin: 10px 0;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
    }
    .assistant-message {
        background: #2d2d2d;
        color: #f0f0f0;
        padding: 15px 20px;
        border-radius: 20px 20px 20px 5px;
        margin: 10px 0;
        max-width: 85%;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        line-height: 1.6;
    }
    .assistant-message code {
        background: #1a1a2e;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: monospace;
    }
    .assistant-message a {
        color: #667eea;
    }
    
    /* Stats cards */
    .stat-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin: 5px 0;
        border: 1px solid #333;
    }
    .stat-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #aaa;
        margin-top: 3px;
    }
    .stat-delta-positive {
        color: #4CAF50;
        font-size: 0.9rem;
    }
    .stat-delta-negative {
        color: #f44336;
        font-size: 0.9rem;
    }
    
    /* Quick action buttons */
    .quick-btn {
        background: #2d2d2d;
        border: 1px solid #444;
        color: #f0f0f0;
        padding: 8px 12px;
        border-radius: 20px;
        margin: 3px;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.85rem;
    }
    .quick-btn:hover {
        background: #667eea;
        border-color: #667eea;
    }
    
    /* Streak badges */
    .streak-win {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
        padding: 8px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 5px 0;
    }
    .streak-loss {
        background: linear-gradient(135deg, #f44336 0%, #c62828 100%);
        color: white;
        padding: 8px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 5px 0;
    }
    
    /* Warning box */
    .warning-box {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        color: white;
        padding: 15px;
        border-radius: 12px;
        margin: 10px 0;
    }
    
    /* Welcome card */
    .welcome-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
        border: 1px solid #333;
    }
    
    /* Opening tag */
    .opening-tag {
        background: #333;
        color: #f0f0f0;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 2px;
        display: inline-block;
    }
    .opening-good {
        border-left: 3px solid #4CAF50;
    }
    .opening-bad {
        border-left: 3px solid #f44336;
    }
    
    /* Loading animation */
    .loading-chess {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        padding: 20px;
    }
    .loading-chess span {
        font-size: 2rem;
        animation: bounce 0.6s ease-in-out infinite;
    }
    .loading-chess span:nth-child(2) { animation-delay: 0.1s; }
    .loading-chess span:nth-child(3) { animation-delay: 0.2s; }
    .loading-chess span:nth-child(4) { animation-delay: 0.3s; }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    /* Recent results */
    .result-icon {
        display: inline-block;
        width: 25px;
        height: 25px;
        border-radius: 50%;
        text-align: center;
        line-height: 25px;
        margin: 2px;
        font-size: 0.8rem;
    }
    .result-win { background: #4CAF50; }
    .result-loss { background: #f44336; }
    .result-draw { background: #ff9800; }
</style>
""", unsafe_allow_html=True)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
DEFAULT_MAX_GAMES = 200
MAX_GAMES_OPTIONS = [100, 200, 500, 1000]
TIME_FILTERS = {
    "All Time": None,
    "Last Week": 7,
    "Last Month": 30,
    "Last 3 Months": 90
}

# Quick questions
QUICK_QUESTIONS = [
    "🎯 What are my main weaknesses?",
    "📚 Which openings should I study?",
    "⏱️ How's my time management?",
    "📈 How can I reach the next level?",
    "🎮 Should I take a break?",
    "⚔️ Analyze my recent games"
]

# Rate limiting
RATE_LIMIT_SECONDS = 3
last_message_time = 0


@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_user_games(username, max_games=200, perf_type="blitz", since_days=None):
    """Fetch user games with caching"""
    url = f"https://lichess.org/api/games/user/{username}"
    headers = {"Accept": "application/x-ndjson"}
    params = {
        "max": max_games,
        "rated": "true",
        "perfType": perf_type,
        "clocks": "true",
        "opening": "true",
        "accuracy": "true"  # Request accuracy data
    }
    
    if since_days:
        since_timestamp = int((datetime.now() - timedelta(days=since_days)).timestamp() * 1000)
        params["since"] = since_timestamp
    
    games = []
    try:
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=60)
        if response.status_code == 404:
            return None, "User not found"
        if response.status_code == 429:
            return None, "Rate limited - please wait a moment"
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                games.append(json.loads(line.decode('utf-8')))
        return games if games else (None, "No games found")
    except requests.exceptions.Timeout:
        return None, "Request timed out - try fewer games"
    except Exception as e:
        return None, f"Error: {str(e)}"


def analyze_games(games, username):
    """Comprehensive game analysis"""
    if not games:
        return None
    
    stats = {
        'total_games': len(games),
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'win_rate': 0,
        'current_rating': 0,
        'rating_change': 0,
        'time_trouble_games': 0,
        'avg_moves': 0,
        'openings': defaultdict(lambda: {'games': 0, 'wins': 0, 'losses': 0}),
        'color_stats': {'white': {'games': 0, 'wins': 0}, 'black': {'games': 0, 'wins': 0}},
        'recent_results': [],
        'streak': 0,
        'best_win': None,
        'worst_loss': None,
        'avg_opponent_rating': 0,
        'games_today': 0,
        'games_this_week': 0,
        'avg_accuracy': 0,
        'accuracy_data': [],
        'opponents': defaultdict(lambda: {'games': 0, 'wins': 0, 'losses': 0, 'rating': 0}),
        'hourly_performance': defaultdict(lambda: {'games': 0, 'wins': 0}),
        'rating_history': [],
        'blunders_estimate': 0
    }
    
    total_moves = 0
    total_opponent_rating = 0
    opponent_count = 0
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    accuracy_sum = 0
    accuracy_count = 0
    
    for i, game in enumerate(games):
        players = game.get('players', {})
        white_info = players.get('white', {})
        black_info = players.get('black', {})
        
        white_user = white_info.get('user', {}).get('name', '').lower()
        is_white = white_user == username.lower()
        color = 'white' if is_white else 'black'
        
        player_info = white_info if is_white else black_info
        opponent_info = black_info if is_white else white_info
        opponent_name = opponent_info.get('user', {}).get('name', 'Anonymous')
        
        # Rating tracking
        current_rating = player_info.get('rating', 0)
        if i == 0:
            stats['current_rating'] = current_rating
        
        stats['rating_history'].append({
            'game': i + 1,
            'rating': current_rating,
            'date': datetime.fromtimestamp(game.get('createdAt', 0) / 1000)
        })
        
        # Result
        winner = game.get('winner')
        if winner == color:
            result = 'win'
            stats['wins'] += 1
        elif winner is None:
            result = 'draw'
            stats['draws'] += 1
        else:
            result = 'loss'
            stats['losses'] += 1
        
        # Color stats
        stats['color_stats'][color]['games'] += 1
        if result == 'win':
            stats['color_stats'][color]['wins'] += 1
        
        # Recent results (last 20)
        if i < 20:
            stats['recent_results'].append(result)
        
        # Opening analysis
        opening = game.get('opening', {})
        opening_name = opening.get('name', 'Unknown')
        if opening_name != 'Unknown':
            base_opening = opening_name.split(':')[0].split(',')[0].strip()
            stats['openings'][base_opening]['games'] += 1
            if result == 'win':
                stats['openings'][base_opening]['wins'] += 1
            elif result == 'loss':
                stats['openings'][base_opening]['losses'] += 1
        
        # Time trouble analysis
        clocks = game.get('clocks', [])
        if clocks:
            player_clocks = []
            for j, clock in enumerate(clocks):
                if (j % 2 == 0 and is_white) or (j % 2 == 1 and not is_white):
                    player_clocks.append(clock / 100)
            if player_clocks and min(player_clocks) < 30:
                stats['time_trouble_games'] += 1
        
        # Move count
        moves = game.get('moves', '')
        if moves:
            total_moves += len(moves.split()) // 2
        
        # Opponent tracking
        opponent_rating = opponent_info.get('rating', 0)
        if opponent_rating:
            total_opponent_rating += opponent_rating
            opponent_count += 1
            
            stats['opponents'][opponent_name]['games'] += 1
            stats['opponents'][opponent_name]['rating'] = opponent_rating
            if result == 'win':
                stats['opponents'][opponent_name]['wins'] += 1
                if stats['best_win'] is None or opponent_rating > stats['best_win']:
                    stats['best_win'] = opponent_rating
            elif result == 'loss':
                stats['opponents'][opponent_name]['losses'] += 1
                if stats['worst_loss'] is None or opponent_rating < stats['worst_loss']:
                    stats['worst_loss'] = opponent_rating
        
        # Accuracy
        player_accuracy = player_info.get('accuracy')
        if player_accuracy:
            accuracy_sum += player_accuracy
            accuracy_count += 1
            stats['accuracy_data'].append(player_accuracy)
        
        # Time-based stats
        game_time = datetime.fromtimestamp(game.get('createdAt', 0) / 1000)
        game_date = game_time.date()
        game_hour = game_time.hour
        
        if game_date == today:
            stats['games_today'] += 1
        if game_date >= week_ago:
            stats['games_this_week'] += 1
        
        # Hourly performance
        stats['hourly_performance'][game_hour]['games'] += 1
        if result == 'win':
            stats['hourly_performance'][game_hour]['wins'] += 1
    
    # Calculate aggregates
    stats['win_rate'] = (stats['wins'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
    stats['avg_moves'] = total_moves / stats['total_games'] if stats['total_games'] > 0 else 0
    stats['avg_opponent_rating'] = total_opponent_rating / opponent_count if opponent_count > 0 else 0
    stats['time_trouble_rate'] = stats['time_trouble_games'] / stats['total_games'] * 100 if stats['total_games'] > 0 else 0
    stats['avg_accuracy'] = accuracy_sum / accuracy_count if accuracy_count > 0 else 0
    
    # Rating change
    if len(stats['rating_history']) >= 20:
        stats['rating_change'] = stats['current_rating'] - stats['rating_history'][19]['rating']
    elif len(stats['rating_history']) > 1:
        stats['rating_change'] = stats['current_rating'] - stats['rating_history'][-1]['rating']
    
    # Current streak
    streak = 0
    for result in stats['recent_results']:
        if result == 'win':
            if streak >= 0:
                streak += 1
            else:
                break
        elif result == 'loss':
            if streak <= 0:
                streak -= 1
            else:
                break
        else:
            break
    stats['streak'] = streak
    
    # Find best/worst hours
    if stats['hourly_performance']:
        best_hour = max(stats['hourly_performance'].items(), 
                       key=lambda x: x[1]['wins'] / x[1]['games'] if x[1]['games'] >= 5 else 0)
        stats['best_hour'] = best_hour[0] if best_hour[1]['games'] >= 5 else None
    
    return stats


def get_opening_stats(stats):
    """Get sorted opening statistics"""
    opening_list = []
    for opening, data in stats['openings'].items():
        if data['games'] >= 3:
            win_rate = data['wins'] / data['games'] * 100
            opening_list.append({
                'name': opening,
                'games': data['games'],
                'win_rate': win_rate,
                'wins': data['wins'],
                'losses': data['losses']
            })
    return sorted(opening_list, key=lambda x: x['games'], reverse=True)


def get_frequent_opponents(stats, top_n=5):
    """Get most frequent opponents"""
    opponents = []
    for name, data in stats['opponents'].items():
        if data['games'] >= 2:
            win_rate = data['wins'] / data['games'] * 100
            opponents.append({
                'name': name,
                'games': data['games'],
                'wins': data['wins'],
                'losses': data['losses'],
                'win_rate': win_rate,
                'rating': data['rating']
            })
    return sorted(opponents, key=lambda x: x['games'], reverse=True)[:top_n]


def create_system_prompt(stats, username, game_type):
    """Create comprehensive system prompt for AI coach"""
    openings = get_opening_stats(stats)
    weak_openings = [o for o in openings if o['win_rate'] < 45][:5]
    strong_openings = [o for o in openings if o['win_rate'] >= 55][:5]
    frequent_opponents = get_frequent_opponents(stats)
    
    white_games = stats['color_stats']['white']['games']
    black_games = stats['color_stats']['black']['games']
    white_wr = stats['color_stats']['white']['wins'] / white_games * 100 if white_games > 0 else 50
    black_wr = stats['color_stats']['black']['wins'] / black_games * 100 if black_games > 0 else 50
    
    recent_str = ', '.join(stats['recent_results'][:10])
    
    weak_str = '\n'.join([f"- {o['name']}: {o['win_rate']:.0f}% ({o['games']} games)" for o in weak_openings]) if weak_openings else "- None identified (good job!)"
    strong_str = '\n'.join([f"- {o['name']}: {o['win_rate']:.0f}% ({o['games']} games)" for o in strong_openings]) if strong_openings else "- No standout openings yet"
    
    streak_type = 'winning' if stats['streak'] > 0 else 'losing' if stats['streak'] < 0 else 'neutral'
    
    # Accuracy insight
    accuracy_insight = ""
    if stats['avg_accuracy'] > 0:
        if stats['avg_accuracy'] >= 90:
            accuracy_insight = f"Excellent accuracy ({stats['avg_accuracy']:.1f}%) - playing very precisely!"
        elif stats['avg_accuracy'] >= 80:
            accuracy_insight = f"Good accuracy ({stats['avg_accuracy']:.1f}%) - solid play with room for improvement"
        elif stats['avg_accuracy'] >= 70:
            accuracy_insight = f"Average accuracy ({stats['avg_accuracy']:.1f}%) - focus on reducing mistakes"
        else:
            accuracy_insight = f"Low accuracy ({stats['avg_accuracy']:.1f}%) - consider playing slower time controls"
    
    # Time management insight
    time_insight = ""
    if stats['time_trouble_rate'] > 30:
        time_insight = "⚠️ CRITICAL: Getting into time trouble in over 30% of games! Needs immediate attention."
    elif stats['time_trouble_rate'] > 20:
        time_insight = "Warning: Time trouble in 20%+ games. Work on playing faster in the opening."
    elif stats['time_trouble_rate'] > 10:
        time_insight = "Occasional time pressure issues. Consider pre-moving in obvious positions."
    else:
        time_insight = "Good time management overall."
    
    # Opponent patterns
    opponent_str = ""
    if frequent_opponents:
        opponent_str = "FREQUENT OPPONENTS:\n"
        for opp in frequent_opponents[:3]:
            opponent_str += f"- vs {opp['name']} ({opp['rating']}): {opp['wins']}W/{opp['losses']}L ({opp['win_rate']:.0f}%)\n"
    
    prompt = f"""You are an expert chess coach providing personalized advice. You have deep knowledge of chess strategy, openings, and improvement methods.

PLAYER PROFILE:
- Username: {username}
- Game Type: {game_type}
- Rating: {stats['current_rating']} ({stats['rating_change']:+d} over last 20 games)
- Record: {stats['wins']}W / {stats['draws']}D / {stats['losses']}L ({stats['win_rate']:.1f}% win rate)
- Games Analyzed: {stats['total_games']}
- Average Opponent Rating: {stats['avg_opponent_rating']:.0f}

ACCURACY & TIME:
- Average Accuracy: {stats['avg_accuracy']:.1f}% (if available)
- {accuracy_insight}
- Time Trouble Rate: {stats['time_trouble_rate']:.1f}%
- {time_insight}
- Average Game Length: {stats['avg_moves']:.0f} moves

COLOR PERFORMANCE:
- As White: {white_wr:.1f}% win rate ({white_games} games)
- As Black: {black_wr:.1f}% win rate ({black_games} games)

CURRENT FORM:
- Last 10 games: {recent_str}
- Current Streak: {abs(stats['streak'])} game {streak_type} streak
- Games Today: {stats['games_today']}
- Games This Week: {stats['games_this_week']}

WEAK OPENINGS (needs work):
{weak_str}

STRONG OPENINGS (keep playing):
{strong_str}

{opponent_str}

NOTABLE RESULTS:
- Best Win: {stats['best_win']} rated opponent
- Worst Loss: {stats['worst_loss']} rated opponent

COACHING INSTRUCTIONS:
1. Be encouraging but honest - point out real issues
2. Give SPECIFIC advice using their actual data
3. Keep responses concise (2-4 paragraphs max)
4. Suggest specific Lichess studies or resources when relevant (use links like https://lichess.org/study)
5. If they're on a losing streak (3+ losses), suggest taking a break
6. If they play too many games (10+ today), suggest quality over quantity
7. Use chess notation when discussing moves
8. Reference their specific openings and stats
9. If accuracy is low, suggest analyzing games with Lichess analysis
10. Be supportive and motivating - they're trying to improve!

Respond as a friendly, knowledgeable coach who genuinely wants to help them improve."""

    return prompt


def get_ai_response_stream(system_prompt, chat_history, user_message):
    """Get AI response with streaming"""
    try:
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in chat_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        messages.append({"role": "user", "content": user_message})
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 1500,
                "temperature": 0.7,
                "stream": False  # Groq streaming is different, keeping simple for now
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"], None
        elif response.status_code == 429:
            return None, "Rate limited - please wait a moment before sending another message."
        else:
            return None, f"API Error: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return None, "Request timed out - please try again."
    except Exception as e:
        return None, f"Error: {str(e)}"


def generate_session_summary(messages, stats):
    """Generate a summary of the coaching session"""
    if len(messages) < 4:
        return None
    
    summary = f"""## 📋 Session Summary

**Player:** Rating {stats['current_rating']} | {stats['win_rate']:.1f}% Win Rate

**Key Topics Discussed:**
"""
    
    # Extract key topics from messages
    topics = []
    keywords = {
        'opening': '📚 Opening preparation',
        'time': '⏱️ Time management',
        'tactic': '⚔️ Tactical training',
        'endgame': '🏁 Endgame technique',
        'blunder': '❌ Reducing blunders',
        'rating': '📈 Rating improvement',
        'streak': '🔥 Handling streaks'
    }
    
    for msg in messages:
        content = msg['content'].lower()
        for keyword, topic in keywords.items():
            if keyword in content and topic not in topics:
                topics.append(topic)
    
    if topics:
        for topic in topics[:5]:
            summary += f"- {topic}\n"
    else:
        summary += "- General chess improvement\n"
    
    summary += f"""
**Quick Stats Reminder:**
- Time Trouble Rate: {stats['time_trouble_rate']:.1f}%
- Current Streak: {stats['streak']:+d}
- Games This Week: {stats['games_this_week']}
"""
    
    return summary


def export_chat(messages, username, stats):
    """Export chat as text"""
    export_text = f"Chess Coach Session - {username}\n"
    export_text += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    export_text += f"Rating: {stats['current_rating']} | Win Rate: {stats['win_rate']:.1f}%\n"
    export_text += "=" * 50 + "\n\n"
    
    for msg in messages:
        role = "You" if msg["role"] == "user" else "Coach"
        export_text += f"{role}:\n{msg['content']}\n\n"
    
    return export_text


# ===== MAIN APP =====

st.markdown("""
<h1 style="text-align: center;">🤖 AI Chess Coach</h1>
<p style="text-align: center; color: #888;">Your personal chess improvement assistant powered by Llama 3.3</p>
""", unsafe_allow_html=True)

# Check API key
if not GROQ_API_KEY:
    st.error("⚠️ GROQ_API_KEY not found!")
    st.markdown("""
    ### Setup Instructions:
    
    1. **Get free API key:** [console.groq.com/keys](https://console.groq.com/keys)
    
    2. **Add to .env file:**
    ```
    GROQ_API_KEY=gsk_xxxxxxxxxxxxx
    ```
    """)
    st.stop()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_stats' not in st.session_state:
    st.session_state.user_stats = None
if 'coach_username' not in st.session_state:
    st.session_state.coach_username = get_username()
if 'system_prompt' not in st.session_state:
    st.session_state.system_prompt = None
if 'game_type' not in st.session_state:
    st.session_state.game_type = "blitz"
if 'last_message_time' not in st.session_state:
    st.session_state.last_message_time = 0

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Setup")
    
    username = st.text_input("Lichess Username", value=st.session_state.coach_username)
    
    col1, col2 = st.columns(2)
    with col1:
        game_type = st.selectbox(
            "Game Type",
            ["blitz", "rapid", "bullet", "classical"],
            index=["blitz", "rapid", "bullet", "classical"].index(st.session_state.game_type)
        )
    with col2:
        max_games = st.selectbox("Games", MAX_GAMES_OPTIONS, index=1)
    
    time_filter = st.selectbox("Time Filter", list(TIME_FILTERS.keys()), index=0)
    since_days = TIME_FILTERS[time_filter]
    
    if st.button("📊 Load My Data", type="primary", use_container_width=True):
        if not username:
            st.warning("Enter username!")
        else:
            with st.spinner(""):
                st.markdown("""
                <div class="loading-chess">
                    <span>♟️</span><span>♞</span><span>♝</span><span>♜</span>
                </div>
                """, unsafe_allow_html=True)
                
                result = fetch_user_games(username, max_games, game_type, since_days)
                
                if isinstance(result, tuple):
                    games, error = result
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        games = result
                else:
                    games = result
                
                if games and not isinstance(games, tuple):
                    stats = analyze_games(games, username)
                    if stats:
                        st.session_state.user_stats = stats
                        st.session_state.coach_username = username
                        st.session_state.game_type = game_type
                        set_username(username)
                        st.session_state.system_prompt = create_system_prompt(stats, username, game_type)
                        
                        # Welcome message
                        welcome = f"👋 Hello **{username}**! I've analyzed your last **{stats['total_games']} {game_type}** games.\n\n"
                        
                        welcome += f"📊 **Quick Overview:**\n"
                        welcome += f"- Rating: **{stats['current_rating']}** ({stats['rating_change']:+d} recently)\n"
                        welcome += f"- Win Rate: **{stats['win_rate']:.1f}%**\n"
                        welcome += f"- Time Trouble: **{stats['time_trouble_rate']:.1f}%** of games\n\n"
                        
                        if stats['streak'] >= 3:
                            welcome += f"🔥 **You're on fire!** {stats['streak']} game winning streak!\n\n"
                        elif stats['streak'] <= -3:
                            welcome += f"😰 Tough stretch with {abs(stats['streak'])} losses in a row. Let's figure out what's going wrong.\n\n"
                        
                        if stats['games_today'] >= 10:
                            welcome += f"⚠️ You've played {stats['games_today']} games today. Consider taking a break for quality over quantity.\n\n"
                        
                        welcome += "Ask me anything about your chess! I can help with:\n"
                        welcome += "- 🎯 Identifying weaknesses\n"
                        welcome += "- 📚 Opening recommendations\n"
                        welcome += "- ⏱️ Time management tips\n"
                        welcome += "- 📈 Rating improvement strategies"
                        
                        st.session_state.messages = [{"role": "assistant", "content": welcome}]
                        st.success(f"✅ Loaded {stats['total_games']} games!")
                        st.rerun()
    
    # Stats display
    if st.session_state.user_stats:
        st.markdown("---")
        stats = st.session_state.user_stats
        
        # Rating card
        delta_color = "stat-delta-positive" if stats['rating_change'] >= 0 else "stat-delta-negative"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['current_rating']}</div>
            <div class="stat-label">Rating</div>
            <div class="{delta_color}">{stats['rating_change']:+d}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Win rate
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #4CAF50;">{stats['win_rate']:.0f}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            trouble_color = "#f44336" if stats['time_trouble_rate'] > 20 else "#4CAF50"
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: {trouble_color};">{stats['time_trouble_rate']:.0f}%</div>
                <div class="stat-label">Time Trouble</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Streak
        if stats['streak'] >= 3:
            st.markdown(f'<div class="streak-win">🔥 {stats["streak"]} Win Streak!</div>', unsafe_allow_html=True)
        elif stats['streak'] <= -3:
            st.markdown(f'<div class="streak-loss">❄️ {abs(stats["streak"])} Loss Streak</div>', unsafe_allow_html=True)
        
        # Recent results
        st.markdown("**Recent:**")
        results_html = ""
        for r in stats['recent_results'][:10]:
            if r == 'win':
                results_html += '<span class="result-icon result-win">W</span>'
            elif r == 'loss':
                results_html += '<span class="result-icon result-loss">L</span>'
            else:
                results_html += '<span class="result-icon result-draw">D</span>'
        st.markdown(results_html, unsafe_allow_html=True)
        
        # Accuracy if available
        if stats['avg_accuracy'] > 0:
            st.markdown(f"**Avg Accuracy:** {stats['avg_accuracy']:.1f}%")
        
        st.markdown("---")
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Summary", use_container_width=True):
                summary = generate_session_summary(st.session_state.messages, stats)
                if summary:
                    st.session_state.messages.append({"role": "assistant", "content": summary})
                    st.rerun()
        with col2:
            if st.button("💾 Export", use_container_width=True):
                export = export_chat(st.session_state.messages, username, stats)
                st.download_button(
                    "📥 Download",
                    export,
                    file_name=f"chess_coach_{username}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# Main chat area
if st.session_state.user_stats:
    # Quick questions
    st.markdown("**Quick Questions:**")
    cols = st.columns(3)
    for i, question in enumerate(QUICK_QUESTIONS):
        with cols[i % 3]:
            if st.button(question, key=f"quick_{i}", use_container_width=True):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": question})
                
                # Get response
                response, error = get_ai_response_stream(
                    st.session_state.system_prompt,
                    st.session_state.messages[:-1],
                    question
                )
                
                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {error}"})
                
                st.rerun()
    
    st.markdown("---")
    
    # Chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
    
    # Chat input
    if prompt := st.chat_input("Ask your chess coach..."):
        # Rate limiting
        current_time = time.time()
        if current_time - st.session_state.last_message_time < RATE_LIMIT_SECONDS:
            st.warning(f"Please wait a moment before sending another message.")
        else:
            st.session_state.last_message_time = current_time
            
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Show loading
            with st.spinner(""):
                st.markdown("""
                <div class="loading-chess">
                    <span>♟️</span><span>♞</span><span>♝</span><span>♜</span>
                </div>
                """, unsafe_allow_html=True)
                
                response, error = get_ai_response_stream(
                    st.session_state.system_prompt,
                    st.session_state.messages[:-1],
                    prompt
                )
            
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                st.session_state.messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {error}. Please try again."})
            
            st.rerun()

else:
    # Welcome screen
    st.markdown("""
    <div class="welcome-card">
        <div style="font-size: 4rem;">♟️🤖</div>
        <h2>Welcome to AI Chess Coach!</h2>
        <p style="color: #aaa;">Enter your Lichess username in the sidebar and click <strong>Load My Data</strong> to start your personalized coaching session.</p>
        <br>
        <p style="color: #888; font-size: 0.9rem;">I'll analyze your games and provide tailored advice on:</p>
        <p>
            <span class="opening-tag">📚 Openings</span>
            <span class="opening-tag">⏱️ Time Management</span>
            <span class="opening-tag">📈 Rating Growth</span>
            <span class="opening-tag">🎯 Weaknesses</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Powered by Groq + Llama 3.3 | Data from Lichess API | Free & Open Source")