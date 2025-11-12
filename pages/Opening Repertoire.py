import streamlit as st
import berserk
import pandas as pd
import plotly.express as px
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token
from utils.cache_manager import fetch_user_games_cached

st.set_page_config(page_title="Opening Repertoire", page_icon="♟️")

token = get_token()

def process_games(games, username):
    games_data = []
    for game in games:
        players = game.get('players', {})
        is_white = players.get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
        color = 'white' if is_white else 'black'
        opponent_color = 'black' if is_white else 'white'
        winner = game.get('winner')
        outcome = 1 if winner == color else 0.5 if winner is None else 0
        opening = game.get('opening', {})
        game_data = {
            'opening_name': opening.get('name', 'Unknown'),
            'eco': opening.get('eco', 'Unknown'),
            'color': color,
            'outcome': outcome,
            'opponent_opening': opening.get('name', 'Unknown') if color == 'black' else None,
            'my_opening': opening.get('name', 'Unknown') if color == 'white' else None
        }
        games_data.append(game_data)
    df = pd.DataFrame(games_data)
    return df

def analyze_openings(df):
    most_played = df.groupby(['opening_name', 'color']).agg(
        games=('opening_name', 'size'),
        win_rate=('outcome', 'mean')
    ).reset_index()
    most_played['win_rate'] *= 100
    most_played = most_played.sort_values('games', ascending=False)

    struggling = most_played[most_played['games'] >= 5].sort_values('win_rate').head(10)

    vs_opponent = df[df['color'] == 'black'].groupby('opponent_opening').agg(
        games=('opponent_opening', 'size'),
        win_rate=('outcome', 'mean')
    ).reset_index()
    vs_opponent['win_rate'] *= 100
    vs_opponent = vs_opponent.sort_values('games', ascending=False)

    return most_played, struggling, vs_opponent

st.title("Opening Repertoire Analysis")

username = st.text_input("Lichess Username", value=get_username())

if username:
    set_username(username)

max_games = st.slider("Max Games to Analyze", 100, 2000, 1000)

if st.button("Analyze Openings"):
    if username:
        with st.spinner("Fetching and analyzing games..."):
            games = fetch_user_games_cached(username, token, max_games, 'all')
            
            if not games:
                st.error("No games fetched.")
                st.stop()
                
            df = process_games(games, username)
            most_played, struggling, vs_opponent = analyze_openings(df)

        st.subheader("Most Played Openings and Success Rates")
        fig_most = px.bar(most_played.head(20), x='opening_name', y='games', color='color',
                          hover_data=['win_rate'], title="Top Openings by Frequency")
        st.plotly_chart(fig_most)
        st.dataframe(most_played.head(20))

        st.subheader("Openings Where You Struggle (Low Win Rate)")
        fig_struggle = px.bar(struggling, x='opening_name', y='win_rate', color='color',
                              hover_data=['games'], title="Lowest Win Rate Openings (Min 5 Games)")
        st.plotly_chart(fig_struggle)
        st.dataframe(struggling)

        st.subheader("Performance Against Opponent's Openings (When You Play Black)")
        fig_vs = px.bar(vs_opponent.head(20), x='opponent_opening', y='win_rate', 
                        hover_data=['games'], title="Win Rate vs Opponent Openings")
        st.plotly_chart(fig_vs)
        st.dataframe(vs_opponent.head(20))
    else:
        st.warning("Enter username.")