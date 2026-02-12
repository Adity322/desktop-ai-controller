import sqlite3
import re
DB_PATH = "file_index.db"
STOP_WORDS = {
    "open", "file", "notes", "note", "unit", "chapter",
    "tutorial", "full", "pdf", "docx"
}
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
def search_file(query, limit=5):
    # break sentence into words
    words = re.findall(r"[a-z0-9]+", query.lower())
    keywords = [w for w in words if w not in STOP_WORDS and len(w) > 1]

    if not keywords:
        return []

    conditions = " OR ".join(["name LIKE ?"] * len(keywords))
    params = [f"%{k}%" for k in keywords]

    sql = f"""
        SELECT path FROM files
        WHERE ({conditions})
        AND path NOT LIKE '%.app/%'
        AND extension IN ('.pdf', '.docx', '.doc', '.txt', '.ppt', '.pptx', '.rtf')
        ORDER BY modified DESC
        LIMIT ?
    """

    cursor.execute(sql, (*params, limit))
    return [row[0] for row in cursor.fetchall()]
