from flask import Flask, request, jsonify
import os
import requests
import json

app = Flask(__name__)

TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"


@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook endpoint is ready for POST requests from Telegram."

    try:
        # دریافت داده‌های ارسالی از تلگرام
        data = request.get_json()
        print(f"Received update: {data}")

        # استخراج chat_id و پاسخ به کاربر
        if data and 'message' in data:
            chat_id = data['message'].get('chat', {}).get('id')
            if chat_id:
                text = "سلام! Webhook به درستی کار می‌کند! 🎉"
                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                payload = {'chat_id': chat_id, 'text': text}
                requests.post(url, json=payload)
                print(f"Response sent to chat {chat_id}")

        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/')
def root():
    return "ربات روشن است!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)