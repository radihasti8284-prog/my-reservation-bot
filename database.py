import sqlite3
from datetime import datetime
import os

DB_PATH = 'data.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # ====== جدول users ======
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            phone TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ====== جدول services ======
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

    # ====== جدول appointments ======
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER,
            appointment_date TEXT,
            appointment_time TEXT,
            status TEXT DEFAULT 'pending',
            receipt TEXT,
            notification_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    ''')

    # ====== جدول work_schedule (ساعات کاری - برای ظرفیت‌دهی) ======
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            capacity INTEGER DEFAULT 2,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # ====== جدول capacity (ظرفیت روزانه - جدید) ======
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_capacity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            booked_count INTEGER DEFAULT 0,
            max_capacity INTEGER DEFAULT 2,
            UNIQUE(appointment_date, appointment_time)
        )
    ''')

    # ====== جدول reviews (نظردهی - جدید) ======
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            appointment_id INTEGER,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        )
    ''')

    # ====== جدول settings (تنظیمات - جدید برای پشتیبانی) ======
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ====== جدول broadcasts ======
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ====== اضافه کردن ستون‌های جدید (سازگاری با نسخه‌های قبلی) ======
    cursor.execute("PRAGMA table_info(appointments)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'notification_sent' not in cols:
        cursor.execute("ALTER TABLE appointments ADD COLUMN notification_sent INTEGER DEFAULT 0")

    cursor.execute("PRAGMA table_info(services)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'description' not in cols:
        cursor.execute("ALTER TABLE services ADD COLUMN description TEXT")

    # ====== تنظیمات پیش‌فرض ساعات کاری با ظرفیت ======
    cursor.execute("SELECT COUNT(*) FROM work_schedule")
    if cursor.fetchone()[0] == 0:
        default_schedule = [
            (0, '09:00', '18:00', 2, 1),  # شنبه
            (1, '09:00', '18:00', 2, 1),  # یکشنبه
            (2, '09:00', '18:00', 2, 1),  # دوشنبه
            (3, '09:00', '18:00', 2, 1),  # سه‌شنبه
            (4, '09:00', '18:00', 2, 1),  # چهارشنبه
            (5, '09:00', '14:00', 1, 0),  # پنجشنبه
            (6, '09:00', '14:00', 0, 0),  # جمعه
        ]
        cursor.executemany(
            "INSERT INTO work_schedule (day_of_week, start_time, end_time, capacity, is_active) VALUES (?, ?, ?, ?, ?)",
            default_schedule
        )

    # ====== تنظیمات پیش‌فرض پشتیبانی ======
    cursor.execute("SELECT COUNT(*) FROM settings WHERE key = 'support_contact'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ('support_contact', '@Tvpnred')
        )

    # ====== خدمات پیش‌فرض ======
    cursor.execute("SELECT COUNT(*) FROM services")
    if cursor.fetchone()[0] == 0:
        services = [
            ('✂️ کوتاهی مو', 30, 200000,
             '✨ کوتاهی و اصلاح مو با جدیدترین متدها.\n\n💳 مبلغ بیعانه: ۲۰۰,۰۰۰ تومان\n⚠️ نکته: در صورت عدم حضور در وقت تعیین‌شده، نوبت شما از بین خواهد رفت.'),
        ]
        cursor.executemany(
            "INSERT INTO services (name, duration, price, description) VALUES (?, ?, ?, ?)",
            services
        )

    conn.commit()
    conn.close()
    print("✅ دیتابیس با تمام جداول جدید راه‌اندازی شد.")


# ====== توابع جدید ======

def get_support_contact():
    """دریافت شماره پشتیبانی از تنظیمات"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'support_contact'")
    result = cursor.fetchone()
    conn.close()
    return result['value'] if result else '@Tvpnred'


def update_support_contact(new_value):
    """به‌روزرسانی شماره پشتیبانی"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = 'support_contact'",
        (new_value,)
    )
    conn.commit()
    conn.close()


def get_daily_capacity(date, time_slot):
    """دریافت ظرفیت باقی‌مانده برای یک روز و ساعت خاص"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT booked_count, max_capacity FROM daily_capacity WHERE appointment_date = ? AND appointment_time = ?",
        (date, time_slot)
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return result['max_capacity'] - result['booked_count']
    # اگر رکوردی وجود نداشت، از تنظیمات عمومی استفاده کن
    # برای سادگی، ۲ ظرفیت پیش‌فرض
    return 2


def increment_capacity(date, time_slot):
    """افزایش تعداد نوبت‌های پر شده برای یک زمان"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO daily_capacity (appointment_date, appointment_time, booked_count, max_capacity) "
        "VALUES (?, ?, 1, 2) "
        "ON CONFLICT(appointment_date, appointment_time) DO UPDATE SET booked_count = booked_count + 1",
        (date, time_slot)
    )
    conn.commit()
    conn.close()


def decrement_capacity(date, time_slot):
    """کاهش تعداد نوبت‌های پر شده (برای لغو یا ویرایش)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE daily_capacity SET booked_count = booked_count - 1 "
        "WHERE appointment_date = ? AND appointment_time = ? AND booked_count > 0",
        (date, time_slot)
    )
    conn.commit()
    conn.close()


# اجرای اولیه
init_db()