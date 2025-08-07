import requests
import time
import os

BOTS = [
    "NimsiluBot",
    "MaggiChess16",
    "NNUE_Drift",
    "Endogenetic-Bot",
    "ToromBot",
    "AttackKing_Bot"
]

OUTPUT_PGN = "PgnFile.pgn"

def fetch_full_games(bot):
    url = f"https://lichess.org/api/games/user/{bot}"
    headers = {
        "Accept": "application/x-chess-pgn"
    }
    params = {
        "max": 3000,
        "variant": "standard",
        "vs": ",".join(BOTS),
        "pgnInJson": False,
        "opening": "false",
        "clocks": "false",
        "evals": "false"
    }

    print(f"\n🔍 Fetching games for {bot}...")
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"  ❌ Failed for {bot} - {response.status_code}")
        return ""

    return response.text

def extract_rating(line):
    try:
        return int(line.split('"')[1])
    except:
        return 0

def filter_games(pgn_data):
    games = pgn_data.strip().split("\n\n\n")
    valid_games = []

    for game in games:
        lines = game.split("\n")
        tags = {line.split(" ")[0][1:]: line for line in lines if line.startswith("[")}

        white = tags.get("White", "").split('"')[1] if "White" in tags else "Unknown"
        black = tags.get("Black", "").split('"')[1] if "Black" in tags else "Unknown"
        wr = extract_rating(tags.get("WhiteElo", ""))
        br = extract_rating(tags.get("BlackElo", ""))
        w_prov = "WhiteRatingDiff" not in tags
        b_prov = "BlackRatingDiff" not in tags

        print(f"🧪 Game: {white} ({wr}) vs {black} ({br})")

        if (w_prov or wr >= 3000) and (b_prov or br >= 3000):
            print("   ✅ Accepted: Both ratings are >= 3000 or provisional")
            valid_games.append(game.strip())
        else:
            print("   ❌ Skipped: Rating too low")

    return valid_games

def main():
    all_games = []
    for bot in BOTS:
        pgn_data = fetch_full_games(bot)
        time.sleep(2)  # rate limit
        filtered = filter_games(pgn_data)
        print(f"  ✅ {len(filtered)} high-rated games found for {bot}")
        all_games.extend(filtered)

    print(f"\n🎯 Total 3000+ games collected: {len(all_games)}")
    with open(OUTPUT_PGN, "w", encoding="utf-8") as f:
        f.write("\n\n\n".join(all_games))
    print(f"📁 PGN saved to {OUTPUT_PGN}")

if __name__ == "__main__":
    main()
