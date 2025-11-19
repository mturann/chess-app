import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px
import plotly.graph_objs as go
from collections import defaultdict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token
from utils.cache_manager import fetch_user_games_cached

st.set_page_config(page_title="Opening Coach", page_icon="📚")

OPENING_DATABASE = {
    "Italian Game": {
        "eco": ["C50", "C51", "C52", "C53", "C54"],
        "key_moves": "e4 e5 Nf3 Nc6 Bc4",
        "alternatives": ["Spanish Opening", "Scotch Game", "Four Knights Game"],
        "study_links": [
            "https://lichess.org/study/iQ4URVCR",
            "https://lichess.org/study/zpLwJLvM"
        ],
        "video_keywords": "Italian Game chess opening tutorial"
    },
    "Sicilian Defense": {
        "eco": ["B20", "B21", "B22", "B23", "B27", "B28", "B29"],
        "key_moves": "e4 c5",
        "alternatives": ["French Defense", "Caro-Kann Defense", "Pirc Defense"],
        "study_links": [
            "https://lichess.org/study/CmhHXNFD",
            "https://lichess.org/study/MYCzx5wX"
        ],
        "video_keywords": "Sicilian Defense chess tutorial Najdorf Dragon"
    },
    "Queen's Gambit": {
        "eco": ["D06", "D07", "D08", "D09", "D10", "D11"],
        "key_moves": "d4 d5 c4",
        "alternatives": ["London System", "Catalan Opening", "Torre Attack"],
        "study_links": [
            "https://lichess.org/study/JDPLxKyM",
            "https://lichess.org/study/wKLiJXwD"
        ],
        "video_keywords": "Queens Gambit chess opening declined accepted"
    },
    "King's Indian Defense": {
        "eco": ["E60", "E61", "E62", "E70", "E71", "E72"],
        "key_moves": "d4 Nf6 c4 g6",
        "alternatives": ["Nimzo-Indian Defense", "Queen's Indian Defense", "Bogo-Indian Defense"],
        "study_links": [
            "https://lichess.org/study/yxiheWKk",
            "https://lichess.org/study/5nDQJSX4"
        ],
        "video_keywords": "Kings Indian Defense KID chess tutorial"
    },
    "French Defense": {
        "eco": ["C00", "C01", "C02", "C03", "C04", "C05"],
        "key_moves": "e4 e6",
        "alternatives": ["Caro-Kann Defense", "Sicilian Defense", "Scandinavian Defense"],
        "study_links": [
            "https://lichess.org/study/zo5n3R8A",
            "https://lichess.org/study/4UlQr0Cc"
        ],
        "video_keywords": "French Defense chess opening Winawer Tarrasch"
    },
    "Caro-Kann Defense": {
        "eco": ["B10", "B11", "B12", "B13", "B14", "B15"],
        "key_moves": "e4 c6",
        "alternatives": ["French Defense", "Sicilian Defense", "Modern Defense"],
        "study_links": [
            "https://lichess.org/study/gvdMFCPy",
            "https://lichess.org/study/OxKnt3u5"
        ],
        "video_keywords": "Caro Kann Defense chess opening advance variation"
    },
    "Spanish Opening": {
        "eco": ["C60", "C61", "C62", "C63", "C64", "C65"],
        "key_moves": "e4 e5 Nf3 Nc6 Bb5",
        "alternatives": ["Italian Game", "Scotch Game", "Vienna Game"],
        "study_links": [
            "https://lichess.org/study/d9OPX3eo",
            "https://lichess.org/study/Graj4QRL"
        ],
        "video_keywords": "Spanish Opening Ruy Lopez Berlin Marshall"
    },
    "London System": {
        "eco": ["D00", "D02"],
        "key_moves": "d4 d5 Bf4",
        "alternatives": ["Queen's Gambit", "Torre Attack", "Colle System"],
        "study_links": [
            "https://lichess.org/study/U9tOgKY8",
            "https://lichess.org/study/ttkNbPz7"
        ],
        "video_keywords": "London System chess opening tutorial for beginners"
    }
}

def analyze_opening_performance(games, username):
    opening_stats = defaultdict(lambda: {
        'games': 0, 'wins': 0, 'draws': 0, 'losses': 0, 
        'as_white': 0, 'as_black': 0, 'avg_accuracy': []
    })
    
    for game in games:
        opening = game.get('opening', {})
        opening_name = opening.get('name', 'Unknown')
        
        if opening_name == 'Unknown':
            continue
            
        players = game.get('players', {})
        is_white = players.get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
        color = 'white' if is_white else 'black'
        winner = game.get('winner')
        
        stats = opening_stats[opening_name]
        stats['games'] += 1
        
        if is_white:
            stats['as_white'] += 1
        else:
            stats['as_black'] += 1
            
        if winner == color:
            stats['wins'] += 1
        elif winner is None:
            stats['draws'] += 1
        else:
            stats['losses'] += 1
            
        if 'accuracy' in players.get(color, {}):
            stats['avg_accuracy'].append(players[color]['accuracy'])
    
    results = []
    for opening, stats in opening_stats.items():
        if stats['games'] >= 3:
            win_rate = (stats['wins'] / stats['games']) * 100
            avg_acc = sum(stats['avg_accuracy']) / len(stats['avg_accuracy']) if stats['avg_accuracy'] else 0
            
            results.append({
                'opening': opening,
                'games': stats['games'],
                'win_rate': win_rate,
                'wins': stats['wins'],
                'draws': stats['draws'],
                'losses': stats['losses'],
                'as_white': stats['as_white'],
                'as_black': stats['as_black'],
                'avg_accuracy': avg_acc,
                'performance_score': win_rate * (stats['games'] / 100)
            })
    
    return pd.DataFrame(results)

