import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from collections import defaultdict
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.session_manager import get_username, set_username, get_token

st.set_page_config(page_title="Opening Coach", page_icon="📚", layout="wide")

# Custom CSS
st.markdown("""
<style>
    /* Opening cards */
    .opening-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        border-left: 4px solid #667eea;
    }
    .opening-card-good {
        border-left-color: #4CAF50;
    }
    .opening-card-bad {
        border-left-color: #f44336;
    }
    .opening-card-neutral {
        border-left-color: #ff9800;
    }
    .opening-name {
        font-size: 1.2rem;
        font-weight: bold;
        color: #f0f0f0;
        margin-bottom: 10px;
    }
    .opening-stats {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .opening-stat {
        text-align: center;
    }
    .opening-stat-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #667eea;
    }
    .opening-stat-label {
        font-size: 0.8rem;
        color: #aaa;
    }
    
    /* ECO badges */
    .eco-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 8px;
    }
    .eco-A { background: #e91e63; color: white; }
    .eco-B { background: #9c27b0; color: white; }
    .eco-C { background: #3f51b5; color: white; }
    .eco-D { background: #009688; color: white; }
    .eco-E { background: #ff9800; color: white; }
    .eco-other { background: #607d8b; color: white; }
    
    /* Win rate bar */
    .winrate-bar {
        height: 8px;
        background: #333;
        border-radius: 4px;
        overflow: hidden;
        margin: 10px 0;
    }
    .winrate-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    
    /* Trend indicators */
    .trend-up { color: #4CAF50; }
    .trend-down { color: #f44336; }
    .trend-neutral { color: #ff9800; }
    
    /* Recommendation card */
    .recommendation-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px 0;
    }
    .recommendation-title {
        font-size: 1.1rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    
    /* Resource card */
    .resource-card {
        background: #2d2d2d;
        padding: 15px;
        border-radius: 10px;
        margin: 8px 0;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .resource-icon {
        font-size: 2rem;
    }
    .resource-info {
        flex-grow: 1;
    }
    .resource-title {
        color: #f0f0f0;
        font-weight: bold;
    }
    .resource-desc {
        color: #aaa;
        font-size: 0.85rem;
    }
    .resource-link {
        color: #667eea;
        text-decoration: none;
    }
    
    /* Stats highlight */
    .stat-highlight {
        background: #2d2d2d;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .stat-highlight-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-highlight-label {
        color: #aaa;
        font-size: 0.85rem;
    }
    
    /* Comparison table */
    .comparison-better { color: #4CAF50; font-weight: bold; }
    .comparison-worse { color: #f44336; }
    
    /* Section header */
    .section-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 15px 20px;
        border-radius: 10px;
        margin: 20px 0 15px 0;
        border-left: 4px solid #667eea;
    }
    .section-title {
        color: #f0f0f0;
        font-size: 1.3rem;
        font-weight: bold;
        margin: 0;
    }
    
    /* Quiz card */
    .quiz-card {
        background: #1e1e1e;
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        border: 2px solid #333;
    }
    .quiz-correct { border-color: #4CAF50; background: rgba(76, 175, 80, 0.1); }
    .quiz-incorrect { border-color: #f44336; background: rgba(244, 67, 54, 0.1); }
</style>
""", unsafe_allow_html=True)

