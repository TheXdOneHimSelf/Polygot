#!/usr/bin/env python3
import requests
import time
import argparse

def fetch_games(bot_name):
    """Fetch rated standard chess games for one bot."""
    url = f"https://lichess.org/api/games/user/{bot_name}"
    headers = {
        "Accept": "application/x-chess-pgn",
        "User-Agent": "PGNFetcher/1.0 (https://github.com/yourusername)"
    }
    params = {
        "max": 3000,
        "rated": True,
        "analysed": False,
        "opening": False,
        "clocks": False,
        "evals": False,
        "perfType": "classical,rapid,blitz,bullet"
    }

    print(f"📥 Fetching STANDARD games for {bot_name}...")
    for attempt in range(3):  # retry up to 3 times
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.text
        print(f"⚠️ Attempt {attempt+1} failed ({response.status_code}), retrying...")
        time.sleep(3)
    return ""

def extract_rating(line):
    """Extract Elo rating from PGN line."""
    try:
        return int(line.split('"')[1])
    except:
        return 0

def filter_games(pgn_data, min_elo):
    """Keep only games with result (win/draw) and Elo >= min_elo for both players."""
    if not pgn_data.strip():
        return ""
    games = pgn_data.strip().split("\n\n\n")
    valid_games = []

    for game in games:
        lines = game.split("\n")
        result = ""
        wr = br = 0

        for line in lines:
            if line.startswith("[Result"):
                result = line
            elif line.startswith("[WhiteElo"):
                wr = extract_rating(line)
            elif line.startswith("[BlackElo"):
                br = extract_rating(line)

        if result and any(x in result for x in ["1-0", "0-1", "1/2-1/2"]):
            if wr >= min_elo and br >= min_elo:
                valid_games.append(game.strip())

    return "\n\n\n".join(valid_games)

def main():
    parser = argparse.ArgumentParser(description="Fetch standard bot games (wins + draws) with min rating filter")
    parser.add_argument("--bot", required=True, help="Lichess bot username")
    parser.add_argument("--out", default="bot_games_std.pgn", help="Output PGN file")
    parser.add_argument("--min-elo", type=int, default=3000, help="Minimum Elo rating filter")
    args = parser.parse_args()

    data = fetch_games(args.bot)
    filtered = filter_games(data, args.min_elo)

    if filtered:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(filtered)
        print(f"✅ Saved all STANDARD games Elo ≥ {args.min_elo} for {args.bot} → {args.out}")
    else:
        print("⚠️ No games found matching criteria.")

if __name__ == "__main__":
    main()
