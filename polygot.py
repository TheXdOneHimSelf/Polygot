#!/usr/bin/env python3
import chess
import chess.pgn
import chess.polyglot
import multiprocessing

MAX_BOOK_PLIES = 60          # 60 plies = 30 full moves
MAX_BOOK_WEIGHT = 10000
CPU_CORES = max(1, multiprocessing.cpu_count() - 1)

def get_zobrist_key_hex(board):
    return f"{chess.polyglot.zobrist_hash(board):016x}"

def process_chunk(pgn_chunk):
    book_data = {}
    for game in pgn_chunk:
        if game.headers.get("Variant", "Standard") != "Standard":
            continue
        result = game.headers.get("Result", "*")
        score = {"1-0": 10, "1/2-1/2": 3, "0-1": 0}.get(result, 0)
        if score == 0:
            continue
        board = game.board()
        ply = 0
        for move in game.mainline_moves():
            if ply >= MAX_BOOK_PLIES:
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

def read_games_in_chunks(pgn_path, chunk_size=5000):
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

def build_book_file(pgn_path, bin_path):
    print(f"🚀 Using {CPU_CORES} CPU cores for fast processing...")
    with multiprocessing.Pool(CPU_CORES) as pool:
        results = pool.map(process_chunk, read_games_in_chunks(pgn_path))
    merged_book = merge_books(results)
    normalize_weights(merged_book)
    save_as_polyglot(merged_book, bin_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fast PGN → BIN Polyglot Book Builder (Wins & Draws only)")
    parser.add_argument("--pgn", required=True, help="Input PGN file")
    parser.add_argument("--bin", required=True, help="Output BIN file")
    args = parser.parse_args()
    build_book_file(args.pgn, args.bin)
