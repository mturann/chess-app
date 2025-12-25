import streamlit as st
import pandas as pd
import numpy as np
import pickle
import requests
import json
import time
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Win Probability",
    page_icon="🎯",
    layout="wide"
)

CURRENT_DIR = Path(__file__).parent
MODEL_PATH = CURRENT_DIR / "models" / "global_model_optimized.pkl"
GAME_TYPE = "blitz"
GAMES_TO_FETCH = 100
MIN_GAMES_REQUIRED = 10
ELO_FALLBACK_THRESHOLD = 400


# Feature columns must match the trained model
FEATURE_COLUMNS = [
    # Rating
    'rating_diff', 'elo_expected',
    
    # Player features
    'form_5_adj', 'form_10_adj', 'form_20_adj',
    'streak_norm', 'time_management', 'time_trouble_rate',
    'is_white', 'color_advantage',
    'rating_trend_norm', 'residual_ma10', 'avg_game_length',
    'eco_A_wr', 'eco_B_wr', 'eco_C_wr', 'eco_D_wr', 'eco_E_wr',
    
    # Opponent features
    'opp_form_5_adj', 'opp_form_10_adj', 'opp_streak_norm',
    'opp_time_management', 'opp_rating_trend_norm', 'opp_residual_ma10',
    'has_opponent_data',
    
    # Difference features
    'form_5_diff', 'form_10_diff', 'streak_diff',
    'time_mgmt_diff', 'residual_diff'
]


def format_probability(prob):
    """Format probability with 3 decimal places."""
    return f'{prob * 100:.3f}%'


@st.cache_resource
def load_model():
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)


def get_api_headers():
    return {"Accept": "application/x-ndjson"}


def fetch_user_games(username, max_games=100, perf_type="blitz"):
    url = f"https://lichess.org/api/games/user/{username}"
    headers = get_api_headers()
    params = {
        "max": max_games,
        "rated": "true",
        "perfType": perf_type,
        "clocks": "true",
        "opening": "true"
    }
    
    games = []
    try:
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=30)
        
        if response.status_code == 404:
            return None, "User not found"
        
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                game = json.loads(line.decode('utf-8'))
                games.append(game)
        
        if len(games) == 0:
            return None, f"No {perf_type} games found"
        
        return games, None
        
    except requests.exceptions.Timeout:
        return None, "Request timeout"
    except requests.exceptions.RequestException as e:
        return None, f"API error: {str(e)}"


def process_games_for_player(games, username):
    processed = []
    
    for game in games:
        try:
            players = game.get('players', {})
            white_info = players.get('white', {})
            black_info = players.get('black', {})
            
            white_user = white_info.get('user', {}).get('name', '').lower()
            black_user = black_info.get('user', {}).get('name', '').lower()
            
            is_white = white_user == username.lower()
            player_color = 'white' if is_white else 'black'
            
            player_info = white_info if is_white else black_info
            opponent_info = black_info if is_white else white_info
            
            player_rating = player_info.get('rating')
            opponent_rating = opponent_info.get('rating')
            
            if not player_rating or not opponent_rating:
                continue
            
            winner = game.get('winner')
            if winner == player_color:
                outcome_numeric = 1.0
            elif winner is None:
                outcome_numeric = 0.5
            else:
                outcome_numeric = 0.0
            
            clocks = game.get('clocks', [])
            time_trouble = 0
            
            if clocks and len(clocks) > 0:
                player_clocks = []
                for i, clock in enumerate(clocks):
                    if (i % 2 == 0 and is_white) or (i % 2 == 1 and not is_white):
                        player_clocks.append(clock / 100)
                
                if player_clocks:
                    min_clock = min(player_clocks)
                    time_trouble = 1 if min_clock < 30 else 0
            
            opening = game.get('opening', {})
            opening_eco = opening.get('eco', 'X')
            eco_category = opening_eco[0] if opening_eco else 'X'
            
            moves_str = game.get('moves', '')
            num_moves = len(moves_str.split()) // 2 if moves_str else 0
            
            processed.append({
                'player_rating': player_rating,
                'opponent_rating': opponent_rating,
                'rating_gap': opponent_rating - player_rating,
                'outcome_numeric': outcome_numeric,
                'player_color': player_color,
                'time_trouble': time_trouble,
                'eco_category': eco_category,
                'num_moves': num_moves
            })
            
        except Exception:
            continue
    
    return processed


