import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt 
import seaborn as sns 
from PIL import Image
import streamlit as st 

st.set_page_config(
    page_title="About",
    page_icon="♟️",
)

col1, mid, col2 = st.columns([1,1,20])
with col1:
    st.image('lichess_logo.jpg', width=70)
with col2:
    st.title(' Analyze your Lichess Games')

st.write("Analyze the games you played on **Lichess**, learn your weaknesses, compare yourself with top-rated players and boost your rating.")

st.image('wallpaper.jpg')
