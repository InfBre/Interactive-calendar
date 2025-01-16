import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import hashlib
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# MongoDB 配置
MONGODB_URI = os.environ.get('MONGODB_URI')
if not MONGODB_URI:
    raise ValueError("No MONGODB_URI in environment")

try:
    client = MongoClient(MONGODB_URI)
    client.admin.command('ping')
    db = client.calendar25_db
    print("Successfully connected to MongoDB")
except Exception as e:
    print(f"MongoDB connection error: {str(e)}")
    raise

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                return render_template('register.html', error='用户名和密码不能为空')
            
            if db.users.find_one({'username': username}):
                return render_template('register.html', error='用户名已存在')
            
            hash_password = hashlib.sha256(password.encode()).hexdigest()
            print(f"Registering user: {username}")
            print(f"Password hash: {hash_password}")
            
            result = db.users.insert_one({
                'username': username,
                'password': hash_password,
                'created_at': datetime.utcnow(),
                'events': [],
                'notes': []
            })
            
            if not result.inserted_id:
                return render_template('register.html', error='注册失败，请重试')
            
            session['username'] = username
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return render_template('register.html', error=f'注册失败: {str(e)}')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                return render_template('login.html', error='用户名和密码不能为空')
            
            hash_password = hashlib.sha256(password.encode()).hexdigest()
            print(f"Login attempt for user: {username}")
            print(f"Password hash: {hash_password}")
            
            user = db.users.find_one({'username': username})
            if user:
                print(f"Found user in database with hash: {user.get('password')}")
            
            if user and user['password'] == hash_password:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='用户名或密码错误')
        except Exception as e:
            print(f"Login error: {str(e)}")
            return render_template('login.html', error=f'登录失败: {str(e)}')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/api/calendar')
def get_calendar_data():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user = db.users.find_one({'username': session['username']})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # 获取默认事件
        default_events = {
            "2025-01-01": "元旦",
            "2025-01-29": "春节",
            "2025-02-14": "情人节",
            "2025-04-05": "清明节",
            "2025-05-01": "劳动节",
            "2025-06-22": "端午节",
            "2025-09-29": "中秋节",
            "2025-10-01": "国庆节",
            "2025-12-25": "圣诞节"
        }
        
        # 获取用户事件
        user_events = user.get('events', [])
        
        # 合并事件
        all_events = default_events.copy()
        for event in user_events:
            date = event.get('date')
            if date:
                all_events[date] = event.get('title', '')
        
        return jsonify({
            'events': all_events,
            'notes': user.get('notes', [])
        })
    except Exception as e:
        print(f"Calendar data error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/event', methods=['POST'])
def add_event():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        event = {
            'date': data.get('date'),
            'title': data.get('title')
        }
        
        result = db.users.update_one(
            {'username': session['username']},
            {'$push': {'events': event}}
        )
        
        if result.modified_count:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to add event'}), 500
    except Exception as e:
        print(f"Add event error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/note', methods=['POST'])
def add_note():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        note = {
            'date': data.get('date'),
            'content': data.get('content')
        }
        
        result = db.users.update_one(
            {'username': session['username']},
            {'$push': {'notes': note}}
        )
        
        if result.modified_count:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to add note'}), 500
    except Exception as e:
        print(f"Add note error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal error: {str(error)}")
    return jsonify({'error': str(error)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    app.run()
