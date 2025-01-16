from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from datetime import datetime, date, timedelta
import calendar
import json
import os
import hashlib
from dateutil.relativedelta import relativedelta
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 用于session加密
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)  # 会话保持31天

# 数据库配置
import os
DATABASE = os.environ.get('DATABASE_URL', 'sqlite:///calendar25.db')

# 自定义密码哈希函数
def generate_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_hash(hash_value, password):
    return hash_value == hashlib.sha256(password.encode()).hexdigest()

# 用户数据
users = {}

# 加载用户数据
def load_users():
    global users
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            users = json.load(f)
load_users()

# 保存用户数据
def save_users():
    with open('users.json', 'w') as f:
        json.dump(users, f)

# 用户数据目录
def get_user_data_dir(username):
    user_dir = os.path.join('user_data', username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

# 用户事件和备忘录文件
def get_user_events_file(username):
    return os.path.join(get_user_data_dir(username), 'events.json')

def get_user_notes_file(username):
    return os.path.join(get_user_data_dir(username), 'notes.json')

# 加载用户数据
def load_user_data(username, file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

# 保存用户数据
def save_user_data(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f)

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
        username = request.form['username']
        password = request.form['password']
        
        if username in users and check_password_hash(users[username]['password'], password):
            session['username'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users:
            return render_template('register.html', error='用户名已存在')
        
        if len(username) < 3:
            return render_template('register.html', error='用户名至少需要3个字符')
        
        if len(password) < 6:
            return render_template('register.html', error='密码至少需要6个字符')
        
        users[username] = {
            'password': generate_password_hash(password),
            'created_at': time.time()
        }
        save_users()
        
        # 创建用户数据目录
        get_user_data_dir(username)
        
        session['username'] = username
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# 主页路由
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    return render_template('index.html', username=username)

# API路由
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
    events_file = get_user_events_file(username)
    events = load_user_data(username, events_file)
    
    # 获取用户备忘录
    notes_file = get_user_notes_file(username)
    notes = load_user_data(username, notes_file)
    
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
                    'notes': notes.get(date_str, []),
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
    events_file = get_user_events_file(username)
    events = load_user_data(username, events_file)
    
    if request.method == 'GET':
        return jsonify({'events': events})
    
    elif request.method == 'POST':
        data = request.get_json()
        date = data.get('date')
        description = data.get('description')
        
        if not date or not description:
            return jsonify({'error': 'Invalid data'}), 400
        
        events[date] = description
        save_user_data(events, events_file)
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        date = request.args.get('date')
        if date in events:
            del events[date]
            save_user_data(events, events_file)
            return jsonify({'success': True})
        return jsonify({'error': 'Event not found'}), 404

@app.route('/api/notes', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle_notes():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    username = session['username']
    notes_file = get_user_notes_file(username)
    
    if request.method == 'GET':
        if os.path.exists(notes_file):
            with open(notes_file, 'r') as f:
                return jsonify({'notes': json.load(f)})
        return jsonify({'notes': {}})
    
    elif request.method == 'POST':
        data = request.get_json()
        date = data.get('date')
        content = data.get('content')
        
        if not date or not content:
            return jsonify({'error': 'Missing date or content'}), 400

        notes = {}
        if os.path.exists(notes_file):
            with open(notes_file, 'r') as f:
                notes = json.load(f)
        
        notes[date] = content

        with open(notes_file, 'w') as f:
            json.dump(notes, f)
        
        return jsonify({'success': True})

    elif request.method == 'PUT':
        data = request.get_json()
        date = data.get('date')
        content = data.get('content')
        
        if not date or not content:
            return jsonify({'error': 'Missing date or content'}), 400

        if not os.path.exists(notes_file):
            return jsonify({'error': 'Note not found'}), 404

        with open(notes_file, 'r') as f:
            notes = json.load(f)
        
        if date not in notes:
            return jsonify({'error': 'Note not found'}), 404

        notes[date] = content

        with open(notes_file, 'w') as f:
            json.dump(notes, f)
        
        return jsonify({'success': True})

    elif request.method == 'DELETE':
        date = request.args.get('date')
        
        if not date:
            return jsonify({'error': 'Missing date'}), 400

        if not os.path.exists(notes_file):
            return jsonify({'error': 'Note not found'}), 404

        with open(notes_file, 'r') as f:
            notes = json.load(f)
        
        if date not in notes:
            return jsonify({'error': 'Note not found'}), 404

        del notes[date]

        with open(notes_file, 'w') as f:
            json.dump(notes, f)
        
        return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
