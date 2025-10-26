import streamlit as st
import requests
import chess
import chess.pgn
from io import StringIO
import chess.svg
import os 


token = os.environ['LICHESS_TOKEN']

def fetch_current_game_pgn(username, token):
    url = f"https://lichess.org/api/user/{username}/current-game"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/x-ches-pgn"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.text
    else:
        st.error(f"Error: {response.status_code} - {response.reason}")
        return None

def parse_pgn(pgn_text):
    game = chess.pgn.read_game(StringIO(pgn_text))
    headers = game.headers
    moves = [move.uci() for move in game.mainline_moves()]
    return headers, moves

def get_board_state(moves):
    board = chess.Board()
    for move in moves:
        board.push_uci(move)
    return board

def board_to_svg(board):
    return chess.svg.board(board, size=400)

st.title("Ongoing Game")


username = st.text_input("Lichess Username")

if st.button("Fetch Current Game"):
    if username:
        pgn = fetch_current_game_pgn(username, token)
        if pgn:
            headers, moves = parse_pgn(pgn)

            st.subheader("Game Details")
            st.write(f"**Event:** {headers.get('Event', 'N/A')}")
            st.write(f"**Site:** {headers.get('Site', 'N/A')}")
            st.write(f"**Date:** {headers.get('Date', 'N/A')}")
            st.write(f"**White Player:** {headers.get('White', 'N/A')}")
            st.write(f"**Black Player:** {headers.get('Black', 'N/A')}")
            st.write(f"**Result:** {headers.get('Result', 'N/A')}")
            st.write(f"**Opening:** {headers.get('Opening', 'N/A')}")
            st.write(f"**ECO:** {headers.get('ECO', 'N/A')}")

            board = get_board_state(moves)


            st.subheader("Current Chessboard")
            svg = board_to_svg(board)
            st.write(svg, unsafe_allow_html=True)

            st.subheader("Game Moves")
            st.write("\n".join(moves))
            
    else:
        st.warning("Please enter a username.")
