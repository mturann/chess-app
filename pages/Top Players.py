import berserk 
import pandas as pd 
import plotly.graph_objs as go
import plotly.express as px
import streamlit as st 
import os

st.set_page_config(page_title="Top Players", page_icon="👑", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .podium-container {
        display: flex;
        justify-content: center;
        align-items: flex-end;
        gap: 10px;
        margin: 30px 0;
    }
    .podium-1 {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        padding: 20px;
        border-radius: 15px 15px 0 0;
        text-align: center;
        width: 200px;
        min-height: 200px;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);
    }
    .podium-2 {
        background: linear-gradient(135deg, #C0C0C0 0%, #A8A8A8 100%);
        padding: 20px;
        border-radius: 15px 15px 0 0;
        text-align: center;
        width: 180px;
        min-height: 160px;
        box-shadow: 0 4px 15px rgba(192, 192, 192, 0.4);
    }
    .podium-3 {
        background: linear-gradient(135deg, #CD7F32 0%, #8B4513 100%);
        padding: 20px;
        border-radius: 15px 15px 0 0;
        text-align: center;
        width: 160px;
        min-height: 130px;
        box-shadow: 0 4px 15px rgba(205, 127, 50, 0.4);
    }
    .podium-rank {
        font-size: 2.5rem;
        font-weight: bold;
        color: rgba(0,0,0,0.3);
    }
    .podium-name {
        font-size: 1.1rem;
        font-weight: bold;
        color: #1a1a2e;
        margin: 10px 0 5px 0;
        word-break: break-word;
    }
    .podium-rating {
        font-size: 1.4rem;
        font-weight: bold;
        color: #1a1a2e;
    }
    .player-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 15px 20px;
        border-radius: 12px;
        margin: 8px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: transform 0.2s;
    }
    .player-card:hover {
        transform: translateX(5px);
    }
    .player-rank {
        font-size: 1.5rem;
        font-weight: bold;
        color: #667eea;
        width: 40px;
    }
    .player-info {
        flex-grow: 1;
        margin-left: 15px;
    }
    .player-name {
        font-size: 1.1rem;
        font-weight: bold;
        color: #f0f0f0;
    }
    .player-rating {
        font-size: 1.3rem;
        font-weight: bold;
        color: #4CAF50;
    }
    .game-type-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px 25px;
        border-radius: 12px;
        color: white;
        margin: 20px 0;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .game-type-icon {
        font-size: 2rem;
    }
    .game-type-title {
        font-size: 1.5rem;
        font-weight: bold;
        text-transform: capitalize;
    }
    .stat-highlight {
        background: #2d2d2d;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        color: #f0f0f0;
    }
    .stat-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #aaa;
    }
