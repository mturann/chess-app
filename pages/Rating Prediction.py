import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
import requests
import plotly.express as px
import plotly.graph_objs as go
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
import os
import json
import warnings

warnings.filterwarnings('ignore')

token = os.environ['LICHESS_TOKEN']
st.set_page_config(page_title="Rating Prediction", page_icon="🔮")

def get_rating_history(username, game_type):
    """Fetch rating history using public API - more reliable"""
    url = f"https://lichess.org/api/user/{username}/rating-history"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            points = []
            for item in data:
                if item.get('name', '').lower() == game_type.lower():
                    points = item.get('points', [])
                    break
            ratings_data = []
            for point in points:
                year, month, day, rating = point
                month += 1  # API month is 0-based
                month = max(1, min(12, month))
                days_in_month = calendar.monthrange(year, month)[1]
                day = max(1, min(days_in_month, day))
                date = datetime(year, month, day)
                ratings_data.append({'date': date, 'rating': rating})
            df = pd.DataFrame(ratings_data).drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
            if not df.empty:
                st.success(f"Fetched {len(df)} rating points. Last update: {df['date'].iloc[-1].strftime('%Y-%m-%d')} | Rating: {df['rating'].iloc[-1]:.0f}")
            return df
    except Exception as e:
        st.error(f"Error fetching rating history: {e}")
    return pd.DataFrame()

def fetch_user_games(username, token, max_games=1000, game_type='blitz'):
    url = f"https://lichess.org/api/games/user/{username}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/x-ndjson"}
    params = {"max": max_games, "rated": "true", "pgnInJson": "true", "clocks": "true", "evals": "false", "opening": "true", "perf": game_type}
    games = []
    try:
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=30)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                game = json.loads(line.decode('utf-8'))
                games.append(game)
        st.info(f"Fetched {len(games)} {game_type} games")
    except Exception as e:
        st.warning(f"Could not fetch games: {e}. Proceeding without game features.")
    return games

def process_games(games, username, game_type):
    games_data = []
    for game in games:
        players = game.get('players', {})
        is_white = players.get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
        player_color = 'white' if is_white else 'black'
        opponent_color = 'black' if is_white else 'white'
        winner = game.get('winner')
        outcome = 'win' if winner == player_color else 'draw' if winner is None else 'loss'
        game_data = {
            'date': pd.to_datetime(game.get('createdAt', 0) / 1000, unit='s').normalize(),
            'game_id': game.get('id'),
            'player_rating': players.get(player_color, {}).get('rating'),
            'opponent_rating': players.get(opponent_color, {}).get('rating'),
            'rating_diff': players.get(player_color, {}).get('ratingDiff', 0),
            'outcome': outcome,
            'moves': len(game.get('moves', '').split()) if game.get('moves') else 0,
        }
        games_data.append(game_data)
    df = pd.DataFrame(games_data)
    if not df.empty:
        df = df.sort_values('date').reset_index(drop=True)
    return df

def create_time_series_features(df_ratings, df_games):
    df = df_ratings.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df = df.resample('D').last().ffill()
    df['rating_change'] = df['rating'].diff()
    df['rating_ma7'] = df['rating'].rolling(window=7, min_periods=1).mean()
    df['rating_ma30'] = df['rating'].rolling(window=30, min_periods=1).mean()
    df['rating_std7'] = df['rating'].rolling(window=7, min_periods=1).std()
    df['rating_std30'] = df['rating'].rolling(window=30, min_periods=1).std()
    df['rating_momentum'] = df['rating'] - df['rating'].shift(7)
    if not df_games.empty:
        daily_games = df_games.groupby('date').agg({
            'game_id': 'count',
            'outcome': lambda x: (x == 'win').mean(),
            'rating_diff': 'mean',
            'opponent_rating': 'mean',
            'moves': 'mean'
        }).rename(columns={
            'game_id': 'games_per_day',
            'outcome': 'daily_win_rate',
            'rating_diff': 'avg_rating_change',
            'opponent_rating': 'avg_opponent_rating',
            'moves': 'avg_moves'
        })
        df = df.join(daily_games, how='left')
        df['games_per_day'] = df['games_per_day'].fillna(0)
        df['daily_win_rate'] = df['daily_win_rate'].ffill().fillna(0.5)
        df['avg_rating_change'] = df['avg_rating_change'].fillna(0)
        df['games_last_7days'] = df['games_per_day'].rolling(7, min_periods=1).sum()
        df['win_rate_7days'] = df['daily_win_rate'].rolling(7, min_periods=1).mean()
    df['day_of_week'] = df.index.dayofweek
    df['day_of_month'] = df.index.day
    df['month'] = df.index.month
    df = df.ffill().bfill()
    return df

