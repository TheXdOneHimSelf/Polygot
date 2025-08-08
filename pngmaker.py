import requests
from concurrent.futures import ThreadPoolExecutor
import re

BOTS = [
    "NimsiluBot",
    "MaggiChess16",
    "NNUE_Drift",
    "Endogenetic-Bot",
    "ToromBot",
    "AttackKing_Bot"
]

OUTPUT_PGN = "PgnFile.pgn"
MAX_WORKERS = 6  # parallel downloads

# Set to store game IDs to avoid duplicates
seen_games = set()

def fetch_bot_games(bot):
    """Fetch bot-vs-bot games for a given bot."""
    url = f"https://lichess.org/api/games/user/{bot}"
    headers = {"Accept": "application/x-chess-pgn"}
    params = {
        "max": 3000,
        "variant": "standard",
        "opening": "false",
        "clocks": "false",
        "evals": "false",
        "perfType": "bullet,blitz,rapid,classical"
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            print(f"❌ {bot} failed - {r.status_code}")
            return []
        games = split_and_filter_games(r.text)
        print(f"✅ {bot}: {len(games)} bot-vs-bot games")
        return games
    except Exception as e:
        print(f"❌ Error fetching {bot}: {e}")
        return []

def split_and_filter_games(pgn_data):
    """Split PGN into individual bot-vs-bot games and deduplicate."""
    games = pgn_data.strip().split("\n\n[Event")
    filtered = []

    for i, game in enumerate(games):
        if i > 0 and not game.startswith("[Event"):
            game = "[Event" + game

        white = re.search(r'\[White "(.*?)"\]', game)
        black = re.search(r'\[Black "(.*?)"\]', game)
        game_id_match = re.search(r'\[Site "https://lichess.org/([a-zA-Z0-9]{8})"\]', game)

        if not (white and black and game_id_match):
            continue

        white_name = white.group(1)
        black_name = black.group(1)
        game_id = game_id_match.group(1)

        if white_name in BOTS and black_name in BOTS:
            if game_id not in seen_games:
                seen_games.add(game_id)
                filtered.append(game.strip())

    return filtered

def main():
    all_games = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(fetch_bot_games, BOTS)

    for games in results:
        all_games.extend(games)

    print(f"\n🎯 Total bot-vs-bot games collected: {len(all_games)}")
    with open(OUTPUT_PGN, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_games))
    print(f"📁 PGN saved to {OUTPUT_PGN}")

if __name__ == "__main__":
    main()
