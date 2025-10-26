import streamlit as st 
import berserk
from datetime import datetime, timezone
import datetime as dt
import pandas as pd 
import plotly.graph_objs as go
import plotly.express as px
import os

st.set_page_config(page_title="Profile", page_icon="😎")

token = os.environ['LICHESS_TOKEN']

username = st.text_input("Your Lichess Username", "")

if st.button("Show Profile"):
    if username:
        try:
            session = berserk.TokenSession(token)
            client = berserk.Client(session=session)


            profile = client.users.get_public_data(username)

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
                    st.markdown('<span style="font-size: 36px;">🟢online</span>', unsafe_allow_html=True)
                else: 
                    st.markdown(f'<span style="font-size: 36px;">{active}🟠 minutes ago</span>', unsafe_allow_html=True)

            st.markdown(f""" URL: 
            {profile["url"]}
            ***
            """)

            creation_time = 'Your account is created at {:%b %d, %Y}'.format(profile['createdAt'])
            st.markdown(f'<span style="font-size: 24px;">{creation_time}</span>', unsafe_allow_html=True)

            time_spent = str(dt.timedelta(seconds=profile['playTime']["total"]))
            st.markdown(f'<span style="font-size: 24px;">Total Time Spent on **Lichess**: {time_spent}🕐</span>', unsafe_allow_html=True)
            st.markdown("***")

            st.title('Rating')

            figure = go.Figure(data=[go.Bar(y=df3["rating"], x=df3.index, marker_color="green")])
            st.plotly_chart(figure)

            stat = [profile["count"]["win"], profile["count"]["loss"],profile["count"]["draw"]]
            key = ["win", "lose","draw"]

            fig = px.pie(values=stat, names=key, title=f'Total Games Played: {profile["count"]["all"]} \t Win: {profile["count"]["win"]} \t Loss: {profile["count"]["loss"]}', 
            color_discrete_sequence=px.colors.qualitative.Dark24, width=800, height=400)

            st.plotly_chart(fig)

        except berserk.exceptions.ResponseError as e:
            st.error(f"Error fetching data: {e}")
    else:
        st.warning("Please enter your Lichess username above and click 'Show Profile'.")
