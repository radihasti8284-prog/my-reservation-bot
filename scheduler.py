import time
import threading
from datetime import datetime, timedelta
from database import get_db
import requests
import os

TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"⚠️ Error sending reminder: {e}")


def check_and_send_reminders():
    """بررسی نوبت‌های فردا و امروز و ارسال یادآوری"""
    conn = get_db()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y/%m/%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y/%m/%d")

    # نوبت‌های فردا که یادآوری نشده‌اند
    cursor.execute('''
        SELECT a.id, a.user_id, a.appointment_date, a.appointment_time, 
               u.telegram_id, s.name as service_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        WHERE a.appointment_date = ? 
        AND a.status = 'confirmed' 
        AND a.notification_sent = 0
    ''', (tomorrow,))
    tomorrow_apps = cursor.fetchall()

    for app in tomorrow_apps:
        msg = f"🔔 یادآوری نوبت فردا!\n\n📅 تاریخ: {app['appointment_date']}\n🕐 ساعت: {app['appointment_time']}\n💇 خدمت: {app['service_name']}\n\n⚠️ لطفاً ۱۰ دقیقه قبل از ساعت رزرو در سالن حضور داشته باشید."
        send_message(app['telegram_id'], msg)
        cursor.execute("UPDATE appointments SET notification_sent = 1 WHERE id = ?", (app['id'],))

    # نوبت‌های امروز (۲ ساعت قبل)
    now = datetime.now()
    two_hours_later = (now + timedelta(hours=2)).strftime("%H:%M")
    today_date = now.strftime("%Y/%m/%d")

    cursor.execute('''
        SELECT a.id, a.user_id, a.appointment_date, a.appointment_time, 
               u.telegram_id, s.name as service_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        WHERE a.appointment_date = ? 
        AND a.appointment_time <= ? 
        AND a.status = 'confirmed' 
        AND a.notification_sent = 0
    ''', (today_date, two_hours_later))
    today_apps = cursor.fetchall()

    for app in today_apps:
        msg = f"🔔 یادآوری نوبت امروز!\n\n📅 تاریخ: {app['appointment_date']}\n🕐 ساعت: {app['appointment_time']}\n💇 خدمت: {app['service_name']}\n\n⚠️ لطفاً در زمان مقرر حضور داشته باشید."
        send_message(app['telegram_id'], msg)
        cursor.execute("UPDATE appointments SET notification_sent = 1 WHERE id = ?", (app['id'],))

    conn.commit()
    conn.close()


def start_scheduler():
    """اجرای scheduler در یک ترد جداگانه"""

    def run():
        while True:
            try:
                check_and_send_reminders()
            except Exception as e:
                print(f"⚠️ Scheduler error: {e}")
            time.sleep(3600)  # هر ۱ ساعت یک بار اجرا کن

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    print("✅ Scheduler برای یادآوری خودکار راه‌اندازی شد.")