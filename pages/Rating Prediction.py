import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import pickle
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token

st.set_page_config(page_title="Rating Prediction", page_icon="🔮", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .prediction-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        color: white;
        margin: 20px 0;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    .prediction-value {
        font-size: 4rem;
        font-weight: bold;
        margin: 10px 0;
    }
    .prediction-label {
        font-size: 1.1rem;
        opacity: 0.9;
    }
    .prediction-change {
        font-size: 1.5rem;
        margin-top: 10px;
    }
    .change-positive { color: #4CAF50; }
    .change-negative { color: #ff6b6b; }
    
    .stat-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid #333;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #aaa;
        margin-top: 5px;
    }
    
    .confidence-bar {
        height: 10px;
        background: #333;
        border-radius: 5px;
        overflow: hidden;
        margin: 10px 0;
    }
    .confidence-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 5px;
    }
    
    .insight-card {
        background: #2d2d2d;
        padding: 15px 20px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #667eea;
    }
    .insight-positive { border-left-color: #4CAF50; }
    .insight-negative { border-left-color: #f44336; }
    .insight-neutral { border-left-color: #ff9800; }
    
    .timeline-point {
        background: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
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
    
    .model-info {
        background: #1e1e1e;
        padding: 10px 15px;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #888;
    }
</style>
""", unsafe_allow_html=True)

# Model path - relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, 'rating_models', 'rating_prediction_model.pkl')

# Game type icons
GAME_TYPE_CONFIG = {
    'bullet': {'icon': '🚀', 'color': '#f44336'},
    'blitz': {'icon': '⚡', 'color': '#ff9800'},
    'rapid': {'icon': '🕐', 'color': '#4CAF50'},
    'classical': {'icon': '🏛️', 'color': '#2196F3'}
}


@st.cache_resource
def load_model():
    """Load the trained model."""
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'rb') as f:
            model_package = pickle.load(f)
        return model_package
    return None


@st.cache_data(ttl=1800)
def fetch_user_games(username, max_games=500, perf_type="blitz"):
    """Fetch user games from Lichess API."""
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
        st.error(f"Error fetching games: {e}")
        return None


@st.cache_data(ttl=3600)
def fetch_rating_history(username):
    """Fetch rating history from Lichess API."""
    url = f"https://lichess.org/api/user/{username}/rating-history"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def process_games_to_daily(games, username):
    """Process games into daily rating data."""
    rows = []
    
    for game in games:
        players = game.get('players', {})
        white_info = players.get('white', {})
        black_info = players.get('black', {})
        
        white_user = white_info.get('user', {}).get('name', '').lower()
        is_white = white_user == username.lower()
        
        player_info = white_info if is_white else black_info
        opponent_info = black_info if is_white else white_info
        
        player_rating = player_info.get('rating')
        opponent_rating = opponent_info.get('rating')
        
        if not player_rating or not opponent_rating:
            continue
        
        # Outcome
        winner = game.get('winner')
        player_color = 'white' if is_white else 'black'
        if winner == player_color:
            outcome = 1.0
        elif winner is None:
            outcome = 0.5
        else:
            outcome = 0.0
        
        # Time trouble
        clocks = game.get('clocks', [])
        time_trouble = 0
        if clocks:
            player_clocks = []
            for idx, clock in enumerate(clocks):
                if (idx % 2 == 0 and is_white) or (idx % 2 == 1 and not is_white):
                    player_clocks.append(clock / 100)
            if player_clocks and min(player_clocks) < 30:
                time_trouble = 1
        
        # Moves
        moves_str = game.get('moves', '')
        num_moves = len(moves_str.split()) // 2 if moves_str else 0
        
        # Date
        created_at = game.get('createdAt', 0)
        game_date = datetime.fromtimestamp(created_at / 1000) if created_at else None
        
        if game_date:
            rows.append({
                'date': game_date,
                'player_rating': player_rating,
                'opponent_rating': opponent_rating,
                'rating_diff': opponent_rating - player_rating,
                'outcome': outcome,
                'time_trouble': time_trouble,
                'num_moves': num_moves
            })
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    
    # Daily aggregation
    daily = df.groupby(df['date'].dt.date).agg({
        'player_rating': 'last',
        'outcome': ['sum', 'count', 'mean'],
        'opponent_rating': 'mean',
        'rating_diff': 'mean',
        'time_trouble': 'mean',
        'num_moves': 'mean'
    }).reset_index()
    
    daily.columns = ['date', 'rating', 'daily_wins', 'daily_games', 'daily_winrate',
                     'avg_opponent_rating', 'avg_rating_diff', 'time_trouble_rate', 'avg_moves']
    
    daily['date'] = pd.to_datetime(daily['date'])
    daily = daily.sort_values('date').reset_index(drop=True)
    
    return daily


def create_features(df):
    """Create features for prediction (same as training)."""
    df = df.copy()
    
    # Lag features
    for lag in [1, 2, 3, 5, 7]:
        df[f'rating_lag_{lag}'] = df['rating'].shift(lag)
    
    # Rolling statistics
    for window in [3, 7, 14, 30]:
        df[f'rating_ma_{window}'] = df['rating'].shift(1).rolling(window, min_periods=1).mean()
        df[f'rating_std_{window}'] = df['rating'].shift(1).rolling(window, min_periods=1).std()
        df[f'rating_min_{window}'] = df['rating'].shift(1).rolling(window, min_periods=1).min()
        df[f'rating_max_{window}'] = df['rating'].shift(1).rolling(window, min_periods=1).max()
        df[f'winrate_ma_{window}'] = df['daily_winrate'].shift(1).rolling(window, min_periods=1).mean()
        df[f'games_ma_{window}'] = df['daily_games'].shift(1).rolling(window, min_periods=1).mean()
    
    # Trend features
    df['rating_change_1d'] = df['rating'].diff().shift(1)
    df['rating_change_7d'] = (df['rating'] - df['rating'].shift(7)).shift(1)
    df['rating_change_14d'] = (df['rating'] - df['rating'].shift(14)).shift(1)
    df['rating_change_30d'] = (df['rating'] - df['rating'].shift(30)).shift(1)
    
    # EMA
    df['rating_ema_7'] = df['rating'].shift(1).ewm(span=7, adjust=False).mean()
    df['rating_ema_14'] = df['rating'].shift(1).ewm(span=14, adjust=False).mean()
    df['rating_ema_30'] = df['rating'].shift(1).ewm(span=30, adjust=False).mean()
    
    # Volatility
    df['rating_volatility_7'] = df['rating_change_1d'].shift(1).rolling(7, min_periods=1).std()
    df['rating_volatility_14'] = df['rating_change_1d'].shift(1).rolling(14, min_periods=1).std()
    
    # Streaks
    df['win_streak'] = (df['daily_winrate'] > 0.5).astype(int)
    df['win_streak'] = df['win_streak'].groupby((df['win_streak'] != df['win_streak'].shift()).cumsum()).cumsum()
    df['win_streak'] = df['win_streak'].shift(1)
    
    # Time features
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    
    # Fill NaN
    df = df.fillna(method='bfill').fillna(method='ffill').fillna(0)
    
    return df


def predict_future_ratings(model_package, current_features, days=30):
    """Predict future ratings with proper feature updates."""
    model = model_package['model']
    scaler = model_package['scaler']
    feature_cols = model_package['feature_columns']
    
    predictions = []
    
    # Keep history of predictions for rolling calculations
    rating_history = current_features['rating'].tolist()
    winrate_history = current_features['daily_winrate'].tolist()
    games_history = current_features['daily_games'].tolist()
    
    current_row = current_features.iloc[-1:].copy()
    
    for i in range(days):
        # Get features and predict
        X = current_row[feature_cols].values
        X_scaled = scaler.transform(X)
        pred = model.predict(X_scaled)[0]
        predictions.append(pred)
        
        # Add prediction to history
        rating_history.append(pred)
        winrate_history.append(0.5)  # Assume 50% win rate for future
        games_history.append(current_row['daily_games'].values[0])  # Keep same activity
        
        # Update ALL features for next iteration
        
        # Lag features
        current_row['rating_lag_1'] = rating_history[-2] if len(rating_history) >= 2 else pred
        current_row['rating_lag_2'] = rating_history[-3] if len(rating_history) >= 3 else pred
        current_row['rating_lag_3'] = rating_history[-4] if len(rating_history) >= 4 else pred
        current_row['rating_lag_5'] = rating_history[-6] if len(rating_history) >= 6 else pred
        current_row['rating_lag_7'] = rating_history[-8] if len(rating_history) >= 8 else pred
        
        # Rolling statistics (use last N values from history)
        for window in [3, 7, 14, 30]:
            recent_ratings = rating_history[-window:] if len(rating_history) >= window else rating_history
            recent_winrates = winrate_history[-window:] if len(winrate_history) >= window else winrate_history
            recent_games = games_history[-window:] if len(games_history) >= window else games_history
            
            current_row[f'rating_ma_{window}'] = np.mean(recent_ratings)
            current_row[f'rating_std_{window}'] = np.std(recent_ratings) if len(recent_ratings) > 1 else 0
            current_row[f'rating_min_{window}'] = np.min(recent_ratings)
            current_row[f'rating_max_{window}'] = np.max(recent_ratings)
            current_row[f'winrate_ma_{window}'] = np.mean(recent_winrates)
            current_row[f'games_ma_{window}'] = np.mean(recent_games)
        
        # Trend features
        current_row['rating_change_1d'] = pred - rating_history[-2] if len(rating_history) >= 2 else 0
        current_row['rating_change_7d'] = pred - rating_history[-8] if len(rating_history) >= 8 else 0
        current_row['rating_change_14d'] = pred - rating_history[-15] if len(rating_history) >= 15 else 0
        current_row['rating_change_30d'] = pred - rating_history[-31] if len(rating_history) >= 31 else 0
        
        # EMA updates (exponential decay)
        alpha_7 = 2 / (7 + 1)
        alpha_14 = 2 / (14 + 1)
        alpha_30 = 2 / (30 + 1)
        current_row['rating_ema_7'] = alpha_7 * pred + (1 - alpha_7) * current_row['rating_ema_7'].values[0]
        current_row['rating_ema_14'] = alpha_14 * pred + (1 - alpha_14) * current_row['rating_ema_14'].values[0]
        current_row['rating_ema_30'] = alpha_30 * pred + (1 - alpha_30) * current_row['rating_ema_30'].values[0]
        
        # Volatility (std of recent changes)
        if len(rating_history) >= 8:
            changes_7 = [rating_history[j] - rating_history[j-1] for j in range(-7, 0)]
            current_row['rating_volatility_7'] = np.std(changes_7)
        if len(rating_history) >= 15:
            changes_14 = [rating_history[j] - rating_history[j-1] for j in range(-14, 0)]
            current_row['rating_volatility_14'] = np.std(changes_14)
        
        # Update rating in current row
        current_row['rating'] = pred
    
    return predictions


def generate_insights(current_rating, predictions, daily_df):
    """Generate insights based on predictions."""
    insights = []
    
    predicted_30d = predictions[-1]
    change_30d = predicted_30d - current_rating
    
    # Trend insight
    if change_30d > 20:
        insights.append({
            'type': 'positive',
            'icon': '📈',
            'title': 'Strong Upward Trend',
            'text': f'Your rating is predicted to increase by {change_30d:.0f} points. Keep up the good work!'
        })
    elif change_30d > 0:
        insights.append({
            'type': 'positive',
            'icon': '📊',
            'title': 'Slight Improvement Expected',
            'text': f'Your rating may increase by {change_30d:.0f} points. Stay consistent!'
        })
    elif change_30d > -20:
        insights.append({
            'type': 'neutral',
            'icon': '➡️',
            'title': 'Stable Rating Expected',
            'text': 'Your rating is expected to remain relatively stable.'
        })
    else:
        insights.append({
            'type': 'negative',
            'icon': '📉',
            'title': 'Potential Rating Drop',
            'text': f'Your rating might decrease by {abs(change_30d):.0f} points. Focus on quality games!'
        })
    
    # Recent performance
    if len(daily_df) >= 7:
        recent_wr = daily_df['daily_winrate'].tail(7).mean()
        if recent_wr > 0.55:
            insights.append({
                'type': 'positive',
                'icon': '🔥',
                'title': 'Hot Streak',
                'text': f'Your win rate in the last 7 days is {recent_wr*100:.0f}%. Great form!'
            })
        elif recent_wr < 0.45:
            insights.append({
                'type': 'negative',
                'icon': '❄️',
                'title': 'Cold Streak',
                'text': f'Your win rate in the last 7 days is {recent_wr*100:.0f}%. Consider taking a break.'
            })
    
    # Volatility
    if len(daily_df) >= 14:
        volatility = daily_df['rating'].tail(14).std()
        if volatility > 30:
            insights.append({
                'type': 'neutral',
                'icon': '🎢',
                'title': 'High Volatility',
                'text': f'Your rating has been quite volatile (±{volatility:.0f} points). Play more consistently.'
            })
    
    return insights


# ===== MAIN APP =====

st.markdown("""
<h1 style="text-align: center;">🔮 Rating Prediction</h1>
<p style="text-align: center; color: #888;">AI-powered chess rating forecast using machine learning</p>
""", unsafe_allow_html=True)

st.markdown("---")

# Load model
model_package = load_model()

if model_package is None:
    st.error("⚠️ Model not found!")
    st.markdown("""
    ### Model Setup Required
    
    The rating prediction model needs to be trained first. Please run the `rating_prediction_analysis.ipynb` notebook to train and save the model.
    
    Expected model path: `pages/rating_models/rating_prediction_model.pkl`
    """)
    st.stop()

# Model info
model_type = model_package.get('model_type', 'Unknown')
model_metrics = model_package.get('metrics', {})
training_date = model_package.get('training_date', 'Unknown')

# Input section
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    username = st.text_input("Lichess Username", value=get_username(), label_visibility="collapsed", placeholder="Enter username...")

with col2:
    game_type = st.selectbox("Type", ["blitz", "rapid", "bullet", "classical"], index=0, label_visibility="collapsed")

with col3:
    forecast_days = st.selectbox("Forecast", [7, 14, 30, 60], index=2, label_visibility="collapsed", format_func=lambda x: f"{x} days")

with col4:
    predict_btn = st.button("🔮 Predict", type="primary", use_container_width=True)

if username:
    set_username(username)

if predict_btn and username:
    with st.spinner("Fetching data and making predictions..."):
        # Fetch games
        games = fetch_user_games(username, max_games=500, perf_type=game_type)
        
        if not games:
            st.error("❌ No games found or user doesn't exist")
            st.stop()
        
        # Process to daily
        daily_df = process_games_to_daily(games, username)
        
        if daily_df is None or len(daily_df) < 14:
            st.warning("⚠️ Not enough data for prediction (need at least 14 days of games)")
            st.stop()
        
        # Create features
        features_df = create_features(daily_df)
        
        # Current rating
        current_rating = daily_df['rating'].iloc[-1]
        
        # Make predictions
        try:
            predictions = predict_future_ratings(model_package, features_df, days=forecast_days)
        except Exception as e:
            st.error(f"Prediction error: {e}")
            st.stop()
        
        # Generate insights
        insights = generate_insights(current_rating, predictions, daily_df)
        
        # Store in session
        st.session_state.pred_daily = daily_df
        st.session_state.pred_predictions = predictions
        st.session_state.pred_current = current_rating
        st.session_state.pred_insights = insights
        st.session_state.pred_game_type = game_type

# Display results
if 'pred_predictions' in st.session_state:
    daily_df = st.session_state.pred_daily
    predictions = st.session_state.pred_predictions
    current_rating = st.session_state.pred_current
    insights = st.session_state.pred_insights
    game_type = st.session_state.pred_game_type
    
    config = GAME_TYPE_CONFIG.get(game_type, {'icon': '♟️', 'color': '#667eea'})
    
    # Prediction cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Current Rating</div>
            <div class="stat-value">{current_rating:.0f}</div>
            <div class="stat-label">{config['icon']} {game_type.capitalize()}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        pred_7d = predictions[min(6, len(predictions)-1)]
        change_7d = pred_7d - current_rating
        change_class = 'change-positive' if change_7d >= 0 else 'change-negative'
        change_sign = '+' if change_7d >= 0 else ''
        
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">7-Day Forecast</div>
            <div class="stat-value">{pred_7d:.0f}</div>
            <div class="stat-label {change_class}">{change_sign}{change_7d:.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pred_final = predictions[-1]
        change_final = pred_final - current_rating
        change_class = 'change-positive' if change_final >= 0 else 'change-negative'
        change_sign = '+' if change_final >= 0 else ''
        
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">{len(predictions)}-Day Forecast</div>
            <div class="stat-value">{pred_final:.0f}</div>
            <div class="stat-label {change_class}">{change_sign}{change_final:.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Main prediction card
    st.markdown(f"""
    <div class="prediction-card">
        <div class="prediction-label">Predicted Rating in {len(predictions)} Days</div>
        <div class="prediction-value">{pred_final:.0f}</div>
        <div class="prediction-change {change_class}">{change_sign}{change_final:.0f} from current</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Forecast chart
    st.markdown('<div class="section-header"><p class="section-title">📈 Rating Forecast</p></div>', unsafe_allow_html=True)
    
    # Prepare data for chart
    last_date = daily_df['date'].max()
    future_dates = [last_date + timedelta(days=i+1) for i in range(len(predictions))]
    
    fig = go.Figure()
    
    # Historical data
    fig.add_trace(go.Scatter(
        x=daily_df['date'],
        y=daily_df['rating'],
        mode='lines',
        name='Historical',
        line=dict(color='#667eea', width=2)
    ))
    
    # Prediction
    fig.add_trace(go.Scatter(
        x=future_dates,
        y=predictions,
        mode='lines',
        name='Forecast',
        line=dict(color='#f44336', width=2, dash='dash')
    ))
    
    # Confidence band (simplified: ±MAE)
    mae = model_metrics.get('MAE', 10)
    upper = [p + mae for p in predictions]
    lower = [p - mae for p in predictions]
    
    fig.add_trace(go.Scatter(
        x=future_dates + future_dates[::-1],
        y=upper + lower[::-1],
        fill='toself',
        fillcolor='rgba(244, 67, 54, 0.1)',
        line=dict(width=0),
        name='Confidence Band',
        showlegend=True
    ))
    
    # Add vertical line at current date
    fig.add_vline(x=last_date, line_dash="dot", line_color="gray")
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f0f0f0'),
        xaxis=dict(title='', gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='Rating', gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        height=450,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True, key="forecast_chart")
    
    # Insights
    st.markdown('<div class="section-header"><p class="section-title">💡 Insights</p></div>', unsafe_allow_html=True)
    
    for insight in insights:
        card_class = f"insight-{insight['type']}"
        st.markdown(f"""
        <div class="insight-card {card_class}">
            <strong>{insight['icon']} {insight['title']}</strong><br>
            <span style="color: #aaa;">{insight['text']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Detailed forecast
    st.markdown('<div class="section-header"><p class="section-title">📅 Forecast Timeline</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Weekly Milestones:**")
        milestones = [7, 14, 21, 30]
        for day in milestones:
            if day <= len(predictions):
                pred = predictions[day-1]
                change = pred - current_rating
                change_class = 'change-positive' if change >= 0 else 'change-negative'
                sign = '+' if change >= 0 else ''
                date = last_date + timedelta(days=day)
                
                st.markdown(f"""
                <div class="timeline-point">
                    <span><strong>Day {day}</strong> ({date.strftime('%b %d')})</span>
                    <span><strong>{pred:.0f}</strong> <span class="{change_class}">({sign}{change:.0f})</span></span>
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        # Recent performance summary
        st.markdown("**Recent Performance:**")
        
        recent_games = len(daily_df)
        recent_wr = daily_df['daily_winrate'].mean() * 100
        rating_7d = daily_df['rating'].iloc[-1] - daily_df['rating'].iloc[-min(7, len(daily_df))]
        
        st.markdown(f"""
        <div class="stat-card" style="text-align: left; padding: 15px;">
            <p>📊 <strong>{recent_games}</strong> days of data</p>
            <p>🎯 <strong>{recent_wr:.1f}%</strong> average win rate</p>
            <p>📈 <strong>{rating_7d:+.0f}</strong> rating in last 7 days</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Model info footer
    st.markdown("---")
    st.markdown(f"""
    <div class="model-info">
        <strong>Model Info:</strong> {model_type} | 
        MAE: ±{model_metrics.get('MAE', 'N/A'):.1f} rating points | 
        R²: {model_metrics.get('R2', 'N/A'):.4f} 
    </div>
    """, unsafe_allow_html=True)

else:
    # Welcome screen
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 5rem; margin-bottom: 20px;">🔮</div>
        <h2 style="color: #f0f0f0;">Predict Your Future Rating</h2>
        <p style="color: #888; max-width: 500px; margin: 20px auto;">
            Enter your Lichess username to get an AI-powered prediction 
            of your rating over the next 7-60 days based on your recent performance.
        </p>
        <div style="margin-top: 30px;">
            <span style="background: #2d2d2d; padding: 8px 16px; border-radius: 20px; margin: 5px; color: #aaa;">🚀 Bullet</span>
            <span style="background: #2d2d2d; padding: 8px 16px; border-radius: 20px; margin: 5px; color: #aaa;">⚡ Blitz</span>
            <span style="background: #2d2d2d; padding: 8px 16px; border-radius: 20px; margin: 5px; color: #aaa;">🕐 Rapid</span>
            <span style="background: #2d2d2d; padding: 8px 16px; border-radius: 20px; margin: 5px; color: #aaa;">🏛️ Classical</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Predictions are based on historical patterns and may not reflect actual future ratings. Play quality matters more than predictions!")
