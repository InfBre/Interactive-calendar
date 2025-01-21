from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from datetime import datetime, date, timedelta
import calendar
import json
import os
import hashlib
from dateutil.relativedelta import relativedelta
import time
from pymongo import MongoClient
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True

# MongoDB 连接
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.calendar25
users_collection = db.users
events_collection = db.events
notes_collection = db.notes

# 自定义密码哈希函数
def generate_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_hash(hash_value, password):
    return hash_value == hashlib.sha256(password.encode()).hexdigest()

# 预设的节日和重要事件
DEFAULT_EVENTS = {
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if users_collection.find_one({'username': username}):
            return render_template('register.html', error='Username already exists')
        
        users_collection.insert_one({
            'username': username,
            'password': generate_password_hash(password)
        })
        
        # 为新用户创建默认事件
        events_collection.insert_one({
            'username': username,
            'events': DEFAULT_EVENTS
        })
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

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
    user_events = events_collection.find_one({'username': username})
    if not user_events:
        events_collection.insert_one({
            'username': username,
            'events': DEFAULT_EVENTS
        })
        user_events = events_collection.find_one({'username': username})
    
    events = user_events['events']
    
    # 获取用户备忘录
    user_notes = notes_collection.find_one({'username': username})
    if not user_notes:
        notes_collection.insert_one({
            'username': username,
            'notes': []
        })
        user_notes = notes_collection.find_one({'username': username})
    
    notes = user_notes.get('notes', [])
    
    # 合并默认事件
    all_events = DEFAULT_EVENTS.copy()
    all_events.update(events)
    
    # 构建日历数据
    calendar_data = []
    current_date = date.today()
    
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
                current = date(year, month, day)
                date_str = current.strftime('%Y-%m-%d')
                
                day_data = {
                    'day': day,
                    'events': [all_events[date_str]] if date_str in all_events else [],
                    'notes': [note for note in notes if note.get('date') == date_str],
                    'is_today': current == current_date
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

@app.route('/api/events', methods=['GET', 'POST', 'DELETE'])
def handle_events():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    username = session['username']
    
    if request.method == 'GET':
        user_events = events_collection.find_one({'username': username})
        if not user_events:
            events_collection.insert_one({
                'username': username,
                'events': DEFAULT_EVENTS
            })
            return jsonify(DEFAULT_EVENTS)
        return jsonify(user_events['events'])
    
    elif request.method == 'POST':
        data = request.get_json()
        date = data.get('date')
        event = data.get('event')
        
        events_collection.update_one(
            {'username': username},
            {'$set': {f'events.{date}': event}},
            upsert=True
        )
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        data = request.get_json()
        date = data.get('date')
        
        events_collection.update_one(
            {'username': username},
            {'$unset': {f'events.{date}': ''}}
        )
        
        return jsonify({'success': True})

@app.route('/api/notes', methods=['GET', 'POST', 'DELETE'])
def handle_notes():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    username = session['username']
    
    if request.method == 'GET':
        user_notes = notes_collection.find_one({'username': username})
        if not user_notes:
            return jsonify([])
        return jsonify(user_notes.get('notes', []))
    
    elif request.method == 'POST':
        data = request.get_json()
        note = data.get('note')
        date = data.get('date')
        
        notes_collection.update_one(
            {'username': username},
            {'$push': {'notes': {'date': date, 'content': note}}},
            upsert=True
        )
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        data = request.get_json()
        note_index = data.get('index')
        
        notes_collection.update_one(
            {'username': username},
            {'$unset': {f'notes.{note_index}': ''}}
        )
        notes_collection.update_one(
            {'username': username},
            {'$pull': {'notes': None}}
        )
        
        return jsonify({'success': True})

# Vercel 需要的入口点
app = app

if __name__ == '__main__':
    app.run(debug=True, port=5015, host='0.0.0.0')
