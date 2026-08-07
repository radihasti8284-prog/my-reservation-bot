from fastapi import FastAPI
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import uvicorn

app = FastAPI()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# تابع ساده برای /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! ربات با موفقیت روی Render اجرا شده! 🎉")

# ساختن اپلیکیشن ربات
def create_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    return application

# مسیر webhook برای دریافت پیام‌ها از تلگرام
@app.post("/webhook")
async def webhook(request):
    bot_app = create_bot()
    await bot_app.initialize()
    await bot_app.process_update(await request.json())
    return {"status": "ok"}

# یه مسیر ساده برای اینکه مطمئن بشی سرور روشنه
@app.get("/")
def root():
    return {"message": "ربات روشن است!"}

# اجرا با پورتی که Render بهمون میده
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)