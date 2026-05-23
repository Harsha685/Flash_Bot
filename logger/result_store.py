import os
import sqlite3
import hashlib

DB_PATH = "logs/flashbot.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flash_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_name TEXT NOT NULL,
            fqbn TEXT NOT NULL,
            port TEXT NOT NULL,
            sketch_path TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
            error TEXT,
            source_hash TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migrate old tables that don't have source_hash
    cursor.execute("PRAGMA table_info(flash_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    if "source_hash" not in columns:
        cursor.execute("ALTER TABLE flash_logs ADD COLUMN source_hash TEXT")
    
    conn.commit()
    conn.close()

def save_result(board_name, fqbn, port, sketch_path, status, error=None, source_hash=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO flash_logs (board_name, fqbn, port, sketch_path, status, error, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (board_name, fqbn, port, sketch_path, status, error, source_hash))
    conn.commit()
    conn.close()

def get_results():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM flash_logs ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_last_successful_hash(board_name, sketch_path):
    """
    Return the source hash from the last successful flash of this board+sketch.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT source_hash FROM flash_logs 
        WHERE board_name=? AND sketch_path=? AND status='success'
        ORDER BY id DESC LIMIT 1
    ''', (board_name, sketch_path))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def _file_hash(path):
    """SHA256 of file contents."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()