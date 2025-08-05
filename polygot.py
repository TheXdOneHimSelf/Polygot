#!/usr/bin/env python3
import chess
import chess.pgn
import chess.polyglot
import argparse
import sys

# Increase recursion limit to handle large PGN files
sys.setrecursionlimit(10000)

# -------------------------
# Helper functions
# -------------------------

def get_zobrist_key_hex(board):
    return f"{chess.polyglot.zobrist_hash(board):016x}"

def parse_elo(elo):
    """Convert Elo to int safely, return 0 if invalid."""
    try:
        return int(elo)
    except:
        return 0

def process_chunk(pgn_chunk, min_elo, max_plies):
    """Process a batch of games and collect book data."""
    book_data = {}
    for game in pgn_chunk:
        # Skip non-standard games
        if game.headers.get("Variant", "Standard") != "Standard":
            continue

        # Elo filter
        white_elo = parse_elo(game.headers.get("WhiteElo", 0))
        black_elo = parse_elo(game.headers.get("BlackElo", 0))
        if white_elo < min_elo or black_elo < min_elo:
            continue

        # Only wins and draws
        result = game.headers.get("Result", "*")
        score = {"1-0": 10, "1/2-1/2": 3, "0-1": 0}.get(result, 0)
        if score == 0:
            continue

        board = game.board()
        ply = 0
        for move in game.mainline_moves():
            if ply >= max_plies:
                break
            key = get_zobrist_key_hex(board)
            if key not in book_data:
                book_data[key] = {}
            uci = move.uci()
            if uci not in book_data[key]:
                book_data[key][uci] = {"move": move, "weight": 0}
            book_data[key][uci]["weight"] += score if board.turn == chess.WHITE else 10 - score
            board.push(move)
            ply += 1
    return book_data

def merge_books(all_books):
    merged = {}
    for book in all_books:
        for key, moves in book.items():
            if key not in merged:
                merged[key] = {}
            for uci, data in moves.items():
                if uci not in merged[key]:
                    merged[key][uci] = {"move": data["move"], "weight": 0}
                merged[key][uci]["weight"] += data["weight"]
    return merged

def normalize_weights(book):
    MAX_BOOK_WEIGHT = 10000
    for moves in book.values():
        total = sum(m["weight"] for m in moves.values())
        if total > 0:
            for m in moves.values():
                m["weight"] = int(m["weight"] / total * MAX_BOOK_WEIGHT)

def save_as_polyglot(book, path):
    entries = []
    for key_hex, moves in book.items():
        zbytes = bytes.fromhex(key_hex)
        for uci, data in moves.items():
            if data["weight"] <= 0:
                continue
            move = data["move"]
            mi = move.from_square + (move.to_square << 6)
            if move.promotion:
                promo_map = {chess.KNIGHT: 1, chess.BISHOP: 2, chess.ROOK: 3, chess.QUEEN: 4}
                mi += (promo_map[move.promotion] << 12)
            mbytes = mi.to_bytes(2, "big")
            wbytes = data["weight"].to_bytes(2, "big")
            lbytes = (0).to_bytes(4, "big")
            entries.append(zbytes + mbytes + wbytes + lbytes)
    entries.sort(key=lambda e: (e[:8], e[8:10]))
    with open(path, "wb") as f:
        for e in entries:
            f.write(e)
    print(f"✅ Book saved: {path} ({len(entries)} moves)")

def read_games_in_chunks(pgn_path, chunk_size=2000):
    chunk = []
    with open(pgn_path, encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            chunk.append(game)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

def build_book_file(pgn_path, bin_path, min_elo, max_plies):
    print(f"🚀 Building book from {pgn_path} (min Elo={min_elo}, max plies={max_plies})...")
    results = []
    for chunk in read_games_in_chunks(pgn_path):
        results.append(process_chunk(chunk, min_elo, max_plies))
    merged_book = merge_books(results)
    normalize_weights(merged_book)
    save_as_polyglot(merged_book, bin_path)

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PGN → BIN Polyglot Book Builder (Safe Mode)")
    parser.add_argument("--pgn", required=True, help="Input PGN file")
    parser.add_argument("--bin", required=True, help="Output BIN file")
    parser.add_argument("--min-elo", type=int, default=0, help="Minimum player Elo to include")
    parser.add_argument("--max-plies", type=int, default=60, help="Max number of plies (half-moves) to include")
    args = parser.parse_args()
    build_book_file(args.pgn, args.bin, args.min_elo, args.max_plies)
