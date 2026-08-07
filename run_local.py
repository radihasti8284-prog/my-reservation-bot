import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler
from telegram.request import HTTPXRequest

# بارگذاری متغیرهای محیطی
load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- تنظیمات پروکسی (پیش‌فرض روی 127.0.0.1:1080 - مناسب برای Shadowsocks/V2Ray) ---
PROXY_TYPE = os.environ.get("PROXY_TYPE", "socks5")  # socks5 یا http
PROXY_HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("PROXY_PORT", 1080))
PROXY_USER = os.environ.get("PROXY_USER", "")  # خالی بگذارید اگر احراز هویت ندارد
PROXY_PASS = os.environ.get("PROXY_PASS", "")  # خالی بگذارید اگر احراز هویت ندارد


# --- ساخت آدرس پروکسی ---
def get_proxy_url():
    if not PROXY_HOST or not PROXY_PORT:
        return None

    protocol = "socks5" if PROXY_TYPE == "socks5" else "http"

    # اگر احراز هویت دارید
    if PROXY_USER and PROXY_PASS:
        return f"{protocol}://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
    return f"{protocol}://{PROXY_HOST}:{PROXY_PORT}"


# --- توابع دستورات ربات ---
async def start(update, context):
    await update.message.reply_text(
        "به ربات رزرو آرایشگاه خوش آمدید! 👋\n"
        "این نسخه برای تست محلی است."
    )


async def menu(update, context):
    await update.message.reply_text("📋 منوی اصلی (محلی)")


async def help_command(update, context):
    await update.message.reply_text("🤖 راهنمای ربات (محلی)")


# --- اجرای ربات با پروکسی ---
def main():
    # رفع مشکل event loop در پایتون ۳.۱۴
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # ساخت درخواست با پروکسی
    proxy_url = get_proxy_url()
    if proxy_url:
        print(f"🔒 استفاده از پروکسی: {proxy_url}")
        request = HTTPXRequest(proxy=proxy_url)
    else:
        print("⚠️ پروکسی تنظیم نشده. اتصال مستقیم...")
        request = HTTPXRequest()

    # ساخت اپلیکیشن
    application = (
        Application.builder()
        .token(TOKEN)
        .request(request)
        .build()
    )

    # ثبت دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("help", help_command))

    print("🚀 ربات در حالت محلی (Polling) شروع به کار کرد...")
    print("📨 برای توقف، کلید Ctrl+C را بزنید.")
    application.run_polling()


if __name__ == "__main__":
    main()