# Expanded Opening Database
OPENING_DATABASE = {
    # e4 openings
    "Italian Game": {
        "eco": ["C50", "C51", "C52", "C53", "C54"],
        "key_moves": "1.e4 e5 2.Nf3 Nc6 3.Bc4",
        "color": "white",
        "style": "positional",
        "difficulty": "beginner",
        "description": "A classic opening focusing on rapid development and control of the center.",
        "alternatives": ["Spanish Opening", "Scotch Game", "Vienna Game"],
        "study_links": [
            {"name": "Italian Game Basics", "url": "https://lichess.org/study/iQ4URVCR"},
            {"name": "Giuoco Piano Deep Dive", "url": "https://lichess.org/study/zpLwJLvM"}
        ],
        "video_keywords": "Italian Game chess opening tutorial",
        "master_games": "https://lichess.org/games/search?opening=C50"
    },
    "Sicilian Defense": {
        "eco": ["B20", "B21", "B22", "B23", "B27", "B28", "B29", "B30", "B40", "B50", "B60", "B70", "B80", "B90"],
        "key_moves": "1.e4 c5",
        "color": "black",
        "style": "aggressive",
        "difficulty": "intermediate",
        "description": "The most popular response to 1.e4, leading to sharp, unbalanced positions.",
        "alternatives": ["French Defense", "Caro-Kann Defense", "Pirc Defense"],
        "study_links": [
            {"name": "Sicilian Overview", "url": "https://lichess.org/study/CmhHXNFD"},
            {"name": "Najdorf Variation", "url": "https://lichess.org/study/MYCzx5wX"},
            {"name": "Dragon Variation", "url": "https://lichess.org/study/DragonSicilian"}
        ],
        "video_keywords": "Sicilian Defense chess tutorial Najdorf Dragon",
        "master_games": "https://lichess.org/games/search?opening=B20"
    },
    "French Defense": {
        "eco": ["C00", "C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C19"],
        "key_moves": "1.e4 e6",
        "color": "black",
        "style": "solid",
        "difficulty": "intermediate",
        "description": "A solid defense that fights for the center with pawns, leading to strategic play.",
        "alternatives": ["Caro-Kann Defense", "Sicilian Defense", "Scandinavian Defense"],
        "study_links": [
            {"name": "French Defense Basics", "url": "https://lichess.org/study/zo5n3R8A"},
            {"name": "Winawer Variation", "url": "https://lichess.org/study/4UlQr0Cc"}
        ],
        "video_keywords": "French Defense chess opening Winawer Tarrasch",
        "master_games": "https://lichess.org/games/search?opening=C00"
    },
    "Caro-Kann Defense": {
        "eco": ["B10", "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18", "B19"],
        "key_moves": "1.e4 c6",
        "color": "black",
        "style": "solid",
        "difficulty": "beginner",
        "description": "A very solid defense that avoids many tactical complications.",
        "alternatives": ["French Defense", "Sicilian Defense", "Scandinavian Defense"],
        "study_links": [
            {"name": "Caro-Kann Fundamentals", "url": "https://lichess.org/study/gvdMFCPy"},
            {"name": "Advance Variation", "url": "https://lichess.org/study/OxKnt3u5"}
        ],
        "video_keywords": "Caro Kann Defense chess opening advance variation",
        "master_games": "https://lichess.org/games/search?opening=B10"
    },
    "Spanish Opening": {
        "eco": ["C60", "C61", "C62", "C63", "C64", "C65", "C66", "C67", "C68", "C69", "C70", "C71", "C72", "C73", "C74", "C75", "C76", "C77", "C78", "C79", "C80", "C81", "C82", "C83", "C84", "C85", "C86", "C87", "C88", "C89", "C90", "C91", "C92", "C93", "C94", "C95", "C96", "C97", "C98", "C99"],
        "key_moves": "1.e4 e5 2.Nf3 Nc6 3.Bb5",
        "color": "white",
        "style": "positional",
        "difficulty": "intermediate",
        "description": "One of the oldest and most respected openings, offering long-term pressure.",
        "alternatives": ["Italian Game", "Scotch Game", "Vienna Game"],
        "study_links": [
            {"name": "Ruy Lopez Basics", "url": "https://lichess.org/study/d9OPX3eo"},
            {"name": "Berlin Defense", "url": "https://lichess.org/study/Graj4QRL"},
            {"name": "Marshall Attack", "url": "https://lichess.org/study/MarshallAttack"}
        ],
        "video_keywords": "Spanish Opening Ruy Lopez Berlin Marshall",
        "master_games": "https://lichess.org/games/search?opening=C60"
    },
    "Scotch Game": {
        "eco": ["C44", "C45"],
        "key_moves": "1.e4 e5 2.Nf3 Nc6 3.d4",
        "color": "white",
        "style": "aggressive",
        "difficulty": "beginner",
        "description": "An open game that immediately challenges Black's center.",
        "alternatives": ["Italian Game", "Spanish Opening", "Vienna Game"],
        "study_links": [
            {"name": "Scotch Game Guide", "url": "https://lichess.org/study/ScotchGame"}
        ],
        "video_keywords": "Scotch Game chess opening tutorial",
        "master_games": "https://lichess.org/games/search?opening=C45"
    },
    "Vienna Game": {
        "eco": ["C25", "C26", "C27", "C28", "C29"],
        "key_moves": "1.e4 e5 2.Nc3",
        "color": "white",
        "style": "aggressive",
        "difficulty": "intermediate",
        "description": "A flexible opening that can transpose into many systems.",
        "alternatives": ["Italian Game", "Scotch Game", "King's Gambit"],
        "study_links": [
            {"name": "Vienna Game Intro", "url": "https://lichess.org/study/ViennaGame"}
        ],
        "video_keywords": "Vienna Game chess opening",
        "master_games": "https://lichess.org/games/search?opening=C25"
    },
    "King's Gambit": {
        "eco": ["C30", "C31", "C32", "C33", "C34", "C35", "C36", "C37", "C38", "C39"],
        "key_moves": "1.e4 e5 2.f4",
        "color": "white",
        "style": "aggressive",
        "difficulty": "advanced",
        "description": "A romantic opening sacrificing a pawn for rapid development and attack.",
        "alternatives": ["Italian Game", "Scotch Game", "Vienna Game"],
        "study_links": [
            {"name": "King's Gambit Accepted", "url": "https://lichess.org/study/KingsGambit"}
        ],
        "video_keywords": "Kings Gambit chess opening attacking",
        "master_games": "https://lichess.org/games/search?opening=C30"
    },
    "Pirc Defense": {
        "eco": ["B07", "B08", "B09"],
        "key_moves": "1.e4 d6 2.d4 Nf6 3.Nc3 g6",
        "color": "black",
        "style": "hypermodern",
        "difficulty": "intermediate",
        "description": "A flexible hypermodern defense that allows White to build a center before challenging it.",
        "alternatives": ["Modern Defense", "Sicilian Defense", "Alekhine Defense"],
        "study_links": [
            {"name": "Pirc Defense Guide", "url": "https://lichess.org/study/PircDefense"}
        ],
        "video_keywords": "Pirc Defense chess opening",
        "master_games": "https://lichess.org/games/search?opening=B07"
    },
    "Scandinavian Defense": {
        "eco": ["B01"],
        "key_moves": "1.e4 d5",
        "color": "black",
        "style": "solid",
        "difficulty": "beginner",
        "description": "An easy-to-learn defense that immediately challenges White's e4 pawn.",
        "alternatives": ["Caro-Kann Defense", "French Defense", "Alekhine Defense"],
        "study_links": [
            {"name": "Scandinavian Basics", "url": "https://lichess.org/study/Scandinavian"}
        ],
        "video_keywords": "Scandinavian Defense chess opening",
        "master_games": "https://lichess.org/games/search?opening=B01"
    },
    # d4 openings
    "Queen's Gambit": {
        "eco": ["D06", "D07", "D08", "D09", "D10", "D11", "D12", "D13", "D14", "D15", "D16", "D17", "D18", "D19", "D20", "D21", "D22", "D23", "D24", "D25", "D26", "D27", "D28", "D29", "D30", "D31", "D32", "D33", "D34", "D35", "D36", "D37", "D38", "D39", "D40", "D41", "D42", "D43", "D44", "D45", "D46", "D47", "D48", "D49"],
        "key_moves": "1.d4 d5 2.c4",
        "color": "white",
        "style": "positional",
        "difficulty": "intermediate",
        "description": "A classical opening offering a pawn to gain central control.",
        "alternatives": ["London System", "Catalan Opening", "Torre Attack"],
        "study_links": [
            {"name": "Queen's Gambit Declined", "url": "https://lichess.org/study/JDPLxKyM"},
            {"name": "Queen's Gambit Accepted", "url": "https://lichess.org/study/wKLiJXwD"},
            {"name": "Slav Defense", "url": "https://lichess.org/study/SlavDefense"}
        ],
        "video_keywords": "Queens Gambit chess opening declined accepted",
        "master_games": "https://lichess.org/games/search?opening=D06"
    },
    "King's Indian Defense": {
        "eco": ["E60", "E61", "E62", "E63", "E64", "E65", "E66", "E67", "E68", "E69", "E70", "E71", "E72", "E73", "E74", "E75", "E76", "E77", "E78", "E79", "E80", "E81", "E82", "E83", "E84", "E85", "E86", "E87", "E88", "E89", "E90", "E91", "E92", "E93", "E94", "E95", "E96", "E97", "E98", "E99"],
        "key_moves": "1.d4 Nf6 2.c4 g6 3.Nc3 Bg7",
        "color": "black",
        "style": "aggressive",
        "difficulty": "advanced",
        "description": "A dynamic defense allowing White to build a big center, then counter-attacking.",
        "alternatives": ["Nimzo-Indian Defense", "Queen's Indian Defense", "Grünfeld Defense"],
        "study_links": [
            {"name": "King's Indian Basics", "url": "https://lichess.org/study/yxiheWKk"},
            {"name": "Classical Variation", "url": "https://lichess.org/study/5nDQJSX4"}
        ],
        "video_keywords": "Kings Indian Defense KID chess tutorial",
        "master_games": "https://lichess.org/games/search?opening=E60"
    },
    "London System": {
        "eco": ["D00", "D02"],
        "key_moves": "1.d4 d5 2.Bf4",
        "color": "white",
        "style": "solid",
        "difficulty": "beginner",
        "description": "A simple, solid system that's easy to learn and hard to refute.",
        "alternatives": ["Queen's Gambit", "Catalan Opening", "Colle System"],
        "study_links": [
            {"name": "London System Guide", "url": "https://lichess.org/study/U9tOgKY8"},
            {"name": "London vs Everything", "url": "https://lichess.org/study/ttkNbPz7"}
        ],
        "video_keywords": "London System chess opening tutorial for beginners",
        "master_games": "https://lichess.org/games/search?opening=D00"
    },
    "Nimzo-Indian Defense": {
        "eco": ["E20", "E21", "E22", "E23", "E24", "E25", "E26", "E27", "E28", "E29", "E30", "E31", "E32", "E33", "E34", "E35", "E36", "E37", "E38", "E39", "E40", "E41", "E42", "E43", "E44", "E45", "E46", "E47", "E48", "E49", "E50", "E51", "E52", "E53", "E54", "E55", "E56", "E57", "E58", "E59"],
        "key_moves": "1.d4 Nf6 2.c4 e6 3.Nc3 Bb4",
        "color": "black",
        "style": "positional",
        "difficulty": "advanced",
        "description": "One of the most respected defenses, pinning the knight and fighting for the center.",
        "alternatives": ["Queen's Indian Defense", "King's Indian Defense", "Bogo-Indian Defense"],
        "study_links": [
            {"name": "Nimzo-Indian Intro", "url": "https://lichess.org/study/NimzoIndian"}
        ],
        "video_keywords": "Nimzo Indian Defense chess opening",
        "master_games": "https://lichess.org/games/search?opening=E20"
    },
    "Grünfeld Defense": {
        "eco": ["D70", "D71", "D72", "D73", "D74", "D75", "D76", "D77", "D78", "D79", "D80", "D81", "D82", "D83", "D84", "D85", "D86", "D87", "D88", "D89", "D90", "D91", "D92", "D93", "D94", "D95", "D96", "D97", "D98", "D99"],
        "key_moves": "1.d4 Nf6 2.c4 g6 3.Nc3 d5",
        "color": "black",
        "style": "aggressive",
        "difficulty": "advanced",
        "description": "A hypermodern defense that allows White to build a center, then attacks it.",
        "alternatives": ["King's Indian Defense", "Nimzo-Indian Defense", "Benoni Defense"],
        "study_links": [
            {"name": "Grünfeld Defense Guide", "url": "https://lichess.org/study/Grunfeld"}
        ],
        "video_keywords": "Grunfeld Defense chess opening",
        "master_games": "https://lichess.org/games/search?opening=D70"
    },
    "Catalan Opening": {
        "eco": ["E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09"],
        "key_moves": "1.d4 Nf6 2.c4 e6 3.g3",
        "color": "white",
        "style": "positional",
        "difficulty": "advanced",
        "description": "A sophisticated opening combining Queen's Gambit with a fianchettoed bishop.",
        "alternatives": ["Queen's Gambit", "London System", "Réti Opening"],
        "study_links": [
            {"name": "Catalan Basics", "url": "https://lichess.org/study/Catalan"}
        ],
        "video_keywords": "Catalan Opening chess tutorial",
        "master_games": "https://lichess.org/games/search?opening=E01"
    },
    "Dutch Defense": {
        "eco": ["A80", "A81", "A82", "A83", "A84", "A85", "A86", "A87", "A88", "A89", "A90", "A91", "A92", "A93", "A94", "A95", "A96", "A97", "A98", "A99"],
        "key_moves": "1.d4 f5",
        "color": "black",
        "style": "aggressive",
        "difficulty": "intermediate",
        "description": "An aggressive defense aiming for kingside attack.",
        "alternatives": ["King's Indian Defense", "Benoni Defense", "Budapest Gambit"],
        "study_links": [
            {"name": "Dutch Defense Guide", "url": "https://lichess.org/study/DutchDefense"}
        ],
        "video_keywords": "Dutch Defense chess opening Leningrad Stonewall",
        "master_games": "https://lichess.org/games/search?opening=A80"
    },
    "Slav Defense": {
        "eco": ["D10", "D11", "D12", "D13", "D14", "D15", "D16", "D17", "D18", "D19"],
        "key_moves": "1.d4 d5 2.c4 c6",
        "color": "black",
        "style": "solid",
        "difficulty": "intermediate",
        "description": "A solid defense supporting the d5 pawn while keeping the light-squared bishop free.",
        "alternatives": ["Queen's Gambit Declined", "Semi-Slav Defense", "Caro-Kann Defense"],
        "study_links": [
            {"name": "Slav Defense Basics", "url": "https://lichess.org/study/SlavDefense"}
        ],
        "video_keywords": "Slav Defense chess opening",
        "master_games": "https://lichess.org/games/search?opening=D10"
    },
    # Other openings
    "English Opening": {
        "eco": ["A10", "A11", "A12", "A13", "A14", "A15", "A16", "A17", "A18", "A19", "A20", "A21", "A22", "A23", "A24", "A25", "A26", "A27", "A28", "A29", "A30", "A31", "A32", "A33", "A34", "A35", "A36", "A37", "A38", "A39"],
        "key_moves": "1.c4",
        "color": "white",
        "style": "flexible",
        "difficulty": "intermediate",
        "description": "A flexible opening that can transpose into many different structures.",
        "alternatives": ["Réti Opening", "King's Indian Attack", "Catalan Opening"],
        "study_links": [
            {"name": "English Opening Guide", "url": "https://lichess.org/study/EnglishOpening"}
        ],
        "video_keywords": "English Opening chess tutorial",
        "master_games": "https://lichess.org/games/search?opening=A10"
    },
    "Réti Opening": {
        "eco": ["A04", "A05", "A06", "A07", "A08", "A09"],
        "key_moves": "1.Nf3 d5 2.c4",
        "color": "white",
        "style": "hypermodern",
        "difficulty": "intermediate",
        "description": "A hypermodern opening controlling the center from a distance.",
        "alternatives": ["English Opening", "King's Indian Attack", "Catalan Opening"],
        "study_links": [
            {"name": "Réti Opening Guide", "url": "https://lichess.org/study/RetiOpening"}
        ],
        "video_keywords": "Reti Opening chess tutorial",
        "master_games": "https://lichess.org/games/search?opening=A04"
    }
}

