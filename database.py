import sqlite3

def init_db():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            date TEXT,
            arrival_time TEXT,
            departure_time TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_arrival(user_id, full_name, date, time_str, status):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO attendance (user_id, full_name, date, arrival_time, status)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, date, time_str, status))
    conn.commit()
    conn.close()

def save_departure(user_id, date, time_str):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE attendance SET departure_time = ? WHERE user_id = ? AND date = ?
    """, (time_str, user_id, date))
    conn.commit()
    conn.close()