def identify_weaknesses(df):
    if df.empty:
        return pd.DataFrame()
    
    df['weakness_score'] = (100 - df['win_rate']) * (df['games'] / df['games'].max())
    weak_openings = df.nlargest(5, 'weakness_score')
    return weak_openings

def get_opening_category(opening_name):
    for category, data in OPENING_DATABASE.items():
        if category.lower() in opening_name.lower():
            return category
        for eco in data['eco']:
            if eco in opening_name:
                return category
    return None

def generate_youtube_search_url(keywords):
    search_query = keywords.replace(' ', '+')
    return f"https://www.youtube.com/results?search_query={search_query}"

def get_improvement_plan(weak_opening):
    opening_base = weak_opening.split(':')[0].strip()
    category = get_opening_category(opening_base)
    
    if category and category in OPENING_DATABASE:
        data = OPENING_DATABASE[category]
        return {
            'alternatives': data['alternatives'],
            'study_links': data['study_links'],
            'video_search': generate_youtube_search_url(data['video_keywords']),
            'key_moves': data['key_moves']
        }
    
    generic_search = f"{opening_base} chess opening tutorial beginners"
    return {
        'alternatives': ["Try different opening systems based on your style"],
        'study_links': ["https://lichess.org/study"],
        'video_search': generate_youtube_search_url(generic_search),
        'key_moves': "Study the main line variations"
    }

st.title("📚 Smart Opening Coach")

username = st.text_input("Lichess Username", value=get_username())

if username:
    set_username(username)

col1, col2 = st.columns(2)
with col1:
    game_type = st.selectbox("Game Type", ["blitz", "rapid", "classical", "bullet"], index=0)
with col2:
    max_games = st.slider("Games to Analyze", 100, 2000, 500)

if st.button("Analyze My Openings"):
    if username:
        with st.spinner("Analyzing your opening repertoire..."):
            token = get_token()
            games = fetch_user_games_cached(username, token, max_games, game_type)
            
            if not games:
                st.error("No games found")
                st.stop()
            
            df = analyze_opening_performance(games, username)
            
            if df.empty:
                st.warning("Not enough data for analysis (need at least 3 games per opening)")
                st.stop()
            
            weak_openings = identify_weaknesses(df)
        
        st.success(f"Analyzed {len(games)} games across {len(df)} different openings")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_win_rate = df['win_rate'].mean()
            st.metric("Average Win Rate", f"{avg_win_rate:.1f}%")
        with col2:
            total_openings = len(df)
            st.metric("Openings Played", total_openings)
        with col3:
            most_played = df.nlargest(1, 'games')['opening'].values[0] if not df.empty else "N/A"
            st.metric("Most Played", most_played[:20] + "...")
        
        st.subheader("🎯 Performance Overview")
        
        fig = px.scatter(df, x='games', y='win_rate', size='games', 
                         hover_data=['opening', 'wins', 'losses', 'draws'],
                         color='win_rate', color_continuous_scale='RdYlGn',
                         title="Opening Performance Map")
        fig.add_hline(y=50, line_dash="dash", line_color="gray", 
                      annotation_text="50% Win Rate")
        fig.update_layout(xaxis_title="Number of Games", 
                         yaxis_title="Win Rate (%)")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("⚠️ Openings Needing Improvement")
        
        if not weak_openings.empty:
            for idx, row in weak_openings.iterrows():
                with st.expander(f"🔴 {row['opening']} - Win Rate: {row['win_rate']:.1f}%"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Games", row['games'])
                    with col2:
                        st.metric("Wins", row['wins'])
                    with col3:
                        st.metric("Draws", row['draws'])
                    with col4:
                        st.metric("Losses", row['losses'])
                    
                    improvement = get_improvement_plan(row['opening'])
                    
                    st.markdown("### 📖 Study Resources")
                    for i, link in enumerate(improvement['study_links'], 1):
                        st.markdown(f"[Lichess Study {i}]({link})")
                    
                    st.markdown("### 🎥 Video Tutorials")
                    st.markdown(f"[Search YouTube Tutorials]({improvement['video_search']})")
                    
                    st.markdown("### 🔄 Alternative Openings to Consider")
                    for alt in improvement['alternatives']:
                        st.markdown(f"• {alt}")
                    
                    st.markdown(f"**Key Moves to Study:** {improvement['key_moves']}")
        
        st.subheader("💪 Your Strongest Openings")
        
        strong_openings = df.nlargest(5, 'win_rate')
        if not strong_openings.empty:
            fig2 = px.bar(strong_openings, x='opening', y='win_rate',
                          color='games', color_continuous_scale='Viridis',
                          title="Top 5 Openings by Win Rate",
                          hover_data=['games', 'wins'])
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)
        
        st.subheader("⚖️ Color Distribution")
        
        color_data = pd.DataFrame({
            'Color': ['White', 'Black'],
            'Games': [df['as_white'].sum(), df['as_black'].sum()]
        })
        
        fig3 = px.pie(color_data, values='Games', names='Color',
                      title="Games by Color",
                      color_discrete_map={'White': '#f0f0f0', 'Black': '#404040'})
        st.plotly_chart(fig3, use_container_width=True)
        
        with st.expander("📊 Detailed Opening Statistics"):
            display_df = df[['opening', 'games', 'win_rate', 'wins', 'draws', 'losses']].sort_values('games', ascending=False)
            display_df['win_rate'] = display_df['win_rate'].round(1)
            st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Please enter a Lichess username")