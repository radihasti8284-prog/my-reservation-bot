import requests

TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"
WEBHOOK_URL = "https://my-reservation-bot.onrender.com/webhook"

url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"

try:
    response = requests.get(url, timeout=30)
    print("✅ نتیجه:", response.json())
except Exception as e:
    print("❌ خطا:", e)