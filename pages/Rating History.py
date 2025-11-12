import streamlit as st
import berserk
import datetime as dt
import pandas as pd
import plotly.express as px
import calendar
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token
from utils.cache_manager import fetch_rating_history_cached

st.set_page_config(page_title="Rating History", page_icon="📕")

token = get_token()

def creating_game_types(top10):
    game_types = []
    for item in top10:
        if isinstance(item, dict) and "name" in item:
            game_types.append(item["name"])
    return game_types

def creating_rating_data(data):
    games = []
    for item in data:
        if isinstance(item, dict) and "points" in item and isinstance(item["points"], list):
            for point in item["points"]:
                if len(point) >= 4:
                    year = point[0]
                    month = point[1] + 1
                    month = max(1, min(12, month))
                    max_days = calendar.monthrange(year, month)[1]
                    day = point[2] if 1 <= point[2] <= max_days else 1
                    date = dt.datetime(year, month, day)
                    rating = point[3]
                    games.append([item["name"], date, rating])
    df = pd.DataFrame(games, columns=["game_type", "date", "ratings"])
    return df

def making_visualizations(df, selected_game_types):
    df_sorted = df.sort_values(by='date')
    fig = px.line(df_sorted[df_sorted['game_type'].isin(selected_game_types)], x='date', y='ratings', color='game_type',
                  markers=True, title='Ratings Over Time for Selected Game Types')
    fig.update_layout(xaxis_title='Date', yaxis_title='Ratings')
    fig.update_traces(mode='lines+markers')
    st.plotly_chart(fig)

username = st.text_input("Lichess Username", value=get_username())

if username:
    set_username(username)

if st.button("Show Rating History"):
    if username:
        try:
            profile = fetch_rating_history_cached(username)
            
            if profile:
                game_types = creating_game_types(profile)
                selected_game_types = st.multiselect("Select Game Types", game_types, default=game_types[:3])
                df = creating_rating_data(profile)
                
                if not selected_game_types:
                    st.warning("Please select at least one game type.")
                elif not df.empty:
                    making_visualizations(df, selected_game_types)
                else:
                    st.warning("No rating data available for this user.")
            else:
                st.error("Could not fetch rating history. Please check the username.")
                
        except Exception as e:
            st.error(f"Error fetching data: {e}")
    else:
        st.warning("Please enter a Lichess username.")