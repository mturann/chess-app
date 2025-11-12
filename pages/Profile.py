import streamlit as st 
import berserk
from datetime import datetime, timezone
import datetime as dt
import pandas as pd 
import plotly.graph_objs as go
import plotly.express as px
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token
from utils.cache_manager import fetch_profile_cached

st.set_page_config(page_title="Profile", page_icon="😎")

token = get_token()

# Get username from session or allow override
username = st.text_input(
    "Lichess Username", 
    value=get_username(),
    help="Leave empty to use saved username from session"
)

if username:
    set_username(username)

if st.button("Show Profile"):
    if username:
        profile = fetch_profile_cached(username, token)
        
        if profile:
            df = pd.DataFrame(profile["perfs"])
            df2 = df.loc["rating"]
            df3 = pd.DataFrame(df2)

            last_active = profile['seenAt']
            now = datetime.now(timezone.utc)
            active = int((now - last_active).total_seconds() // 60)

            col1, mid, col2, col3 = st.columns([1,1,12,10])
            with col1:
                st.image('lichess_logo.jpg', width=70)
            with col2:
                st.markdown(f'<span style="font-size: 36px;">{username}</span>', unsafe_allow_html=True)
            with col3:
                if active < 10:
                    st.markdown('<span style="font-size: 36px;">🟢 Online</span>', unsafe_allow_html=True)
                else: 
                    st.markdown(f'<span style="font-size: 36px;">🟠 {active} minutes ago</span>', unsafe_allow_html=True)

            st.markdown(f""" URL: 
            {profile["url"]}
            ***
            """)

            creation_time = 'Account created: {:%b %d, %Y}'.format(profile['createdAt'])
            st.markdown(f'<span style="font-size: 24px;">{creation_time}</span>', unsafe_allow_html=True)

            time_spent = str(dt.timedelta(seconds=profile['playTime']["total"]))
            st.markdown(f'<span style="font-size: 24px;">Total time on Lichess: {time_spent} 🕐</span>', unsafe_allow_html=True)
            st.markdown("***")

            st.title('Ratings')

            figure = go.Figure(data=[go.Bar(
                y=df3["rating"], 
                x=df3.index, 
                marker_color="green",
                text=df3["rating"],
                textposition='outside'
            )])
            figure.update_layout(
                title="Current Ratings by Game Type",
                xaxis_title="Game Type",
                yaxis_title="Rating",
                showlegend=False
            )
            st.plotly_chart(figure)

            stat = [profile["count"]["win"], profile["count"]["loss"], profile["count"]["draw"]]
            key = ["Wins", "Losses", "Draws"]

            fig = px.pie(
                values=stat, 
                names=key, 
                title=f'Total Games: {profile["count"]["all"]} | Wins: {profile["count"]["win"]} | Losses: {profile["count"]["loss"]} | Draws: {profile["count"]["draw"]}',
                color_discrete_sequence=px.colors.qualitative.Dark24, 
                width=800, 
                height=400
            )
            st.plotly_chart(fig)
        else:
            st.error("Could not fetch profile data. Please check username and try again.")
    else:
        st.warning("Please enter a Lichess username.")