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
import logging
from werkzeug.security import generate_password_hash as werkzeug_generate_password_hash

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# MongoDB 配置
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
try:
    client = MongoClient(MONGODB_URI, 
                        serverSelectionTimeoutMS=5000,
                        connectTimeoutMS=5000,
                        socketTimeoutMS=5000)
    # 验证连接
    client.admin.command('ping')
    db = client.calendar25_db
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")
    raise

def generate_password_hash(password):
    """生成密码哈希"""
    return werkzeug_generate_password_hash(password)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            # 基本验证
            if not username or not password:
                logger.warning("Registration attempt with empty username or password")
                return render_template('register.html', error='用户名和密码不能为空')
            
            if len(username) < 2:
                return render_template('register.html', error='用户名至少需要2个字符')
            if len(password) < 4:
                return render_template('register.html', error='密码至少需要4个字符')
            
            # 检查用户名是否已存在
            existing_user = db.users.find_one(
                {'username': username},
                projection={'_id': 1}
            )
            
            if existing_user:
                logger.warning(f"Registration attempt with existing username: {username}")
                return render_template('register.html', error='用户名已存在')
            
            # 创建新用户
            hashed_password = generate_password_hash(password)
            user = {
                'username': username,
                'password': hashed_password,
                'created_at': datetime.utcnow(),
                'events': [],
                'notes': []
            }
            
            result = db.users.insert_one(user)
            
            if result.inserted_id:
                logger.info(f"New user registered: {username}")
                session.clear()  # 清除旧的会话数据
                session['username'] = username
                session.permanent = True
                return redirect(url_for('index'))
            else:
                logger.error("Failed to insert new user into database")
                return render_template('register.html', error='注册失败，请重试')
                
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return render_template('register.html', error='注册时发生错误，请重试')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            user = db.users.find_one({
                'username': username
            })
            
            if user and werkzeug_generate_password_hash(password) == user['password']:
                session.clear()  # 清除旧的会话数据
                session['username'] = username
                return redirect(url_for('index'))
            else:
                logger.warning(f"Login attempt with incorrect credentials: {username}")
                return render_template('login.html', error='用户名或密码错误')
        
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return render_template('login.html', error='登录时发生错误，请重试')
    
    return render_template('login.html')

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
    user = db.users.find_one({'username': username})
    events = user.get('events', [])
    
    # 获取用户备忘录
    notes = user.get('notes', [])
    
    # 合并默认事件
    all_events = {
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
    for event in events:
        date_str = event.get('date', '')
        if date_str:
            all_events[date_str] = event.get('description', '')
    
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
                    'notes': [note.get('content', '') for note in notes if note.get('date', '') == date_str],
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

@app.errorhandler(500)
def internal_error(error):
    app.logger.error('Server Error: %s', error)
    return render_template('error.html', error='服务器内部错误'), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='页面未找到'), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
