import requests

TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"
WEBHOOK_URL = "https://my-reservation-bot.onrender.com/webhook"  # آدرس درست با /webhook

# اگه V2Ray داری (پورت 10808)
proxies = {
    'http': 'socks5://127.0.0.1:10808',
    'https': 'socks5://127.0.0.1:10808'
}

url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"

try:
    response = requests.get(url, proxies=proxies, timeout=30)
    print("✅ نتیجه:", response.json())
except Exception as e:
    print("❌ خطا:", e)