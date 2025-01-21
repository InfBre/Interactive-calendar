from flask import Flask, jsonify, request, render_template, session, redirect, url_for, flash
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
try:
    mongodb_uri = os.getenv('MONGODB_URI')
    print(f"MongoDB URI prefix: {mongodb_uri[:15] if mongodb_uri else 'None'}...")
    
    if not mongodb_uri:
        raise ValueError("MONGODB_URI environment variable is not set")
    
    if not (mongodb_uri.startswith('mongodb://') or mongodb_uri.startswith('mongodb+srv://')):
        raise ValueError("MongoDB URI must start with 'mongodb://' or 'mongodb+srv://'")
    
    client = MongoClient(mongodb_uri)
    # 测试连接
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"MongoDB connection error: {str(e)}")
    if os.getenv('VERCEL_ENV') != 'production':
        print("Using default MongoDB URI for development")
        client = MongoClient('mongodb://localhost:27017/calendar25')
    else:
        raise

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

def is_logged_in():
    return 'username' in session

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({'username': username})
        if user and user['password'] == hashlib.sha256(password.encode()).hexdigest():
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 简单的验证：只要用户名和密码不为空即可
        if not username or not password:
            flash('Username and password are required')
            return redirect(url_for('register'))

        # 检查用户名是否已存在
        if users_collection.find_one({'username': username}):
            flash('Username already exists')
            return redirect(url_for('register'))

        # 创建新用户
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        users_collection.insert_one({
            'username': username,
            'password': hashed_password
        })

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/api/calendar')
def get_calendar_data():
    if not is_logged_in():
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
            'notes': {}
        })
        user_notes = notes_collection.find_one({'username': username})
    
    notes = user_notes.get('notes', {})
    
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
                    'notes': [notes.get(date_str, '')],
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

@app.route('/api/notes', methods=['GET', 'POST', 'DELETE'])
def handle_notes():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    username = session['username']
    
    if request.method == 'GET':
        user_notes = notes_collection.find_one({'username': username})
        if not user_notes:
            notes_collection.insert_one({
                'username': username,
                'notes': {}
            })
            return jsonify({'notes': {}})
        return jsonify({'notes': user_notes.get('notes', {})})
    
    elif request.method == 'POST':
        data = request.get_json()
        note = data.get('note')
        date = data.get('date')
        
        if not note or not date:
            return jsonify({'error': 'Missing note or date'}), 400
            
        try:
            # 更新或添加备忘录
            notes_collection.update_one(
                {'username': username},
                {'$set': {f'notes.{date}': note}},
                upsert=True
            )
            
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error saving note: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'Missing date'}), 400
            
        try:
            # 删除指定日期的备忘录
            notes_collection.update_one(
                {'username': username},
                {'$unset': {f'notes.{date}': ''}}
            )
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error deleting note: {str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['GET', 'POST', 'DELETE'])
def handle_events():
    if not is_logged_in():
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

@app.route('/save_event', methods=['POST'])
def save_event():
    if not is_logged_in():
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    username = session['username']
    event_id = data.get('id')
    event_date = data.get('date')
    event_title = data.get('title')
    
    if not all([event_id, event_date, event_title]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # 查找用户的事件文档
        user_events = events_collection.find_one({'username': username})
        if user_events:
            # 检查事件是否已存在
            events = user_events.get('events', [])
            event_exists = False
            for i, event in enumerate(events):
                if event.get('id') == event_id:
                    events[i] = data
                    event_exists = True
                    break
            
            if not event_exists:
                events.append(data)
            
            # 更新事件列表
            result = events_collection.update_one(
                {'username': username},
                {'$set': {'events': events}}
            )
        else:
            # 创建新文档
            result = events_collection.insert_one({
                'username': username,
                'events': [data]
            })
            
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving event: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_events', methods=['GET'])
def get_events():
    if not is_logged_in():
        return jsonify({'error': 'Not logged in'}), 401
        
    username = session['username']
    
    try:
        # 查找用户的事件文档
        user_events = events_collection.find_one({'username': username})
        if not user_events:
            # 如果用户没有事件文档，创建一个空的
            events_collection.insert_one({
                'username': username,
                'events': []
            })
            return jsonify([])
        
        events = user_events.get('events', [])
        # 按日期排序
        events.sort(key=lambda x: x.get('date', ''))
        
        return jsonify(events)
    except Exception as e:
        print(f"Error getting events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_event', methods=['POST'])
def delete_event():
    if not is_logged_in():
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({'error': 'No event ID provided'}), 400
        
    username = session['username']
    event_id = data.get('id')
    
    try:
        # 从用户的事件列表中删除指定事件
        result = events_collection.update_one(
            {'username': username},
            {'$pull': {'events': {'id': event_id}}}
        )
        
        if result.modified_count == 0:
            return jsonify({'error': 'Event not found'}), 404
            
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting event: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Vercel 需要的入口点
app = app

if __name__ == '__main__':
    app.debug = True  # 启用调试模式
    app.run(host='0.0.0.0', port=5000)
