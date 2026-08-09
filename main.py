from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)
TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "✅ Webhook endpoint is ready for GET requests. Use POST for Telegram updates."

    try:
        data = request.get_json(silent=True)
        print(f"📩 Received data: {data}")

        if data and 'message' in data:
            chat_id = data['message']['chat']['id']
            text = "سلام! وب‌هوک با موفقیت کار می‌کند! 🎉"
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

            try:
                response = requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
                print(f"✅ Response from Telegram: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Error sending message to Telegram: {e}")

            return jsonify({"status": "ok", "message": "Response sent"}), 200

        return jsonify({"status": "ok", "message": "No message received"}), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/')
def home():
    return "✅ ربات روشن است!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)