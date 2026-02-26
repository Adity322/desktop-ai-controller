import os
import sqlite3
import time
import platform

DB_PATH = "file_index.db"
LAST_INDEX_FILE = "last_index.txt"

SYSTEM = platform.system()

# OS-specific exclusions
EXCLUDE_DIRS = {
    "Windows", "Program Files", "Program Files (x86)",
    "$Recycle.Bin", "System Volume Information",
    ".git", "node_modules", "__pycache__"
}

# Root paths based on OS
if SYSTEM == "Darwin":  # macOS
    ROOT_PATHS = [
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser(
            "~/Library/Mobile Documents/com~apple~CloudDocs"
        )  # iCloud Drive
    ]
else:  # Windows
    ROOT_PATHS = ["C:\\"]


# ---------------- DB SETUP ----------------

# ---------------- TIME ----------------
def load_last_index_time():
    try:
        with open(LAST_INDEX_FILE, "r") as f:
            return float(f.read())
    except:
        return 0

def save_last_index_time():
    with open(LAST_INDEX_FILE, "w") as f:
        f.write(str(time.time()))

# ---------------- INDEXER ----------------
def index_path(start_path,cursor,conn):
    last_index_time = load_last_index_time()

    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            try:
                full_path = os.path.join(root, file)
                modified = os.path.getmtime(full_path)

                if modified > last_index_time:
                    name, ext = os.path.splitext(file)

                    cursor.execute("""
                        INSERT OR REPLACE INTO files
                        (path, name, extension, modified)
                        VALUES (?, ?, ?, ?)
                    """, (
                        full_path,
                        name.lower(),
                        ext.lower(),
                        modified
                    ))
            except:
                pass

    conn.commit()

def run_indexer():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        path TEXT PRIMARY KEY,
        name TEXT,
        extension TEXT,
        modified REAL
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON files(name)")
    conn.commit()

    for path in ROOT_PATHS:
        index_path(path, cursor, conn)

    save_last_index_time()
    conn.close()


# ---------------- RUN ----------------
if __name__ == "__main__":
    run_indexer()
