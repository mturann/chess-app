import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from collections import defaultdict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token

st.set_page_config(page_title="Time Management", page_icon="⏱️", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stat-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid #333;
    }
    .stat-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #aaa;
        margin-top: 5px;
    }
    .stat-icon {
        font-size: 1.5rem;
        margin-bottom: 5px;
    }
    
    .alert-card {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
        padding: 15px 20px;
        border-radius: 12px;
        color: white;
        margin: 10px 0;
    }
    .warning-card {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        padding: 15px 20px;
        border-radius: 12px;
        color: white;
        margin: 10px 0;
    }
    .success-card {
        background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%);
        padding: 15px 20px;
        border-radius: 12px;
        color: white;
        margin: 10px 0;
    }
    
    .phase-card {
        background: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #667eea;
    }
    .phase-opening { border-left-color: #4CAF50; }
    .phase-middlegame { border-left-color: #ff9800; }
    .phase-endgame { border-left-color: #f44336; }
    
    .phase-icon {
        font-size: 2rem;
        margin-bottom: 5px;
    }
    .phase-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #f0f0f0;
    }
    .phase-label {
        font-size: 0.8rem;
        color: #aaa;
    }
    
    .recommendation-card {
        background: #2d2d2d;
        padding: 15px;
        border-radius: 10px;
        margin: 8px 0;
        border-left: 4px solid #667eea;
    }
    .recommendation-title {
        color: #f0f0f0;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .recommendation-text {
        color: #aaa;
        font-size: 0.9rem;
    }
    
    .game-row {
        background: #1e1e1e;
        padding: 12px 15px;
        border-radius: 8px;
        margin: 5px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .game-row-trouble {
        border-left: 3px solid #f44336;
    }
    .game-row-ok {
        border-left: 3px solid #4CAF50;
    }
    
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 12px 20px;
        border-radius: 10px;
        margin: 20px 0 15px 0;
    }
    .section-title {
        color: white;
        font-size: 1.1rem;
        font-weight: bold;
        margin: 0;
    }
    
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .badge-danger { background: #f44336; color: white; }
    .badge-warning { background: #ff9800; color: white; }
    .badge-success { background: #4CAF50; color: white; }
</style>
""", unsafe_allow_html=True)

token = get_token()


@st.cache_data(ttl=1800)
def fetch_user_games(username, max_games=500, perf_type="blitz"):
    """Fetch user games with clock data"""
    url = f"https://lichess.org/api/games/user/{username}"
    headers = {"Accept": "application/x-ndjson"}
    params = {
        "max": max_games,
        "rated": "true",
        "perfType": perf_type,
        "clocks": "true",
        "opening": "true"
    }
    
    games = []
    try:
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=60)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                games.append(json.loads(line.decode('utf-8')))
        return games if games else None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def analyze_time_usage(games, username):
    """Comprehensive time analysis"""
    time_data = []
    all_move_times = []
    phase_times = {'opening': [], 'middlegame': [], 'endgame': []}
    
    for game in games:
        if 'clocks' not in game or not game['clocks']:
            continue
        
        players = game.get('players', {})
        is_white = players.get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
        color = 'white' if is_white else 'black'
        
        clocks = game.get('clocks', [])
        if len(clocks) < 4:
            continue
        
        # Extract player's clock times
        player_clocks = []
        for i, clock in enumerate(clocks):
            if (i % 2 == 0 and is_white) or (i % 2 == 1 and not is_white):
                player_clocks.append(clock / 100)  # Convert to seconds
        
        if len(player_clocks) < 2:
            continue
        
        # Calculate time per move
        time_per_move = []
        for i in range(1, len(player_clocks)):
            time_spent = player_clocks[i-1] - player_clocks[i]
            if time_spent >= 0:  # Ignore increment additions
                time_per_move.append(time_spent)
                all_move_times.append({
                    'move_number': i,
                    'time_spent': time_spent
                })
        
        if not time_per_move:
            continue
        
        total_moves = len(time_per_move)
        initial_time = player_clocks[0]
        final_time = player_clocks[-1] if player_clocks else 0
        
        # Phase breakdown
        opening_end = min(10, total_moves)
        middlegame_end = min(30, total_moves)
        
        opening_time = time_per_move[:opening_end]
        middlegame_time = time_per_move[opening_end:middlegame_end]
        endgame_time = time_per_move[middlegame_end:]
        
        if opening_time:
            phase_times['opening'].extend(opening_time)
        if middlegame_time:
            phase_times['middlegame'].extend(middlegame_time)
        if endgame_time:
            phase_times['endgame'].extend(endgame_time)
        
        # Game result
        winner = game.get('winner')
        if winner == color:
            result = 'win'
        elif winner is None:
            result = 'draw'
        else:
            result = 'loss'
        
        # Time trouble detection
        min_clock = min(player_clocks)
        time_trouble = min_clock < 30
        critical_time = min_clock < 10
        
        # Find longest think
        max_think = max(time_per_move) if time_per_move else 0
        max_think_move = time_per_move.index(max_think) + 1 if max_think > 0 else 0
        
        game_data = {
            'game_id': game.get('id'),
            'date': pd.to_datetime(game.get('createdAt', 0) / 1000, unit='s'),
            'speed': game.get('speed'),
            'color': color,
            'result': result,
            'total_moves': total_moves,
            'initial_time': initial_time,
            'final_time': final_time,
            'time_used': initial_time - final_time,
            'avg_time_per_move': np.mean(time_per_move),
            'median_time_per_move': np.median(time_per_move),
            'max_think': max_think,
            'max_think_move': max_think_move,
            'opening_avg': np.mean(opening_time) if opening_time else 0,
            'middlegame_avg': np.mean(middlegame_time) if middlegame_time else 0,
            'endgame_avg': np.mean(endgame_time) if endgame_time else 0,
            'time_trouble': time_trouble,
            'critical_time': critical_time,
            'min_clock': min_clock,
            'clock_history': player_clocks,
            'time_per_move': time_per_move
        }
        
        time_data.append(game_data)
    
    return pd.DataFrame(time_data), all_move_times, phase_times


def calculate_time_stats(df):
    """Calculate overall time statistics"""
    if df.empty:
        return None
    
    stats = {
        'total_games': len(df),
        'time_trouble_rate': df['time_trouble'].mean() * 100,
        'critical_time_rate': df['critical_time'].mean() * 100,
        'avg_time_per_move': df['avg_time_per_move'].mean(),
        'avg_final_clock': df['final_time'].mean(),
        'avg_max_think': df['max_think'].mean(),
        
        # By result
        'win_time_trouble': df[df['result'] == 'win']['time_trouble'].mean() * 100,
        'loss_time_trouble': df[df['result'] == 'loss']['time_trouble'].mean() * 100,
        
        # Win rates
        'wr_no_trouble': (df[~df['time_trouble']]['result'] == 'win').mean() * 100 if len(df[~df['time_trouble']]) > 0 else 0,
        'wr_with_trouble': (df[df['time_trouble']]['result'] == 'win').mean() * 100 if len(df[df['time_trouble']]) > 0 else 0,
        
        # Phase averages
        'opening_avg': df['opening_avg'].mean(),
        'middlegame_avg': df['middlegame_avg'].mean(),
        'endgame_avg': df['endgame_avg'].mean()
    }
    
    return stats


def generate_recommendations(stats, df):
    """Generate personalized recommendations"""
    recommendations = []
    
    # Time trouble recommendations
    if stats['time_trouble_rate'] > 30:
        recommendations.append({
            'type': 'critical',
            'icon': '🚨',
            'title': 'Critical: Time Trouble Issue',
            'text': f"You're getting into time trouble in {stats['time_trouble_rate']:.0f}% of games. This is severely impacting your play. Consider playing slower time controls or studying openings to play faster in the early game."
        })
    elif stats['time_trouble_rate'] > 15:
        recommendations.append({
            'type': 'warning',
            'icon': '⚠️',
            'title': 'Time Management Needs Work',
            'text': f"Time trouble in {stats['time_trouble_rate']:.0f}% of games. Try to make faster decisions in clear positions and save time for critical moments."
        })
    else:
        recommendations.append({
            'type': 'success',
            'icon': '✅',
            'title': 'Good Time Management',
            'text': f"Only {stats['time_trouble_rate']:.0f}% time trouble rate. Keep it up!"
        })
    
    # Phase-specific recommendations
    if stats['opening_avg'] > stats['middlegame_avg'] * 1.5:
        recommendations.append({
            'type': 'warning',
            'icon': '📚',
            'title': 'Slow in the Opening',
            'text': f"You spend {stats['opening_avg']:.1f}s per move in openings vs {stats['middlegame_avg']:.1f}s in middlegame. Study your openings to play faster early on."
        })
    
    if stats['endgame_avg'] > stats['middlegame_avg'] * 2:
        recommendations.append({
            'type': 'warning',
            'icon': '🏁',
            'title': 'Struggling in Endgames',
            'text': f"Endgame time ({stats['endgame_avg']:.1f}s/move) is much higher than middlegame ({stats['middlegame_avg']:.1f}s). Practice common endgame patterns."
        })
    
    # Win rate comparison
    if stats['wr_no_trouble'] - stats['wr_with_trouble'] > 15:
        recommendations.append({
            'type': 'info',
            'icon': '📊',
            'title': 'Time Pressure Hurts Results',
            'text': f"Win rate without time trouble: {stats['wr_no_trouble']:.0f}% vs with trouble: {stats['wr_with_trouble']:.0f}%. Managing time better could significantly improve your results."
        })
    
    # Long thinks
    if stats['avg_max_think'] > 60:
        recommendations.append({
            'type': 'warning',
            'icon': '🤔',
            'title': 'Very Long Thinks',
            'text': f"Average longest think is {stats['avg_max_think']:.0f}s. Try to set a mental time limit for decisions."
        })
    
    return recommendations


def create_clock_gauge(value, max_value, title, threshold_bad=30, threshold_warn=60):
    """Create a gauge chart for clock/time visualization"""
    if value <= threshold_bad:
        color = '#f44336'
    elif value <= threshold_warn:
        color = '#ff9800'
    else:
        color = '#4CAF50'
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': 's', 'font': {'color': '#f0f0f0', 'size': 30}},
        title={'text': title, 'font': {'color': '#aaa', 'size': 14}},
        gauge={
            'axis': {'range': [0, max_value], 'tickcolor': '#666'},
            'bar': {'color': color},
            'bgcolor': '#1e1e1e',
            'bordercolor': '#333',
            'steps': [
                {'range': [0, threshold_bad], 'color': 'rgba(244, 67, 54, 0.2)'},
                {'range': [threshold_bad, threshold_warn], 'color': 'rgba(255, 152, 0, 0.2)'},
                {'range': [threshold_warn, max_value], 'color': 'rgba(76, 175, 80, 0.2)'}
            ],
            'threshold': {
                'line': {'color': '#f44336', 'width': 2},
                'thickness': 0.75,
                'value': threshold_bad
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#f0f0f0'},
        height=200,
        margin=dict(l=30, r=30, t=50, b=20)
    )
    
    return fig


def create_time_curve(df):
    """Create average time per move curve"""
    # Aggregate time per move by move number
    move_times = defaultdict(list)
    
    for _, row in df.iterrows():
        for i, time_spent in enumerate(row['time_per_move']):
            move_times[i + 1].append(time_spent)
    
    # Calculate averages
    curve_data = []
    for move_num in sorted(move_times.keys()):
        if len(move_times[move_num]) >= 5:  # Minimum sample size
            curve_data.append({
                'move': move_num,
                'avg_time': np.mean(move_times[move_num]),
                'median_time': np.median(move_times[move_num]),
                'std_time': np.std(move_times[move_num]),
                'count': len(move_times[move_num])
            })
    
    if not curve_data:
        return None
    
    curve_df = pd.DataFrame(curve_data)
    
    fig = go.Figure()
    
    # Confidence band
    fig.add_trace(go.Scatter(
        x=list(curve_df['move']) + list(curve_df['move'])[::-1],
        y=list(curve_df['avg_time'] + curve_df['std_time']) + list(curve_df['avg_time'] - curve_df['std_time'])[::-1],
        fill='toself',
        fillcolor='rgba(102, 126, 234, 0.2)',
        line=dict(color='rgba(0,0,0,0)'),
        name='Std Dev',
        showlegend=True
    ))
    
    # Average line
    fig.add_trace(go.Scatter(
        x=curve_df['move'],
        y=curve_df['avg_time'],
        mode='lines',
        name='Average',
        line=dict(color='#667eea', width=3)
    ))
    
    # Median line
    fig.add_trace(go.Scatter(
        x=curve_df['move'],
        y=curve_df['median_time'],
        mode='lines',
        name='Median',
        line=dict(color='#4CAF50', width=2, dash='dash')
    ))
    
    # Phase annotations
    fig.add_vrect(x0=0, x1=10, fillcolor="rgba(76, 175, 80, 0.1)", layer="below", line_width=0)
    fig.add_vrect(x0=10, x1=30, fillcolor="rgba(255, 152, 0, 0.1)", layer="below", line_width=0)
    fig.add_vrect(x0=30, x1=max(curve_df['move']), fillcolor="rgba(244, 67, 54, 0.1)", layer="below", line_width=0)
    
    fig.add_annotation(x=5, y=curve_df['avg_time'].max(), text="Opening", showarrow=False, font=dict(color='#4CAF50'))
    fig.add_annotation(x=20, y=curve_df['avg_time'].max(), text="Middlegame", showarrow=False, font=dict(color='#ff9800'))
    if max(curve_df['move']) > 35:
        fig.add_annotation(x=35, y=curve_df['avg_time'].max(), text="Endgame", showarrow=False, font=dict(color='#f44336'))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f0f0f0'),
        xaxis=dict(title='Move Number', gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='Time (seconds)', gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        height=400,
        hovermode='x unified'
    )
    
    return fig


def create_result_comparison(df):
    """Compare time metrics between wins and losses"""
    wins = df[df['result'] == 'win']
    losses = df[df['result'] == 'loss']
    
    if len(wins) < 5 or len(losses) < 5:
        return None
    
    metrics = ['avg_time_per_move', 'opening_avg', 'middlegame_avg', 'endgame_avg', 'max_think', 'final_time']
    labels = ['Avg/Move', 'Opening', 'Middlegame', 'Endgame', 'Max Think', 'Final Clock']
    
    win_values = [wins[m].mean() for m in metrics]
    loss_values = [losses[m].mean() for m in metrics]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Wins',
        x=labels,
        y=win_values,
        marker_color='#4CAF50',
        text=[f'{v:.1f}s' for v in win_values],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Losses',
        x=labels,
        y=loss_values,
        marker_color='#f44336',
        text=[f'{v:.1f}s' for v in loss_values],
        textposition='outside'
    ))
    
    fig.update_layout(
        barmode='group',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f0f0f0'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='Time (seconds)', gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        height=350
    )
    
    return fig


def create_heatmap(df):
    """Create move number vs time spent heatmap"""
    # Bin move numbers and time
    all_data = []
    
    for _, row in df.iterrows():
        for i, time_spent in enumerate(row['time_per_move'][:50]):  # First 50 moves
            all_data.append({
                'move_bin': (i // 5) * 5,  # Bin by 5 moves
                'time_bin': min(int(time_spent // 5) * 5, 30),  # Bin by 5 seconds, cap at 30+
                'count': 1
            })
    
    if not all_data:
        return None
    
    heatmap_df = pd.DataFrame(all_data)
    pivot = heatmap_df.groupby(['move_bin', 'time_bin']).size().unstack(fill_value=0)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f'{int(c)}s' for c in pivot.columns],
        y=[f'Move {int(r)}-{int(r)+4}' for r in pivot.index],
        colorscale='Viridis',
        hovertemplate='%{y}<br>Time: %{x}<br>Count: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f0f0f0'),
        xaxis=dict(title='Time Spent'),
        yaxis=dict(title=''),
        height=350
    )
    
    return fig


def create_single_game_chart(game_row):
    """Create clock timeline for a single game"""
    clocks = game_row['clock_history']
    times = game_row['time_per_move']
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Clock Remaining', 'Time per Move'),
        vertical_spacing=0.15,
        row_heights=[0.5, 0.5]
    )
    
    # Clock remaining
    fig.add_trace(go.Scatter(
        x=list(range(len(clocks))),
        y=clocks,
        mode='lines+markers',
        name='Clock',
        line=dict(color='#667eea', width=2),
        marker=dict(size=4)
    ), row=1, col=1)
    
    # Add danger zone
    fig.add_hline(y=30, line_dash="dash", line_color="#f44336", row=1, col=1)
    fig.add_hline(y=60, line_dash="dash", line_color="#ff9800", row=1, col=1)
    
    # Time per move
    colors = ['#f44336' if t > 15 else '#ff9800' if t > 8 else '#4CAF50' for t in times]
    fig.add_trace(go.Bar(
        x=list(range(1, len(times) + 1)),
        y=times,
        name='Time/Move',
        marker_color=colors
    ), row=2, col=1)
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f0f0f0'),
        height=450,
        showlegend=False
    )
    
    fig.update_xaxes(title_text='Move', gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text='Seconds', gridcolor='rgba(255,255,255,0.1)')
    
    return fig


# ===== MAIN APP =====

st.markdown("""
<h1 style="text-align: center;">⏱️ Time Management Analysis</h1>
<p style="text-align: center; color: #888;">Understand how you use your clock and improve your time management</p>
""", unsafe_allow_html=True)

st.markdown("---")

# Input
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    username = st.text_input("Lichess Username", value=get_username(), label_visibility="collapsed", placeholder="Enter username...")

with col2:
    game_type = st.selectbox("Type", ["blitz", "rapid", "bullet", "classical"], index=0, label_visibility="collapsed")

with col3:
    max_games = st.selectbox("Games", [100, 200, 500, 1000], index=1, label_visibility="collapsed")

with col4:
    analyze_btn = st.button("⏱️ Analyze", type="primary", use_container_width=True)

if username:
    set_username(username)

if analyze_btn and username:
    with st.spinner("Analyzing time management..."):
        games = fetch_user_games(username, max_games, game_type)
        
        if not games:
            st.error("❌ No games found or user doesn't exist")
            st.stop()
        
        df, all_move_times, phase_times = analyze_time_usage(games, username)
        
        if df.empty:
            st.warning("No games with clock data found")
            st.stop()
        
        stats = calculate_time_stats(df)
        recommendations = generate_recommendations(stats, df)
        
        st.session_state.time_df = df
        st.session_state.time_stats = stats
        st.session_state.time_recommendations = recommendations
        st.session_state.time_phase = phase_times

# Display results
if 'time_df' in st.session_state and not st.session_state.time_df.empty:
    df = st.session_state.time_df
    stats = st.session_state.time_stats
    recommendations = st.session_state.time_recommendations
    phase_times = st.session_state.time_phase
    
    # Key Stats Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        trouble_color = '#f44336' if stats['time_trouble_rate'] > 25 else '#ff9800' if stats['time_trouble_rate'] > 15 else '#4CAF50'
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">⚠️</div>
            <div class="stat-value" style="color: {trouble_color};">{stats['time_trouble_rate']:.1f}%</div>
            <div class="stat-label">Time Trouble Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">⏱️</div>
            <div class="stat-value">{stats['avg_time_per_move']:.1f}s</div>
            <div class="stat-label">Avg per Move</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">🏁</div>
            <div class="stat-value">{stats['avg_final_clock']:.0f}s</div>
            <div class="stat-label">Avg Final Clock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">🤔</div>
            <div class="stat-value">{stats['avg_max_think']:.0f}s</div>
            <div class="stat-label">Avg Longest Think</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-value">{stats['total_games']}</div>
            <div class="stat-label">Games Analyzed</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Phase breakdown
    st.markdown('<div class="section-header"><p class="section-title">🎯 Time by Game Phase</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="phase-card phase-opening">
            <div class="phase-icon">♟️</div>
            <div class="phase-value">{stats['opening_avg']:.1f}s</div>
            <div class="phase-label">Opening (moves 1-10)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="phase-card phase-middlegame">
            <div class="phase-icon">⚔️</div>
            <div class="phase-value">{stats['middlegame_avg']:.1f}s</div>
            <div class="phase-label">Middlegame (moves 11-30)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="phase-card phase-endgame">
            <div class="phase-icon">🏁</div>
            <div class="phase-value">{stats['endgame_avg']:.1f}s</div>
            <div class="phase-label">Endgame (moves 30+)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Win Rate Impact
    st.markdown('<div class="section-header"><p class="section-title">📈 Impact on Results</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gauge charts
        gauge_col1, gauge_col2 = st.columns(2)
        
        with gauge_col1:
            fig_gauge1 = create_clock_gauge(stats['wr_no_trouble'], 100, 'Win Rate (Good Time)', 40, 55)
            st.plotly_chart(fig_gauge1, use_container_width=True, key="gauge_no_trouble")
        
        with gauge_col2:
            fig_gauge2 = create_clock_gauge(stats['wr_with_trouble'], 100, 'Win Rate (Time Trouble)', 40, 55)
            st.plotly_chart(fig_gauge2, use_container_width=True, key="gauge_with_trouble")
        
        diff = stats['wr_no_trouble'] - stats['wr_with_trouble']
        if diff > 0:
            st.markdown(f"""
            <div class="warning-card">
                <strong>💡 Insight:</strong> You win {diff:.0f}% more games when you manage your time well!
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        fig_comparison = create_result_comparison(df)
        if fig_comparison:
            st.plotly_chart(fig_comparison, use_container_width=True, key="result_comparison")
    
    # Recommendations
    st.markdown('<div class="section-header"><p class="section-title">💡 Recommendations</p></div>', unsafe_allow_html=True)
    
    for rec in recommendations:
        card_class = 'alert-card' if rec['type'] == 'critical' else 'warning-card' if rec['type'] == 'warning' else 'success-card' if rec['type'] == 'success' else 'recommendation-card'
        st.markdown(f"""
        <div class="{card_class}">
            <strong>{rec['icon']} {rec['title']}</strong><br>
            <span style="font-size: 0.9rem;">{rec['text']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Tabs for detailed analysis
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Time Curve", "🔥 Heatmap", "🎮 Single Game", "📋 All Games"])
    
    with tab1:
        st.markdown("### Average Time per Move by Move Number")
        fig_curve = create_time_curve(df)
        if fig_curve:
            st.plotly_chart(fig_curve, use_container_width=True, key="time_curve")
            st.caption("Shaded area shows standard deviation. Green = Opening, Orange = Middlegame, Red = Endgame")
        else:
            st.info("Not enough data for time curve")
    
    with tab2:
        st.markdown("### Time Usage Heatmap")
        fig_heatmap = create_heatmap(df)
        if fig_heatmap:
            st.plotly_chart(fig_heatmap, use_container_width=True, key="time_heatmap")
            st.caption("Brighter colors indicate more frequent time usage patterns")
        else:
            st.info("Not enough data for heatmap")
    
    with tab3:
        st.markdown("### Single Game Analysis")
        
        # Game selector
        game_options = []
        for i, row in df.head(20).iterrows():
            result_emoji = '✅' if row['result'] == 'win' else '❌' if row['result'] == 'loss' else '➖'
            trouble_emoji = '⚠️' if row['time_trouble'] else ''
            game_options.append(f"{result_emoji} {row['date'].strftime('%Y-%m-%d')} - {row['total_moves']} moves {trouble_emoji}")
        
        if game_options:
            selected_idx = st.selectbox("Select a game", range(len(game_options)), format_func=lambda x: game_options[x])
            
            selected_game = df.iloc[selected_idx]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Result", selected_game['result'].upper())
            with col2:
                st.metric("Final Clock", f"{selected_game['final_time']:.0f}s")
            with col3:
                st.metric("Max Think", f"{selected_game['max_think']:.0f}s (move {selected_game['max_think_move']})")
            with col4:
                st.metric("Time Trouble", "Yes ⚠️" if selected_game['time_trouble'] else "No ✅")
            
            fig_game = create_single_game_chart(selected_game)
            st.plotly_chart(fig_game, use_container_width=True, key="single_game_chart")
    
    with tab4:
        st.markdown("### Recent Games Overview")
        
        display_df = df[['date', 'result', 'total_moves', 'avg_time_per_move', 'max_think', 'final_time', 'time_trouble']].copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d %H:%M')
        display_df['avg_time_per_move'] = display_df['avg_time_per_move'].round(1)
        display_df['max_think'] = display_df['max_think'].round(0)
        display_df['final_time'] = display_df['final_time'].round(0)
        display_df['time_trouble'] = display_df['time_trouble'].map({True: '⚠️ Yes', False: '✅ No'})
        display_df['result'] = display_df['result'].map({'win': '✅ Win', 'loss': '❌ Loss', 'draw': '➖ Draw'})
        
        display_df.columns = ['Date', 'Result', 'Moves', 'Avg/Move (s)', 'Max Think (s)', 'Final Clock (s)', 'Time Trouble']
        
        st.dataframe(display_df.head(50), use_container_width=True, hide_index=True)
        
        # Export
        csv = display_df.to_csv(index=False)
        st.download_button(
            "📥 Export to CSV",
            csv,
            file_name=f"time_analysis_{username}.csv",
            mime="text/csv"
        )

else:
    # Welcome screen
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 5rem; margin-bottom: 20px;">⏱️</div>
        <h2 style="color: #f0f0f0;">Analyze Your Time Management</h2>
        <p style="color: #888; max-width: 500px; margin: 20px auto;">
            Enter your Lichess username to understand how you use your clock,
            identify time trouble patterns, and get personalized recommendations.
        </p>
        <div style="margin-top: 30px;">
            <span class="badge badge-success">♟️ Opening</span>
            <span class="badge badge-warning">⚔️ Middlegame</span>
            <span class="badge badge-danger">🏁 Endgame</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("⏱️ Time trouble = less than 30 seconds remaining | Data from Lichess API")