#!/usr/bin/env python3
import chess.pgn
import argparse
import os

def filter_pgn(input_pgn, output_pgn, min_elo=2000, min_moves=25):
    print(f"📂 Filtering PGN: {input_pgn}")
    print(f"⚡ Keeping games: Elo ≥ {min_elo}, Moves ≥ {min_moves}, No draws")

    seen_positions = set()
    total = 0
    kept = 0

    with open(input_pgn, encoding="utf-8", errors="ignore") as pgn, \
         open(output_pgn, "w", encoding="utf-8") as out:

        while True:
            game = chess.pgn.read_game(pgn)
            if game is None:
                break
            total += 1

            # Elo filter
            try:
                white_elo = int(game.headers.get("WhiteElo", 0))
                black_elo = int(game.headers.get("BlackElo", 0))
            except:
                white_elo = black_elo = 0

            if max(white_elo, black_elo) < min_elo:
                continue

            # Result filter (remove draws)
            if game.headers.get("Result") not in ["1-0", "0-1"]:
                continue

            # Move count filter
            move_count = sum(1 for _ in game.mainline_moves())
            if move_count < min_moves:
                continue

            # Duplicate detection (avoid repeating same sequence)
            board = game.board()
            positions = [board.fen()]
            for move in game.mainline_moves():
                board.push(move)
                positions.append(board.fen())
            pos_hash = hash("".join(positions))
            if pos_hash in seen_positions:
                continue
            seen_positions.add(pos_hash)

            # Write good game
            exporter = chess.pgn.FileExporter(out)
            game.accept(exporter)
            kept += 1

    print(f"✅ Filtered {total} games → {kept} high-quality games saved in {output_pgn}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter PGN for best games")
    parser.add_argument("--pgn", required=True, help="Input PGN file")
    parser.add_argument("--out", required=True, help="Filtered PGN output file")
    parser.add_argument("--min-elo", type=int, default=2000, help="Minimum Elo filter")
    parser.add_argument("--min-moves", type=int, default=25, help="Minimum number of moves")
    args = parser.parse_args()

    if not os.path.exists(args.pgn):
        print("❌ Error: PGN file not found!")
        exit(1)

    filter_pgn(args.pgn, args.out, args.min_elo, args.min_moves)