</style>
""", unsafe_allow_html=True)

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
    'ultraBullet': '💨'
}

# Initialize Lichess client
token = os.environ.get('LICHESS_TOKEN', '')
session = berserk.TokenSession(token)
client = berserk.Client(session=session)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_top_players():
    """Fetch top 10 players for all game types"""
    try:
        return client.users.get_all_top_10()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def parse_top_players(top10):
    """Parse top 10 data into structured format"""
    if not top10:
        return {}
    
    parsed = {}
    for game_type, players in top10.items():
        parsed[game_type] = []
        for i, player in enumerate(players):
            rating = player.get('perfs', {}).get(game_type, {}).get('rating', 0)
            parsed[game_type].append({
                'rank': i + 1,
                'username': player.get('username', 'Unknown'),
                'rating': rating,
                'title': player.get('title', ''),
                'online': player.get('online', False)
            })
    return parsed

def create_podium(players):
    """Create HTML podium for top 3"""
    if len(players) < 3:
        return ""
    
    p1, p2, p3 = players[0], players[1], players[2]
    
    title1 = f"<small>{p1['title']}</small> " if p1['title'] else ""
    title2 = f"<small>{p2['title']}</small> " if p2['title'] else ""
    title3 = f"<small>{p3['title']}</small> " if p3['title'] else ""
    
    html = f"""
    <div class="podium-container">
        <div class="podium-2">
            <div class="podium-rank">2</div>
            <div class="podium-name">{title2}{p2['username']}</div>
            <div class="podium-rating">{p2['rating']}</div>
        </div>
        <div class="podium-1">
            <div class="podium-rank">👑</div>
            <div class="podium-name">{title1}{p1['username']}</div>
            <div class="podium-rating">{p1['rating']}</div>
        </div>
        <div class="podium-3">
            <div class="podium-rank">3</div>
            <div class="podium-name">{title3}{p3['username']}</div>
            <div class="podium-rating">{p3['rating']}</div>
        </div>
    </div>
    """
    return html

def create_player_cards(players):
    """Create HTML cards for players 4-10"""
    html = ""
    for player in players[3:]:
        title = f"<span style='color: #FFD700; margin-right: 5px;'>{player['title']}</span>" if player['title'] else ""
        online = "🟢" if player['online'] else ""
        
        html += f"""
        <div class="player-card">
            <div class="player-rank">#{player['rank']}</div>
            <div class="player-info">
                <div class="player-name">{title}{player['username']} {online}</div>
            </div>
            <div class="player-rating">{player['rating']}</div>
        </div>
        """
    return html

# Title
st.markdown("""
<h1 style="text-align: center;">👑 Top Players on Lichess</h1>
<p style="text-align: center; color: #888; margin-bottom: 30px;">The highest rated players across all game types</p>
""", unsafe_allow_html=True)

# Fetch data
with st.spinner("Loading top players..."):
    top10_raw = get_top_players()
    top10 = parse_top_players(top10_raw)

if top10:
    # Game type selector
    game_types = list(top10.keys())
    
    # Add icons to display names
    display_names = [f"{GAME_ICONS.get(gt, '♟️')} {gt.capitalize()}" for gt in game_types]
    
    selected_display = st.multiselect(
        "Select Game Types",
        options=display_names,
        default=display_names[:3],  # Default: first 3
        help="Choose which game types to display"
    )
    
    # Map back to original game type names
    selected_types = [game_types[display_names.index(d)] for d in selected_display]
    
    if not selected_types:
        st.warning("Please select at least one game type")
    else:
        # Stats overview
        st.markdown("### 📊 Quick Stats")
        
        cols = st.columns(len(selected_types))
        for i, game_type in enumerate(selected_types):
            players = top10.get(game_type, [])
            if players:
                top_rating = players[0]['rating']
                avg_rating = sum(p['rating'] for p in players) / len(players)
                
                with cols[i]:
                    st.markdown(f"""
                    <div class="stat-highlight">
                        <div style="font-size: 1.5rem;">{GAME_ICONS.get(game_type, '♟️')}</div>
                        <div class="stat-value">{top_rating}</div>
                        <div class="stat-label">{game_type.capitalize()} #1</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Display each selected game type
        for game_type in selected_types:
            players = top10.get(game_type, [])
            
            if not players:
                continue
            
            icon = GAME_ICONS.get(game_type, '♟️')
            
            # Game type header
            st.markdown(f"""
            <div class="game-type-header">
                <span class="game-type-icon">{icon}</span>
                <span class="game-type-title">{game_type}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Layout: Podium + Chart | Player list
            col1, col2 = st.columns([3, 2])
            
            with col1:
                # Podium
                podium_html = create_podium(players)
                st.markdown(podium_html, unsafe_allow_html=True)
                
                # Bar chart
                df = pd.DataFrame(players)
                
                fig = go.Figure()
                
                colors = ['#FFD700', '#C0C0C0', '#CD7F32'] + ['#667eea'] * 7
                
                fig.add_trace(go.Bar(
                    x=df['username'],
                    y=df['rating'],
                    marker_color=colors[:len(df)],
                    text=df['rating'],
                    textposition='outside',
                    textfont=dict(color='#f0f0f0', size=11),
                    hovertemplate='<b>%{x}</b><br>Rating: %{y}<extra></extra>'
                ))
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f0f0f0'),
                    xaxis=dict(
                        title='',
                        tickangle=-45,
                        gridcolor='rgba(255,255,255,0.05)'
                    ),
                    yaxis=dict(
                        title='Rating',
                        gridcolor='rgba(255,255,255,0.1)',
                        range=[min(df['rating']) * 0.95, max(df['rating']) * 1.05]
                    ),
                    margin=dict(l=50, r=20, t=20, b=100),
                    height=350,
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Player cards for 4-10
                st.markdown("#### 🏅 Rankings")
                
                for player in players:
                    title = f"**{player['title']}** " if player['title'] else ""
                    online = " 🟢" if player['online'] else ""
                    
                    # Different styling for top 3
                    if player['rank'] == 1:
                        medal = "🥇"
                        color = "#FFD700"
                    elif player['rank'] == 2:
                        medal = "🥈"
                        color = "#C0C0C0"
                    elif player['rank'] == 3:
                        medal = "🥉"
                        color = "#CD7F32"
                    else:
                        medal = f"#{player['rank']}"
                        color = "#667eea"
                    
                    st.markdown(f"""
                    <div class="player-card">
                        <div class="player-rank" style="color: {color};">{medal}</div>
                        <div class="player-info">
                            <div class="player-name">
                                <span style="color: #FFD700;">{player.get('title', '')}</span>
                                {player['username']}{online}
                            </div>
                        </div>
                        <div class="player-rating">{player['rating']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Link to Lichess leaderboard
                st.markdown(f"""
                <div style="text-align: center; margin-top: 15px;">
                    <a href="https://lichess.org/player/top/1/{game_type}" target="_blank" 
                       style="color: #667eea; text-decoration: none;">
                        View full leaderboard →
                    </a>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Comparison chart if multiple types selected
        if len(selected_types) > 1:
            st.markdown("### 📊 Rating Comparison Across Game Types")
            
            comparison_data = []
            for game_type in selected_types:
                players = top10.get(game_type, [])
                if players:
                    comparison_data.append({
                        'Game Type': f"{GAME_ICONS.get(game_type, '♟️')} {game_type.capitalize()}",
                        'Top Rating': players[0]['rating'],
                        'Average Top 10': sum(p['rating'] for p in players) / len(players),
                        '#10 Rating': players[-1]['rating'] if len(players) >= 10 else players[-1]['rating']
                    })
            
            df_comp = pd.DataFrame(comparison_data)
            
            fig_comp = go.Figure()
            
            fig_comp.add_trace(go.Bar(
                name='#1 Rating',
                x=df_comp['Game Type'],
                y=df_comp['Top Rating'],
                marker_color='#FFD700',
                text=df_comp['Top Rating'].round(0).astype(int),
                textposition='outside'
            ))
            
            fig_comp.add_trace(go.Bar(
                name='Avg Top 10',
                x=df_comp['Game Type'],
                y=df_comp['Average Top 10'],
                marker_color='#667eea',
                text=df_comp['Average Top 10'].round(0).astype(int),
                textposition='outside'
            ))
            
            fig_comp.update_layout(
                barmode='group',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f0f0f0'),
                xaxis=dict(title='', gridcolor='rgba(255,255,255,0.05)'),
                yaxis=dict(title='Rating', gridcolor='rgba(255,255,255,0.1)'),
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='center',
                    x=0.5
                ),
                margin=dict(l=50, r=50, t=50, b=50),
                height=400
            )
            
            st.plotly_chart(fig_comp, use_container_width=True)

else:
    st.error("Could not load top players data. Please try again later.")

# Footer
st.markdown("---")
st.caption("Data refreshes every 5 minutes • Powered by Lichess API")