def train_gradient_boosting(df_features, forecast_days):
    feature_columns = [col for col in df_features.columns if col != 'rating']
    X = df_features[feature_columns].fillna(0)
    y = df_features['rating']
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = GradientBoostingRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
    model.fit(X_scaled, y)
    # Future features
    last_date = df_features.index[-1]
    future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=forecast_days, freq='D')
    future_df = pd.DataFrame(index=future_dates, columns=feature_columns)
    for col in feature_columns:
        if col == 'day_of_week':
            future_df[col] = future_dates.dayofweek
        elif col == 'day_of_month':
            future_df[col] = future_dates.day
        elif col == 'month':
            future_df[col] = future_dates.month
        else:
            future_df[col] = df_features[col].iloc[-1]
    future_df = future_df.fillna(0)
    future_scaled = scaler.transform(future_df)
    predictions = model.predict(future_scaled)
    # RMSE as uncertainty
    y_pred = model.predict(X_scaled)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    return future_dates, predictions, rmse, model, scaler

st.title("Rating Prediction")
username = st.text_input("Lichess Username", value="")
game_type = st.selectbox("Game Type", ["blitz", "bullet", "rapid", "classical", "chess960", "crazyhouse", "antichess", "atomic", "horde", "kingOfTheHill", "racingKings", "threeCheck"], index=0)
forecast_days = st.number_input("Forecast Days", min_value=1, max_value=365, value=30)
max_games = st.slider("Max Games to Analyze", 100, 5000, 1000)

if st.button("Predict Rating"):
    if username:
        with st.spinner("Fetching data..."):
            df_ratings = get_rating_history(username, game_type)
            if df_ratings.empty or len(df_ratings) < 20:
                st.error("Insufficient rating data (need 20+ points). Try another user or game type.")
                st.stop()
            games = fetch_user_games(username, token, max_games, game_type)
            df_games = process_games(games, username, game_type)
            df_features = create_time_series_features(df_ratings, df_games)
            if len(df_features) < 20:
                st.error("Insufficient features.")
                st.stop()
            future_dates, predictions, rmse, _, _ = train_gradient_boosting(df_features, forecast_days)
        
        # History Plot
        st.subheader("Rating History")
        fig_hist = px.line(df_features.reset_index(), x='date', y='rating', title=f"{game_type.capitalize()} Rating History & Trends")
        fig_hist.add_scatter(x=df_features.index, y=df_features['rating_ma7'], mode='lines', name='7-Day MA', line=dict(dash='dash'))
        fig_hist.add_scatter(x=df_features.index, y=df_features['rating_ma30'], mode='lines', name='30-Day MA', line=dict(dash='dot'))
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Forecast Plot
        st.subheader("Future Rating Forecast")
        fig_forecast = go.Figure()
        fig_forecast.add_trace(go.Scatter(x=df_features.index, y=df_features['rating'], mode='lines', name='Historical Rating', line=dict(color='blue', width=3)))
        fig_forecast.add_trace(go.Scatter(x=future_dates, y=predictions, mode='lines+markers', name='Forecast', line=dict(color='red', width=3)))
        fig_forecast.add_trace(go.Scatter(x=future_dates, y=predictions + rmse, mode='lines', line=dict(color='red', width=0), showlegend=False))
        fig_forecast.add_trace(go.Scatter(x=future_dates, y=predictions - rmse, mode='lines', fill='tonexty', fillcolor='rgba(255,0,0,0.2)', line=dict(color='red', width=0), name='± RMSE Confidence'))
        fig_forecast.update_layout(title=f"{game_type.capitalize()} Forecast ({forecast_days} Days)", xaxis_title='Date', yaxis_title='Rating', hovermode='x unified')
        st.plotly_chart(fig_forecast, use_container_width=True)
        
        # Summary
        current_rating = df_features['rating'].iloc[-1]
        final_pred = predictions[-1]
        change = final_pred - current_rating
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Rating", f"{current_rating:.0f}")
        col2.metric("Predicted in 30 Days", f"{final_pred:.0f}")
        col3.metric("Expected Change", f"{change:+.0f}")
        col4.metric("Model RMSE", f"{rmse:.0f}")
        
        st.success("Now uses public API for full rating history. Forecast starts after LAST real data point!")
    else:
        st.warning("Enter username.")