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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template('register.html', error='用户名和密码不能为空')
            
        if len(username) < 2:
            return render_template('register.html', error='用户名至少需要2个字符')
        if len(password) < 4:
            return render_template('register.html', error='密码至少需要4个字符')
        
        if db.users.find_one({'username': username}):
            return render_template('register.html', error='用户名已存在')
        
        hash_password = hashlib.sha256(password.encode()).hexdigest()
        user = {
            'username': username,
            'password': hash_password,
            'created_at': datetime.utcnow(),
            'events': [],
            'notes': []
        }
        
        db.users.insert_one(user)
        session['username'] = username
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template('login.html', error='用户名和密码不能为空')
        
        hash_password = hashlib.sha256(password.encode()).hexdigest()
        user = db.users.find_one({
            'username': username,
            'password': hash_password
        })
        
        if user:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    
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

if __name__ == '__main__':
    app.run(debug=True)
