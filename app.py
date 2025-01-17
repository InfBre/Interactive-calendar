from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, timedelta
import hashlib
import json
import os
from pymongo import MongoClient
from bson import ObjectId
from dateutil.relativedelta import relativedelta
import calendar
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# MongoDB 配置
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://calendar25_admin:8MkdzNgbXAJkcCo8@cluster0.eisbw.mongodb.net/?retryWrites=true&w=majority')
client = MongoClient(MONGODB_URI)
db = client.calendar25_db

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            print(f"Registration attempt for username: {username}")  # 日志
            
            if not username or not password:
                print("Empty username or password")  # 日志
                return render_template('register.html', error='用户名和密码不能为空')
                
            if len(username) < 2:
                print("Username too short")  # 日志
                return render_template('register.html', error='用户名至少需要2个字符')
            if len(password) < 4:
                print("Password too short")  # 日志
                return render_template('register.html', error='密码至少需要4个字符')
            
            # 检查用户是否存在
            existing_user = db.users.find_one({'username': username})
            if existing_user:
                print(f"Username already exists: {username}")  # 日志
                return render_template('register.html', error='用户名已存在')
            
            # 计算密码哈希
            hash_password = hashlib.sha256(password.encode()).hexdigest()
            print(f"Generated password hash: {hash_password}")  # 日志
            
            user = {
                'username': username,
                'password': hash_password,
                'created_at': datetime.utcnow(),
                'events': [],
                'notes': []
            }
            
            # 插入用户
            result = db.users.insert_one(user)
            if not result.inserted_id:
                print("Failed to insert user")  # 日志
                return render_template('register.html', error='注册失败，请重试')
            
            print(f"Successfully registered user: {username}")  # 日志
            session['username'] = username
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Registration error: {str(e)}")  # 日志
            return render_template('register.html', error=f'注册失败: {str(e)}')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            print(f"Login attempt for username: {username}")  # 日志
            
            if not username or not password:
                print("Empty username or password")  # 日志
                return render_template('login.html', error='用户名和密码不能为空')
            
            # 计算密码哈希
            hash_password = hashlib.sha256(password.encode()).hexdigest()
            print(f"Password hash: {hash_password}")  # 日志
            
            # 查找用户
            user = db.users.find_one({'username': username})
            
            if not user:
                print(f"User not found: {username}")  # 日志
                return render_template('login.html', error='用户名或密码错误')
            
            print(f"Found user: {user}")  # 日志
            print(f"Stored password hash: {user.get('password')}")  # 日志
            
            if user and user.get('password') == hash_password:
                print(f"Login successful for user: {username}")  # 日志
                session['username'] = username
                return redirect(url_for('index'))
            else:
                print(f"Password mismatch for user: {username}")  # 日志
                return render_template('login.html', error='用户名或密码错误')
            
        except Exception as e:
            print(f"Login error: {str(e)}")  # 日志
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
    
    username = session['username']
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    
    # 获取日历数据
    cal = calendar.monthcalendar(year, month)
    
    # 获取用户事件
    user = db.users.find_one({'username': username})
    events = user.get('events', [])
    
    # 获取用户备忘录
    notes = user.get('notes', [])
    
    # 合并默认事件
    all_events = {
        "2025-01-01": ["元旦"],
        "2025-01-29": ["春节"],
        "2025-02-14": ["情人节"],
        "2025-04-05": ["清明节"],
        "2025-05-01": ["劳动节"],
        "2025-06-22": ["端午节"],
        "2025-09-29": ["中秋节"],
        "2025-10-01": ["国庆节"],
        "2025-12-25": ["圣诞节"]
    }
    
    # 添加用户事件
    for event in events:
        date_str = event.get('date', '')
        if date_str:
            if date_str not in all_events:
                all_events[date_str] = []
            all_events[date_str].append(event.get('description', ''))
    
    # 构建日历数据
    calendar_data = []
    current_date = datetime.now().date()
    
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({
                    'day': '',
                    'events': [],
                    'notes': [],
                    'is_today': False
                })
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                day_notes = [note for note in notes if note.get('date') == date_str]
                
                day_data = {
                    'day': day,
                    'events': all_events.get(date_str, []),
                    'notes': [note.get('content', '') for note in day_notes],
                    'is_today': datetime(year, month, day).date() == current_date
                }
                week_data.append(day_data)
        calendar_data.append(week_data)
    
    # 获取月份信息
    month_info = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'prev_month': (year, month-1) if month > 1 else (year-1, 12),
        'next_month': (year, month+1) if month < 12 else (year+1, 1)
    }
    
    return jsonify({
        'calendar': calendar_data,
        'month_info': month_info
    })

@app.route('/api/events', methods=['GET'])
def get_events():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = db.users.find_one({'username': session['username']})
    return jsonify(user.get('events', []))

@app.route('/api/events', methods=['POST'])
def add_event():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    event = request.json
    db.users.update_one(
        {'username': session['username']},
        {'$push': {'events': event}}
    )
    return jsonify({'success': True})

@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db.users.update_one(
        {'username': session['username']},
        {'$pull': {'events': {'_id': ObjectId(event_id)}}}
    )
    return jsonify({'success': True})

@app.route('/api/notes', methods=['GET'])
def get_notes():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = db.users.find_one({'username': session['username']})
    return jsonify(user.get('notes', []))

@app.route('/api/notes', methods=['POST'])
def add_note():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    note = request.json
    db.users.update_one(
        {'username': session['username']},
        {'$push': {'notes': note}}
    )
    return jsonify({'success': True})

@app.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db.users.update_one(
        {'username': session['username']},
        {'$pull': {'notes': {'_id': ObjectId(note_id)}}}
    )
    return jsonify({'success': True})

@app.route('/init_user', methods=['GET'])
def init_user():
    try:
        # 检查用户是否已存在
        if db.users.find_one({'username': 'infinity'}):
            return jsonify({'message': '用户已存在'})
        
        # 创建初始用户
        user = {
            'username': 'infinity',
            'password': hashlib.sha256('infinity'.encode()).hexdigest(),
            'created_at': datetime.utcnow(),
            'events': [],
            'notes': []
        }
        
        # 插入用户
        result = db.users.insert_one(user)
        if result.inserted_id:
            return jsonify({'message': '初始用户创建成功'})
        else:
            return jsonify({'message': '创建用户失败'})
            
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
