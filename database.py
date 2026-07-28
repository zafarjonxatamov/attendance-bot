import sqlite3

def init_db():
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            department TEXT,
            role TEXT,
            is_blocked INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            department TEXT,
            role TEXT,
            action TEXT,
            time TEXT,
            status TEXT,
            distance TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, full_name, department=None, role=None):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, full_name, department, role, is_blocked)
        VALUES (?, ?, ?, ?, 0)
    ''', (user_id, full_name, department, role))
    if role:
        cursor.execute('UPDATE users SET role = ?, department = ?, full_name = ? WHERE user_id = ?', (role, department, full_name, user_id))
    conn.commit()
    conn.close()

def get_user_info(user_id):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT role, department, is_blocked FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        role, department, is_blocked = row
        if is_blocked == 1:
            return "BLOCKED", None
        return role, department
    return None, None

def update_user_role_dept(user_id, department, role):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET department = ?, role = ? WHERE user_id = ?', (department, role, user_id))
    conn.commit()
    conn.close()

def set_user_block_status(user_id, status):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_blocked = ? WHERE user_id = ?', (status, user_id))
    conn.commit()
    conn.close()

def save_attendance(user_id, full_name, department, role, action, time, status, distance):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attendance (user_id, full_name, department, role, action, time, status, distance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, full_name, department, role, action, time, status, distance))
    conn.commit()
    conn.close()
