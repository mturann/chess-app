import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_rating_history_cached(username):
    """Fetch and cache rating history"""
    url = f"https://lichess.org/api/user/{username}/rating-history"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return None
    return None

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def fetch_user_games_cached(username, token, max_games=1000, perf='all'):
    """Fetch and cache user games"""
    url = f"https://lichess.org/api/games/user/{username}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/x-ndjson"}
    params = {"max": max_games, "rated": "true", "pgnInJson": "true", 
              "clocks": "true", "opening": "true", "perf": perf}
    games = []
    try:
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=30)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                game = json.loads(line.decode('utf-8'))
                games.append(game)
    except Exception:
        pass
    return games

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_profile_cached(username, token):
    """Fetch and cache user profile"""
    import berserk
    try:
        session = berserk.TokenSession(token)
        client = berserk.Client(session=session)
        return client.users.get_public_data(username)
    except:
        return None