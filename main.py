from flask import Flask, request, jsonify, send_from_directory
import os
import requests
import sqlite3
import json
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"

# تنظیمات آپلود
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    ''')
    # اضافه کردن ستون receipt اگه وجود نداره
    cursor.execute("PRAGMA table_info(appointments)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'receipt' not in cols:
        cursor.execute("ALTER TABLE appointments ADD COLUMN receipt TEXT")

    # خدمات پیش‌فرض
    cursor.execute("SELECT COUNT(*) FROM services")
    if cursor.fetchone()[0] == 0:
        services = [
            ('کوتاهی موی مردانه', 30, 150000, 'کوتاهی و اصلاح مو'),
            ('اصلاح صورت', 20, 100000, 'اصلاح ریش و سبیل'),
            ('کوتاهی موی زنانه', 45, 250000, 'کوتاهی و لایه‌لایه'),
            ('رنگ مو', 60, 350000, 'رنگ‌آمیزی حرفه‌ای'),
        ]
        cursor.executemany("INSERT INTO services (name, duration, price, description) VALUES (?, ?, ?, ?)", services)
    conn.commit()
    conn.close()


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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    if user:
        conn.close()
        return dict(user)
    is_admin = 1 if telegram_id in ADMIN_IDS else 0
    cursor.execute("INSERT INTO users (telegram_id, name, phone, is_admin) VALUES (?, ?, ?, ?)",
                   (telegram_id, name, phone, is_admin))
    conn.commit()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
                             "👋 به ربات رزرو آرایشگاه خوش آمدید!\nبرای رزرو روی دکمه زیر کلیک کنید:",
                             reply_markup={
                                 "inline_keyboard": [[
                                     {"text": "📅 رزرو نوبت",
                                      "web_app": {"url": "https://my-reservation-bot.onrender.com/static/user.html"}}
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
        conn.close()
        return jsonify({"status": "error", "message": "User not found"}), 404

    cursor.execute('''
        INSERT INTO appointments (user_id, service_id, appointment_date, appointment_time, status, receipt)
        VALUES (?, ?, ?, ?, 'pending', ?)
    ''', (user['id'], service_id, app_date, app_time, receipt_url))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "نوبت با موفقیت ثبت شد! منتظر تأیید ادمین باشید."})


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
    apps = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "appointments": [dict(a) for a in apps]})


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
    apps = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "appointments": [dict(a) for a in apps]})


@app.route('/api/admin/appointments/<int:appointment_id>/status', methods=['POST'])
def admin_update_status(appointment_id):
    data = request.get_json()
    new_status = data.get('status')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, appointment_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": f"وضعیت به {new_status} تغییر کرد."})


@app.route('/api/admin/services', methods=['POST'])
def admin_add_service():
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO services (name, duration, price, description) VALUES (?, ?, ?, ?)",
                   (data['name'], data['duration'], data['price'], data.get('description', '')))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "خدمت اضافه شد."})


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/')
def home():
    return "✅ ربات رزرو آرایشگاه روشن است!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)