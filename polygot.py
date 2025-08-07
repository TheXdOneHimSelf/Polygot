import chess
import chess.pgn
import chess.polyglot
import datetime

# ===========================
# CONFIGURATION
# ===========================

# Maximum number of half-moves (plies) to include per game
MAX_BOOK_PLIES = 300

# Target weight for normalization (internal scaling)
MAX_BOOK_WEIGHT = 1000000

# Maximum weight allowed in the Polyglot format (16-bit limit)
POLYGLOT_MAX_WEIGHT = 65535

# ===========================
# HELPER FUNCTIONS
# ===========================

def format_zobrist_key_hex(zobrist_key):
    """Convert Zobrist hash (int) into a 16-char hex string."""
    return f"{zobrist_key:016x}"

def get_zobrist_key_hex(board):
    """Compute Zobrist key for a board position and return as hex string."""
    return format_zobrist_key_hex(chess.polyglot.zobrist_hash(board))

# ===========================
# DATA STRUCTURES
# ===========================

class BookMove:
    """Stores a single move and its accumulated weight."""
    def __init__(self):
        self.weight = 0
        self.move = None

class BookPosition:
    """Stores all moves from a given board position."""
    def __init__(self):
        self.moves = {}  # key = UCI move string, value = BookMove
        self.fen = ""    # Not used here but can store FEN if needed

    def get_move(self, uci):
        """Retrieve an existing BookMove or create a new one for this UCI."""
        return self.moves.setdefault(uci, BookMove())

class Book:
    """Main book class to store all positions and export to Polyglot format."""
    def __init__(self):
        self.positions = {}  # key = zobrist hash hex, value = BookPosition

    def get_position(self, zobrist_key_hex):
        """Retrieve an existing position or create a new one."""
        return self.positions.setdefault(zobrist_key_hex, BookPosition())

    def normalize_weights(self):
        """Normalize all move weights so they sum to MAX_BOOK_WEIGHT."""
        for pos in self.positions.values():
            total_weight = sum(bm.weight for bm in pos.moves.values())
            if total_weight > 0:
                for bm in pos.moves.values():
                    # Scale weight proportionally
                    bm.weight = int(bm.weight / total_weight * MAX_BOOK_WEIGHT)
                    if bm.weight < 1:
                        bm.weight = 1  # Ensure no zero weights

    def save_as_polyglot(self, path):
        """Save all collected moves to a binary Polyglot .bin book file."""
        with open(path, 'wb') as outfile:
            entries = []

            # Loop through every position
            for key_hex, pos in self.positions.items():
                zbytes = bytes.fromhex(key_hex)

                # Loop through every move from this position
                for uci, bm in pos.moves.items():
                    if bm.weight <= 0:
                        continue

                    move = bm.move

                    # Encode move into Polyglot format (16 bits)
                    mi = move.to_square + (move.from_square << 6)
                    if move.promotion:
                        mi += ((move.promotion - 1) << 12)
                    mbytes = mi.to_bytes(2, byteorder="big")

                    # Clamp weight to Polyglot max
                    weight = min(max(bm.weight, 1), POLYGLOT_MAX_WEIGHT)
                    wbytes = weight.to_bytes(2, byteorder="big")

                    # Learn value (always zero here)
                    lbytes = (0).to_bytes(4, byteorder="big")

                    # Final 16-byte Polyglot entry
                    entry = zbytes + mbytes + wbytes + lbytes
                    entries.append(entry)

            # Sort book entries by Zobrist key and move order
            entries.sort(key=lambda e: (e[:8], e[10:12]), reverse=False)

            # Write all entries to file
            for entry in entries:
                outfile.write(entry)

            print(f"✅ Saved {len(entries)} moves to book: {path}")

    def merge_file(self, path):
        """Merge an existing Polyglot book into this one (adds weights)."""
        with chess.polyglot.open_reader(path) as reader:
            for i, entry in enumerate(reader, start=1):
                key_hex = format_zobrist_key_hex(entry.key)
                pos = self.get_position(key_hex)
                move = entry.move()
                uci = move.uci()

                bm = pos.get_move(uci)
                bm.move = move
                bm.weight += entry.weight

                # Status update every 10k moves
                if i % 10000 == 0:
                    print(f"Merged {i} moves")

# ===========================
# LICHESS GAME WRAPPER
# ===========================

class LichessGame:
    """Wrapper around PGN game to easily extract ID, timestamp, and result."""
    def __init__(self, game):
        self.game = game

    def get_id(self):
        """Extract game ID from the 'Site' PGN header (lichess.org link)."""
        return self.game.headers["Site"].split("/")[-1]

    def get_time(self):
        """Parse UTC date and time into a timestamp."""
        dt_str = self.game.headers["UTCDate"] + "T" + self.game.headers["UTCTime"]
        return datetime.datetime.strptime(dt_str, "%Y.%m.%dT%H:%M:%S").timestamp()

    def result(self):
        """Return game result (1-0, 0-1, or 1/2-1/2)."""
        return self.game.headers.get("Result", "*")

    def score(self):
        """
        Convert result to numerical score:
        - 1-0 (White wins) -> 2
        - 1/2-1/2 (Draw) -> 1
        - 0-1 (Black wins) -> 0
        """
        res = self.result()
        return {"1-0": 2, "1/2-1/2": 1}.get(res, 0)

# ===========================
# MAIN BOOK BUILD FUNCTION
# ===========================

def build_book_file(pgn_path, book_path):
    """
    Build a Polyglot opening book from a PGN file.
    Reads all games, collects moves, applies scores, and saves to .bin format.
    """
    book = Book()

    with open(pgn_path) as pgn_file:
        for i, game in enumerate(iter(lambda: chess.pgn.read_game(pgn_file), None), start=1):
            # Status update every 100 games
            if i % 100 == 0:
                print(f"Processed {i} games from {pgn_path}")

            ligame = LichessGame(game)
            board = game.board()
            score = ligame.score()
            ply = 0

            # Iterate through every move in the main line of the game
            for move in game.mainline_moves():
                if ply >= MAX_BOOK_PLIES:
                    break  # Stop if we've hit the max plies

                uci = move.uci()  # Standard UCI string (no manual corrections needed)
                zobrist_key_hex = get_zobrist_key_hex(board)
                position = book.get_position(zobrist_key_hex)
                bm = position.get_move(uci)

                # Store move and weight based on game result
                bm.move = move
                bm.weight += score if board.turn == chess.WHITE else (2 - score)

                board.push(move)
                ply += 1

    # Normalize all move weights
    book.normalize_weights()

    # Save final compiled Polyglot book
    book.save_as_polyglot(book_path)

# ===========================
# ENTRY POINT
# ===========================
if __name__ == "__main__":
    build_book_file("PgnFile.pgn", "bot.bin")

