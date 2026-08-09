from flask import Flask, request, jsonify, send_from_directory
import os
import requests
import json
from datetime import datetime, date
import sqlite3
from database import get_db, init_db

app = Flask(__name__)
TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"

# ========== راه‌اندازی اولیه ==========
init_db()


# ========== وب‌هوک تلگرام ==========
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print(f"📩 Received: {data}")

        if 'message' in data:
            msg = data['message']
            chat_id = msg['chat']['id']
            text = msg.get('text', '')

            if text == '/start':
                send_message(chat_id,
                             "👋 به ربات رزرو آرایشگاه خوش آمدید!\n"
                             "برای رزرو نوبت، روی دکمه زیر کلیک کنید:",
                             reply_markup={
                                 "inline_keyboard": [[
                                     {"text": "📅 رزرو نوبت",
                                      "web_app": {"url": "https://my-reservation-bot.onrender.com/static/user.html"}}
                                 ]]
                             }
                             )
            elif text == '/admin':
                # بررسی ادمین بودن
                user = get_user_by_telegram_id(chat_id)
                if user and user['is_admin'] == 1:
                    send_message(chat_id,
                                 "👋 به پنل ادمین خوش آمدید!",
                                 reply_markup={
                                     "inline_keyboard": [[
                                         {"text": "📊 مدیریت نوبت‌ها", "web_app": {
                                             "url": "https://my-reservation-bot.onrender.com/static/admin.html"}}
                                     ]]
                                 }
                                 )
                else:
                    send_message(chat_id, "⛔ شما دسترسی ادمین ندارید.")
            else:
                send_message(chat_id, "❓ دستور نامعتبر. از /start استفاده کنید.")

        return {"status": "ok"}, 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"status": "error"}, 500


# ========== API برای مینی‌اپ ==========

# ---- ثبت/ورود کاربر ----
@app.route('/api/auth', methods=['POST'])
def auth_user():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    name = data.get('name')
    phone = data.get('phone')

    if not telegram_id:
        return jsonify({"status": "error", "message": "telegram_id required"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # بررسی وجود کاربر
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    if user:
        return jsonify({"status": "ok", "user": dict(user)})
    else:
        # ثبت کاربر جدید
        cursor.execute(
            "INSERT INTO users (telegram_id, name, phone) VALUES (?, ?, ?)",
            (telegram_id, name, phone)
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        return jsonify({"status": "ok", "user": dict(user)})


# ---- دریافت لیست خدمات ----
@app.route('/api/services', methods=['GET'])
def get_services():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM services WHERE is_active = 1")
    services = cursor.fetchall()
    return jsonify({"status": "ok", "services": [dict(s) for s in services]})


# ---- دریافت نوبت‌های یک کاربر ----
@app.route('/api/appointments/user/<int:telegram_id>', methods=['GET'])
def get_user_appointments(telegram_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, s.name as service_name 
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        WHERE u.telegram_id = ?
        ORDER BY a.appointment_date DESC
    ''', (telegram_id,))
    appointments = cursor.fetchall()
    return jsonify({"status": "ok", "appointments": [dict(a) for a in appointments]})


# ---- ثبت نوبت جدید ----
@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    service_id = data.get('service_id')
    app_date = data.get('date')
    app_time = data.get('time')

    conn = get_db()
    cursor = conn.cursor()

    # پیدا کردن کاربر
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # ثبت نوبت
    cursor.execute('''
        INSERT INTO appointments (user_id, service_id, appointment_date, appointment_time, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (user['id'], service_id, app_date, app_time))
    conn.commit()

    # ارسال پیام به ادمین‌ها
    notify_admins(f"📢 نوبت جدید ثبت شد:\nکاربر: {telegram_id}\nتاریخ: {app_date}\nساعت: {app_time}")

    return jsonify({"status": "ok", "message": "نوبت با موفقیت ثبت شد!"})


# ---- لغو نوبت ----
@app.route('/api/appointments/<int:appointment_id>/cancel', methods=['POST'])
def cancel_appointment(appointment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appointment_id,))
    conn.commit()
    return jsonify({"status": "ok", "message": "نوبت لغو شد."})


@app.route('/api/make_admin', methods=['GET'])
def make_admin():
    telegram_id = request.args.get('telegram_id')
    if not telegram_id:
        return jsonify({"status": "error", "message": "telegram_id required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_admin = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()

    if cursor.rowcount > 0:
        return jsonify({"status": "ok", "message": f"User {telegram_id} is now admin!"})
    else:
        return jsonify({"status": "error", "message": "User not found. Please use /start first."}), 404
# ---- ادمین: دریافت همه نوبت‌ها ----
@app.route('/api/admin/appointments', methods=['GET'])
def admin_get_appointments():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, u.name as user_name, u.phone, s.name as service_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        ORDER BY a.appointment_date DESC
    ''')
    appointments = cursor.fetchall()
    return jsonify({"status": "ok", "appointments": [dict(a) for a in appointments]})


# ---- ادمین: تغییر وضعیت نوبت ----
@app.route('/api/admin/appointments/<int:appointment_id>/status', methods=['POST'])
def admin_update_status(appointment_id):
    data = request.get_json()
    new_status = data.get('status')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, appointment_id))
    conn.commit()
    return jsonify({"status": "ok", "message": f"وضعیت به {new_status} تغییر کرد."})


# ---- ادمین: اضافه کردن خدمت ----
@app.route('/api/admin/services', methods=['POST'])
def admin_add_service():
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO services (name, duration, price, description) VALUES (?, ?, ?, ?)",
        (data['name'], data['duration'], data['price'], data.get('description', ''))
    )
    conn.commit()
    return jsonify({"status": "ok", "message": "خدمت اضافه شد."})


# ========== توابع کمکی ==========
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Error sending message: {e}")


def get_user_by_telegram_id(telegram_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    return cursor.fetchone()


def notify_admins(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users WHERE is_admin = 1")
    admins = cursor.fetchall()
    for admin in admins:
        send_message(admin['telegram_id'], message)


# ========== سرو فایل‌های استاتیک ==========
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/')
def home():
    return "✅ ربات رزرو آرایشگاه روشن است!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)