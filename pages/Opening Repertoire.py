import streamlit as st
import berserk
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token
from utils.cache_manager import fetch_user_games_cached

st.set_page_config(page_title="Opening Repertoire", page_icon="♟️", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .summary-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid #333;
    }
    .summary-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
    }
    .summary-label {
        font-size: 0.9rem;
        color: #aaa;
        margin-top: 5px;
    }
    .opening-row {
        background: #1e1e1e;
        padding: 15px 20px;
        border-radius: 10px;
        margin: 8px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 4px solid #667eea;
    }
    .opening-row-good {
        border-left-color: #4CAF50;
    }
    .opening-row-bad {
        border-left-color: #f44336;
    }
    .opening-name {
        font-size: 1rem;
        color: #f0f0f0;
        font-weight: 500;
    }
    .opening-stats {
        display: flex;
        gap: 20px;
        align-items: center;
    }
    .opening-games {
        color: #888;
        font-size: 0.9rem;
    }
    .opening-winrate {
        font-size: 1.1rem;
        font-weight: bold;
        padding: 5px 12px;
        border-radius: 20px;
    }
    .winrate-good {
        background: rgba(76, 175, 80, 0.2);
        color: #4CAF50;
    }
    .winrate-bad {
        background: rgba(244, 67, 54, 0.2);
        color: #f44336;
    }
    .winrate-neutral {
        background: rgba(255, 152, 0, 0.2);
        color: #ff9800;
    }
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 12px 20px;
        border-radius: 10px;
        margin: 25px 0 15px 0;
    }
    .section-title {
        color: white;
        font-size: 1.1rem;
        font-weight: bold;
        margin: 0;
    }
    .color-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .color-white {
        background: #f0f0f0;
        border: 1px solid #ccc;
    }
    .color-black {
        background: #333;
        border: 1px solid #555;
    }
