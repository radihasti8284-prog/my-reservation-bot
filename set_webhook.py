import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# ⚠️ این آدرس را بعد از دیپلوی روی لیارا، به آدرس واقعی خود تغییر دهید
# مثال: https://my-reservation-bot.iran.liara.ir/webhook
WEBHOOK_URL = "https://your-app-id.iran.liara.ir/webhook"

url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
response = requests.get(url)

if response.status_code == 200 and response.json().get("ok"):
    print("✅ Webhook با موفقیت تنظیم شد!")
    print(f"آدرس Webhook: {WEBHOOK_URL}")
else:
    print("❌ خطا در تنظیم Webhook:")
    print(response.text)