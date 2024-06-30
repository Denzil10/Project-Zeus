
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
def getUser(query):
    # smart detection of number 
    if query.get('isGroup'):
        user_identifier = query.get('groupParticipant')
    else:
        user_identifier = query.get('sender')
        
    # if number then clean    
    if user_identifier and not any(char.isdigit() for char in user_identifier):
        print("It's a saved contact") # might have to remove the space 
    else: 
        user_identifier = re.sub(r'[^0-9]', '', user_identifier)
        
    return user_identifier

def generate_referral_code():
    code_length = 5
    referral_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(code_length))
    return referral_code

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    query = data.get('query')

    # fetch msg parameters
    message = query.get('message')    
    username = re.search(r"register:\s*(\w+)", message).group(1)
    referrer_code = re.search(r"referral:\s*(\w+)", message) #optional referral
    referrer_code = referrer_code.group(1) if referrer_code else ""
    referral_code = generate_referral_code()
    
    now = datetime.now(timezone.utc)
    yes_time = now - timedelta(days=1)
    yes_date =yes_time.strftime('%Y-%m-%d')

    level = 0
    if referrer_code != "":
        ref =  db.reference('users').order_by_child('referralCode').equal_to(referrer_code)
        referrer = ref.get()
        if len(referrer) == 0:
            return jsonify({"replies": [{"message": "❌ Invalid referral code"}]}), 200
        else:
            level = 1
    
    user_identifier = getUser(query)
    users_ref = db.reference('users').order_by_child('identifier').equal_to(user_identifier)
    user_snapshot = users_ref.get()

    if user_snapshot:
        return jsonify({"replies": [{"message": "❌ User already exists"}]}), 200
    else:
        # Push data to the database under 'users' node
        user = {
            'identifier': user_identifier,
            'username': username,
            'referrerCode': referrer_code,
            'level': level,
            'lastCheckInDate': yes_date,
            'referralCount': 0, 
            'referralCode': referral_code,
            'streak': 0,
            'bestStreak': 0
        }
        db.reference('users').push(user)

    response_message = f"🎉 Welcome {user.get('username', '')}!\n Upgraded to lvl {user['level']}🔥"
    return jsonify({"replies": [{"message": response_message}]}), 200

@app.route('/info', methods=['POST'])
def info():
    data = request.json
    query = data.get('query')
    
    # collect user details 
    user_identifier = getUser(query)
    user_ref = db.reference('users').order_by_child('identifier').equal_to(user_identifier)
    user_snapshot= user_ref.get()
    user_key = list(user_snapshot.keys())[0]
    user = user_snapshot[user_key]
    
    if not user:
        return jsonify({"replies": [{"message": "Please register first"}]}), 200
    
    data = request.json
    message = data.get('query')
 
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
    query = data.get('query')
    
    # collect details 
    user_identifier = getUser(query)
    user_ref = db.reference('users').order_by_child('identifier').equal_to(user_identifier)
    user_snapshot= user_ref.get()
    if not user_snapshot:
        return jsonify({"replies": [{"message": "Please register first"}]}), 200
    user_key = list(user_snapshot.keys())[0]
    user = user_snapshot[user_key]

    now = datetime.now(timezone.utc)
    today_date = now.strftime('%Y-%m-%d')
    yes_time = now - timedelta(days=1)
    yes_date =yes_time.strftime('%Y-%m-%d')

    # checkin logic
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

    db.reference('users').child(user_key).update(user)
    return jsonify({"replies": [{"message": msg}]}), 200

@app.route('/milestone', methods=['POST'])
def track_milestones():
    # testing updates 
    user_id = '699539284744'  
    user_ref = db.reference(f'users/{user_id}')
    # Update level
    user_ref.update({
        'level': 56
    })
    
    # user_id = '699539284744'  
    
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
        user_value = user_data.get(field, 0)
        for value in values:
            if user_value >= value:
                milestones[value].append(user_data['username'])
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

# special end points for load distrbition  untested
@app.route('/other', methods=['POST'])
def other():
    data = request.json
    query = data.get('query')
    message = query.get('message')

    # Split message into words
    words = message.split()

    if words:
        first_word = words[0].lower()

        if first_word == 'register': #use proper regex to avoid syntax errors
            register(data)
        elif first_word == 'info':
            info(data)
        elif first_word == 'milestone':
            track_milestones(data)

@app.route('/any_checkin', methods=['POST'])
def any_checkin():
    data = request.json
    checkin(data)    

@app.route('/')
def index():
    return '<pre>Nothing to see here.\nCheckout README.md to start.</pre>'

if __name__ == '__main__':
    app.run(port=5000)
