import sqlite3
import datetime

class ResultStore:
    def __init__(self, db_path: str = "flashbot.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT UNIQUE,
                name          TEXT,
                fqbn          TEXT,
                vid           TEXT,
                pid           TEXT
            );

            CREATE TABLE IF NOT EXISTS flash_runs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id  INTEGER,
                sketch     TEXT,
                success    INTEGER,
                error      TEXT,
                timestamp  TEXT,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            );

            CREATE TABLE IF NOT EXISTS test_results (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id   INTEGER,
                command  TEXT,
                response TEXT,
                passed   INTEGER,
                FOREIGN KEY (run_id) REFERENCES flash_runs(id)
            );
        """)
        self.conn.commit()

    def log_device(self, device) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO devices (serial_number, name, fqbn, vid, pid)
            VALUES (?, ?, ?, ?, ?)
        """, (device.serial_number, device.name, device.fqbn, device.vid, device.pid))
        self.conn.commit()
        cursor.execute("SELECT id FROM devices WHERE serial_number = ?", (device.serial_number,))
        return cursor.fetchone()[0]

    def log_flash(self, device_id: int, sketch: str, success: bool, error: str = "") -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO flash_runs (device_id, sketch, success, error, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (device_id, sketch, int(success), error, datetime.datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid

    def log_test(self, run_id: int, command: str, response: str, passed: bool):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO test_results (run_id, command, response, passed)
            VALUES (?, ?, ?, ?)
        """, (run_id, command, response, int(passed)))
        self.conn.commit()

    def get_recent_failures(self, days: int = 7):
        cursor = self.conn.cursor()
        since = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT f.id, d.name, f.sketch, f.error, f.timestamp
            FROM flash_runs f
            JOIN devices d ON f.device_id = d.id
            WHERE f.success = 0
            AND f.timestamp >= ?
            ORDER BY f.timestamp DESC
        """, (since,))
        return cursor.fetchall()

    def get_all_runs(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT f.id, d.name, f.sketch, f.success, f.error, f.timestamp
            FROM flash_runs f
            JOIN devices d ON f.device_id = d.id
            ORDER BY f.timestamp DESC
        """)
        return cursor.fetchall()

    def export_csv(self, path: str = "flashbot_results.csv"):
        import csv
        rows = self.get_all_runs()
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "device", "sketch", "success", "error", "timestamp"])
            writer.writerows(rows)
        print(f"Exported {len(rows)} rows to {path}")

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    store = ResultStore()
    print("Database created successfully")
    store.close()