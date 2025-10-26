import berserk 
import pandas as pd 
import matplotlib.pyplot as plt 
import seaborn as sns
import plotly.graph_objs as go
from plotly.offline import iplot
import streamlit as st 
import os

st.set_page_config(page_title="Top Players", page_icon="👑")

st.title("Top Players on Lichess 👑")


token = os.environ['LICHESS_TOKEN']
session = berserk.TokenSession(token)
client = berserk.Client(session=session)

top10 = client.users.get_all_top_10()

def top10_players(top10):
    rating = []
    username_ = []
    new_dict = {}
    df_list = []
    m = 0

    top_list = list(top10.keys())
    for i in range(0,len(top_list)):
        for k in range(0,10):
            rating.append(top10[top_list[i]][k]["perfs"][top_list[i]]["rating"])
            username_.append(top10[top_list[i]][k]["username"])
            if len(rating)%10==0:
                new_dict[top_list[i]] = [rating[m*10:(m+1)*10],username_[m*10:(m+1)*10]]
                m += 1

    for i in range(0,len(top_list)):
        df_list.append(pd.DataFrame(index=new_dict[top_list[i]][1:][0], data=new_dict[top_list[i]][:1][0], columns=[top_list[i]]))

    return df_list  

df_list = top10_players(top10)

def get_column_names(df_list):
    column_names = set()
    for df in df_list:
        column_names.update(df.columns)
    return sorted(column_names)

selected_columns = st.multiselect('Select Game Type', options=get_column_names(df_list))

for df in df_list:
    for column in selected_columns:
        if column in df.columns:
            sorted_df = df.sort_values(by=column, ascending=True)
            
            figure = go.Figure(data=[go.Bar(y=sorted_df.index, x=sorted_df[column], name=column, orientation='h', marker_color="red")])
            figure.update_layout(title=str(f"{column}").upper())
            st.plotly_chart(figure)