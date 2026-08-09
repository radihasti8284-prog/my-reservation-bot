import sqlite3
from datetime import datetime, date
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # جدول کاربران
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # جدول خدمات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration INTEGER DEFAULT 30,
            price INTEGER DEFAULT 0,
            description TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # جدول نوبت‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    ''')

    # اضافه کردن خدمات پیش‌فرض (اگه خالی باشه)
    cursor.execute("SELECT COUNT(*) FROM services")
    if cursor.fetchone()[0] == 0:
        services = [
            ('کوتاهی موی مردانه', 30, 150000, 'کوتاهی و اصلاح مو'),
            ('اصلاح صورت', 20, 100000, 'اصلاح ریش و سبیل'),
            ('کوتاهی موی زنانه', 45, 250000, 'کوتاهی و لایه‌لایه'),
            ('رنگ مو', 60, 350000, 'رنگ‌آمیزی حرفه‌ای'),
        ]
        cursor.executemany(
            "INSERT INTO services (name, duration, price, description) VALUES (?, ?, ?, ?)",
            services
        )

    conn.commit()
    conn.close()
    print("✅ دیتابیس راه‌اندازی شد.")


# اجرای اولیه
init_db()