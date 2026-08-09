from fastapi import FastAPI, Request
import os
import httpx
import uvicorn
import json

app = FastAPI()

TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"

# استفاده از api_route به جای post تا اعتبارسنجی خودکار FastAPI دور زده شود
@app.api_route("/webhook", methods=["POST"])
async def webhook(request: Request):
    try:
        # دریافت بدنه خام درخواست
        body = await request.body()
        print(f"Raw body: {body}")  # در لاگ‌ها نمایش داده می‌شود

        # اگر بدنه خالی نبود، پردازش کن
        if body:
            # تبدیل bytes به دیکشنری
            data = json.loads(body.decode('utf-8'))
            print(f"Received update: {data}")

            # استخراج chat_id از داده
            chat_id = data.get("message", {}).get("chat", {}).get("id")
            if chat_id:
                text = "سلام! Webhook به درستی کار می‌کند! 🎉"
                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                async with httpx.AsyncClient() as client:
                    await client.post(url, json={"chat_id": chat_id, "text": text})
        else:
            print("بدنه درخواست خالی است")

        # همیشه پاسخ موفق برمی‌گردانیم تا تلگرام دوباره تلاش نکند
        return {"status": "ok"}

    except json.JSONDecodeError as e:
        print(f"خطا در پردازش JSON: {e}")
        return {"status": "error", "message": "Invalid JSON"}
    except Exception as e:
        print(f"خطای غیرمنتظره: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
def root():
    return {"message": "ربات روشن است!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)