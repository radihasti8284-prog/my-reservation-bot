import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# توکن از متغیر محیطی خوانده می‌شود
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


# --- تابع دستور /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ساخت دکمه برای باز کردن مینی‌اپ
    keyboard = [
        [InlineKeyboardButton("📅 رزرو نوبت", web_app={"url": "https://your-app-id.iran.liara.ir/app"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "به ربات رزرو آرایشگاه خوش آمدید! 👋\n"
        "برای رزرو نوبت، روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup
    )


# --- تابع دستور /menu ---
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 منوی اصلی:\n"
        "1. رزرو نوبت جدید\n"
        "2. لغو نوبت\n"
        "3. مشاهده نوبت‌های من"
    )


# --- تابع دستور /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 راهنمای ربات:\n"
        "/start - شروع و مشاهده دکمه رزرو\n"
        "/menu - مشاهده منوی اصلی\n"
        "/help - مشاهده این راهنما"
    )


# --- ساخت اپلیکیشن ربات (برای Webhook) ---
def create_bot_application():
    application = (
        Application.builder()
        .token(TOKEN)
        .updater(None)  # غیرفعال کردن Polling (برای Webhook)
        .build()
    )

    # ثبت دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("help", help_command))

    return application