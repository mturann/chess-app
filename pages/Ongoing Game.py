import streamlit as st
import requests
import chess
import chess.pgn
from io import StringIO
import chess.svg
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token

st.set_page_config(
    page_title="Game Viewer",
    page_icon="🎮",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .game-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px 0;
    }
    .player-white {
        background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);
        padding: 15px;
        border-radius: 10px;
        color: #1a1a2e;
        text-align: center;
        border: 2px solid #ccc;
    }
    .player-black {
        background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
        border: 2px solid #444;
    }
    .move-current {
        background-color: #4CAF50;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .move-item {
        padding: 2px 6px;
        margin: 1px;
        display: inline-block;
        cursor: pointer;
        border-radius: 3px;
        color: #f0f0f0;
    }
    .move-item:hover {
        background-color: #444;
    }
    .info-box {
        background: #2d2d2d;
        padding: 10px 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 5px 0;
        color: #f0f0f0;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

token = get_token()

def fetch_current_game_pgn(username, token):
    """Fetch current ongoing game"""
    url = f"https://lichess.org/api/user/{username}/current-game"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/x-chess-pgn"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text, None
        elif response.status_code == 404:
            return None, "No ongoing game found for this user"
        else:
            return None, f"Error: {response.status_code} - {response.reason}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def fetch_recent_game_pgn(username, token):
    """Fetch most recent game if no ongoing game"""
    url = f"https://lichess.org/api/games/user/{username}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/x-chess-pgn"
    }
    params = {"max": 1, "pgnInJson": False}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.text, None
        else:
            return None, f"Error fetching recent game"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def parse_pgn(pgn_text):
    """Parse PGN and extract game info"""
    game = chess.pgn.read_game(StringIO(pgn_text))
    if game is None:
        return None, None, None
    
    headers = dict(game.headers)
    
    # Get moves in both UCI and SAN format
    moves_uci = []
    moves_san = []
    board = chess.Board()
    
    for move in game.mainline_moves():
        moves_san.append(board.san(move))
        moves_uci.append(move.uci())
        board.push(move)
    
    return headers, moves_uci, moves_san

def get_board_at_move(moves_uci, move_index):
    """Get board state at specific move index"""
    board = chess.Board()
    for i in range(move_index):
        if i < len(moves_uci):
            board.push_uci(moves_uci[i])
    return board

def board_to_svg(board, last_move=None, size=400):
    """Convert board to SVG with optional last move highlight"""
    return chess.svg.board(
        board, 
        size=size,
        lastmove=last_move,
        colors={
            'square light': '#f0d9b5',
            'square dark': '#b58863',
            'margin': '#212121',
            'coord': '#e0e0e0'
        }
    )

def format_moves_display(moves_san, current_index):
    """Format moves for display with current move highlighted"""
    html = '<div style="font-family: monospace; line-height: 2; color: #f0f0f0;">'
    
    for i in range(0, len(moves_san), 2):
        move_num = i // 2 + 1
        html += f'<span style="color: #aaa; margin-right: 5px;">{move_num}.</span>'
        
        # White's move
        if current_index == i + 1:
            html += f'<span class="move-current">{moves_san[i]}</span> '
        else:
            html += f'<span class="move-item">{moves_san[i]}</span> '
        
        # Black's move
        if i + 1 < len(moves_san):
            if current_index == i + 2:
                html += f'<span class="move-current">{moves_san[i+1]}</span> '
            else:
                html += f'<span class="move-item">{moves_san[i+1]}</span> '
        
        html += '&nbsp;&nbsp;'
    
    html += '</div>'
    return html

# Title
st.markdown("""
<h1 style="text-align: center;">🎮 Game Viewer</h1>
<p style="text-align: center; color: #888;">Watch ongoing games or replay recent games move by move</p>
""", unsafe_allow_html=True)

st.markdown("---")

# Initialize session state
if 'game_loaded' not in st.session_state:
    st.session_state.game_loaded = False
if 'current_move' not in st.session_state:
    st.session_state.current_move = 0
if 'moves_uci' not in st.session_state:
    st.session_state.moves_uci = []
if 'moves_san' not in st.session_state:
    st.session_state.moves_san = []
if 'headers' not in st.session_state:
    st.session_state.headers = {}

