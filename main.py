from flask import Flask, request, jsonify, send_from_directory
import os
import requests
import sqlite3
import json
import time
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()]


# ========== دیتابیس ==========
def get_db():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("PRAGMA table_info(appointments)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'notification_sent' not in cols:
        cursor.execute("ALTER TABLE appointments ADD COLUMN notification_sent INTEGER DEFAULT 0")

    cursor.execute("PRAGMA table_info(services)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'description' not in cols:
        cursor.execute("ALTER TABLE services ADD COLUMN description TEXT")

    cursor.execute("DELETE FROM services")
    services = [
        ('✂️ کوتاهی مو', 30, 200000,
         '✨ کوتاهی و اصلاح مو با جدیدترین متدها.\n\n💳 مبلغ بیعانه: ۲۰۰,۰۰۰ تومان\n⚠️ نکته: در صورت عدم حضور در وقت تعیین‌شده، نوبت شما از بین خواهد رفت.')
    ]
    cursor.executemany(
        "INSERT INTO services (name, duration, price, description) VALUES (?, ?, ?, ?)",
        services
    )

    cursor.execute("SELECT COUNT(*) FROM work_schedule")
    if cursor.fetchone()[0] == 0:
        default_schedule = [
            (0, '09:00', '18:00', 1),
            (1, '09:00', '18:00', 1),
            (2, '09:00', '18:00', 1),
            (3, '09:00', '18:00', 1),
            (4, '09:00', '18:00', 1),
            (5, '09:00', '14:00', 0),
            (6, '09:00', '14:00', 0),
        ]
        cursor.executemany(
            "INSERT INTO work_schedule (day_of_week, start_time, end_time, is_active) VALUES (?, ?, ?, ?)",
            default_schedule
        )

    conn.commit()
    conn.close()
    print("✅ دیتابیس راه‌اندازی شد")


init_db()


# ========== توابع کمکی ==========
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Error: {e}")


def get_or_create_user(telegram_id, name, phone):
    if not telegram_id:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    if user:
        conn.close()
        return dict(user)
    is_admin = 1 if telegram_id in ADMIN_IDS else 0
    cursor.execute(
        "INSERT INTO users (telegram_id, name, phone, is_admin) VALUES (?, ?, ?, ?)",
        (telegram_id, name, phone, is_admin)
    )
    conn.commit()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_all_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [u['telegram_id'] for u in users]


def send_broadcast(message):
    users = get_all_users()
    success_count = 0
    for chat_id in users:
        try:
            send_message(chat_id, f"📢 اعلان همگانی:\n\n{message}")
            success_count += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ Failed to send to {chat_id}: {e}")
    return success_count


# ========== وب‌هوک ==========
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print(f"📩 Received: {data}")
        if 'message' in data:
            msg = data['message']
            chat_id = msg['chat']['id']
            text = msg.get('text', '')
            user = msg.get('from', {})
            telegram_id = user.get('id')
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            get_or_create_user(telegram_id, full_name, "")

            if text == '/start':
                send_message(chat_id,
                             "✨ سلام دوست عزیز به **M4Cut** خوش آمدید! ✨\n\n"
                             "💇‍♂️ **آرایشگاه تخصصی مردانه**\n"
                             "با ما بهترین تجربه‌ی کوتاهی مو را داشته باشید.\n\n"
                             "🔹 **خدمات ما:**\n"
                             "✂️ کوتاهی موی حرفه‌ای (مخصوص آقایان)\n"
                             "✨ اصلاح و استایل‌دهی با جدیدترین متدها\n"
                             "💆‍♂️ مشاوره رایگان قبل از هر سرویس\n\n"
                             "📅 **رزرو آسان و سریع**\n"
                             "فقط با چند کلیک، نوبت خود را ثبت کنید.\n\n"
                             "💳 **بیعانه:** ۲۰۰,۰۰۰ تومان (قابل بازگشت در صورت حضور)\n"
                             "⚠️ توجه: در صورت عدم حضور، نوبت شما از بین خواهد رفت.\n\n"
                             "📞 **پشتیبانی:**\n"
                             "برای راهنمایی و ارتباط با ادمین، از دستور /admin استفاده کنید.\n\n"
                             "👇 برای رزرو نوبت، روی دکمه زیر کلیک کنید:",
                             reply_markup={
                                 "inline_keyboard": [[
                                     {"text": "📅 رزرو نوبت",
                                      "web_app": {"url": "https://my-reservation-bot.onrender.com/static/landing.html"}}
                                 ]]
                             }
                             )
            elif text == '/admin':
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (chat_id,))
                row = cursor.fetchone()
                conn.close()
                if row and row['is_admin'] == 1:
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


# ========== API ==========
@app.route('/api/auth', methods=['POST'])
def auth_user():
    data = request.get_json()
    user = get_or_create_user(data['telegram_id'], data['name'], data['phone'])
    if not user:
        return jsonify({"status": "error", "message": "Failed"}), 500
    return jsonify({"status": "ok", "user": user})


@app.route('/api/services', methods=['GET'])
def get_services():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM services WHERE is_active = 1")
    services = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "services": [dict(s) for s in services]})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    if file and allowed_file(file.filename):
        filename = f"{int(time.time())}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        url = f"/static/uploads/{filename}"
        return jsonify({"status": "ok", "url": url})
    return jsonify({"status": "error", "message": "Invalid format"}), 400


