
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import re

# Initialize Firebase Admin SDK
cred = credentials.Certificate("credentials.json") 
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://project-zeus-98a8c-default-rtdb.firebaseio.com/'  # Replace with your database URL
})

app = Flask(__name__)
def sanitize_phone(phone):
    return re.sub(r'[^0-9]', '', phone)

@app.route('/register', methods=['POST'])
def register():
    header = request.headers
    print(header)
    # referrer_code = request.headers.get('code')
    data = request.json
    print(data)

    if not data:
        app.logger.error("Invalid JSON data received")
        return jsonify({"replies": [{"message": "❌ Invalid JSON data"}]}), 400

    message = data.get('query')
    if not message:
        return jsonify({"replies": [{"message": "❌ Invalid message type"}]}), 400

    user_phone = message.get('sender')
    number = sanitize_phone(user_phone)
    level = 1 if referrer_code else 0
    print(level)

    user_ref = db.reference(f'users/{number}')
    user = user_ref.get()

    if not user:
        user = {
            'phone': number,
            'username': username,
            'referrerCode': referrer_code,
            'level': level,
            'lastMessageDate': None,
        }
    else:
        user.update({
            'username': username,
            'level': level,
        })

    user_ref.set(user)

    response_message = f"Welcome {user.get('username', '')}! Upgraded to lvl {user['level']}"
    return jsonify({"replies": [{"message": response_message}]}), 200

@app.route('/checkin', methods=['POST'])
def checkin():
    data = request.json

    if not data:
        app.logger.error("Invalid JSON data received")
        return jsonify({"replies": [{"message": "❌ Invalid JSON data"}]}), 400

    message = data.get('query')
    if not message:
        return jsonify({"replies": [{"message": "❌ Invalid message type"}]}), 400

    user_phone = message.get('sender')

    now = datetime.utcnow()
    today = now.strftime('%Y-%m-%d')

    user_ref = db.reference(f'users/{user_phone}')
    user = user_ref.get()

    if not user:
        return jsonify({"replies": [{"message": "Please register first"}]}), 404

    if user['lastMessageDate'] != today:
        if user['lastMessageDate'] and user['lastMessageDate'] != today:
            user['level'] = 0
        user['level'] += 1
        user['lastMessageDate'] = today

    user_ref.set(user)

    return jsonify({"replies": [{"message": f"Reached Lvl{user['level']}"}]}), 200

@app.route('/')
def index():
    return '<pre>Nothing to see here.\nCheckout README.md to start.</pre>'

if __name__ == '__main__':
    app.run(port=5000)
