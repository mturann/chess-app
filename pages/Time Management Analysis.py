import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from datetime import datetime
import chess.pgn
from io import StringIO
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token
from utils.cache_manager import fetch_user_games_cached

st.set_page_config(page_title="Time Management Analysis", page_icon="⏱️")

def parse_clock_data(game):
    """Extract clock times from game moves"""
    clocks = game.get('clocks', [])
    if not clocks:
        return None
    
    # Convert centiseconds to seconds
    clock_times = [c/100 for c in clocks]
    return clock_times

def analyze_time_usage(games, username):
    """Analyze time usage patterns"""
    time_data = []
    
    for game in games:
        if 'clocks' not in game or not game['clocks']:
            continue
            
        players = game.get('players', {})
        is_white = players.get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
        color = 'white' if is_white else 'black'
        
        clocks = game.get('clocks', [])
        if not clocks:
            continue
            
        # Get player's clock times (white on odd moves, black on even)
        player_clocks = []
        for i, clock in enumerate(clocks):
            if (i % 2 == 0 and is_white) or (i % 2 == 1 and not is_white):
                player_clocks.append(clock/100)  # Convert to seconds
        
        if len(player_clocks) < 2:
            continue
            
        # Calculate time spent per move
        time_per_move = []
        for i in range(1, len(player_clocks)):
            time_spent = player_clocks[i-1] - player_clocks[i]
            if time_spent > 0:  # Ignore time increments
                time_per_move.append(time_spent)
        
        if not time_per_move:
            continue
            
        # Analyze game phases
        total_moves = len(time_per_move)
        opening_moves = min(10, total_moves)
        middlegame_end = min(30, total_moves)
        
        game_data = {
            'game_id': game.get('id'),
            'date': pd.to_datetime(game.get('createdAt', 0) / 1000, unit='s'),
            'speed': game.get('speed'),
            'color': color,
            'total_moves': total_moves,
            'avg_time_per_move': np.mean(time_per_move) if time_per_move else 0,
            'opening_avg_time': np.mean(time_per_move[:opening_moves]) if opening_moves > 0 else 0,
            'middlegame_avg_time': np.mean(time_per_move[opening_moves:middlegame_end]) if middlegame_end > opening_moves else 0,
            'endgame_avg_time': np.mean(time_per_move[middlegame_end:]) if total_moves > middlegame_end else 0,
            'max_think_time': max(time_per_move) if time_per_move else 0,
            'time_trouble': 1 if (len(player_clocks) > 0 and min(player_clocks) < 30) else 0,
            'final_clock': player_clocks[-1] if player_clocks else 0,
            'winner': game.get('winner'),
            'won': 1 if game.get('winner') == color else 0
        }
        
        time_data.append(game_data)
    
    return pd.DataFrame(time_data)

def identify_time_patterns(df):
    """Identify time trouble patterns"""
    if df.empty:
        return {}
    
    patterns = {
        'time_trouble_rate': df['time_trouble'].mean() * 100,
        'avg_time_in_trouble': df[df['time_trouble'] == 1]['final_clock'].mean() if any(df['time_trouble'] == 1) else 0,
        'win_rate_time_trouble': df[df['time_trouble'] == 1]['won'].mean() * 100 if any(df['time_trouble'] == 1) else 0,
        'win_rate_no_trouble': df[df['time_trouble'] == 0]['won'].mean() * 100 if any(df['time_trouble'] == 0) else 0,
    }
    
    return patterns

st.title("⏱️ Time Management Analysis")

username = st.text_input(
    "Lichess Username",
    value=get_username(),
    help="Analyze time management patterns in your games"
)

if username:
    set_username(username)

game_type = st.selectbox(
    "Game Type",
    ["blitz", "rapid", "classical", "bullet"],
    index=0
)

max_games = st.slider("Number of games to analyze", 100, 2000, 500)