# Quiz questions for openings
OPENING_QUIZ = {
    "Italian Game": [
        {
            "position": "After 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5, what is the main idea for White?",
            "options": ["a) Castle quickly and prepare d3", "b) Play Ng5 immediately", "c) Play a4", "d) Play h3"],
            "correct": 0,
            "explanation": "White should castle and prepare d3 to support the center, possibly followed by c3 and d4."
        },
        {
            "position": "In the Fried Liver Attack (1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5), what should Black play?",
            "options": ["a) d5!", "b) Bc5", "c) h6", "d) Qe7"],
            "correct": 0,
            "explanation": "4...d5! is the best response, and after 5.exd5 Na5! Black gets good counterplay."
        }
    ],
    "Sicilian Defense": [
        {
            "position": "After 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 Nf6 5.Nc3, what's a key move for Black?",
            "options": ["a) a6 (Najdorf)", "b) Nc6", "c) e6", "d) All are main lines"],
            "correct": 3,
            "explanation": "All are main lines! a6 is Najdorf, Nc6 is Classical, e6 is Scheveningen - all are excellent choices."
        }
    ],
    "London System": [
        {
            "position": "What's the typical setup for White in the London System?",
            "options": ["a) d4, Bf4, e3, Nf3, Bd3, c3", "b) d4, c4, Nc3, e4", "c) d4, g3, Bg2", "d) d4, Nc3, e4"],
            "correct": 0,
            "explanation": "The London System has a very specific setup: d4, Bf4 (before e3!), e3, Nf3, Bd3, c3, forming a solid pyramid."
        }
    ]
}


