from fastapi import FastAPI, Request
import os
import httpx
import uvicorn
import json

app = FastAPI()

TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"

# Webhook endpoint - POST برای دریافت آپدیت‌ها
@app.api_route("/webhook", methods=["POST"])
async def webhook(request: Request):
    try:
        body = await request.body()
        print(f"Raw body: {body}")

        if body:
            data = json.loads(body.decode('utf-8'))
            print(f"Received update: {data}")

            chat_id = data.get("message", {}).get("chat", {}).get("id")
            if chat_id:
                text = "سلام! Webhook به درستی کار می‌کند! 🎉"
                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                async with httpx.AsyncClient() as client:
                    await client.post(url, json={"chat_id": chat_id, "text": text})
        else:
            print("Empty body received")

        return {"status": "ok"}

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return {"status": "error", "message": "Invalid JSON"}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"status": "error", "message": str(e)}

# اضافه کردن متد GET برای تست و بررسی
@app.get("/webhook")
async def webhook_get():
    return {"message": "Webhook endpoint is ready for POST requests from Telegram."}

@app.get("/")
def root():
    return {"message": "ربات روشن است!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)