if st.button("Analyze Time Management"):
    if username:
        with st.spinner("Fetching and analyzing games..."):
            token = get_token()
            games = fetch_user_games_cached(username, token, max_games, game_type)
            
            if not games:
                st.error("No games found. Please check username and game type.")
                st.stop()
            
            df_time = analyze_time_usage(games, username)
            
            if df_time.empty:
                st.error("No games with clock data found.")
                st.stop()
            
            patterns = identify_time_patterns(df_time)
        
        # Display metrics
        st.subheader("Key Time Management Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Time Trouble Rate",
                f"{patterns['time_trouble_rate']:.1f}%",
                help="Percentage of games ending with less than 30 seconds"
            )
        with col2:
            st.metric(
                "Avg Final Clock",
                f"{patterns['avg_time_in_trouble']:.0f}s",
                help="Average remaining time in time trouble games"
            )
        with col3:
            st.metric(
                "Win Rate (Time Trouble)",
                f"{patterns['win_rate_time_trouble']:.1f}%"
            )
        with col4:
            st.metric(
                "Win Rate (Good Time)",
                f"{patterns['win_rate_no_trouble']:.1f}%"
            )
        
        # Time usage by game phase
        st.subheader("Average Time per Move by Game Phase")
        
        phase_data = pd.DataFrame({
            'Phase': ['Opening (1-10)', 'Middlegame (11-30)', 'Endgame (30+)'],
            'Average Time (seconds)': [
                df_time['opening_avg_time'].mean(),
                df_time['middlegame_avg_time'].mean(),
                df_time['endgame_avg_time'].mean()
            ]
        })
        
        fig_phases = px.bar(
            phase_data,
            x='Phase',
            y='Average Time (seconds)',
            title="Time Distribution Across Game Phases",
            color='Average Time (seconds)',
            color_continuous_scale='RdYlGn_r'
        )
        st.plotly_chart(fig_phases, use_container_width=True)
        
        # Time trouble frequency over time
        st.subheader("Time Trouble Trends")
        
        df_time['date'] = pd.to_datetime(df_time['date'])
        df_time = df_time.sort_values('date')
        df_time['rolling_trouble_rate'] = df_time['time_trouble'].rolling(window=20, min_periods=5).mean() * 100
        
        fig_trend = px.line(
            df_time,
            x='date',
            y='rolling_trouble_rate',
            title="Time Trouble Rate Over Time (20-game rolling average)",
            labels={'rolling_trouble_rate': 'Time Trouble Rate (%)'},
            line_shape='spline'
        )
        fig_trend.update_traces(line=dict(color='red', width=2))
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Distribution of thinking times
        st.subheader("Maximum Thinking Time Distribution")
        
        fig_dist = px.histogram(
            df_time,
            x='max_think_time',
            nbins=30,
            title="Distribution of Longest Think per Game",
            labels={'max_think_time': 'Maximum Thinking Time (seconds)'},
            color_discrete_sequence=['blue']
        )
        fig_dist.update_layout(
            xaxis_title="Seconds",
            yaxis_title="Number of Games",
            showlegend=False
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        
        # Win rate correlation with time management
        st.subheader("Performance vs Time Management")
        
        df_time['time_category'] = pd.cut(
            df_time['final_clock'],
            bins=[0, 10, 30, 60, 300, float('inf')],
            labels=['Critical (<10s)', 'Low (10-30s)', 'Medium (30-60s)', 'Good (60-300s)', 'Excellent (>300s)']
        )
        
        win_by_time = df_time.groupby('time_category').agg({
            'won': 'mean',
            'game_id': 'count'
        }).reset_index()
        win_by_time.columns = ['Time Category', 'Win Rate', 'Games']
        win_by_time['Win Rate'] *= 100
        
        fig_winrate = px.bar(
            win_by_time,
            x='Time Category',
            y='Win Rate',
            text='Games',
            title="Win Rate by Final Clock Time",
            color='Win Rate',
            color_continuous_scale='RdYlGn'
        )
        fig_winrate.update_traces(texttemplate='%{text} games', textposition='outside')
        fig_winrate.update_layout(
            yaxis_title="Win Rate (%)",
            showlegend=False
        )
        st.plotly_chart(fig_winrate, use_container_width=True)
        
        # Recent games time usage table
        st.subheader("Recent Games Time Analysis")
        
        recent_games = df_time.nlargest(10, 'date')[['date', 'speed', 'avg_time_per_move', 'max_think_time', 'final_clock', 'time_trouble', 'won']]
        recent_games['date'] = recent_games['date'].dt.strftime('%Y-%m-%d %H:%M')
        recent_games['time_trouble'] = recent_games['time_trouble'].map({1: '⚠️ Yes', 0: '✅ No'})
        recent_games['won'] = recent_games['won'].map({1: '✅ Won', 0: '❌ Lost'})
        recent_games.columns = ['Date', 'Speed', 'Avg Time/Move (s)', 'Max Think (s)', 'Final Clock (s)', 'Time Trouble', 'Result']
        
        st.dataframe(recent_games, use_container_width=True)
        
    else:
        st.warning("Please enter a Lichess username")