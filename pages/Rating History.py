import streamlit as st
import requests
import datetime as dt
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import calendar
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token

st.set_page_config(page_title="Rating History", page_icon="📈", layout="wide")

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
    .stat-delta {
        font-size: 1rem;
        margin-top: 5px;
    }
    .delta-positive { color: #4CAF50; }
    .delta-negative { color: #f44336; }
    
    .game-type-badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
        margin: 3px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .badge-bullet { background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%); color: white; }
    .badge-blitz { background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; }
    .badge-rapid { background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%); color: white; }
    .badge-classical { background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); color: white; }
    .badge-default { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    
    .milestone-card {
        background: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
        border-left: 4px solid #667eea;
    }
    .milestone-reached {
        border-left-color: #4CAF50;
    }
    .milestone-pending {
        border-left-color: #ff9800;
    }
    
    .sparkline-container {
        background: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
    
    .progress-container {
        background: #333;
        border-radius: 10px;
        height: 20px;
        overflow: hidden;
        margin: 10px 0;
    }
    .progress-fill {
        height: 100%;
        border-radius: 10px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        transition: width 0.5s ease;
    }
    
    .section-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 12px 20px;
        border-radius: 10px;
        margin: 20px 0 15px 0;
        border-left: 4px solid #667eea;
    }
    .section-title {
        color: #f0f0f0;
        font-size: 1.1rem;
        font-weight: bold;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# Game type colors and icons
GAME_TYPE_CONFIG = {
    'bullet': {'color': '#f44336', 'icon': '🚀', 'badge': 'badge-bullet'},
    'blitz': {'color': '#ff9800', 'icon': '⚡', 'badge': 'badge-blitz'},
    'rapid': {'color': '#4CAF50', 'icon': '🕐', 'badge': 'badge-rapid'},
    'classical': {'color': '#2196F3', 'icon': '🏛️', 'badge': 'badge-classical'},
    'correspondence': {'color': '#9c27b0', 'icon': '📧', 'badge': 'badge-default'},
    'chess960': {'color': '#00bcd4', 'icon': '🎲', 'badge': 'badge-default'},
    'kingOfTheHill': {'color': '#ffeb3b', 'icon': '👑', 'badge': 'badge-default'},
    'threeCheck': {'color': '#e91e63', 'icon': '✓', 'badge': 'badge-default'},
    'antichess': {'color': '#795548', 'icon': '🔄', 'badge': 'badge-default'},
    'atomic': {'color': '#ff5722', 'icon': '💥', 'badge': 'badge-default'},
    'horde': {'color': '#607d8b', 'icon': '👥', 'badge': 'badge-default'},
    'racingKings': {'color': '#8bc34a', 'icon': '🏁', 'badge': 'badge-default'},
    'crazyhouse': {'color': '#673ab7', 'icon': '🏠', 'badge': 'badge-default'},
    'puzzle': {'color': '#009688', 'icon': '🧩', 'badge': 'badge-default'},
    'ultraBullet': {'color': '#d32f2f', 'icon': '💨', 'badge': 'badge-default'}
}

MILESTONES = [800, 1000, 1200, 1400, 1500, 1600, 1800, 2000, 2200, 2400, 2600, 2800, 3000]


@st.cache_data(ttl=3600)
def fetch_rating_history(username):
    """Fetch rating history from Lichess API"""
    url = f"https://lichess.org/api/user/{username}/rating-history"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None


def parse_rating_data(data):
    """Parse rating history into DataFrame"""
    all_games = []
    game_types = []
    
    for item in data:
        if isinstance(item, dict) and "points" in item and isinstance(item["points"], list):
            game_type = item.get("name", "Unknown")
            game_types.append(game_type)
            
            for point in item["points"]:
                if len(point) >= 4:
                    year = point[0]
                    month = point[1] + 1  # API month is 0-based
                    month = max(1, min(12, month))
                    max_days = calendar.monthrange(year, month)[1]
                    day = max(1, min(point[2], max_days))
                    
                    date = dt.datetime(year, month, day)
                    rating = point[3]
                    
                    all_games.append({
                        'game_type': game_type,
                        'date': date,
                        'rating': rating
                    })
    
    df = pd.DataFrame(all_games)
    if not df.empty:
        df = df.sort_values('date')
    
    return df, game_types


def calculate_stats(df, game_type):
    """Calculate statistics for a game type"""
    type_df = df[df['game_type'] == game_type].copy()
    
    if type_df.empty:
        return None
    
    type_df = type_df.sort_values('date')
    
    current = type_df['rating'].iloc[-1]
    peak = type_df['rating'].max()
    lowest = type_df['rating'].min()
    peak_date = type_df[type_df['rating'] == peak]['date'].iloc[0]
    
    # Calculate changes
    if len(type_df) >= 30:
        change_30d = current - type_df.iloc[-30]['rating']
    else:
        change_30d = current - type_df.iloc[0]['rating']
    
    if len(type_df) >= 7:
        change_7d = current - type_df.iloc[-7]['rating']
    else:
        change_7d = 0
    
    # Volatility (standard deviation of daily changes)
    type_df['change'] = type_df['rating'].diff()
    volatility = type_df['change'].std() if len(type_df) > 1 else 0
    
    # Growth rate (average change per day)
    days_span = (type_df['date'].max() - type_df['date'].min()).days
    total_change = current - type_df['rating'].iloc[0]
    growth_rate = total_change / days_span if days_span > 0 else 0
    
    return {
        'current': current,
        'peak': peak,
        'peak_date': peak_date,
        'lowest': lowest,
        'change_7d': change_7d,
        'change_30d': change_30d,
        'volatility': volatility,
        'growth_rate': growth_rate,
        'total_points': len(type_df),
        'first_date': type_df['date'].min(),
        'last_date': type_df['date'].max()
    }


def get_next_milestone(current_rating):
    """Get the next milestone to reach"""
    for m in MILESTONES:
        if current_rating < m:
            return m
    return None


def create_main_chart(df, selected_types, show_milestones=True, date_range=None):
    """Create the main rating history chart"""
    fig = go.Figure()
    
    # Filter by date if specified
    plot_df = df.copy()
    if date_range:
        plot_df = plot_df[(plot_df['date'] >= date_range[0]) & (plot_df['date'] <= date_range[1])]
    
    for game_type in selected_types:
        type_df = plot_df[plot_df['game_type'] == game_type].sort_values('date')
        
        if type_df.empty:
            continue
        
        config = GAME_TYPE_CONFIG.get(game_type, {'color': '#667eea', 'icon': '♟️'})
        color = config['color']
        
        # Add area fill
        fig.add_trace(go.Scatter(
            x=type_df['date'],
            y=type_df['rating'],
            mode='lines',
            name=f"{config.get('icon', '♟️')} {game_type}",
            line=dict(color=color, width=3),
            fill='tozeroy',
            fillcolor=f'rgba{tuple(list(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + [0.1])}',
            hovertemplate='<b>%{fullData.name}</b><br>Date: %{x|%Y-%m-%d}<br>Rating: %{y}<extra></extra>'
        ))
        
        # Mark peak
        peak_idx = type_df['rating'].idxmax()
        peak_row = type_df.loc[peak_idx]
        fig.add_trace(go.Scatter(
            x=[peak_row['date']],
            y=[peak_row['rating']],
            mode='markers',
            marker=dict(size=12, color=color, symbol='star'),
            name=f'Peak ({game_type})',
            showlegend=False,
            hovertemplate=f'<b>Peak!</b><br>Rating: {peak_row["rating"]}<br>Date: {peak_row["date"].strftime("%Y-%m-%d")}<extra></extra>'
        ))
    
    # Add milestone lines
    if show_milestones and not plot_df.empty:
        min_rating = plot_df['rating'].min()
        max_rating = plot_df['rating'].max()
        
        for milestone in MILESTONES:
            if min_rating - 100 < milestone < max_rating + 100:
                fig.add_hline(
                    y=milestone,
                    line_dash="dot",
                    line_color="rgba(255,255,255,0.2)",
                    annotation_text=str(milestone),
                    annotation_position="right",
                    annotation_font_color="rgba(255,255,255,0.5)"
                )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f0f0f0'),
        xaxis=dict(
            title='',
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True,
            rangeslider=dict(visible=True),
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all", label="All")
                ],
                bgcolor='#1a1a2e',
                activecolor='#667eea',
                font=dict(color='#f0f0f0')
            )
        ),
        yaxis=dict(
            title='Rating',
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            bgcolor='rgba(0,0,0,0)'
        ),
        hovermode='x unified',
        height=500,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def create_monthly_heatmap(df, game_type):
    """Create monthly rating change heatmap"""
    type_df = df[df['game_type'] == game_type].copy()
    
    if type_df.empty:
        return None
    
    type_df['year'] = type_df['date'].dt.year
    type_df['month'] = type_df['date'].dt.month
    
    # Get last rating of each month
    monthly = type_df.groupby(['year', 'month']).agg({
        'rating': ['first', 'last']
    }).reset_index()
    monthly.columns = ['year', 'month', 'start_rating', 'end_rating']
    monthly['change'] = monthly['end_rating'] - monthly['start_rating']
    
    # Pivot for heatmap
    pivot = monthly.pivot(index='year', columns='month', values='change')
    
    # Fill month names
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=month_names[:pivot.shape[1]],
        y=pivot.index,
        colorscale='RdYlGn',
        zmid=0,
        text=[[f'{v:+.0f}' if not np.isnan(v) else '' for v in row] for row in pivot.values],
        texttemplate='%{text}',
        textfont=dict(color='white'),
        hovertemplate='%{y} %{x}<br>Change: %{z:+.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f0f0f0'),
        xaxis=dict(title=''),
        yaxis=dict(title='', autorange='reversed'),
        height=250
    )
    
    return fig