def calculate_elo_expected(rating_diff):
    return 1 / (1 + 10 ** (rating_diff / 400))


def calculate_player_features(processed_games):
    if len(processed_games) < MIN_GAMES_REQUIRED:
        return None
    
    df = pd.DataFrame(processed_games)
    
    current_rating = df.iloc[0]['player_rating']
    
    form_5 = df.head(5)['outcome_numeric'].mean()
    form_10 = df.head(10)['outcome_numeric'].mean()
    form_20 = df.head(20)['outcome_numeric'].mean()
    
    streak = 0
    for outcome in df['outcome_numeric']:
        if outcome == 1:
            if streak >= 0:
                streak += 1
            else:
                streak = 1
        elif outcome == 0:
            if streak <= 0:
                streak -= 1
            else:
                streak = -1
        else:
            break
    
    time_trouble_rate = df['time_trouble'].mean()
    
    white_games = df[df['player_color'] == 'white']
    black_games = df[df['player_color'] == 'black']
    
    white_wr = white_games['outcome_numeric'].mean() if len(white_games) > 0 else 0.5
    black_wr = black_games['outcome_numeric'].mean() if len(black_games) > 0 else 0.5
    
    if len(df) >= 20:
        rating_trend = df.iloc[0]['player_rating'] - df.iloc[19]['player_rating']
    else:
        rating_trend = 0
    
    avg_game_length = df.head(20)['num_moves'].mean()
    
    eco_wrs = {}
    for eco_cat in ['A', 'B', 'C', 'D', 'E']:
        eco_games = df[df['eco_category'] == eco_cat]
        if len(eco_games) >= 3:
            eco_wrs[eco_cat] = eco_games['outcome_numeric'].mean()
        else:
            eco_wrs[eco_cat] = 0.5
    
    residuals = []
    for _, row in df.head(10).iterrows():
        expected = calculate_elo_expected(row['rating_gap'])
        residual = row['outcome_numeric'] - expected
        residuals.append(residual)
    residual_ma10 = np.mean(residuals) if residuals else 0
    
    games_last_7d = len(df)
    
    return {
        'rating': current_rating,
        'form_5': form_5,
        'form_10': form_10,
        'form_20': form_20,
        'streak': streak,
        'time_trouble_rate': time_trouble_rate,
        'white_wr': white_wr,
        'black_wr': black_wr,
        'rating_trend': rating_trend,
        'avg_game_length': avg_game_length,
        'eco_A_wr': eco_wrs['A'],
        'eco_B_wr': eco_wrs['B'],
        'eco_C_wr': eco_wrs['C'],
        'eco_D_wr': eco_wrs['D'],
        'eco_E_wr': eco_wrs['E'],
        'residual_ma10': residual_ma10,
        'games_last_7d': games_last_7d,
        'games_analyzed': len(df)
    }


