from flask import Flask, request
import os
import requests

app = Flask(__name__)
TOKEN = "8971000707:AAESYFI--ALKEXQgDN7c0yb9SjEBbQQN3BM"


@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook is ready!"

    data = request.get_json(silent=True)
    print(f"Data: {data}")

    if data and 'message' in data:
        chat_id = data['message']['chat']['id']
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': chat_id, 'text': 'سلام! این یه پاسخ تستیه!'})

    return "OK", 200


@app.route('/')
def root():
    return "ربات روشن است!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)