import streamlit as st
import berserk
import datetime as dt
import pandas as pd
import plotly.express as px
import calendar
import os

st.set_page_config(page_title="Rating History", page_icon="📕")

token = os.environ['LICHESS_TOKEN']

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
                if hasattr(point, 'year') and hasattr(point, 'month') and hasattr(point, 'day') and hasattr(point, 'rating'):
                    year = point.year
                    month = point.month if 1 <= point.month <= 12 else 1
                    max_days = calendar.monthrange(year, month)[1]
                    day = point.day if 1 <= point.day <= max_days else 1
                    date = dt.datetime(year, month, day)
                    games.append([item["name"], date, point.rating])
    df = pd.DataFrame(games, columns=["game_type", "date", "ratings"])
    return df


def making_visualizations(df, selected_game_types):
    df_sorted = df.sort_values(by='date')
    fig = px.line(df_sorted[df_sorted['game_type'].isin(selected_game_types)], x='date', y='ratings', color='game_type',
                  markers=True, title='Ratings Over Time for Selected Game Types')
    fig.update_layout(xaxis_title='Date', yaxis_title='Ratings')
    fig.update_traces(mode='lines+markers')
    st.plotly_chart(fig)

username = st.text_input("Your Lichess Username", "")

if st.button("Show Profile"):
    if username:
        try:
            session = berserk.TokenSession(token)
            client = berserk.Client(session=session)
            profile = client.users.get_rating_history(username)
            game_types = creating_game_types(profile)
            selected_game_types = st.multiselect("Select Game Types", game_types, default=game_types[:])
            df = creating_rating_data(profile)
            if not selected_game_types:
                st.warning("Please select at least one game type.")
            else:
                making_visualizations(df, selected_game_types)
        except berserk.exceptions.ResponseError as e:
            st.error(f"Error fetching data: {e}")
    else:
        st.warning("Please enter your Lichess username above and click 'Show Profile'.")