def prepare_model_features(player_features, opponent_features, is_white):
    """
    Prepare features for the model including opponent and difference features.
    """
    rating_diff = opponent_features['rating'] - player_features['rating']
    elo_expected = calculate_elo_expected(rating_diff)
    
    # Player features (adjusted)
    form_5_adj = player_features['form_5'] - 0.5
    form_10_adj = player_features['form_10'] - 0.5
    form_20_adj = player_features['form_20'] - 0.5
    streak_norm = player_features['streak'] / 10
    time_management = 1 - player_features['time_trouble_rate']
    rating_trend_norm = player_features['rating_trend'] / 100
    
    if is_white:
        color_advantage = player_features['white_wr'] - 0.5
    else:
        color_advantage = player_features['black_wr'] - 0.5
    
    # Opponent features (adjusted)
    opp_form_5_adj = opponent_features['form_5'] - 0.5
    opp_form_10_adj = opponent_features['form_10'] - 0.5
    opp_streak_norm = opponent_features['streak'] / 10
    opp_time_management = 1 - opponent_features['time_trouble_rate']
    opp_rating_trend_norm = opponent_features['rating_trend'] / 100
    
    # Difference features
    form_5_diff = form_5_adj - opp_form_5_adj
    form_10_diff = form_10_adj - opp_form_10_adj
    streak_diff = streak_norm - opp_streak_norm
    time_mgmt_diff = time_management - opp_time_management
    residual_diff = player_features['residual_ma10'] - opponent_features['residual_ma10']
    
    features = {
        # Rating
        'rating_diff': rating_diff,
        'elo_expected': elo_expected,
        
        # Player features
        'form_5_adj': form_5_adj,
        'form_10_adj': form_10_adj,
        'form_20_adj': form_20_adj,
        'streak_norm': streak_norm,
        'time_management': time_management,
        'time_trouble_rate': player_features['time_trouble_rate'],
        'is_white': 1 if is_white else 0,
        'color_advantage': color_advantage,
        'rating_trend_norm': rating_trend_norm,
        'residual_ma10': player_features['residual_ma10'],
        'avg_game_length': player_features['avg_game_length'],
        'eco_A_wr': player_features['eco_A_wr'],
        'eco_B_wr': player_features['eco_B_wr'],
        'eco_C_wr': player_features['eco_C_wr'],
        'eco_D_wr': player_features['eco_D_wr'],
        'eco_E_wr': player_features['eco_E_wr'],
        
        # Opponent features
        'opp_form_5_adj': opp_form_5_adj,
        'opp_form_10_adj': opp_form_10_adj,
        'opp_streak_norm': opp_streak_norm,
        'opp_time_management': opp_time_management,
        'opp_rating_trend_norm': opp_rating_trend_norm,
        'opp_residual_ma10': opponent_features['residual_ma10'],
        'has_opponent_data': 1,
        
        # Difference features
        'form_5_diff': form_5_diff,
        'form_10_diff': form_10_diff,
        'streak_diff': streak_diff,
        'time_mgmt_diff': time_mgmt_diff,
        'residual_diff': residual_diff
    }
    
    return features


def predict_win_probability(model_package, player_a_features, player_b_features, a_is_white):
    """
    Predict win probability with ELO fallback for extreme rating differences.
    """
    rating_diff = abs(player_a_features['rating'] - player_b_features['rating'])
    
    # Prepare features for display (always needed)
    a_model_features = prepare_model_features(player_a_features, player_b_features, a_is_white)
    b_model_features = prepare_model_features(player_b_features, player_a_features, not a_is_white)
    
    # Fallback: Extreme rating difference → Use ELO baseline
    if rating_diff > ELO_FALLBACK_THRESHOLD:
        elo_prob_a = calculate_elo_expected(player_b_features['rating'] - player_a_features['rating'])
        elo_prob_b = 1 - elo_prob_a
        
        return elo_prob_a, elo_prob_b, a_model_features, b_model_features, True
    
    # Normal: Use ML model
    model = model_package['model']
    feature_columns = model_package.get('feature_columns', FEATURE_COLUMNS)
    
    a_input = np.array([[a_model_features[col] for col in feature_columns]])
    b_input = np.array([[b_model_features[col] for col in feature_columns]])
    
    prob_a = model.predict_proba(a_input)[0, 1]
    prob_b = model.predict_proba(b_input)[0, 1]
    
    total = prob_a + prob_b
    if total > 0:
        prob_a_normalized = prob_a / total
        prob_b_normalized = prob_b / total
    else:
        prob_a_normalized = 0.5
        prob_b_normalized = 0.5
    
    return prob_a_normalized, prob_b_normalized, a_model_features, b_model_features, False


