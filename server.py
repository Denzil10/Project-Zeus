
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timezone, timedelta
import re
import secrets
import string
import pprint
# Initialize Firebase Admin SDK
cred = credentials.Certificate("credentials.json") 
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://project-zeus-98a8c-default-rtdb.firebaseio.com/'  # Replace with your database URL
})

app = Flask(__name__)
def sanitize_phone(phone):
    return re.sub(r'[^0-9]', '', phone)

def generate_referral_code():
    code_length = 5
    referral_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(code_length))
    return referral_code

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    query = data.get('query')
    message = query.get('message')
    if not message:
        return jsonify({"replies": [{"message": "❌ Invalid message type"}]}), 400
    
    username = re.search(r"register:\s*(\w+)", message).group(1)
    referrer_code = re.search(r"referral:\s*(\w+)", message).group(1)

    

    #changed user phone to user identifier, to handle the names due to saved contacts
    user_identifier = query.get('groupParticipant')
    ref = db.reference('users')
    user = ref.order_by_child('user_identifier').equal_to(user_identifier)
    user = user.get()
    #pprint.pprint(user)
    if len(user) != 0:
        return jsonify({"replies": [{"message": "❌ User already exists"}]}), 409
    
    referral_code = generate_referral_code()
    #print("refercode generted")
    
    # while True: #code to ensure unique referral code, can be used in future
    #     referral_code = generate_referral_code()
    #     user = ref.order_by_child('referral_code').equal_to(referral_code)
    #     print('Generating referral code')
    #     if(user != None):
    #        break

    level = 0
    if referral_code != "":
        user = ref.order_by_child('referralCode').equal_to(referrer_code)
        user = user.get()
        #pprint.pprint(user)
        if len(user) == 0:
            return jsonify({"replies": [{"message": "❌ Invalid referral code"}]}), 460
        else:
            level = 1

    
    now = datetime.now(timezone.utc)
    today_date = now.strftime('%Y-%m-%d')
    yesterday_time = now - timedelta(days=1)
    yesterday_date =yesterday_time.strftime('%Y-%m-%d')


    user = {
        "user_identifier" : user_identifier,
        'username': username,
        'referrerCode': referrer_code,
        'level': level,
        'lastCheckInDate': yesterday_date,
        'referralCount': 0, 
        'referralCode': referral_code,
        'streak': 0,
        'bestStreak': 0
    }
   
    #print(user)
    ref.push(user)
    

    response_message = f"🎉 Welcome {user.get('username', '')}!\n Upgraded to lvl {user['level']}🔥"
    return jsonify({"replies": [{"message": response_message}]}), 200

@app.route('/info', methods=['POST'])
def info():
    data = request.json
    message = data.get('query')
    if not message:
        return jsonify({"replies": [{"message": "❌ Invalid message type"}]}), 400


   
    number =  sanitize_phone(message.get('groupParticipant')) 
    user_ref = db.reference(f'users/{number}')
    user = user_ref.get()
    
    info = (
    "Info😎\n"
    f"Username: {user['username']}\n"
    f"Level: {user['level']}\n"
    f"Streak: {user['streak']}\n"
    f"Best Streak: {user['bestStreak']}\n"
    f"Referral Code: {user['referralCode']}\n"
    f"Referral Count: {user['referralCount']}\n"
)

    response_message = f"{info}"
    return jsonify({"replies": [{"message": response_message}]}), 200

@app.route('/checkin', methods=['POST'])
def checkin():
    data = request.json
    print(data)

    if not data:
        app.logger.error("Invalid JSON data received")
        return jsonify({"replies": [{"message": "❌ Invalid JSON data"}]}), 400

    message = data.get('query')
    if not message:
        return jsonify({"replies": [{"message": "❌ Invalid message type"}]}), 400

    user_phone = message.get('groupParticipant')
    number = sanitize_phone(user_phone)
    user_ref = db.reference(f'users/{number}')
    user = user_ref.get()

    now = datetime.now(timezone.utc)
    today_date = now.strftime('%Y-%m-%d')
    yesterday_time = now - timedelta(days=1)
    yesterday_date =yesterday_time.strftime('%Y-%m-%d')

    if not user:
        return jsonify({"replies": [{"message": "Please register first"}]}), 404
    
    print("userlast " + str(user['lastCheckInDate']) + " today " + str(today_date))

    
    if user['lastCheckInDate'] == today_date:
        msg = f"✅ Check-in has been already done"
    elif user['lastCheckInDate'] != yesterday_date:
        user['level'] = 1
        user['streak'] = 1
        msg = f"🔴 You broke your streak. Starting from lvl 1"
    else:
        user['level'] += 1
        user['lastCheckInDate'] = today_date
        user['streak'] += 1
        if user['streak']>user['bestStreak']:
            user['bestStreak'] = user['streak']
        msg = f"🎉 Reached Lvl {user['level']}"

    user_ref.set(user)
    # return jsonify({"replies": [{"message": "Please register first"}]}), 404
    return jsonify({"replies": [{"message": msg}]}), 200

@app.route('/')
def index():
    return '<pre>Nothing to see here.\nCheckout README.md to start.</pre>'

if __name__ == '__main__':
    app.run(port=5000)
