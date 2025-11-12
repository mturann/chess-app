import pandas as pd 
import numpy as np 
import streamlit as st 
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.session_manager import init_session_state, set_username, get_username

st.set_page_config(
    page_title="About",
    page_icon="♟️",
)

# Initialize session state
init_session_state()

col1, mid, col2 = st.columns([1,1,20])
with col1:
    st.image('lichess_logo.jpg', width=70)
with col2:
    st.title('Analyze your Lichess Games')

st.write("Analyze the games you played on **Lichess**, learn your weaknesses, compare yourself with top-rated players and boost your rating.")

# Username input with session state
username = st.text_input(
    "Enter your Lichess username", 
    value=get_username(),
    key="main_username_input"
)

if username:
    set_username(username)
    st.success(f"Username '{username}' saved for this session!")

st.image('wallpaper.jpg')

st.info("Navigate to different pages using the sidebar to explore your chess statistics!")