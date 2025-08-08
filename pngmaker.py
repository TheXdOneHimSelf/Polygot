import time
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
MAX_WORKERS = 3  # fewer workers = less chance of 429
RETRY_DELAY = 5  # seconds to wait after 429

seen_games = set()

def fetch_bot_games(bot):
    """Fetch bot-vs-bot games for a given bot with retry on 429."""
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

    for attempt in range(3):  # retry up to 3 times
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 429:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"⏳ {bot} hit rate limit (429) — waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            if r.status_code == 404:
                print(f"❌ {bot} not found or no games.")
                return []
            if r.status_code != 200:
                print(f"❌ {bot} failed - {r.status_code}")
                return []
            games = split_and_filter_games(r.text)
            print(f"✅ {bot}: {len(games)} win/draw bot-vs-bot games")
            return games
        except Exception as e:
            print(f"❌ Error fetching {bot}: {e}")
            time.sleep(2)
    return []

def split_and_filter_games(pgn_data):
    """Split PGN into individual games, filter bot-vs-bot, wins & draws, and deduplicate."""
    games = pgn_data.strip().split("\n\n[Event")
    filtered = []

    for i, game in enumerate(games):
        if i > 0 and not game.startswith("[Event"):
            game = "[Event" + game

        white = re.search(r'\[White "(.*?)"\]', game)
        black = re.search(r'\[Black "(.*?)"\]', game)
        result = re.search(r'\[Result "(.*?)"\]', game)
        game_id_match = re.search(r'\[Site "https://lichess.org/([a-zA-Z0-9]{8})"\]', game)

        if not (white and black and result and game_id_match):
            continue

        white_name = white.group(1)
        black_name = black.group(1)
        game_result = result.group(1)
        game_id = game_id_match.group(1)

        # Only keep bot-vs-bot games where result is win or draw
        if white_name in BOTS and black_name in BOTS:
            if (game_result == "1-0" and white_name in BOTS) or \
               (game_result == "0-1" and black_name in BOTS) or \
               (game_result == "1/2-1/2"):
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

    print(f"\n🎯 Total win/draw bot-vs-bot games collected: {len(all_games)}")
    with open(OUTPUT_PGN, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_games))
    print(f"📁 PGN saved to {OUTPUT_PGN}")

if __name__ == "__main__":
    main()
