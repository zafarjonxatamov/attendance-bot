import sqlite3

def init_db():
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            role TEXT,
            action TEXT,
            time TEXT,
            status TEXT,
            distance TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, full_name, role=None):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, full_name, role)
        VALUES (?, ?, ?)
    ''', (user_id, full_name, role))
    if role:
        cursor.execute('UPDATE users SET role = ?, full_name = ? WHERE user_id = ?', (role, full_name, user_id))
    conn.commit()
    conn.close()

def get_user_role(user_id):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def update_user_role(user_id, role):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = ? WHERE user_id = ?', (role, user_id))
    conn.commit()
    conn.close()

def save_attendance(user_id, full_name, role, action, time, status, distance):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attendance (user_id, full_name, role, action, time, status, distance)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, full_name, role, action, time, status, distance))
    conn.commit()
    conn.close()
