from flask import Flask, request, jsonify, send_from_directory
import os
import requests
import sqlite3
import json
import time
from werkzeug.utils import secure_filename
from datetime import datetime
from database import (
    get_db, get_support_contact, update_support_contact,
    get_daily_capacity, increment_capacity, decrement_capacity
)
from scheduler import start_scheduler
import jdatetime  # برای تاریخ شمسی دقیق

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
                             f"ارتباط با ادمین: {get_support_contact()}\n\n"
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

# --- احراز هویت ---
@app.route('/api/auth', methods=['POST'])
def auth_user():
    data = request.get_json()
    user = get_or_create_user(data['telegram_id'], data['name'], data['phone'])
    if not user:
        return jsonify({"status": "error", "message": "Failed"}), 500
    return jsonify({"status": "ok", "user": user})


# --- دریافت خدمات ---
@app.route('/api/services', methods=['GET'])
def get_services():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM services WHERE is_active = 1")
    services = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "services": [dict(s) for s in services]})


# --- آپلود فایل ---
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


# --- ثبت نوبت جدید (با بررسی ظرفیت) ---
@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    service_id = data.get('service_id')
    app_date = data.get('date')
    app_time = data.get('time')
    receipt_url = data.get('receipt')

    # بررسی ظرفیت
    remaining = get_daily_capacity(app_date, app_time)
    if remaining <= 0:
        return jsonify(
            {"status": "error", "message": "ظرفیت این ساعت تکمیل شده است. لطفاً ساعت دیگری را انتخاب کنید."}), 400

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

    # افزایش ظرفیت
    increment_capacity(app_date, app_time)

    return jsonify({"status": "ok", "message": "نوبت ثبت شد! منتظر تأیید ادمین باشید."})


# --- دریافت نوبت‌های کاربر ---
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


# --- ویرایش نوبت (تاریخ و ساعت) ---
@app.route('/api/appointments/<int:appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    data = request.get_json()
    new_date = data.get('date')
    new_time = data.get('time')
    telegram_id = data.get('telegram_id')

    # بررسی ظرفیت برای زمان جدید
    remaining = get_daily_capacity(new_date, new_time)
    if remaining <= 0:
        return jsonify({"status": "error", "message": "ظرفیت این ساعت تکمیل شده است."}), 400

    conn = get_db()
    cursor = conn.cursor()

    # دریافت اطلاعات نوبت فعلی
    cursor.execute("SELECT appointment_date, appointment_time FROM appointments WHERE id = ?", (appointment_id,))
    old = cursor.fetchone()
    if not old:
        conn.close()
        return jsonify({"status": "error", "message": "نوبت پیدا نشد."}), 404

    # بروزرسانی نوبت
    cursor.execute('''
        UPDATE appointments 
        SET appointment_date = ?, appointment_time = ? 
        WHERE id = ? AND status = 'pending'
    ''', (new_date, new_time, appointment_id))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"status": "error", "message": "فقط نوبت‌های در انتظار قابل ویرایش هستند."}), 400

    # بروزرسانی ظرفیت
    decrement_capacity(old['appointment_date'], old['appointment_time'])
    increment_capacity(new_date, new_time)

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "نوبت با موفقیت ویرایش شد."})


# --- لغو نوبت ---
@app.route('/api/appointments/<int:appointment_id>/cancel', methods=['POST'])
def cancel_appointment(appointment_id):
    conn = get_db()
    cursor = conn.cursor()

    # دریافت تاریخ و ساعت برای کاهش ظرفیت
    cursor.execute("SELECT appointment_date, appointment_time FROM appointments WHERE id = ?", (appointment_id,))
    app = cursor.fetchone()

    cursor.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()

    if app:
        decrement_capacity(app['appointment_date'], app['appointment_time'])

    return jsonify({"status": "ok", "message": "نوبت لغو شد."})


# --- دریافت نوبت‌های ادمین ---
@app.route('/api/admin/appointments', methods=['GET'])
def admin_get_appointments():
    status_filter = request.args.get('status')
    date_filter = request.args.get('date')
    user_filter = request.args.get('user')

    conn = get_db()
    cursor = conn.cursor()

    query = '''
        SELECT a.*, u.name as user_name, u.phone, u.telegram_id, s.name as service_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        WHERE 1=1
    '''
    params = []

    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)
    if date_filter:
        query += " AND a.appointment_date = ?"
        params.append(date_filter)
    if user_filter:
        query += " AND u.telegram_id = ?"
        params.append(user_filter)

    query += " ORDER BY a.appointment_date DESC"

    cursor.execute(query, params)
    apps = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "appointments": [dict(a) for a in apps]})


