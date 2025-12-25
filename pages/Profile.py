import streamlit as st 
import berserk
from datetime import datetime, timezone
import datetime as dt
import pandas as pd 
import plotly.graph_objs as go
import plotly.express as px
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token
from utils.cache_manager import fetch_profile_cached

st.set_page_config(page_title="Profile", page_icon="👤", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .profile-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .profile-avatar {
        font-size: 5rem;
        margin-bottom: 10px;
    }
    .profile-name {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .profile-url {
        color: rgba(255,255,255,0.8);
        font-size: 0.9rem;
    }
    .status-online {
        display: inline-block;
        background: #4CAF50;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        margin-top: 10px;
    }
    .status-offline {
        display: inline-block;
        background: #ff9800;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        margin-top: 10px;
    }
    .stat-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        color: white;
        height: 100%;
    }
    .stat-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #aaa;
        margin-top: 5px;
    }
    .rating-card {
        background: #1e1e1e;
        padding: 15px;
        border-radius: 12px;
        margin: 8px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .rating-type {
        font-size: 1rem;
        color: #f0f0f0;
        text-transform: capitalize;
    }
    .rating-value {
        font-size: 1.3rem;
        font-weight: bold;
        color: #4CAF50;
    }
    .info-card {
        background: #2d2d2d;
        padding: 20px;
        border-radius: 15px;
        color: #f0f0f0;
        margin: 10px 0;
    }
    .info-item {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid #444;
    }
    .info-item:last-child {
        border-bottom: none;
    }
    .info-label {
        color: #aaa;
    }
    .info-value {
        color: #f0f0f0;
        font-weight: bold;
    }
    .game-type-icon {
        font-size: 1.5rem;
        margin-right: 10px;
    }
</style>
""", unsafe_allow_html=True)

token = get_token()

# Game type icons
GAME_ICONS = {
    'bullet': '🚀',
    'blitz': '⚡',
    'rapid': '🕐',
    'classical': '🏛️',
    'correspondence': '📧',
    'chess960': '🎲',
    'crazyhouse': '🏠',
    'antichess': '🔄',
    'atomic': '💥',
    'horde': '👥',
    'kingOfTheHill': '👑',
    'racingKings': '🏁',
    'threeCheck': '✓✓✓',
    'puzzle': '🧩',
    'ultraBullet': '💨',
    'storm': '⛈️'
}

def get_rating_color(rating):
    """Get color based on rating"""
    if rating >= 2200:
        return '#FFD700'  # Gold
    elif rating >= 2000:
        return '#E040FB'  # Purple
    elif rating >= 1800:
        return '#2196F3'  # Blue
    elif rating >= 1600:
        return '#4CAF50'  # Green
    elif rating >= 1400:
        return '#8BC34A'  # Light Green
    else:
        return '#9E9E9E'  # Gray

def format_time_spent(seconds):
    """Format seconds to readable time"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

# Title
st.markdown("""
<h1 style="text-align: center; margin-bottom: 30px;">👤 Player Profile</h1>
""", unsafe_allow_html=True)

# Username input
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    username = st.text_input(
        "Enter Lichess Username",
        value=get_username(),
        placeholder="e.g., DrNykterstein"
    )

if username:
    set_username(username)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    show_profile = st.button("🔍 Load Profile", use_container_width=True)

if show_profile and username:
    with st.spinner("Fetching profile..."):
        profile = fetch_profile_cached(username, token)
    
    if profile:
        # Calculate online status
        last_active = profile.get('seenAt')
        now = datetime.now(timezone.utc)
        
        if last_active:
            active_minutes = int((now - last_active).total_seconds() // 60)
            if active_minutes < 5:
                status_html = '<span class="status-online">🟢 Online</span>'
            elif active_minutes < 60:
                status_html = f'<span class="status-offline">🟠 {active_minutes} minutes ago</span>'
            elif active_minutes < 1440:
                hours = active_minutes // 60
                status_html = f'<span class="status-offline">🟠 {hours} hours ago</span>'
            else:
                days = active_minutes // 1440
                status_html = f'<span class="status-offline">🔴 {days} days ago</span>'
        else:
            status_html = '<span class="status-offline">🔴 Unknown</span>'
        
        # Profile Header
        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-avatar">👤</div>
            <p class="profile-name">{username}</p>
            <p class="profile-url">🔗 {profile.get("url", "")}</p>
            {status_html}
        </div>
        """, unsafe_allow_html=True)
        
        # Stats Row
        st.markdown("### 📊 Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_games = profile.get("count", {}).get("all", 0)
        wins = profile.get("count", {}).get("win", 0)
        losses = profile.get("count", {}).get("loss", 0)
        draws = profile.get("count", {}).get("draw", 0)
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{total_games:,}</div>
                <div class="stat-label">Total Games</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #4CAF50;">{wins:,}</div>
                <div class="stat-label">Wins</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #f44336;">{losses:,}</div>
                <div class="stat-label">Losses</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #ff9800;">{win_rate:.1f}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Ratings and Info
        col_left, col_right = st.columns([3, 2])
        
        with col_left:
            st.markdown("### 📈 Ratings")
            
            perfs = profile.get("perfs", {})
            
            if perfs:
                # Create rating data
                rating_data = []
                for game_type, data in perfs.items():
                    if isinstance(data, dict) and 'rating' in data:
                        rating_data.append({
                            'type': game_type,
                            'rating': data['rating'],
                            'games': data.get('games', 0),
                            'icon': GAME_ICONS.get(game_type, '♟️')
                        })
                
                # Sort by games played
                rating_data = sorted(rating_data, key=lambda x: x['games'], reverse=True)
                
                # Create bar chart
                df_ratings = pd.DataFrame(rating_data)
                
                if not df_ratings.empty:
                    fig = go.Figure()
                    
                    colors = [get_rating_color(r) for r in df_ratings['rating']]
                    
                    fig.add_trace(go.Bar(
                        x=df_ratings['type'],
                        y=df_ratings['rating'],
                        marker_color=colors,
                        text=df_ratings['rating'],
                        textposition='outside',
                        textfont=dict(color='white', size=12)
                    ))
                    
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f0f0f0'),
                        xaxis=dict(
                            title='',
                            tickangle=-45,
                            gridcolor='rgba(255,255,255,0.1)'
                        ),
                        yaxis=dict(
                            title='Rating',
                            gridcolor='rgba(255,255,255,0.1)',
                            range=[0, max(df_ratings['rating']) * 1.15]
                        ),
                        margin=dict(l=50, r=50, t=30, b=100),
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Rating cards for top 4
                    st.markdown("#### 🏆 Top Ratings")
                    top_ratings = sorted(rating_data, key=lambda x: x['rating'], reverse=True)[:4]
                    
                    cols = st.columns(2)
                    for i, r in enumerate(top_ratings):
                        with cols[i % 2]:
                            color = get_rating_color(r['rating'])
                            st.markdown(f"""
                            <div class="rating-card">
                                <div>
                                    <span class="game-type-icon">{r['icon']}</span>
                                    <span class="rating-type">{r['type']}</span>
                                </div>
                                <div class="rating-value" style="color: {color};">{r['rating']}</div>
                            </div>
                            """, unsafe_allow_html=True)
        
        with col_right:
            st.markdown("### ℹ️ Account Info")
            
            # Account creation date
            created_at = profile.get('createdAt')
            if created_at:
                created_str = created_at.strftime('%B %d, %Y')
                account_age = (now - created_at).days
                years = account_age // 365
                months = (account_age % 365) // 30
                age_str = f"{years}y {months}m" if years > 0 else f"{months} months"
            else:
                created_str = "Unknown"
                age_str = "Unknown"
            
            # Time spent
            play_time = profile.get('playTime', {})
            total_time = play_time.get('total', 0)
            tv_time = play_time.get('tv', 0)
            
            st.markdown(f"""
            <div class="info-card">
                <div class="info-item">
                    <span class="info-label">📅 Account Created</span>
                    <span class="info-value">{created_str}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">⏳ Account Age</span>
                    <span class="info-value">{age_str}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">🕐 Time Playing</span>
                    <span class="info-value">{format_time_spent(total_time)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">📺 Time on TV</span>
                    <span class="info-value">{format_time_spent(tv_time)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">🎮 Games Played</span>
                    <span class="info-value">{total_games:,}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">🤝 Draws</span>
                    <span class="info-value">{draws:,}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Win/Loss/Draw Pie Chart
            st.markdown("### 📊 Results")
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Wins', 'Losses', 'Draws'],
                values=[wins, losses, draws],
                hole=0.5,
                marker_colors=['#4CAF50', '#f44336', '#ff9800'],
                textinfo='percent',
                textfont=dict(color='white', size=14),
                hovertemplate='%{label}: %{value:,}<extra></extra>'
            )])
            
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f0f0f0'),
                showlegend=True,
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=-0.2,
                    xanchor='center',
                    x=0.5
                ),
                margin=dict(l=20, r=20, t=20, b=50),
                height=280,
                annotations=[dict(
                    text=f'{win_rate:.0f}%',
                    x=0.5, y=0.5,
                    font_size=24,
                    font_color='#4CAF50',
                    showarrow=False
                )]
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Full ratings table
        with st.expander("📋 All Ratings Details"):
            if rating_data:
                df_full = pd.DataFrame(rating_data)
                df_full = df_full[['icon', 'type', 'rating', 'games']]
                df_full.columns = ['', 'Game Type', 'Rating', 'Games Played']
                df_full = df_full.sort_values('Rating', ascending=False)
                st.dataframe(df_full, use_container_width=True, hide_index=True)
    
    else:
        st.error(f"❌ Could not find user '{username}'. Please check the username and try again.")

elif show_profile and not username:
    st.warning("⚠️ Please enter a Lichess username")

else:
    # Welcome state
    st.markdown("""
    <div style="text-align: center; padding: 50px; color: #888;">
        <div style="font-size: 4rem;">👤</div>
        <h3>Enter a Lichess username to view their profile</h3>
        <p>See ratings, statistics, and game history</p>
    </div>
    """, unsafe_allow_html=True)