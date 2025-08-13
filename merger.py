import os
import chess
import chess.polyglot

# Folder containing your .bin books
BOOK_FOLDER = "bin"  # Change this to your folder name
OUTPUT_FILE = "Book.bin"
POLYGLOT_MAX_WEIGHT = 65535

def format_key_hex(key):
    return f"{key:016x}"

class Book:
    def __init__(self):
        self.positions = {}  # {key_hex: {uci: weight}}

    def add_move(self, key_hex, move, weight):
        pos = self.positions.setdefault(key_hex, {})
        uci = move.uci()
        pos[uci] = pos.get(uci, 0) + weight

    def save(self, path):
        append = bytes.__add__
        to_bytes = int.to_bytes
        Move = chess.Move.from_uci
        entries = []
        for key_hex, moves in self.positions.items():
            zbytes = bytes.fromhex(key_hex)
            for uci, weight in moves.items():
                move = Move(uci)
                mi = move.to_square + (move.from_square << 6)
                if move.promotion:
                    mi += ((move.promotion - 1) << 12)
                mbytes = to_bytes(mi, 2, "big")
                wbytes = to_bytes(min(weight, POLYGLOT_MAX_WEIGHT), 2, "big")
                lbytes = b"\x00\x00\x00\x00"
                entries.append(append(append(zbytes, mbytes), append(wbytes, lbytes)))
        entries.sort(key=lambda e: (e[:8], e[10:12]))
        with open(path, "wb") as f:
            f.writelines(entries)
        print(f"✅ Saved merged book with {len(entries)} moves → {path}")

def merge_polyglot_books():
    merged = Book()
    fmt = format_key_hex
    add = merged.add_move

    # Find all .bin files in the folder
    book_files = [os.path.join(BOOK_FOLDER, f) for f in os.listdir(BOOK_FOLDER) if f.lower().endswith(".bin")]

    if not book_files:
        print(f"⚠️ No .bin files found in folder '{BOOK_FOLDER}'")
        return

    for book_file in book_files:
        try:
            with chess.polyglot.open_reader(book_file) as reader:
                for entry in reader:
                    add(fmt(entry.key), entry.move(), entry.weight)
            print(f"📂 Merged: {book_file}")
        except Exception as e:
            print(f"⚠️ Error reading {book_file}: {e}")

    merged.save(OUTPUT_FILE)

if __name__ == "__main__":
    merge_polyglot_books()
