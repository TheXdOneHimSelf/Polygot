#!/usr/bin/env python3
import requests
import time
import argparse

def fetch_games(bot_name, variant):
    """Fetch rated games for one bot and one variant (std or 960)."""
    url = f"https://lichess.org/api/games/user/{bot_name}"
    headers = {"Accept": "application/x-chess-pgn"}
    params = {
        "max": 2000,
        "rated": True,
        "analysed": False,
        "opening": False,
        "clocks": False,
        "evals": False
    }

    if variant == "960":
        params["variant"] = "chess960"
        params["perfType"] = "chess960"
    elif variant == "std":
        params["perfType"] = "classical,rapid,blitz,bullet"

    print(f"📥 Fetching {variant.upper()} games for {bot_name}...")
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"  ❌ Failed for {bot_name} ({variant}) - {response.status_code}")
        return ""

    return response.text

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
    parser = argparse.ArgumentParser(description="Fetch bot games (wins + draws) with min rating filter")
    parser.add_argument("--bot", required=True, help="Lichess bot username")
    parser.add_argument("--out", default="bot_games.pgn", help="Output PGN file")
    parser.add_argument("--min-elo", type=int, default=3000, help="Minimum Elo rating filter")
    args = parser.parse_args()

    all_games = []

    for variant in ["std", "960"]:
        data = fetch_games(args.bot, variant)
        time.sleep(2)
        filtered = filter_games(data, args.min_elo)
        if filtered:
            all_games.append(filtered)

    if all_games:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n\n\n".join(all_games))
        print(f"✅ Saved all games Elo ≥ {args.min_elo} for {args.bot} → {args.out}")
    else:
        print("⚠️ No games found matching criteria.")

if __name__ == "__main__":
    main()
