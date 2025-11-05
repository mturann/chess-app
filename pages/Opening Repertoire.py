import streamlit as st
import berserk
import pandas as pd
import plotly.express as px
import os
import json
import requests

st.set_page_config(page_title="Opening Repertoire", page_icon="♟️")

token = os.environ['LICHESS_TOKEN']

def fetch_user_games(username, token, max_games=1000):
    url = f"https://lichess.org/api/games/user/{username}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/x-ndjson"}
    params = {"max": max_games, "rated": "true", "pgnInJson": "true", "opening": "true", "perf": "all"}  # All perf types for broad analysis
    games = []
    try:
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=30)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                game = json.loads(line.decode('utf-8'))
                games.append(game)
        st.info(f"Fetched {len(games)} games")
    except Exception as e:
        st.warning(f"Could not fetch games: {e}")
    return games

def process_games(games, username):
    games_data = []
    for game in games:
        players = game.get('players', {})
        is_white = players.get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
        color = 'white' if is_white else 'black'
        opponent_color = 'black' if is_white else 'white'
        winner = game.get('winner')
        outcome = 1 if winner == color else 0.5 if winner is None else 0  # 1=win, 0.5=draw, 0=loss
        opening = game.get('opening', {})
        game_data = {
            'opening_name': opening.get('name', 'Unknown'),
            'eco': opening.get('eco', 'Unknown'),
            'color': color,
            'outcome': outcome,
            'opponent_opening': opening.get('name', 'Unknown') if color == 'black' else None,  # When black, opponent's opening
            'my_opening': opening.get('name', 'Unknown') if color == 'white' else None  # When white, my opening
        }
        games_data.append(game_data)
    df = pd.DataFrame(games_data)
    return df

def analyze_openings(df):
    # Most played openings and success rates
    most_played = df.groupby(['opening_name', 'color']).agg(
        games=('opening_name', 'size'),
        win_rate=('outcome', 'mean')
    ).reset_index()
    most_played['win_rate'] *= 100  # To percentage
    most_played = most_played.sort_values('games', ascending=False)

    # Openings where struggling (low win rate, min 5 games)
    struggling = most_played[most_played['games'] >= 5].sort_values('win_rate').head(10)

    # Performance against opponent's openings (when I'm black)
    vs_opponent = df[df['color'] == 'black'].groupby('opponent_opening').agg(
        games=('opponent_opening', 'size'),
        win_rate=('outcome', 'mean')
    ).reset_index()
    vs_opponent['win_rate'] *= 100
    vs_opponent = vs_opponent.sort_values('games', ascending=False)

    return most_played, struggling, vs_opponent

st.title("Opening Repertoire Analysis")

username = st.text_input("Lichess Username", value="")
max_games = st.slider("Max Games to Analyze", 100, 2000, 1000)

if st.button("Analyze Openings"):
    if username:
        with st.spinner("Fetching and analyzing games..."):
            games = fetch_user_games(username, token, max_games)
            if not games:
                st.error("No games fetched.")
                st.stop()
            df = process_games(games, username)
            most_played, struggling, vs_opponent = analyze_openings(df)

        # Most played openings
        st.subheader("Most Played Openings and Success Rates")
        fig_most = px.bar(most_played.head(20), x='opening_name', y='games', color='color',
                          hover_data=['win_rate'], title="Top Openings by Frequency")
        st.plotly_chart(fig_most)
        st.dataframe(most_played.head(20))

        # Struggling openings
        st.subheader("Openings Where You Struggle (Low Win Rate)")
        fig_struggle = px.bar(struggling, x='opening_name', y='win_rate', color='color',
                              hover_data=['games'], title="Lowest Win Rate Openings (Min 5 Games)")
        st.plotly_chart(fig_struggle)
        st.dataframe(struggling)

        # Vs opponent openings
        st.subheader("Performance Against Opponent's Openings (When You Play Black)")
        fig_vs = px.bar(vs_opponent.head(20), x='opponent_opening', y='win_rate', 
                        hover_data=['games'], title="Win Rate vs Opponent Openings")
        st.plotly_chart(fig_vs)
        st.dataframe(vs_opponent.head(20))
    else:
        st.warning("Enter username.")