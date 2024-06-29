
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timezone, timedelta
import re
import secrets
import string

# Initialize Firebase Admin SDK
cred = credentials.Certificate("credentials.json") 
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://project-zeus-98a8c-default-rtdb.firebaseio.com/'  # Replace with your database URL
})

app = Flask(__name__)
def sanitize_phone(phone):
    if phone and not any(char.isdigit() for char in phone):
        print("It's a saved contact")
    return re.sub(r'[^0-9]', '', phone)

def getNumber(data):
    # smart detection of number 
    message = data.get('query')
    
    if message.get('isGroup'):
        user_phone = message.get('groupParticipant')
    else:
        user_phone = message.get('sender')
        
    number = sanitize_phone(user_phone)
    print(number)
    return number

@app.route('/register', methods=['POST'])
def register():
    headers = request.headers.get('username').split()
    username = headers[0]
    referrer_code = headers[1]
    print(headers)
    # Generate a random referral code
    referral_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
    data = request.json
    print(data)

    message = data.get('query')
    if not message:
        return jsonify({"replies": [{"message": "❌ Invalid message type"}]}), 400

    # set level    
    level = 1 if referrer_code !="%capturing_group_2%" else 0
    
    number = getNumber(data)
    user_ref = db.reference(f'users/{number}')
    user = user_ref.get()
    
    now = datetime.now(timezone.utc)
    today_date = now.strftime('%Y-%m-%d')
    yes_time = now - timedelta(days=1)
    yes_date =yes_time.strftime('%Y-%m-%d')

    # initialize user
    if not user:
        user = {
            'phone': number,
            'username': username,
            'referrerCode': referrer_code,
            'level': level,
            'lastCheckInDate': yes_date,
            'referralCount': 0, 
            'referralCode': referral_code,
            'streak': 0,
            'bestStreak': 0
        }
    else:
        user.update({
            'username': username,
            'level': level,
            'lastCheckInDate': yes_date
        })

    user_ref.set(user)

    response_message = f"🎉 Welcome {user.get('username', '')}!\n Upgraded to lvl {user['level']}🔥"
    return jsonify({"replies": [{"message": response_message}]}), 200

@app.route('/info', methods=['POST'])
def info():
    
    if not user:
        return jsonify({"replies": [{"message": "Please register first"}]}), 200
    
    data = request.json
    message = data.get('query')
    if not message:
        return jsonify({"replies": [{"message": "❌ Invalid message type"}]}), 400

   
    number =  getNumber(data)
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

    message = data.get('query')
    if not message:
        return jsonify({"replies": [{"message": "❌ Invalid message type"}]}), 400

    number =  getNumber(data)
    print(number)
    user_ref = db.reference(f'users/{number}')
    user = user_ref.get()

    now = datetime.now(timezone.utc)
    today_date = now.strftime('%Y-%m-%d')
    yes_time = now - timedelta(days=1)
    yes_date =yes_time.strftime('%Y-%m-%d')

    if not user:
        return jsonify({"replies": [{"message": "Please register first"}]}), 200
    
    if user['lastCheckInDate'] == today_date:
        msg = f"✅ Check-in has been already done"
    elif user['lastCheckInDate'] != yes_date:
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
    return jsonify({"replies": [{"message": msg}]}), 200

@app.route('/milestone', methods=['GET'])
def track_milestones():
    
    milestones = {
        'level': [25, 50, 75],
        'streak': 5,
        'referral': [5, 20]
    }

    level_milestones = get_users_with_milestones('level', milestones['level'])
    streak_milestones = get_users_with_streak_milestones_today(milestones['streak'])
    referral_milestones = get_users_with_milestones('referralCount', milestones['referral'])

    message = "*Milestone Report*\n\n"
    
    if level_milestones:
        message += "*Level Milestones*\n"
        for level, users in level_milestones.items():
            message += f"Level {level}:\n" + "\n".join(users) + "\n\n"
    
    if streak_milestones:
        message += "*Streak Milestones*\n"
        for streak, users in streak_milestones.items():
            message += f"Streak {streak}:\n" + "\n".join(users) + "\n\n"
    
    if referral_milestones:
        message += "*Referral Milestones*\n"
        for count, users in referral_milestones.items():
            message += f"Referrals {count}:\n" + "\n".join(users) + "\n\n"
    
    return jsonify({"replies": [{"message": message}]}), 200


def get_users_with_milestones(field, values):
    users_ref = db.reference('users')
    all_users = users_ref.get()

    milestones = {value: [] for value in values}
    for user_id, user_data in all_users.items():
        if user_data.get(field) in values:
            milestones[user_data[field]].append(user_data['username'])
    
    return milestones

def get_users_with_streak_milestones_today(multiple):
    users_ref = db.reference('users')
    all_users = users_ref.get()

    milestones = {}
    now = datetime.now(timezone.utc)
    today_date = now.strftime('%Y-%m-%d')

    for user_id, user_data in all_users.items():
        last_check_in_date = user_data.get('lastCheckInDate')
        if last_check_in_date == today_date and user_data.get('streak') % multiple == 0:
            streak = user_data['streak']
            if streak not in milestones:
                milestones[streak] = []
            milestones[streak].append(user_data['username'])

    return milestones


@app.route('/')
def index():
    return '<pre>Nothing to see here.\nCheckout README.md to start.</pre>'

if __name__ == '__main__':
    app.run(port=5000)