# Sidebar controls
with st.sidebar:
    st.header("🔍 Load Game")
    
    username = st.text_input("Lichess Username", value=get_username())
    
    if username:
        set_username(username)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fetch_ongoing = st.button("🔴 Live Game", use_container_width=True)
    with col2:
        fetch_recent = st.button("📜 Last Game", use_container_width=True)
    
    if fetch_ongoing or fetch_recent:
        if username:
            with st.spinner("Fetching game..."):
                if fetch_ongoing:
                    pgn, error = fetch_current_game_pgn(username, token)
                else:
                    pgn, error = fetch_recent_game_pgn(username, token)
                
                if pgn:
                    headers, moves_uci, moves_san = parse_pgn(pgn)
                    if headers:
                        st.session_state.headers = headers
                        st.session_state.moves_uci = moves_uci
                        st.session_state.moves_san = moves_san
                        st.session_state.current_move = len(moves_uci)  # Start at final position
                        st.session_state.game_loaded = True
                        st.success(f"✅ Loaded {len(moves_uci)} moves")
                    else:
                        st.error("Could not parse game")
                else:
                    st.error(error or "Could not fetch game")
        else:
            st.warning("Enter a username")
    
    if st.session_state.game_loaded:
        st.markdown("---")
        st.header("🎛️ Navigation")
        
        # Navigation buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("⏮️", help="First move"):
                st.session_state.current_move = 0
        with col2:
            if st.button("◀️", help="Previous move"):
                if st.session_state.current_move > 0:
                    st.session_state.current_move -= 1
        with col3:
            if st.button("▶️", help="Next move"):
                if st.session_state.current_move < len(st.session_state.moves_uci):
                    st.session_state.current_move += 1
        with col4:
            if st.button("⏭️", help="Last move"):
                st.session_state.current_move = len(st.session_state.moves_uci)
        
        # Move slider
        st.session_state.current_move = st.slider(
            "Move",
            0, 
            len(st.session_state.moves_uci),
            st.session_state.current_move,
            help="Drag to navigate through the game"
        )
        
        # Current position info
        total = len(st.session_state.moves_uci)
        current = st.session_state.current_move
        
        if current == 0:
            st.info("📍 Starting position")
        else:
            move_num = (current + 1) // 2
            color = "White" if current % 2 == 1 else "Black"
            st.info(f"📍 Move {move_num}. {color}: {st.session_state.moves_san[current-1]}")

# Main content
if st.session_state.game_loaded:
    headers = st.session_state.headers
    
    # Player cards
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        white_rating = headers.get('WhiteElo', '?')
        st.markdown(f"""
        <div class="player-white">
            <div style="font-size: 2rem;">♔</div>
            <div style="font-size: 1.2rem; font-weight: bold;">{headers.get('White', 'White')}</div>
            <div style="font-size: 1rem; color: #666;">Rating: {white_rating}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding-top: 20px;">
            <div style="font-size: 1.5rem; font-weight: bold;">VS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        black_rating = headers.get('BlackElo', '?')
        st.markdown(f"""
        <div class="player-black">
            <div style="font-size: 2rem;">♚</div>
            <div style="font-size: 1.2rem; font-weight: bold;">{headers.get('Black', 'Black')}</div>
            <div style="font-size: 1rem; color: #aaa;">Rating: {black_rating}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Board and moves
    col_board, col_info = st.columns([3, 2])
    
    with col_board:
        # Get board at current position
        board = get_board_at_move(st.session_state.moves_uci, st.session_state.current_move)
        
        # Get last move for highlighting
        last_move = None
        if st.session_state.current_move > 0:
            move_uci = st.session_state.moves_uci[st.session_state.current_move - 1]
            last_move = chess.Move.from_uci(move_uci)
        
        # Display board
        svg = board_to_svg(board, last_move, size=450)
        st.markdown(f"""
        <div style="display: flex; justify-content: center;">
            {svg}
        </div>
        """, unsafe_allow_html=True)
        
        # Keyboard hint
        st.caption("💡 Use the slider or buttons in the sidebar to navigate moves")
    
    with col_info:
        # Game info
        st.markdown("### 📋 Game Info")
        
        result = headers.get('Result', '*')
        result_text = {
            '1-0': '⚪ White wins',
            '0-1': '⚫ Black wins',
            '1/2-1/2': '🤝 Draw',
            '*': '🔴 In progress'
        }.get(result, result)
        
        st.markdown(f"""
        <div class="info-box">
            <strong>Result:</strong> {result_text}
        </div>
        """, unsafe_allow_html=True)
        
        if headers.get('Opening'):
            st.markdown(f"""
            <div class="info-box">
                <strong>Opening:</strong> {headers.get('Opening', 'N/A')}<br>
                <small>ECO: {headers.get('ECO', 'N/A')}</small>
            </div>
            """, unsafe_allow_html=True)
        
        if headers.get('TimeControl'):
            st.markdown(f"""
            <div class="info-box">
                <strong>Time Control:</strong> {headers.get('TimeControl', 'N/A')}
            </div>
            """, unsafe_allow_html=True)
        
        if headers.get('Date'):
            st.markdown(f"""
            <div class="info-box">
                <strong>Date:</strong> {headers.get('Date', 'N/A')}
            </div>
            """, unsafe_allow_html=True)
        
        # Link to game
        site = headers.get('Site', '')
        if 'lichess.org' in site:
            st.markdown(f"[🔗 View on Lichess]({site})")
        
        # Moves display
        st.markdown("### 📝 Moves")
        
        moves_html = format_moves_display(
            st.session_state.moves_san, 
            st.session_state.current_move
        )
        
        st.markdown(f"""
        <div style="max-height: 300px; overflow-y: auto; padding: 10px; background: #2d2d2d; border-radius: 10px; color: #f0f0f0;">
            {moves_html}
        </div>
        """, unsafe_allow_html=True)

else:
    # Welcome screen when no game loaded
    st.markdown("""
    <div style="text-align: center; padding: 50px;">
        <div style="font-size: 4rem;">♟️</div>
        <h2>No game loaded</h2>
        <p style="color: #888;">
            Enter a Lichess username in the sidebar and click:<br><br>
            <strong>🔴 Live Game</strong> - Watch an ongoing game<br>
            <strong>📜 Last Game</strong> - Replay the most recent game
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Use ◀️ ▶️ buttons or the slider to navigate through moves")