@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    service_id = data.get('service_id')
    app_date = data.get('date')
    app_time = data.get('time')
    receipt_url = data.get('receipt')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    if not user:
        user_dict = get_or_create_user(telegram_id, "کاربر", "")
        if user_dict:
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"status": "error", "message": "User not found. Please use /start first."}), 404

    cursor.execute('''
        INSERT INTO appointments (user_id, service_id, appointment_date, appointment_time, status, receipt)
        VALUES (?, ?, ?, ?, 'pending', ?)
    ''', (user['id'], service_id, app_date, app_time, receipt_url))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "نوبت ثبت شد! منتظر تأیید ادمین باشید."})


@app.route('/api/appointments/user/<int:telegram_id>', methods=['GET'])
def get_user_appointments(telegram_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, s.name as service_name, s.description as service_description
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        WHERE u.telegram_id = ?
        ORDER BY a.appointment_date DESC
    ''', (telegram_id,))
    apps = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "appointments": [dict(a) for a in apps]})


@app.route('/api/admin/appointments', methods=['GET'])
def admin_get_appointments():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, u.name as user_name, u.phone, u.telegram_id, s.name as service_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        ORDER BY a.appointment_date DESC
    ''')
    apps = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "appointments": [dict(a) for a in apps]})


@app.route('/api/admin/appointments/<int:appointment_id>/status', methods=['POST'])
def admin_update_status(appointment_id):
    data = request.get_json()
    new_status = data.get('status')
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.user_id, u.telegram_id, a.appointment_date, a.appointment_time, s.name as service_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        WHERE a.id = ?
    ''', (appointment_id,))
    appointment = cursor.fetchone()

    cursor.execute("UPDATE appointments SET status = ?, notification_sent = 0 WHERE id = ?",
                   (new_status, appointment_id))
    conn.commit()
    conn.close()

    if appointment and new_status == 'confirmed':
        user_telegram_id = appointment['telegram_id']
        msg = f"✅ نوبت شما با موفقیت تأیید شد!\n\n📅 تاریخ: {appointment['appointment_date']}\n🕐 ساعت: {appointment['appointment_time']}\n💇 خدمت: {appointment['service_name']}\n\n⚠️ نکته: در صورت عدم حضور در وقت تعیین‌شده، نوبت شما از بین خواهد رفت.\n\nلطفاً در زمان مقرر حضور داشته باشید."
        send_message(user_telegram_id, msg)

    return jsonify({"status": "ok", "message": f"وضعیت به {new_status} تغییر کرد."})


@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, telegram_id, name, phone, is_admin, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "users": [dict(u) for u in users]})


@app.route('/api/admin/stats', methods=['GET'])
def admin_get_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]
    cursor.execute("SELECT status, COUNT(*) as count FROM appointments GROUP BY status")
    status_counts = cursor.fetchall()
    status_stats = {row['status']: row['count'] for row in status_counts}
    today = datetime.now().strftime("%Y/%m/%d")
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = ?", (today,))
    today_appointments = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date >= ?", (today,))
    upcoming_appointments = cursor.fetchone()[0]
    conn.close()
    return jsonify({
        "status": "ok",
        "stats": {
            "total_users": total_users,
            "total_appointments": total_appointments,
            "today_appointments": today_appointments,
            "upcoming_appointments": upcoming_appointments,
            "status": {
                "pending": status_stats.get('pending', 0),
                "confirmed": status_stats.get('confirmed', 0),
                "completed": status_stats.get('completed', 0),
                "cancelled": status_stats.get('cancelled', 0)
            }
        }
    })


@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast():
    data = request.get_json()
    message = data.get('message')
    if not message:
        return jsonify({"status": "error", "message": "Message required"}), 400
    count = send_broadcast(message)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO broadcasts (message) VALUES (?)", (message,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": f"پیام به {count} کاربر ارسال شد."})


@app.route('/api/admin/schedule', methods=['GET'])
def get_schedule():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM work_schedule ORDER BY day_of_week")
    schedule = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "schedule": [dict(s) for s in schedule]})


@app.route('/api/admin/schedule', methods=['POST'])
def update_schedule():
    data = request.get_json()
    day_of_week = data.get('day_of_week')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    is_active = data.get('is_active', 1)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE work_schedule 
        SET start_time = ?, end_time = ?, is_active = ? 
        WHERE day_of_week = ?
    ''', (start_time, end_time, is_active, day_of_week))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "ساعت کاری به‌روز شد."})


@app.route('/api/admin/services', methods=['POST'])
def admin_add_service():
    return jsonify({"status": "error", "message": "افزودن خدمات جدید مجاز نیست. فقط خدمت کوتاهی مو موجود است."}), 403


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/')
def home():
    return "✅ ربات رزرو آرایشگاه M4Cut روشن است!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)