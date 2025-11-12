import streamlit as st

def init_session_state():
    """Initialize session state variables"""
    if 'username' not in st.session_state:
        st.session_state.username = ''
    if 'token' not in st.session_state:
        st.session_state.token = None
    
def get_username():
    """Get username from session state"""
    init_session_state()
    return st.session_state.username

def set_username(username):
    """Set username in session state"""
    st.session_state.username = username
    
def get_token():
    """Get token from session state or environment"""
    import os
    if 'token' not in st.session_state or st.session_state.token is None:
        st.session_state.token = os.environ.get('LICHESS_TOKEN', '')
    return st.session_state.token