@st.cache_data(ttl=1800)
def fetch_user_games(username, max_games=500, perf_type="blitz"):
    """Fetch user games with caching"""
    url = f"https://lichess.org/api/games/user/{username}"
    headers = {"Accept": "application/x-ndjson"}
    params = {
        "max": max_games,
        "rated": "true",
        "perfType": perf_type,
        "clocks": "true",
        "opening": "true",
        "accuracy": "true"
    }
    
    games = []
    try:
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=60)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                games.append(json.loads(line.decode('utf-8')))
        return games if games else None
    except Exception as e:
        st.error(f"Error fetching games: {e}")
        return None


def analyze_opening_performance(games, username):
    """Comprehensive opening analysis"""
    opening_stats = defaultdict(lambda: {
        'games': 0, 'wins': 0, 'draws': 0, 'losses': 0,
        'as_white': 0, 'as_black': 0,
        'white_wins': 0, 'black_wins': 0,
        'accuracy_sum': 0, 'accuracy_count': 0,
        'time_sum': 0, 'time_count': 0,
        'avg_opponent_rating': [],
        'rating_diff_sum': 0,
        'recent_results': [],
        'eco_codes': set(),
        'variations': defaultdict(lambda: {'games': 0, 'wins': 0})
    })
    
    # Track by rating bracket
    rating_bracket_stats = defaultdict(lambda: defaultdict(lambda: {'games': 0, 'wins': 0}))
    
    # Track time-based trends
    monthly_openings = defaultdict(lambda: defaultdict(lambda: {'games': 0, 'wins': 0}))
    
    for game in games:
        opening = game.get('opening', {})
        opening_name = opening.get('name', 'Unknown')
        eco = opening.get('eco', '')
        
        if opening_name == 'Unknown':
            continue
        
        # Get base opening name
        base_opening = opening_name.split(':')[0].split(',')[0].strip()
        variation = opening_name if ':' in opening_name or ',' in opening_name else None
        
        players = game.get('players', {})
        is_white = players.get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
        color = 'white' if is_white else 'black'
        
        player_info = players.get(color, {})
        opponent_info = players.get('black' if is_white else 'white', {})
        opponent_rating = opponent_info.get('rating', 0)
        
        winner = game.get('winner')
        if winner == color:
            result = 'win'
        elif winner is None:
            result = 'draw'
        else:
            result = 'loss'
        
        stats = opening_stats[base_opening]
        stats['games'] += 1
        stats['eco_codes'].add(eco)
        
        if result == 'win':
            stats['wins'] += 1
        elif result == 'draw':
            stats['draws'] += 1
        else:
            stats['losses'] += 1
        
        if is_white:
            stats['as_white'] += 1
            if result == 'win':
                stats['white_wins'] += 1
        else:
            stats['as_black'] += 1
            if result == 'win':
                stats['black_wins'] += 1
        
        # Accuracy
        accuracy = player_info.get('accuracy')
        if accuracy:
            stats['accuracy_sum'] += accuracy
            stats['accuracy_count'] += 1
        
        # Time usage (from clocks)
        clocks = game.get('clocks', [])
        if clocks and len(clocks) >= 2:
            initial_time = clocks[0] / 100 if is_white else clocks[1] / 100
            final_idx = -2 if is_white else -1
            if len(clocks) > abs(final_idx):
                final_time = clocks[final_idx] / 100
                time_used = initial_time - final_time
                if time_used > 0:
                    stats['time_sum'] += time_used
                    stats['time_count'] += 1
        
        # Opponent rating
        if opponent_rating:
            stats['avg_opponent_rating'].append(opponent_rating)
        
        # Recent results (last 5)
        if len(stats['recent_results']) < 5:
            stats['recent_results'].append(result)
        
        # Variation tracking
        if variation:
            stats['variations'][variation]['games'] += 1
            if result == 'win':
                stats['variations'][variation]['wins'] += 1
        
        # Rating bracket analysis
        if opponent_rating:
            if opponent_rating < 1200:
                bracket = "<1200"
            elif opponent_rating < 1400:
                bracket = "1200-1400"
            elif opponent_rating < 1600:
                bracket = "1400-1600"
            elif opponent_rating < 1800:
                bracket = "1600-1800"
            elif opponent_rating < 2000:
                bracket = "1800-2000"
            else:
                bracket = "2000+"
            
            rating_bracket_stats[base_opening][bracket]['games'] += 1
            if result == 'win':
                rating_bracket_stats[base_opening][bracket]['wins'] += 1
        
        # Monthly tracking
        game_date = datetime.fromtimestamp(game.get('createdAt', 0) / 1000)
        month_key = game_date.strftime('%Y-%m')
        monthly_openings[month_key][base_opening]['games'] += 1
        if result == 'win':
            monthly_openings[month_key][base_opening]['wins'] += 1
    
    # Calculate aggregates
    results = []
    for opening, stats in opening_stats.items():
        if stats['games'] >= 3:
            win_rate = (stats['wins'] / stats['games']) * 100
            avg_accuracy = stats['accuracy_sum'] / stats['accuracy_count'] if stats['accuracy_count'] > 0 else 0
            avg_time = stats['time_sum'] / stats['time_count'] if stats['time_count'] > 0 else 0
            avg_opp_rating = sum(stats['avg_opponent_rating']) / len(stats['avg_opponent_rating']) if stats['avg_opponent_rating'] else 0
            
            white_wr = (stats['white_wins'] / stats['as_white'] * 100) if stats['as_white'] > 0 else 0
            black_wr = (stats['black_wins'] / stats['as_black'] * 100) if stats['as_black'] > 0 else 0
            
            # Get ECO category
            eco_codes = list(stats['eco_codes'])
            eco_category = eco_codes[0][0] if eco_codes and eco_codes[0] else 'X'
            
            # Calculate trend from recent results
            recent_wins = sum(1 for r in stats['recent_results'] if r == 'win')
            recent_wr = (recent_wins / len(stats['recent_results']) * 100) if stats['recent_results'] else 0
            trend = recent_wr - win_rate
            
            results.append({
                'opening': opening,
                'games': stats['games'],
                'win_rate': win_rate,
                'wins': stats['wins'],
                'draws': stats['draws'],
                'losses': stats['losses'],
                'as_white': stats['as_white'],
                'as_black': stats['as_black'],
                'white_wr': white_wr,
                'black_wr': black_wr,
                'avg_accuracy': avg_accuracy,
                'avg_time': avg_time,
                'avg_opponent_rating': avg_opp_rating,
                'eco_category': eco_category,
                'eco_codes': eco_codes[:3],
                'trend': trend,
                'recent_results': stats['recent_results'],
                'variations': dict(stats['variations'])
            })
    
    df = pd.DataFrame(results)
    
    return df, dict(rating_bracket_stats), dict(monthly_openings)


