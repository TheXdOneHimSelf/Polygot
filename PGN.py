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

    # Variant type
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

def filter_wins_and_draws(pgn_data):
    """Keep only games with result 1-0, 0-1, or 1/2-1/2 (wins + draws)."""
    if not pgn_data.strip():
        return ""
    games = pgn_data.strip().split("\n\n\n")
    valid_games = []

    for game in games:
        for line in game.split("\n"):
            if line.startswith("[Result"):
                if any(x in line for x in ["1-0", "0-1", "1/2-1/2"]):
                    valid_games.append(game.strip())
                break

    return "\n\n\n".join(valid_games)

def main():
    parser = argparse.ArgumentParser(description="Fetch all winning and drawing games of a bot (Std + Chess960)")
    parser.add_argument("--bot", required=True, help="Lichess bot username")
    parser.add_argument("--out", default="bot_games.pgn", help="Output PGN file")
    args = parser.parse_args()

    all_games = []

    for variant in ["std", "960"]:
        data = fetch_games(args.bot, variant)
        time.sleep(2)
        filtered = filter_wins_and_draws(data)
        if filtered:
            all_games.append(filtered)

    if all_games:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n\n\n".join(all_games))
        print(f"✅ Saved all winning + drawing games for {args.bot} → {args.out}")
    else:
        print("⚠️ No games found.")

if __name__ == "__main__":
    main()