# --- تغییر وضعیت نوبت توسط ادمین ---
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

    # اگر تأیید شد، ظرفیت قبلاً در زمان ثبت افزایش یافته، نیازی به تغییر نیست
    cursor.execute("UPDATE appointments SET status = ?, notification_sent = 0 WHERE id = ?",
                   (new_status, appointment_id))
    conn.commit()
    conn.close()

    if appointment and new_status == 'confirmed':
        user_telegram_id = appointment['telegram_id']
        msg = f"✅ نوبت شما با موفقیت تأیید شد!\n\n📅 تاریخ: {appointment['appointment_date']}\n🕐 ساعت: {appointment['appointment_time']}\n💇 خدمت: {appointment['service_name']}\n\n⚠️ نکته: در صورت عدم حضور در وقت تعیین‌شده، نوبت شما از بین خواهد رفت.\n\nلطفاً در زمان مقرر حضور داشته باشید."
        send_message(user_telegram_id, msg)

    return jsonify({"status": "ok", "message": f"وضعیت به {new_status} تغییر کرد."})


# --- مدیریت کاربران پیشرفته ---
@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, telegram_id, name, phone, is_admin, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    return jsonify({"status": "ok", "users": [dict(u) for u in users]})


@app.route('/api/admin/users/<int:telegram_id>', methods=['PUT'])
def admin_update_user(telegram_id):
    data = request.get_json()
    is_admin = data.get('is_admin', 0)
    name = data.get('name')

    conn = get_db()
    cursor = conn.cursor()
    if name:
        cursor.execute("UPDATE users SET name = ? WHERE telegram_id = ?", (name, telegram_id))
    cursor.execute("UPDATE users SET is_admin = ? WHERE telegram_id = ?", (is_admin, telegram_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "کاربر به‌روزرسانی شد."})


@app.route('/api/admin/users/<int:telegram_id>', methods=['DELETE'])
def admin_delete_user(telegram_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "کاربر حذف شد."})


# --- آمار ---
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


# --- نظردهی ---
@app.route('/api/reviews', methods=['POST'])
def add_review():
    data = request.get_json()
    user_id = data.get('user_id')
    appointment_id = data.get('appointment_id')
    rating = data.get('rating')
    comment = data.get('comment', '')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reviews (user_id, appointment_id, rating, comment) VALUES (?, ?, ?, ?)",
        (user_id, appointment_id, rating, comment)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "نظر شما با موفقیت ثبت شد."})


@app.route('/api/reviews/<int:appointment_id>', methods=['GET'])
def get_review(appointment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews WHERE appointment_id = ?", (appointment_id,))
    review = cursor.fetchone()
    conn.close()
    return jsonify({"status": "ok", "review": dict(review) if review else None})


# --- تنظیمات پشتیبانی (ادمین) ---
@app.route('/api/admin/support', methods=['GET'])
def get_support():
    return jsonify({"status": "ok", "support_contact": get_support_contact()})


@app.route('/api/admin/support', methods=['POST'])
def update_support():
    data = request.get_json()
    new_value = data.get('support_contact')
    if not new_value:
        return jsonify({"status": "error", "message": "مقدار پشتیبانی الزامی است."}), 400
    update_support_contact(new_value)
    return jsonify({"status": "ok", "message": "شماره پشتیبانی به‌روزرسانی شد."})


# --- ساعات کاری (با ظرفیت) ---
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
    capacity = data.get('capacity', 2)
    is_active = data.get('is_active', 1)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE work_schedule 
        SET start_time = ?, end_time = ?, capacity = ?, is_active = ? 
        WHERE day_of_week = ?
    ''', (start_time, end_time, capacity, is_active, day_of_week))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "ساعت کاری به‌روز شد."})


# --- اعلان همگانی ---
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


# --- خروجی اکسل ---
@app.route('/api/admin/export/excel', methods=['GET'])
def export_excel():
    import openpyxl
    from openpyxl.styles import Font, Alignment
    from io import BytesIO

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

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "نوبت‌ها"

    # هدر
    headers = ['شناسه', 'کاربر', 'شماره تماس', 'خدمت', 'تاریخ', 'ساعت', 'وضعیت', 'تاریخ ثبت']
    for i, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # داده‌ها
    for row_idx, app in enumerate(apps, 2):
        ws.cell(row=row_idx, column=1, value=app['id'])
        ws.cell(row=row_idx, column=2, value=app['user_name'])
        ws.cell(row=row_idx, column=3, value=app['phone'])
        ws.cell(row=row_idx, column=4, value=app['service_name'])
        ws.cell(row=row_idx, column=5, value=app['appointment_date'])
        ws.cell(row=row_idx, column=6, value=app['appointment_time'])
        ws.cell(row=row_idx, column=7, value=app['status'])
        ws.cell(row=row_idx, column=8, value=app['created_at'])

    for col in range(1, 9):
        ws.column_dimensions[chr(64 + col)].width = 18

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"nobat-ha-{datetime.now().strftime('%Y%m%d')}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# --- تاریخ شمسی دقیق (با jdatetime) ---
@app.route('/api/persian_date', methods=['GET'])
def get_persian_date():
    now = jdatetime.datetime.now()
    return jsonify({
        "status": "ok",
        "date": now.strftime("%Y/%m/%d"),
        "time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A")
    })


# ========== سرو فایل‌های استاتیک ==========
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/')
def home():
    return "✅ ربات رزرو آرایشگاه M4Cut روشن است!"


if __name__ == "__main__":
    # شروع scheduler برای یادآوری خودکار
    start_scheduler()

    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)