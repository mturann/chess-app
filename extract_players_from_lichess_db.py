"""
Lichess Database Player Extractor 
"""

import requests
import zstandard as zstd
import json
import re
from collections import defaultdict
import io

LICHESS_DB_URL = "https://database.lichess.org/standard/lichess_db_standard_rated_2025-01.pgn.zst"

DOWNLOAD_SIZE = 500 * 1024 * 1024  # 500 MB

RATING_RANGES = [
    (800, 1000),
    (1000, 1200),
    (1200, 1400),
    (1400, 1600),
    (1600, 1800),
    (1800, 2000),
    (2000, 2200),
    (2200, 2400),
    (2400, 9999),  
]

PLAYERS_PER_RANGE = 350

GAME_TYPE_FILTER = "Blitz"
OUTPUT_FILE = "player_list_by_rating_v2.json"


def download_partial_db(url, size_bytes):
    print(f"Downloading first {size_bytes / (1024*1024):.0f} MB from Lichess DB...")
    
    headers = {
        "Range": f"bytes=0-{size_bytes}",
        "User-Agent": "ChessWinProbabilityBot/1.0"
    }
    
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=120)
        response.raise_for_status()
        
        compressed_data = b""
        downloaded = 0
        
        for chunk in response.iter_content(chunk_size=1024*1024):
            compressed_data += chunk
            downloaded += len(chunk)
            print(f"\rDownloaded: {downloaded / (1024*1024):.1f} MB", end="")
            
            if downloaded >= size_bytes:
                break
        
        print(f"\nDownload complete: {len(compressed_data) / (1024*1024):.1f} MB")
        return compressed_data
        
    except Exception as e:
        print(f"Download error: {e}")
        return None


def decompress_partial(compressed_data):
    print("Decompressing...")
    
    dctx = zstd.ZstdDecompressor()
    decompressed = b""
    
    try:
        with dctx.stream_reader(io.BytesIO(compressed_data)) as reader:
            while True:
                chunk = reader.read(1024 * 1024)
                if not chunk:
                    break
                decompressed += chunk
                print(f"\rDecompressed: {len(decompressed) / (1024*1024):.1f} MB", end="")
        
        print(f"\nDecompression complete: {len(decompressed) / (1024*1024):.1f} MB")
        return decompressed.decode('utf-8', errors='ignore')
        
    except Exception as e:
        print(f"\nPartial decompression (expected): {e}")
        if decompressed:
            return decompressed.decode('utf-8', errors='ignore')
        return None


def parse_pgn_headers(pgn_text, game_type_filter=None):
    print("Parsing game headers...")
    
    players = defaultdict(lambda: {"games": 0, "ratings": []})
    
    white_pattern = re.compile(r'\[White "([^"]+)"\]')
    black_pattern = re.compile(r'\[Black "([^"]+)"\]')
    white_elo_pattern = re.compile(r'\[WhiteElo "(\d+)"\]')
    black_elo_pattern = re.compile(r'\[BlackElo "(\d+)"\]')
    event_pattern = re.compile(r'\[Event "([^"]+)"\]')
    
    games = pgn_text.split("\n\n[Event")
    total_games = len(games)
    
    print(f"Found approximately {total_games:,} games to parse")
    
    parsed = 0
    filtered = 0
    
    for i, game in enumerate(games):
        if i > 0:
            game = "[Event" + game
        
        if game_type_filter:
            event_match = event_pattern.search(game)
            if event_match:
                event = event_match.group(1)
                if game_type_filter.lower() not in event.lower():
                    filtered += 1
                    continue
        
        # White player
        white_match = white_pattern.search(game)
        white_elo_match = white_elo_pattern.search(game)
        
        if white_match and white_elo_match:
            username = white_match.group(1)
            try:
                elo = int(white_elo_match.group(1))
                if 800 <= elo <= 3500 and username != "?":
                    players[username]["ratings"].append(elo)
                    players[username]["games"] += 1
            except:
                pass
        
        # Black player
        black_match = black_pattern.search(game)
        black_elo_match = black_elo_pattern.search(game)
        
        if black_match and black_elo_match:
            username = black_match.group(1)
            try:
                elo = int(black_elo_match.group(1))
                if 800 <= elo <= 3500 and username != "?":
                    players[username]["ratings"].append(elo)
                    players[username]["games"] += 1
            except:
                pass
        
        parsed += 1
        
        if (i + 1) % 100000 == 0:
            print(f"\rParsed: {i+1:,} games, Found: {len(players):,} unique players", end="")
    
    for username in players:
        ratings = players[username]["ratings"]
        if ratings:
            players[username]["elo"] = int(sum(ratings) / len(ratings))
        del players[username]["ratings"]  
    
    print(f"\n\nParsing complete:")
    print(f"  Total games parsed: {parsed:,}")
    print(f"  Filtered out: {filtered:,}")
    print(f"  Unique players found: {len(players):,}")
    
    return dict(players)