def get_opening_category(opening_name):
    """Match opening to database"""
    for category, data in OPENING_DATABASE.items():
        if category.lower() in opening_name.lower():
            return category, data
    return None, None


def get_eco_badge_class(eco_category):
    """Get CSS class for ECO badge"""
    if eco_category in ['A']:
        return 'eco-A'
    elif eco_category in ['B']:
        return 'eco-B'
    elif eco_category in ['C']:
        return 'eco-C'
    elif eco_category in ['D']:
        return 'eco-D'
    elif eco_category in ['E']:
        return 'eco-E'
    return 'eco-other'


def generate_recommendations(df, username):
    """Generate personalized opening recommendations"""
    recommendations = []
    
    if df.empty:
        return recommendations
    
    # Find weak openings
    weak = df[df['win_rate'] < 45].nlargest(3, 'games')
    for _, row in weak.iterrows():
        category, data = get_opening_category(row['opening'])
        if data:
            recommendations.append({
                'type': 'weakness',
                'title': f"Improve your {row['opening']}",
                'description': f"Only {row['win_rate']:.0f}% win rate in {row['games']} games. Consider studying the main lines or switching to {', '.join(data['alternatives'][:2])}.",
                'action': f"Study: {data['study_links'][0]['url']}" if data['study_links'] else None
            })
    
    # Find strengths to exploit
    strong = df[df['win_rate'] >= 60].nlargest(3, 'games')
    for _, row in strong.iterrows():
        recommendations.append({
            'type': 'strength',
            'title': f"Keep playing {row['opening']}!",
            'description': f"Excellent {row['win_rate']:.0f}% win rate! This opening suits your style well.",
            'action': None
        })
    
    # Color imbalance
    white_openings = df[df['as_white'] > df['as_black']]
    black_openings = df[df['as_black'] > df['as_white']]
    
    if len(white_openings) > 0:
        avg_white_wr = white_openings['white_wr'].mean()
        avg_black_wr = black_openings['black_wr'].mean() if len(black_openings) > 0 else 50
        
        if avg_white_wr > avg_black_wr + 10:
            recommendations.append({
                'type': 'insight',
                'title': "Stronger with White",
                'description': f"You perform better with White ({avg_white_wr:.0f}% vs {avg_black_wr:.0f}%). Focus on improving your Black repertoire.",
                'action': None
            })
        elif avg_black_wr > avg_white_wr + 10:
            recommendations.append({
                'type': 'insight',
                'title': "Stronger with Black",
                'description': f"You perform better with Black ({avg_black_wr:.0f}% vs {avg_white_wr:.0f}%). Consider trying more aggressive White openings.",
                'action': None
            })
    
    # Time management
    high_time = df[df['avg_time'] > df['avg_time'].quantile(0.75)]
    if len(high_time) > 0:
        slow_opening = high_time.iloc[0]['opening']
        recommendations.append({
            'type': 'time',
            'title': f"Time sink: {slow_opening}",
            'description': f"You spend more time in this opening than others. Consider studying it more to play faster.",
            'action': None
        })
    
    return recommendations


def create_win_rate_bar(win_rate):
    """Create win rate progress bar HTML"""
    if win_rate >= 55:
        color = '#4CAF50'
    elif win_rate >= 45:
        color = '#ff9800'
    else:
        color = '#f44336'
    
    return f"""
    <div class="winrate-bar">
        <div class="winrate-fill" style="width: {win_rate}%; background: {color};"></div>
    </div>
    """