def create_probability_bar(prob_a, prob_b, name_a, name_b):
    fig = go.Figure()
    
    # Use dynamic formatting for text
    text_a = format_probability(prob_a)
    text_b = format_probability(prob_b)
    
    fig.add_trace(go.Bar(
        y=['Win Probability'],
        x=[prob_a * 100],
        orientation='h',
        name=name_a,
        marker_color='#3498db',
        text=text_a,
        textposition='inside',
        textfont=dict(size=18, color='white')
    ))
    
    fig.add_trace(go.Bar(
        y=['Win Probability'],
        x=[prob_b * 100],
        orientation='h',
        name=name_b,
        marker_color='#e74c3c',
        text=text_b,
        textposition='inside',
        textfont=dict(size=18, color='white')
    ))
    
    fig.update_layout(
        barmode='stack',
        height=120,
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_gauge_chart(probability, player_name):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=probability * 100,
        number={'suffix': '%', 'font': {'size': 40}, 'valueformat': '.3f'},
        title={'text': f"{player_name}", 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#3498db"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': '#ffebee'},
                {'range': [30, 50], 'color': '#fff3e0'},
                {'range': [50, 70], 'color': '#e8f5e9'},
                {'range': [70, 100], 'color': '#c8e6c9'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=30, r=30, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_comparison_radar(features_a, features_b, name_a, name_b):
    categories = ['Form', 'Streak', 'Time Mgmt', 'Color Perf', 'Rating Trend']
    
    values_a = [
        (features_a['form_10_adj'] + 0.5) * 100,
        (features_a['streak_norm'] + 1) * 50,
        features_a['time_management'] * 100,
        (features_a['color_advantage'] + 0.5) * 100,
        (features_a['rating_trend_norm'] + 1) * 50
    ]
    
    values_b = [
        (features_b['form_10_adj'] + 0.5) * 100,
        (features_b['streak_norm'] + 1) * 50,
        features_b['time_management'] * 100,
        (features_b['color_advantage'] + 0.5) * 100,
        (features_b['rating_trend_norm'] + 1) * 50
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values_a + [values_a[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name=name_a,
        line_color='#3498db',
        fillcolor='rgba(52, 152, 219, 0.3)'
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=values_b + [values_b[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name=name_b,
        line_color='#e74c3c',
        fillcolor='rgba(231, 76, 60, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=True,
        height=350,
        margin=dict(l=60, r=60, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def get_factor_analysis(features_a, features_b, player_a_features, player_b_features, name_a, name_b):
    factors = []
    
    rating_diff = player_a_features['rating'] - player_b_features['rating']
    if abs(rating_diff) >= 20:
        advantage = name_a if rating_diff > 0 else name_b
        factors.append({
            'factor': 'Rating',
            'description': f"{advantage} has {abs(rating_diff):.0f} point rating advantage",
            'impact': 'High',
            'advantage': advantage
        })
    
    form_diff = features_a['form_10_diff']
    if abs(form_diff) >= 0.05:
        advantage = name_a if form_diff > 0 else name_b
        better_form = player_a_features['form_10'] if form_diff > 0 else player_b_features['form_10']
        factors.append({
            'factor': 'Recent Form',
            'description': f"{advantage} showing better form ({better_form*100:.0f}% last 10 games)",
            'impact': 'Medium',
            'advantage': advantage
        })
    
    streak_a = player_a_features['streak']
    streak_b = player_b_features['streak']
    if streak_a >= 3:
        factors.append({
            'factor': 'Win Streak',
            'description': f"{name_a} on a {streak_a} game winning streak",
            'impact': 'Medium',
            'advantage': name_a
        })
    elif streak_a <= -3:
        factors.append({
            'factor': 'Losing Streak',
            'description': f"{name_a} on a {abs(streak_a)} game losing streak",
            'impact': 'Medium',
            'advantage': name_b
        })
    if streak_b >= 3:
        factors.append({
            'factor': 'Win Streak',
            'description': f"{name_b} on a {streak_b} game winning streak",
            'impact': 'Medium',
            'advantage': name_b
        })
    elif streak_b <= -3:
        factors.append({
            'factor': 'Losing Streak',
            'description': f"{name_b} on a {abs(streak_b)} game losing streak",
            'impact': 'Medium',
            'advantage': name_a
        })
    
    time_diff = features_a['time_mgmt_diff']
    if abs(time_diff) >= 0.1:
        advantage = name_a if time_diff > 0 else name_b
        factors.append({
            'factor': 'Time Management',
            'description': f"{advantage} has better time management skills",
            'impact': 'Low',
            'advantage': advantage
        })
    
    if features_a['is_white'] == 1:
        white_player = name_a
        white_wr = player_a_features['white_wr']
    else:
        white_player = name_b
        white_wr = player_b_features['white_wr']
    
    if white_wr > 0.55:
        factors.append({
            'factor': 'Color Advantage',
            'description': f"{white_player} plays White with {white_wr*100:.0f}% win rate",
            'impact': 'Medium',
            'advantage': white_player
        })
    
    return factors[:5]


# Main App
st.title("Win Probability Predictor")
st.markdown("Predict the outcome of a chess match based on player statistics and machine learning.")

try:
    model_package = load_model()
    model_loaded = True
except FileNotFoundError:
    st.error(f"Model file not found at {MODEL_PATH}")
    model_loaded = False
except Exception as e:
    st.error(f"Error loading model: {str(e)}")
    model_loaded = False

if model_loaded:
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.subheader("Player A")
        player_a_username = st.text_input("Lichess Username", key="player_a", placeholder="e.g., Hikaru")
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>VS</h2>", unsafe_allow_html=True)
    
    with col3:
        st.subheader("Player B")
        player_b_username = st.text_input("Lichess Username", key="player_b", placeholder="e.g., DrNykterstein")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_white1, col_white2, col_white3 = st.columns([1, 2, 1])
    with col_white2:
        white_player = st.radio(
            "Who plays White?",
            options=["Player A", "Player B"],
            horizontal=True,
            index=0
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn2:
        calculate_button = st.button("Calculate Win Probability", type="primary", use_container_width=True)
    
    if calculate_button:
        if not player_a_username or not player_b_username:
            st.error("Please enter both usernames")
        elif player_a_username.lower() == player_b_username.lower():
            st.error("Please enter two different players")
        else:
            with st.spinner("Fetching player data..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text(f"Fetching games for {player_a_username}...")
                games_a, error_a = fetch_user_games(player_a_username, GAMES_TO_FETCH, GAME_TYPE)
                progress_bar.progress(25)
                
                if error_a:
                    st.error(f"Error fetching {player_a_username}: {error_a}")
                else:
                    status_text.text(f"Fetching games for {player_b_username}...")
                    games_b, error_b = fetch_user_games(player_b_username, GAMES_TO_FETCH, GAME_TYPE)
                    progress_bar.progress(50)
                    
                    if error_b:
                        st.error(f"Error fetching {player_b_username}: {error_b}")
                    else:
                        status_text.text("Processing games...")
                        
                        processed_a = process_games_for_player(games_a, player_a_username)
                        processed_b = process_games_for_player(games_b, player_b_username)
                        progress_bar.progress(75)
                        
                        player_a_features = calculate_player_features(processed_a)
                        player_b_features = calculate_player_features(processed_b)
                        
                        if player_a_features is None:
                            st.error(f"{player_a_username} doesn't have enough {GAME_TYPE} games (minimum {MIN_GAMES_REQUIRED})")
                        elif player_b_features is None:
                            st.error(f"{player_b_username} doesn't have enough {GAME_TYPE} games (minimum {MIN_GAMES_REQUIRED})")
                        else:
                            status_text.text("Calculating win probability...")
                            
                            a_is_white = (white_player == "Player A")
                            
                            prob_a, prob_b, model_features_a, model_features_b, used_fallback = predict_win_probability(
                                model_package,
                                player_a_features,
                                player_b_features,
                                a_is_white
                            )
                            
                            progress_bar.progress(100)
                            status_text.empty()
                            progress_bar.empty()
                            
                            # Show fallback warning if used
                            if used_fallback:
                                rating_diff = abs(player_a_features['rating'] - player_b_features['rating'])
                                st.warning(f"⚠️ Rating difference ({rating_diff:.0f}) exceeds {ELO_FALLBACK_THRESHOLD}. Using ELO baseline instead of ML model for more accurate prediction.")
                            
                            st.markdown("---")
                            st.subheader("Results")
                            
                            prob_fig = create_probability_bar(prob_a, prob_b, player_a_username, player_b_username)
                            st.plotly_chart(prob_fig, use_container_width=True)
                            
                            col_gauge1, col_gauge2 = st.columns(2)
                            
                            with col_gauge1:
                                gauge_a = create_gauge_chart(prob_a, player_a_username)
                                st.plotly_chart(gauge_a, use_container_width=True)
                            
                            with col_gauge2:
                                gauge_b = create_gauge_chart(prob_b, player_b_username)
                                st.plotly_chart(gauge_b, use_container_width=True)
                            
                            st.markdown("---")
                            st.subheader("Player Comparison")
                            
                            col_stats, col_radar = st.columns([1, 1])
                            
                            with col_stats:
                                comparison_data = {
                                    'Metric': [
                                        'Rating',
                                        'Recent Form (10 games)',
                                        'Current Streak',
                                        'Time Trouble Rate',
                                        'White Win Rate',
                                        'Black Win Rate',
                                        'Rating Trend (20 games)',
                                        'Games Analyzed'
                                    ],
                                    player_a_username: [
                                        f"{player_a_features['rating']:.0f}",
                                        f"{player_a_features['form_10']*100:.1f}%",
                                        f"{player_a_features['streak']:+d}",
                                        f"{player_a_features['time_trouble_rate']*100:.1f}%",
                                        f"{player_a_features['white_wr']*100:.1f}%",
                                        f"{player_a_features['black_wr']*100:.1f}%",
                                        f"{player_a_features['rating_trend']:+.0f}",
                                        f"{player_a_features['games_analyzed']}"
                                    ],
                                    player_b_username: [
                                        f"{player_b_features['rating']:.0f}",
                                        f"{player_b_features['form_10']*100:.1f}%",
                                        f"{player_b_features['streak']:+d}",
                                        f"{player_b_features['time_trouble_rate']*100:.1f}%",
                                        f"{player_b_features['white_wr']*100:.1f}%",
                                        f"{player_b_features['black_wr']*100:.1f}%",
                                        f"{player_b_features['rating_trend']:+.0f}",
                                        f"{player_b_features['games_analyzed']}"
                                    ]
                                }
                                
                                df_comparison = pd.DataFrame(comparison_data)
                                st.dataframe(df_comparison, use_container_width=True, hide_index=True)
                            
                            with col_radar:
                                radar_fig = create_comparison_radar(
                                    model_features_a, model_features_b,
                                    player_a_username, player_b_username
                                )
                                st.plotly_chart(radar_fig, use_container_width=True)
                            
                            st.markdown("---")
                            st.subheader("Key Factors")
                            
                            factors = get_factor_analysis(
                                model_features_a, model_features_b,
                                player_a_features, player_b_features,
                                player_a_username, player_b_username
                            )
                            
                            if factors:
                                for factor in factors:
                                    impact_color = {
                                        'High': '🔴',
                                        'Medium': '🟡',
                                        'Low': '🟢'
                                    }.get(factor['impact'], '⚪')
                                    
                                    advantage_color = '#3498db' if factor['advantage'] == player_a_username else '#e74c3c'
                                    
                                    st.markdown(f"""
                                    <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {advantage_color}; background-color: rgba(0,0,0,0.05); border-radius: 4px;'>
                                        <strong>{impact_color} {factor['factor']}</strong><br>
                                        {factor['description']}
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.info("Players are evenly matched based on available statistics.")
                            
                            st.markdown("---")
                            with st.expander("Model Information"):
                                model_metrics = model_package.get('metrics', {})
                                optimization_info = model_package.get('optimization', {})
                                
                                col_info1, col_info2 = st.columns(2)
                                
                                with col_info1:
                                    st.markdown("**Model Performance**")
                                    st.write(f"- ROC AUC: {model_metrics.get('optimized_auc', model_metrics.get('model_auc', 'N/A')):.4f}")
                                    st.write(f"- Accuracy: {model_metrics.get('accuracy', 'N/A'):.4f}")
                                    st.write(f"- Brier Score: {model_metrics.get('brier_score', 'N/A'):.4f}")
                                    st.write(f"- vs ELO: +{model_metrics.get('improvement_vs_elo', 0):.2f}%")
                                
                                with col_info2:
                                    st.markdown("**Model Details**")
                                    prediction_method = "ELO Baseline (fallback)" if used_fallback else "LightGBM (Optimized)"
                                    st.write(f"- Prediction Method: {prediction_method}")
                                    st.write(f"- Features: {len(FEATURE_COLUMNS)}")
                                    st.write(f"- Game Type: {GAME_TYPE}")
                                    st.write(f"- ELO Fallback Threshold: {ELO_FALLBACK_THRESHOLD}")
                                    if optimization_info:
                                        st.write(f"- Optuna Trials: {optimization_info.get('n_trials', 'N/A')}")