def create_sparkline(df, game_type, width=150, height=50):
    """Create a simple sparkline for a game type"""
    type_df = df[df['game_type'] == game_type].sort_values('date').tail(30)
    
    if type_df.empty:
        return None
    
    config = GAME_TYPE_CONFIG.get(game_type, {'color': '#667eea'})
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=type_df['date'],
        y=type_df['rating'],
        mode='lines',
        line=dict(color=config['color'], width=2),
        fill='tozeroy',
        fillcolor=f'rgba{tuple(list(int(config["color"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + [0.2])}'
    ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=height,
        width=width,
        showlegend=False
    )
    
    return fig


# ===== MAIN APP =====

st.markdown("""
<h1 style="text-align: center;">📈 Rating History</h1>
<p style="text-align: center; color: #888;">Track your chess rating progress over time</p>
""", unsafe_allow_html=True)

st.markdown("---")

# Input
col1, col2 = st.columns([3, 1])

with col1:
    username = st.text_input("Lichess Username", value=get_username(), label_visibility="collapsed", placeholder="Enter Lichess username...")

with col2:
    fetch_btn = st.button("📊 Load History", type="primary", use_container_width=True)

if username:
    set_username(username)

if fetch_btn and username:
    with st.spinner("Fetching rating history..."):
        data = fetch_rating_history(username)
        
        if not data:
            st.error("❌ Could not fetch data. Check username and try again.")
            st.stop()
        
        df, game_types = parse_rating_data(data)
        
        if df.empty:
            st.warning("No rating history found for this user.")
            st.stop()
        
        st.session_state.rating_df = df
        st.session_state.rating_game_types = game_types