def group_players_by_rating(players, rating_ranges, players_per_range):
    print("\nGrouping players by rating...")
    
    grouped = {}
    for r in rating_ranges:
        if r[1] == 9999:
            key = f"{r[0]}+"
        else:
            key = f"{r[0]}-{r[1]}"
        grouped[key] = []
    
    for username, data in players.items():
        elo = data.get("elo", 0)
        games = data.get("games", 0)
        
        if games < 10:
            continue
        
        for min_r, max_r in rating_ranges:
            if min_r <= elo < max_r:
                if max_r == 9999:
                    key = f"{min_r}+"
                else:
                    key = f"{min_r}-{max_r}"
                grouped[key].append({
                    "username": username,
                    "elo": elo,
                    "games": games
                })
                break
    
    result = {}
    
    print("\nRating Range    | Available | Selected")
    print("-" * 45)
    
    for range_key in grouped:
        sorted_players = sorted(grouped[range_key], key=lambda x: x["games"], reverse=True)
        selected = sorted_players[:players_per_range]
        result[range_key] = selected
        
        print(f"{range_key:15} | {len(grouped[range_key]):9,} | {len(selected):8}")
    
    return result


def save_player_list(grouped_players, output_file):
    simple_list = {}
    for range_key, players in grouped_players.items():
        simple_list[range_key] = [p["username"] for p in players]
    
    with open(output_file, 'w') as f:
        json.dump(simple_list, f, indent=2)
    
    print(f"\nPlayer list saved to: {output_file}")
    
    detailed_file = output_file.replace(".json", "_detailed.json")
    with open(detailed_file, 'w') as f:
        json.dump(grouped_players, f, indent=2)
    
    print(f"Detailed list saved to: {detailed_file}")


def main():
    print("=" * 60)
    print("LICHESS DATABASE PLAYER EXTRACTOR")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Download size: {DOWNLOAD_SIZE / (1024*1024):.0f} MB")
    print(f"  Game type: {GAME_TYPE_FILTER}")
    print(f"  Players per bucket: {PLAYERS_PER_RANGE}")
    print(f"  Buckets: {len(RATING_RANGES)}")
    print()
    
    # Download
    compressed_data = download_partial_db(LICHESS_DB_URL, DOWNLOAD_SIZE)
    if not compressed_data:
        print("ERROR: Download failed")
        return
    
    # Decompress
    pgn_text = decompress_partial(compressed_data)
    if not pgn_text:
        print("ERROR: Decompression failed")
        return
    
    # Parse
    players = parse_pgn_headers(pgn_text, GAME_TYPE_FILTER)
    if len(players) < 100:
        print("ERROR: Not enough players found")
        return
    
    # Group
    grouped = group_players_by_rating(players, RATING_RANGES, PLAYERS_PER_RANGE)
    
    # Save
    save_player_list(grouped, OUTPUT_FILE)
    
    # Summary
    total = sum(len(p) for p in grouped.values())
    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {total:,} players across {len(RATING_RANGES)} buckets")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()