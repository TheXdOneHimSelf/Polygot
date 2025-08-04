import requests
import time
import os

BOTS = [
    "NimsiluBot",
    "MaggiChess16",
    "NNUE_Drift",
    "Endogenetic-Bot",
    "AttackKing_Bot"
]

OUTPUT_PGN = "filtered_960_bots_2200plus.pgn"

def is_valid_line(line):
    return line.startswith("[Event") or line.startswith("[Site") or line.startswith("[Date") or line.startswith("[Round") or line.startswith("[White") or line.startswith("[Black") or line.startswith("[Result") or line.startswith("[FEN") or line.startswith("[SetUp") or line.startswith("1.") or line == ""

def fetch_full_games(bot):
    url = f"https://lichess.org/api/games/user/{bot}"
    headers = {
        "Accept": "application/x-chess-pgn"
    }
    params = {
        "max": 3000,
        "variant": "chess960",
        "perfType": "chess960",
        "vs": ",".join(BOTS),
        "pgnInJson": False,
        "rated": "true",
        "analysed": "false",
        "opening": "false",
        "clocks": "false",
        "evals": "false"
    }

    print(f"Fetching games for {bot}...")
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"  Failed for {bot} - {response.status_code}")
        return ""

    return response.text

def filter_games(pgn_data):
    games = pgn_data.strip().split("\n\n\n")
    valid_games = []

    for game in games:
        lines = game.split("\n")
        tags = {line.split(" ")[0][1:]: line for line in lines if line.startswith("[")}
        if "[Variant \"Chess960\"]" not in tags.get("Variant", ""):
            continue
        white = tags.get("White", "")
        black = tags.get("Black", "")
        w_rating_line = tags.get("WhiteElo", "")
        b_rating_line = tags.get("BlackElo", "")
        w_prov = "WhiteRatingDiff" not in tags
        b_prov = "BlackRatingDiff" not in tags

        def extract_rating(line):
            try:
                return int(line.split('"')[1])
            except:
                return 0

        wr = extract_rating(w_rating_line)
        br = extract_rating(b_rating_line)

        if (w_prov or wr >= 2400) and (b_prov or br >= 2400):
            valid_games.append(game.strip())

    return valid_games

def main():
    all_games = []
    for bot in BOTS:
        pgn_data = fetch_full_games(bot)
        time.sleep(2)  # rate limit
        filtered = filter_games(pgn_data)
        print(f"  → {len(filtered)} valid games for {bot}")
        all_games.extend(filtered)

    print(f"\nTotal games collected: {len(all_games)}")
    with open(OUTPUT_PGN, "w", encoding="utf-8") as f:
        f.write("\n\n\n".join(all_games))
    print(f"PGN saved to {OUTPUT_PGN}")

if __name__ == "__main__":
    main()