# Display results
if 'rating_df' in st.session_state and not st.session_state.rating_df.empty:
    df = st.session_state.rating_df
    game_types = st.session_state.rating_game_types
    
    # Game type selector with badges
    st.markdown("**Select Game Types:**")
    
    badge_html = ""
    for gt in game_types:
        config = GAME_TYPE_CONFIG.get(gt, {'icon': '♟️', 'badge': 'badge-default'})
        badge_html += f'<span class="game-type-badge {config["badge"]}">{config["icon"]} {gt}</span>'
    
    st.markdown(badge_html, unsafe_allow_html=True)
    
    # Actual selector
    default_types = [gt for gt in ['blitz', 'rapid', 'bullet'] if gt in game_types][:3]
    selected_types = st.multiselect(
        "Game Types",
        game_types,
        default=default_types if default_types else game_types[:3],
        label_visibility="collapsed"
    )
    
    if not selected_types:
        st.warning("Please select at least one game type")
        st.stop()
    
    # Stats cards for primary selected type
    primary_type = selected_types[0]
    stats = calculate_stats(df, primary_type)
    
    if stats:
        st.markdown(f'<div class="section-header"><p class="section-title">{GAME_TYPE_CONFIG.get(primary_type, {}).get("icon", "♟️")} {primary_type.capitalize()} Statistics</p></div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{stats['current']}</div>
                <div class="stat-label">Current Rating</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #FFD700;">⭐ {stats['peak']}</div>
                <div class="stat-label">Peak Rating</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            delta_class = 'delta-positive' if stats['change_30d'] >= 0 else 'delta-negative'
            delta_symbol = '+' if stats['change_30d'] >= 0 else ''
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value {delta_class}">{delta_symbol}{stats['change_30d']:.0f}</div>
                <div class="stat-label">Last 30 Days</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            delta_class = 'delta-positive' if stats['change_7d'] >= 0 else 'delta-negative'
            delta_symbol = '+' if stats['change_7d'] >= 0 else ''
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value {delta_class}">{delta_symbol}{stats['change_7d']:.0f}</div>
                <div class="stat-label">Last 7 Days</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="font-size: 1.5rem;">{stats['volatility']:.1f}</div>
                <div class="stat-label">Volatility</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Progress to next milestone
        next_milestone = get_next_milestone(stats['current'])
        if next_milestone:
            prev_milestone = MILESTONES[MILESTONES.index(next_milestone) - 1] if MILESTONES.index(next_milestone) > 0 else stats['lowest']
            progress = (stats['current'] - prev_milestone) / (next_milestone - prev_milestone) * 100
            points_needed = next_milestone - stats['current']
            
            st.markdown(f"""
            <div class="milestone-card milestone-pending">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #f0f0f0;"><strong>Next Milestone: {next_milestone}</strong></span>
                    <span style="color: #ff9800;">{points_needed} points to go</span>
                </div>
                <div class="progress-container">
                    <div class="progress-fill" style="width: {progress}%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Main chart
    st.markdown('<div class="section-header"><p class="section-title">📈 Rating Over Time</p></div>', unsafe_allow_html=True)
    
    show_milestones = st.checkbox("Show milestone lines", value=True)
    
    fig_main = create_main_chart(df, selected_types, show_milestones)
    st.plotly_chart(fig_main, use_container_width=True, key="main_rating_chart")
    
    # Tabs for additional analysis
    tab1, tab2, tab3 = st.tabs(["📊 Comparison", "🗓️ Monthly Heatmap", "📋 All Stats"])
    
    with tab1:
        if len(selected_types) > 1:
            st.markdown("### Rating Comparison")
            
            comparison_data = []
            for gt in selected_types:
                gt_stats = calculate_stats(df, gt)
                if gt_stats:
                    comparison_data.append({
                        'Game Type': gt,
                        'Current': gt_stats['current'],
                        'Peak': gt_stats['peak'],
                        '30D Change': gt_stats['change_30d'],
                        'Volatility': gt_stats['volatility']
                    })
            
            if comparison_data:
                comp_df = pd.DataFrame(comparison_data)
                
                # Bar chart comparison
                fig_comp = go.Figure()
                
                colors = [GAME_TYPE_CONFIG.get(gt, {}).get('color', '#667eea') for gt in comp_df['Game Type']]
                
                fig_comp.add_trace(go.Bar(
                    name='Current',
                    x=comp_df['Game Type'],
                    y=comp_df['Current'],
                    marker_color=colors,
                    text=comp_df['Current'],
                    textposition='outside'
                ))
                
                fig_comp.add_trace(go.Bar(
                    name='Peak',
                    x=comp_df['Game Type'],
                    y=comp_df['Peak'],
                    marker_color=[f'rgba{tuple(list(int(c.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + [0.5])}' for c in colors],
                    text=comp_df['Peak'],
                    textposition='outside'
                ))
                
                fig_comp.update_layout(
                    barmode='group',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f0f0f0'),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                    yaxis=dict(title='Rating', gridcolor='rgba(255,255,255,0.1)'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02),
                    height=350
                )
                
                st.plotly_chart(fig_comp, use_container_width=True, key="comparison_chart")
                
                # Table
                st.dataframe(comp_df, use_container_width=True, hide_index=True)
        else:
            st.info("Select multiple game types to compare")
    
    with tab2:
        st.markdown("### Monthly Rating Change")
        
        selected_heatmap_type = st.selectbox("Select game type", selected_types, key="heatmap_type")
        
        fig_heatmap = create_monthly_heatmap(df, selected_heatmap_type)
        
        if fig_heatmap:
            st.plotly_chart(fig_heatmap, use_container_width=True, key="monthly_heatmap")
            st.caption("🟢 Green = Rating gained | 🔴 Red = Rating lost")
        else:
            st.info("Not enough data for heatmap")
    
    with tab3:
        st.markdown("### All Game Types Overview")
        
        all_stats = []
        for gt in game_types:
            gt_stats = calculate_stats(df, gt)
            if gt_stats:
                config = GAME_TYPE_CONFIG.get(gt, {'icon': '♟️'})
                all_stats.append({
                    'Type': f"{config['icon']} {gt}",
                    'Current': gt_stats['current'],
                    'Peak': gt_stats['peak'],
                    'Lowest': gt_stats['lowest'],
                    '7D': f"{gt_stats['change_7d']:+.0f}",
                    '30D': f"{gt_stats['change_30d']:+.0f}",
                    'Data Points': gt_stats['total_points']
                })
        
        if all_stats:
            stats_df = pd.DataFrame(all_stats)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        # Sparklines
        st.markdown("### Quick Trends (Last 30 points)")
        
        cols = st.columns(min(4, len(game_types)))
        for i, gt in enumerate(game_types[:8]):
            with cols[i % 4]:
                config = GAME_TYPE_CONFIG.get(gt, {'icon': '♟️', 'color': '#667eea'})
                gt_stats = calculate_stats(df, gt)
                
                if gt_stats:
                    delta_class = 'delta-positive' if gt_stats['change_7d'] >= 0 else 'delta-negative'
                    st.markdown(f"""
                    <div class="sparkline-container">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                            <span style="color: #f0f0f0;">{config['icon']} {gt}</span>
                            <span class="{delta_class}">{gt_stats['change_7d']:+.0f}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    sparkline = create_sparkline(df, gt)
                    if sparkline:
                        st.plotly_chart(sparkline, use_container_width=True, key=f"sparkline_{gt}")
    
    # Export
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # Export to CSV
        export_df = df[df['game_type'].isin(selected_types)].copy()
        csv = export_df.to_csv(index=False)
        st.download_button(
            "📥 Export CSV",
            csv,
            file_name=f"rating_history_{username}.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    # Welcome screen
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 5rem; margin-bottom: 20px;">📈</div>
        <h2 style="color: #f0f0f0;">Track Your Rating Journey</h2>
        <p style="color: #888; max-width: 500px; margin: 20px auto;">
            Enter your Lichess username to visualize your rating history, 
            track progress, and analyze trends across all game types.
        </p>
        <div style="margin-top: 30px;">
            <span class="game-type-badge badge-bullet">🚀 Bullet</span>
            <span class="game-type-badge badge-blitz">⚡ Blitz</span>
            <span class="game-type-badge badge-rapid">🕐 Rapid</span>
            <span class="game-type-badge badge-classical">🏛️ Classical</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Data from Lichess API • Updates hourly • ⭐ marks your peak rating")