def generate_repertoire(df, style='balanced'):
    """Generate a recommended repertoire"""
    repertoire = {'white': [], 'black': []}
    
    # Based on style preference
    if style == 'aggressive':
        white_prefs = ['Sicilian', 'King\'s Gambit', 'Scotch', 'Vienna']
        black_prefs = ['Sicilian', 'King\'s Indian', 'Dutch', 'Grünfeld']
    elif style == 'solid':
        white_prefs = ['London', 'Italian', 'Queen\'s Gambit', 'Catalan']
        black_prefs = ['Caro-Kann', 'Slav', 'French', 'Queen\'s Gambit Declined']
    else:  # balanced
        white_prefs = ['Italian', 'Queen\'s Gambit', 'London', 'Spanish']
        black_prefs = ['Sicilian', 'French', 'King\'s Indian', 'Slav']
    
    for opening, data in OPENING_DATABASE.items():
        if data['color'] == 'white' and any(p.lower() in opening.lower() for p in white_prefs):
            if len(repertoire['white']) < 3:
                repertoire['white'].append({
                    'name': opening,
                    'moves': data['key_moves'],
                    'style': data['style'],
                    'difficulty': data['difficulty']
                })
        elif data['color'] == 'black' and any(p.lower() in opening.lower() for p in black_prefs):
            if len(repertoire['black']) < 3:
                repertoire['black'].append({
                    'name': opening,
                    'moves': data['key_moves'],
                    'style': data['style'],
                    'difficulty': data['difficulty']
                })
    
    return repertoire


# ===== MAIN APP =====

st.markdown("""
<h1 style="text-align: center;">📚 Smart Opening Coach</h1>
<p style="text-align: center; color: #888;">Analyze your opening repertoire and get personalized recommendations</p>
""", unsafe_allow_html=True)

# Input section
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    username = st.text_input("Lichess Username", value=get_username())
    if username:
        set_username(username)

with col2:
    game_type = st.selectbox("Game Type", ["blitz", "rapid", "bullet", "classical"], index=0)

with col3:
    max_games = st.selectbox("Games to Analyze", [100, 200, 500, 1000, 2000], index=2)

analyze_btn = st.button("🔍 Analyze My Openings", type="primary", use_container_width=True)

if analyze_btn and username:
    with st.spinner(""):
        # Progress indication
        progress_bar = st.progress(0)
        status = st.empty()
        
        status.text("Fetching games from Lichess...")
        progress_bar.progress(20)
        
        games = fetch_user_games(username, max_games, game_type)
        
        if not games:
            st.error("❌ No games found or user doesn't exist")
            st.stop()
        
        status.text("Analyzing opening performance...")
        progress_bar.progress(50)
        
        df, rating_brackets, monthly_data = analyze_opening_performance(games, username)
        
        if df.empty:
            st.warning("Not enough opening data (need at least 3 games per opening)")
            st.stop()
        
        status.text("Generating recommendations...")
        progress_bar.progress(80)
        
        recommendations = generate_recommendations(df, username)
        
        progress_bar.progress(100)
        status.empty()
        progress_bar.empty()
        
        # Store in session state
        st.session_state.opening_df = df
        st.session_state.rating_brackets = rating_brackets
        st.session_state.monthly_data = monthly_data
        st.session_state.recommendations = recommendations
        st.session_state.opening_games = games

