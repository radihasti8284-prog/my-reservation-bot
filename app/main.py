import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.bot import create_bot_application


# --- مدیریت چرخه حیات (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # قبل از شروع سرور
    bot_app = create_bot_application()
    await bot_app.initialize()
    await bot_app.start()
    app.state.bot_app = bot_app

    yield  # سرور در این مرحله اجرا می‌شود

    # بعد از بسته شدن سرور
    await bot_app.stop()


# --- ایجاد اپلیکیشن FastAPI ---
app = FastAPI(lifespan=lifespan)


# --- Webhook برای دریافت آپدیت‌های تلگرام ---
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    # دریافت داده‌های ارسالی از تلگرام
    update_data = await request.json()

    # پردازش در پس‌زمینه برای پاسخ سریع
    bot_app = request.app.state.bot_app
    background_tasks.add_task(bot_app.process_update, update_data)

    return {"status": "ok"}


# --- مسیر تست برای اطمینان از روشن بودن سرور ---
@app.get("/")
async def root():
    return {"message": "ربات رزرو آرایشگاه فعال است!"}


# --- سرو کردن فایل‌های استاتیک مینی‌اپ ---
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- صفحه مینی‌اپ ---
@app.get("/app", response_class=HTMLResponse)
async def get_miniapp():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)