</style>
""", unsafe_allow_html=True)

token = get_token()

def process_games(games, username):
    """Process games and extract opening data"""
    games_data = []
    
    for game in games:
        players = game.get('players', {})
        is_white = players.get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
        color = 'white' if is_white else 'black'
        opponent_color = 'black' if is_white else 'white'
        
        winner = game.get('winner')
        if winner == color:
            outcome = 1
        elif winner is None:
            outcome = 0.5
        else:
            outcome = 0
        
        opening = game.get('opening', {})
        opening_name = opening.get('name', 'Unknown')
        
        if opening_name == 'Unknown':
            continue
        
        # Get base opening name
        base_opening = opening_name.split(':')[0].split(',')[0].strip()
        
        games_data.append({
            'opening_name': base_opening,
            'full_name': opening_name,
            'eco': opening.get('eco', ''),
            'color': color,
            'outcome': outcome,
        })
    
    return pd.DataFrame(games_data)

def analyze_openings(df):
    """Analyze opening statistics"""
    # Most played openings with color
    most_played = df.groupby(['opening_name', 'color']).agg(
        games=('opening_name', 'size'),
        win_rate=('outcome', 'mean')
    ).reset_index()
    most_played['win_rate'] *= 100
    most_played = most_played.sort_values('games', ascending=False)
    
    # Struggling openings (min 5 games, low win rate)
    struggling = most_played[most_played['games'] >= 5].sort_values('win_rate').head(10)
    
    # Best openings
    best = most_played[most_played['games'] >= 5].sort_values('win_rate', ascending=False).head(10)
    
    # As White
    white_openings = df[df['color'] == 'white'].groupby('opening_name').agg(
        games=('opening_name', 'size'),
        win_rate=('outcome', 'mean')
    ).reset_index()
    white_openings['win_rate'] *= 100
    white_openings = white_openings.sort_values('games', ascending=False)
    
    # As Black (against opponent openings)
    black_openings = df[df['color'] == 'black'].groupby('opening_name').agg(
        games=('opening_name', 'size'),
        win_rate=('outcome', 'mean')
    ).reset_index()
    black_openings['win_rate'] *= 100
    black_openings = black_openings.sort_values('games', ascending=False)
    
    return most_played, struggling, best, white_openings, black_openings

def get_winrate_class(wr):
    """Get CSS class based on win rate"""
    if wr >= 55:
        return 'winrate-good'
    elif wr < 45:
        return 'winrate-bad'
    return 'winrate-neutral'

def get_row_class(wr):
    """Get row CSS class based on win rate"""
    if wr >= 55:
        return 'opening-row-good'
    elif wr < 45:
        return 'opening-row-bad'
    return ''

# Title
st.markdown("""
<h1 style="text-align: center;">♟️ Opening Repertoire</h1>
<p style="text-align: center; color: #888;">A quick overview of your opening choices and performance</p>
""", unsafe_allow_html=True)

st.markdown("---")

# Input
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    username = st.text_input("Lichess Username", value=get_username(), label_visibility="collapsed", placeholder="Enter Lichess username...")

with col2:
    max_games = st.selectbox("Games", [500, 1000, 2000], index=0, label_visibility="collapsed")

with col3:
    analyze_btn = st.button("📊 Analyze", type="primary", use_container_width=True)

if username:
    set_username(username)

if analyze_btn and username:
    with st.spinner("Fetching games..."):
        games = fetch_user_games_cached(username, token, max_games, 'all')
        
        if not games:
            st.error("❌ No games found or user doesn't exist")
            st.stop()
        
        df = process_games(games, username)
        
        if df.empty:
            st.warning("No opening data available")
            st.stop()
        
        most_played, struggling, best, white_openings, black_openings = analyze_openings(df)
    
    # Store in session
    st.session_state.rep_df = df
    st.session_state.rep_most_played = most_played
    st.session_state.rep_struggling = struggling
    st.session_state.rep_best = best
    st.session_state.rep_white = white_openings
    st.session_state.rep_black = black_openings

# Display results
if 'rep_df' in st.session_state:
    df = st.session_state.rep_df
    most_played = st.session_state.rep_most_played
    struggling = st.session_state.rep_struggling
    best = st.session_state.rep_best
    white_openings = st.session_state.rep_white
    black_openings = st.session_state.rep_black
    
    # Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    
    total_openings = len(most_played['opening_name'].unique())
    total_games = len(df)
    avg_wr = df['outcome'].mean() * 100
    most_played_name = most_played.iloc[0]['opening_name'] if len(most_played) > 0 else "N/A"
    
    with col1:
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-value">{total_games}</div>
            <div class="summary-label">Games Analyzed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-value">{total_openings}</div>
            <div class="summary-label">Different Openings</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        color = '#4CAF50' if avg_wr >= 50 else '#f44336'
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-value" style="color: {color};">{avg_wr:.1f}%</div>
            <div class="summary-label">Overall Win Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-value" style="font-size: 1.3rem;">{most_played_name[:12]}...</div>
            <div class="summary-label">Most Played</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Tabs for White/Black
    tab1, tab2, tab3 = st.tabs(["⚪ As White", "⚫ As Black", "📊 Overview"])
    
    with tab1:
        st.markdown('<div class="section-header"><p class="section-title">⚪ Your White Repertoire</p></div>', unsafe_allow_html=True)
        
        if len(white_openings) > 0:
            # Top 10 chart
            top_white = white_openings.head(10)
            
            fig_white = go.Figure()
            
            colors = ['#4CAF50' if wr >= 55 else '#f44336' if wr < 45 else '#ff9800' 
                     for wr in top_white['win_rate']]
            
            fig_white.add_trace(go.Bar(
                y=top_white['opening_name'],
                x=top_white['games'],
                orientation='h',
                marker_color=colors,
                text=[f"{wr:.0f}%" for wr in top_white['win_rate']],
                textposition='auto',
                textfont=dict(color='white'),
                hovertemplate='<b>%{y}</b><br>Games: %{x}<br>Win Rate: %{text}<extra></extra>'
            ))
            
            fig_white.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f0f0f0'),
                xaxis=dict(title='Games Played', gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title='', autorange='reversed'),
                height=400,
                margin=dict(l=200)
            )
            
            st.plotly_chart(fig_white, use_container_width=True, key="white_repertoire_chart")
            
            # List view
            st.markdown("**All White Openings:**")
            for _, row in white_openings.head(15).iterrows():
                wr_class = get_winrate_class(row['win_rate'])
                row_class = get_row_class(row['win_rate'])
                st.markdown(f"""
                <div class="opening-row {row_class}">
                    <div class="opening-name">
                        <span class="color-indicator color-white"></span>
                        {row['opening_name']}
                    </div>
                    <div class="opening-stats">
                        <span class="opening-games">{row['games']} games</span>
                        <span class="opening-winrate {wr_class}">{row['win_rate']:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No White games found")
    
    with tab2:
        st.markdown('<div class="section-header"><p class="section-title">⚫ Your Black Repertoire</p></div>', unsafe_allow_html=True)
        
        if len(black_openings) > 0:
            # Top 10 chart
            top_black = black_openings.head(10)
            
            fig_black = go.Figure()
            
            colors = ['#4CAF50' if wr >= 55 else '#f44336' if wr < 45 else '#ff9800' 
                     for wr in top_black['win_rate']]
            
            fig_black.add_trace(go.Bar(
                y=top_black['opening_name'],
                x=top_black['games'],
                orientation='h',
                marker_color=colors,
                text=[f"{wr:.0f}%" for wr in top_black['win_rate']],
                textposition='auto',
                textfont=dict(color='white'),
                hovertemplate='<b>%{y}</b><br>Games: %{x}<br>Win Rate: %{text}<extra></extra>'
            ))
            
            fig_black.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f0f0f0'),
                xaxis=dict(title='Games Played', gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title='', autorange='reversed'),
                height=400,
                margin=dict(l=200)
            )
            
            st.plotly_chart(fig_black, use_container_width=True, key="black_repertoire_chart")
            
            # List view
            st.markdown("**All Black Openings:**")
            for _, row in black_openings.head(15).iterrows():
                wr_class = get_winrate_class(row['win_rate'])
                row_class = get_row_class(row['win_rate'])
                st.markdown(f"""
                <div class="opening-row {row_class}">
                    <div class="opening-name">
                        <span class="color-indicator color-black"></span>
                        {row['opening_name']}
                    </div>
                    <div class="opening-stats">
                        <span class="opening-games">{row['games']} games</span>
                        <span class="opening-winrate {wr_class}">{row['win_rate']:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No Black games found")
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="section-header"><p class="section-title">✅ Best Openings</p></div>', unsafe_allow_html=True)
            
            for _, row in best.head(5).iterrows():
                color_class = 'color-white' if row['color'] == 'white' else 'color-black'
                st.markdown(f"""
                <div class="opening-row opening-row-good">
                    <div class="opening-name">
                        <span class="color-indicator {color_class}"></span>
                        {row['opening_name']}
                    </div>
                    <div class="opening-stats">
                        <span class="opening-games">{row['games']} games</span>
                        <span class="opening-winrate winrate-good">{row['win_rate']:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="section-header"><p class="section-title">⚠️ Needs Work</p></div>', unsafe_allow_html=True)
            
            for _, row in struggling.head(5).iterrows():
                color_class = 'color-white' if row['color'] == 'white' else 'color-black'
                st.markdown(f"""
                <div class="opening-row opening-row-bad">
                    <div class="opening-name">
                        <span class="color-indicator {color_class}"></span>
                        {row['opening_name']}
                    </div>
                    <div class="opening-stats">
                        <span class="opening-games">{row['games']} games</span>
                        <span class="opening-winrate winrate-bad">{row['win_rate']:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Win Rate Distribution
        st.markdown('<div class="section-header"><p class="section-title">📈 Win Rate Distribution</p></div>', unsafe_allow_html=True)
        
        # Combine for distribution chart
        all_openings = most_played[most_played['games'] >= 3].copy()
        
        fig_dist = px.histogram(
            all_openings,
            x='win_rate',
            nbins=20,
            color='color',
            color_discrete_map={'white': '#f0f0f0', 'black': '#333'},
            barmode='overlay',
            opacity=0.7
        )
        
        fig_dist.add_vline(x=50, line_dash="dash", line_color="#667eea", 
                          annotation_text="50%", annotation_position="top")
        
        fig_dist.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f0f0f0'),
            xaxis=dict(title='Win Rate (%)', gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(title='Number of Openings', gridcolor='rgba(255,255,255,0.1)'),
            legend=dict(title='Color'),
            height=300
        )
        
        st.plotly_chart(fig_dist, use_container_width=True, key="winrate_distribution_chart")
        
        # Color comparison
        st.markdown('<div class="section-header"><p class="section-title">⚖️ Color Comparison</p></div>', unsafe_allow_html=True)
        
        white_games = len(df[df['color'] == 'white'])
        black_games = len(df[df['color'] == 'black'])
        white_wr = df[df['color'] == 'white']['outcome'].mean() * 100
        black_wr = df[df['color'] == 'black']['outcome'].mean() * 100
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="summary-card" style="border-left: 4px solid #f0f0f0;">
                <div style="font-size: 1.5rem; margin-bottom: 10px;">⚪ White</div>
                <div class="summary-value">{white_wr:.1f}%</div>
                <div class="summary-label">{white_games} games</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="summary-card" style="border-left: 4px solid #333;">
                <div style="font-size: 1.5rem; margin-bottom: 10px;">⚫ Black</div>
                <div class="summary-value">{black_wr:.1f}%</div>
                <div class="summary-label">{black_games} games</div>
            </div>
            """, unsafe_allow_html=True)

else:
    # Welcome screen
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 5rem; margin-bottom: 20px;">♟️</div>
        <h2 style="color: #f0f0f0;">Analyze Your Opening Repertoire</h2>
        <p style="color: #888; max-width: 500px; margin: 20px auto;">
            Enter your Lichess username above to see a quick overview of your opening choices, 
            win rates, and which openings need improvement.
        </p>
        <div style="margin-top: 30px;">
            <span style="background: #2d2d2d; padding: 8px 16px; border-radius: 20px; margin: 5px; color: #aaa;">⚪ White Analysis</span>
            <span style="background: #2d2d2d; padding: 8px 16px; border-radius: 20px; margin: 5px; color: #aaa;">⚫ Black Analysis</span>
            <span style="background: #2d2d2d; padding: 8px 16px; border-radius: 20px; margin: 5px; color: #aaa;">📊 Win Rates</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("💡 For detailed analysis and recommendations, visit the Opening Coach page")