# Display results
if 'opening_df' in st.session_state and not st.session_state.opening_df.empty:
    df = st.session_state.opening_df
    recommendations = st.session_state.recommendations
    rating_brackets = st.session_state.rating_brackets
    monthly_data = st.session_state.monthly_data
    
    # Overview stats
    st.markdown('<div class="section-header"><p class="section-title">📊 Overview</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-highlight">
            <div class="stat-highlight-value">{len(df)}</div>
            <div class="stat-highlight-label">Different Openings</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_wr = df['win_rate'].mean()
        st.markdown(f"""
        <div class="stat-highlight">
            <div class="stat-highlight-value" style="color: {'#4CAF50' if avg_wr >= 50 else '#f44336'};">{avg_wr:.1f}%</div>
            <div class="stat-highlight-label">Average Win Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        most_played = df.nlargest(1, 'games').iloc[0]['opening']
        st.markdown(f"""
        <div class="stat-highlight">
            <div class="stat-highlight-value" style="font-size: 1.2rem;">{most_played[:15]}...</div>
            <div class="stat-highlight-label">Most Played</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        best_opening = df.nlargest(1, 'win_rate').iloc[0]
        st.markdown(f"""
        <div class="stat-highlight">
            <div class="stat-highlight-value" style="color: #4CAF50;">{best_opening['win_rate']:.0f}%</div>
            <div class="stat-highlight-label">Best: {best_opening['opening'][:12]}...</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Recommendations
    if recommendations:
        st.markdown('<div class="section-header"><p class="section-title">🎯 Personalized Recommendations</p></div>', unsafe_allow_html=True)
        
        cols = st.columns(min(len(recommendations), 3))
        for i, rec in enumerate(recommendations[:3]):
            with cols[i]:
                icon = '⚠️' if rec['type'] == 'weakness' else '✅' if rec['type'] == 'strength' else '💡'
                card_class = 'opening-card-bad' if rec['type'] == 'weakness' else 'opening-card-good' if rec['type'] == 'strength' else 'opening-card-neutral'
                
                st.markdown(f"""
                <div class="opening-card {card_class}">
                    <div class="opening-name">{icon} {rec['title']}</div>
                    <p style="color: #ccc; font-size: 0.9rem;">{rec['description']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if rec.get('action'):
                    st.markdown(f"[📚 Study Link]({rec['action'].replace('Study: ', '')})")
    
    # Performance map
    st.markdown('<div class="section-header"><p class="section-title">🗺️ Performance Map</p></div>', unsafe_allow_html=True)
    
    fig = px.scatter(
        df,
        x='games',
        y='win_rate',
        size='games',
        color='win_rate',
        color_continuous_scale='RdYlGn',
        hover_data=['opening', 'wins', 'losses', 'draws', 'avg_accuracy'],
        text='opening'
    )
    
    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50% Win Rate")
    
    fig.update_traces(textposition='top center', textfont_size=9)
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f0f0f0'),
        xaxis=dict(title='Number of Games', gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='Win Rate (%)', gridcolor='rgba(255,255,255,0.1)'),
        height=450,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True, key="performance_map")
    
    # Tabs for detailed analysis
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 All Openings", "🎨 By Color", "📈 Trends", "🎓 Quiz", "📚 Repertoire Builder"])
    
    with tab1:
        st.markdown("### Opening Details")
        
        # Sort options
        sort_by = st.selectbox("Sort by", ["Games Played", "Win Rate", "Accuracy", "Recent Trend"], key="sort_openings")
        
        sort_map = {
            "Games Played": ('games', False),
            "Win Rate": ('win_rate', False),
            "Accuracy": ('avg_accuracy', False),
            "Recent Trend": ('trend', False)
        }
        
        sort_col, ascending = sort_map[sort_by]
        df_sorted = df.sort_values(sort_col, ascending=ascending)
        
        for _, row in df_sorted.iterrows():
            # Determine card class
            if row['win_rate'] >= 55:
                card_class = 'opening-card-good'
            elif row['win_rate'] < 45:
                card_class = 'opening-card-bad'
            else:
                card_class = 'opening-card-neutral'
            
            # Trend indicator
            if row['trend'] > 5:
                trend_html = '<span class="trend-up">↑ Improving</span>'
            elif row['trend'] < -5:
                trend_html = '<span class="trend-down">↓ Declining</span>'
            else:
                trend_html = '<span class="trend-neutral">→ Stable</span>'
            
            # ECO badge
            eco_class = get_eco_badge_class(row['eco_category'])
            eco_badges = ' '.join([f'<span class="eco-badge {eco_class}">{eco}</span>' for eco in row['eco_codes'][:2]])
            
            with st.expander(f"**{row['opening']}** - {row['win_rate']:.1f}% ({row['games']} games)"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"{eco_badges} {trend_html}", unsafe_allow_html=True)
                    st.markdown(create_win_rate_bar(row['win_rate']), unsafe_allow_html=True)
                    
                    # Stats grid
                    st.markdown(f"""
                    | Metric | Value |
                    |--------|-------|
                    | **Record** | {row['wins']}W / {row['draws']}D / {row['losses']}L |
                    | **As White** | {row['as_white']} games ({row['white_wr']:.1f}% WR) |
                    | **As Black** | {row['as_black']} games ({row['black_wr']:.1f}% WR) |
                    | **Avg Accuracy** | {row['avg_accuracy']:.1f}% |
                    | **Avg Opponent** | {row['avg_opponent_rating']:.0f} |
                    """)
                
                with col2:
                    # Radar chart for this opening
                    categories = ['Win Rate', 'Accuracy', 'Games', 'Consistency']
                    values = [
                        row['win_rate'] / 100,
                        row['avg_accuracy'] / 100 if row['avg_accuracy'] > 0 else 0.5,
                        min(row['games'] / df['games'].max(), 1),
                        1 - (abs(row['trend']) / 20)
                    ]
                    
                    fig_radar = go.Figure(data=go.Scatterpolar(
                        r=values + [values[0]],
                        theta=categories + [categories[0]],
                        fill='toself',
                        fillcolor='rgba(102, 126, 234, 0.3)',
                        line_color='#667eea'
                    ))
                    
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 1], showticklabels=False),
                            bgcolor='rgba(0,0,0,0)'
                        ),
                        paper_bgcolor='rgba(0,0,0,0)',
                        showlegend=False,
                        height=200,
                        margin=dict(l=30, r=30, t=30, b=30)
                    )
                    
                    st.plotly_chart(fig_radar, use_container_width=True, key=f"radar_{row['opening'].replace(' ', '_')}")
                
                # Resources
                category, data = get_opening_category(row['opening'])
                if data:
                    st.markdown("**📚 Study Resources:**")
                    resource_cols = st.columns(3)
                    
                    for i, study in enumerate(data.get('study_links', [])[:3]):
                        with resource_cols[i]:
                            st.markdown(f"[{study['name']}]({study['url']})")
                    
                    if data.get('master_games'):
                        st.markdown(f"[🏆 Master Games]({data['master_games']})")
    
    with tab2:
        st.markdown("### Performance by Color")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ⚪ As White")
            white_df = df[df['as_white'] > 0].sort_values('white_wr', ascending=False)
            
            fig_white = go.Figure(data=go.Bar(
                x=white_df['opening'].head(10),
                y=white_df['white_wr'].head(10),
                marker_color='#f0f0f0',
                text=white_df['white_wr'].head(10).round(1),
                textposition='outside'
            ))
            
            fig_white.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f0f0f0'),
                xaxis=dict(tickangle=-45),
                yaxis=dict(title='Win Rate %', range=[0, 100]),
                height=350
            )
            
            st.plotly_chart(fig_white, use_container_width=True, key="white_performance_chart")
        
        with col2:
            st.markdown("#### ⚫ As Black")
            black_df = df[df['as_black'] > 0].sort_values('black_wr', ascending=False)
            
            fig_black = go.Figure(data=go.Bar(
                x=black_df['opening'].head(10),
                y=black_df['black_wr'].head(10),
                marker_color='#333',
                text=black_df['black_wr'].head(10).round(1),
                textposition='outside',
                textfont=dict(color='#f0f0f0')
            ))
            
            fig_black.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f0f0f0'),
                xaxis=dict(tickangle=-45),
                yaxis=dict(title='Win Rate %', range=[0, 100]),
                height=350
            )
            
            st.plotly_chart(fig_black, use_container_width=True, key="black_performance_chart")
        
        # Heatmap: Opening vs Rating Bracket
        st.markdown("### 🔥 Performance Heatmap (Opening vs Opponent Rating)")
        
        if rating_brackets:
            # Prepare heatmap data
            heatmap_data = []
            brackets = ["<1200", "1200-1400", "1400-1600", "1600-1800", "1800-2000", "2000+"]
            top_openings = df.nlargest(8, 'games')['opening'].tolist()
            
            for opening in top_openings:
                row_data = []
                for bracket in brackets:
                    data = rating_brackets.get(opening, {}).get(bracket, {'games': 0, 'wins': 0})
                    wr = (data['wins'] / data['games'] * 100) if data['games'] > 0 else np.nan
                    row_data.append(wr)
                heatmap_data.append(row_data)
            
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=heatmap_data,
                x=brackets,
                y=top_openings,
                colorscale='RdYlGn',
                zmin=30,
                zmax=70,
                text=[[f'{v:.0f}%' if not np.isnan(v) else '-' for v in row] for row in heatmap_data],
                texttemplate='%{text}',
                textfont=dict(color='white'),
                hovertemplate='%{y}<br>vs %{x}: %{z:.1f}%<extra></extra>'
            ))
            
            fig_heatmap.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f0f0f0'),
                xaxis=dict(title='Opponent Rating'),
                yaxis=dict(title=''),
                height=400
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True, key="rating_heatmap_chart")
    
    with tab3:
        st.markdown("### 📈 Opening Trends Over Time")
        
        if monthly_data:
            # Get top 5 openings
            top_5 = df.nlargest(5, 'games')['opening'].tolist()
            
            # Prepare timeline data
            timeline_data = []
            for month, openings in sorted(monthly_data.items()):
                for opening in top_5:
                    if opening in openings:
                        data = openings[opening]
                        wr = (data['wins'] / data['games'] * 100) if data['games'] > 0 else None
                        if wr is not None:
                            timeline_data.append({
                                'month': month,
                                'opening': opening,
                                'win_rate': wr,
                                'games': data['games']
                            })
            
            if timeline_data:
                timeline_df = pd.DataFrame(timeline_data)
                
                fig_timeline = px.line(
                    timeline_df,
                    x='month',
                    y='win_rate',
                    color='opening',
                    markers=True,
                    title='Win Rate Trends by Month'
                )
                
                fig_timeline.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f0f0f0'),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                    yaxis=dict(title='Win Rate %', gridcolor='rgba(255,255,255,0.1)'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02),
                    height=400
                )
                
                st.plotly_chart(fig_timeline, use_container_width=True, key="timeline_trend_chart")
            else:
                st.info("Not enough monthly data to show trends")
        
        # ECO distribution pie chart
        st.markdown("### 🥧 Opening Category Distribution")
        
        eco_counts = df.groupby('eco_category')['games'].sum().reset_index()
        eco_counts.columns = ['ECO', 'Games']
        
        colors = {'A': '#e91e63', 'B': '#9c27b0', 'C': '#3f51b5', 'D': '#009688', 'E': '#ff9800'}
        eco_counts['color'] = eco_counts['ECO'].map(colors).fillna('#607d8b')
        
        fig_pie = go.Figure(data=go.Pie(
            labels=eco_counts['ECO'],
            values=eco_counts['Games'],
            marker_colors=eco_counts['color'],
            hole=0.4,
            textinfo='percent+label'
        ))
        
        fig_pie.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f0f0f0'),
            height=350,
            annotations=[dict(text='ECO', x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
        st.plotly_chart(fig_pie, use_container_width=True, key="eco_distribution_pie")
        
        st.caption("**ECO Categories:** A = Flank openings, B = Semi-open (1.e4 not 1...e5), C = Open games (1.e4 e5), D = Closed/Semi-closed (1.d4 d5), E = Indian defenses")
    
    with tab4:
        st.markdown("### 🎓 Opening Quiz")
        st.markdown("Test your knowledge of key opening positions!")
        
        # Find openings user plays that have quizzes
        user_openings = df['opening'].tolist()
        available_quizzes = []
        
        for opening in user_openings:
            for quiz_opening, questions in OPENING_QUIZ.items():
                if quiz_opening.lower() in opening.lower():
                    available_quizzes.append((quiz_opening, questions))
                    break
        
        if available_quizzes:
            selected_quiz = st.selectbox(
                "Select an opening to quiz",
                [q[0] for q in available_quizzes]
            )
            
            questions = dict(available_quizzes)[selected_quiz]
            
            for i, q in enumerate(questions):
                st.markdown(f"**Question {i+1}:** {q['position']}")
                
                answer = st.radio(
                    "Select your answer:",
                    q['options'],
                    key=f"quiz_{selected_quiz}_{i}"
                )
                
                if st.button(f"Check Answer", key=f"check_{selected_quiz}_{i}"):
                    selected_idx = q['options'].index(answer)
                    if selected_idx == q['correct']:
                        st.success(f"✅ Correct! {q['explanation']}")
                    else:
                        st.error(f"❌ Incorrect. The correct answer is: {q['options'][q['correct']]}")
                        st.info(q['explanation'])
                
                st.markdown("---")
        else:
            st.info("No quizzes available for your most played openings yet. Keep playing and check back later!")
    
    with tab5:
        st.markdown("### 📚 Repertoire Builder")
        st.markdown("Get a personalized opening repertoire based on your style preference.")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            style = st.radio(
                "Select your preferred style:",
                ["Aggressive", "Solid", "Balanced"],
                index=2
            )
            
            generate_rep = st.button("🎯 Generate Repertoire", use_container_width=True)
        
        with col2:
            if generate_rep:
                repertoire = generate_repertoire(df, style.lower())
                
                st.markdown("#### ⚪ White Repertoire")
                for opening in repertoire['white']:
                    category, data = get_opening_category(opening['name'])
                    st.markdown(f"""
                    <div class="resource-card">
                        <div class="resource-icon">⚪</div>
                        <div class="resource-info">
                            <div class="resource-title">{opening['name']}</div>
                            <div class="resource-desc">{opening['moves']}</div>
                            <div class="resource-desc">Style: {opening['style']} | Level: {opening['difficulty']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if data and data.get('study_links'):
                        st.markdown(f"[📚 Study]({data['study_links'][0]['url']})")
                
                st.markdown("#### ⚫ Black Repertoire")
                for opening in repertoire['black']:
                    category, data = get_opening_category(opening['name'])
                    st.markdown(f"""
                    <div class="resource-card">
                        <div class="resource-icon">⚫</div>
                        <div class="resource-info">
                            <div class="resource-title">{opening['name']}</div>
                            <div class="resource-desc">{opening['moves']}</div>
                            <div class="resource-desc">Style: {opening['style']} | Level: {opening['difficulty']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if data and data.get('study_links'):
                        st.markdown(f"[📚 Study]({data['study_links'][0]['url']})")
                
                # Export option
                st.markdown("---")
                pgn_text = "# Opening Repertoire\n\n"
                pgn_text += f"# Style: {style}\n\n"
                pgn_text += "# White:\n"
                for o in repertoire['white']:
                    pgn_text += f"# {o['name']}: {o['moves']}\n"
                pgn_text += "\n# Black:\n"
                for o in repertoire['black']:
                    pgn_text += f"# {o['name']}: {o['moves']}\n"
                
                st.download_button(
                    "📥 Download Repertoire (TXT)",
                    pgn_text,
                    file_name=f"repertoire_{username}_{style.lower()}.txt",
                    mime="text/plain"
                )

else:
    # Welcome screen
    st.markdown("""
    <div style="text-align: center; padding: 50px;">
        <div style="font-size: 4rem;">📚♟️</div>
        <h2>Analyze Your Opening Repertoire</h2>
        <p style="color: #888;">Enter your Lichess username above to get:</p>
        <p>
            <span class="eco-badge eco-A">Performance Analysis</span>
            <span class="eco-badge eco-B">Personalized Tips</span>
            <span class="eco-badge eco-C">Study Resources</span>
            <span class="eco-badge eco-D">Repertoire Builder</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Data from Lichess API • Opening database with 20+ openings • Updated every 30 minutes")
