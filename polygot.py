#!/usr/bin/env python3
import chess.pgn
import chess.polyglot
import argparse
import os

def build_polyglot(pgn_file, bin_file, min_elo, max_plies):
    print(f"📂 Reading PGN: {pgn_file}")
    print(f"🔧 Filters: min_elo={min_elo}, max_plies={max_plies}")
    print(f"💾 Writing Polyglot book: {bin_file}")

    # Open input PGN and output BIN
    with open(pgn_file, encoding="utf-8", errors="ignore") as pgn, \
         chess.polyglot.Writer(open(bin_file, "wb")) as writer:

        game_count = 0
        added_moves = 0

        while True:
            game = chess.pgn.read_game(pgn)
            if game is None:
                break
            game_count += 1

            # Filter by Elo
            try:
                white_elo = int(game.headers.get("WhiteElo", 0))
                black_elo = int(game.headers.get("BlackElo", 0))
            except:
                white_elo = black_elo = 0

            if max(white_elo, black_elo) < min_elo:
                continue

            board = game.board()
            ply_count = 0

            for move in game.mainline_moves():
                if ply_count >= max_plies:
                    break
                writer.write(board, move, weight=10)
                board.push(move)
                ply_count += 1
                added_moves += 1

        print(f"✅ Processed {game_count} games, added {added_moves} moves.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PGN → Polyglot book builder")
    parser.add_argument("--pgn", required=True, help="Input PGN file")
    parser.add_argument("--bin", required=True, help="Output Polyglot BIN file")
    parser.add_argument("--min-elo", type=int, default=2000, help="Minimum Elo rating filter")
    parser.add_argument("--max-plies", type=int, default=80, help="Maximum plies per game")
    args = parser.parse_args()

    if not os.path.exists(args.pgn):
        print("❌ Error: PGN file not found!")
        exit(1)

    build_polyglot(args.pgn, args.bin, args.min_elo, args.max_plies)
k.bin")
