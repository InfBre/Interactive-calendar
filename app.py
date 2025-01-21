from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from datetime import datetime, timedelta
import hashlib
import calendar
import json
import os
from pymongo import MongoClient
from bson import ObjectId
from dateutil.relativedelta import relativedelta
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# MongoDB connection
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://calendar25_admin:8MkdzNgbXAJkcCo8@cluster0.eisbw.mongodb.net/?retryWrites=true&w=majority')
client = MongoClient(MONGODB_URI)
db = client.calendar25_db  # 使用正确的数据库名称

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.before_request
def before_request():
    try:
        # 确保每个请求都有一个有效的数据库连接
        if not hasattr(g, 'db'):
            g.db = client.calendar25_db  # 使用相同的数据库名称
        
        # 检查会话是否有效
        if request.path != '/login' and request.path != '/register' and not request.path.startswith('/static/'):
            if 'username' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Unauthorized', 'code': 401}), 401
                else:
                    return redirect(url_for('login'))
    except Exception as e:
        print(f"Error in before_request: {str(e)}")
        import traceback
        traceback.print_exc()
        if request.path.startswith('/api/'):
            return jsonify({'error': str(e), 'code': 500}), 500
        else:
            return redirect(url_for('login'))

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
            existing_user = g.db.users.find_one({'username': username})
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
                'events': {},
                'notes': []
            }
            
            # 插入用户
            result = g.db.users.insert_one(user)
            if not result.inserted_id:
                print("Failed to insert user")  # 日志
                return render_template('register.html', error='注册失败，请重试')
            
            print(f"Successfully registered user: {username}")  # 日志
            session['username'] = username
            session.permanent = True  # 设置会话为永久
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Registration error: {str(e)}")  # 日志
            return render_template('register.html', error=f'注册失败: {str(e)}')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # 打印所有请求数据
            print("Form data:", dict(request.form))
            print("Headers:", dict(request.headers))
            print("Method:", request.method)
            
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            print(f"Login attempt for username: {username}")  # 日志
            print(f"Raw password length: {len(password)}")  # 日志
            print(f"Databases: {client.list_database_names()}")  # 日志
            print(f"Collections: {g.db.list_collection_names()}")  # 日志
            
            if not username or not password:
                print("Empty username or password")  # 日志
                return render_template('login.html', error='用户名和密码不能为空')
            
            # 计算密码哈希
            hash_password = hashlib.sha256(password.encode()).hexdigest()
            print(f"Input password hash: {hash_password}")  # 日志
            
            # 查找用户
            user = g.db.users.find_one({'username': username})
            print(f"Found user: {user}")  # 日志
            
            if not user:
                print(f"User not found: {username}")  # 日志
                return render_template('login.html', error='用户名或密码错误')
            
            stored_hash = user.get('password')
            print(f"Stored password hash: {stored_hash}")  # 日志
            print(f"Hashes match: {stored_hash == hash_password}")  # 日志
            
            if stored_hash == hash_password:
                print(f"Login successful for user: {username}")  # 日志
                session.clear()  # 清除所有会话数据
                session['username'] = username
                session.permanent = True  # 设置会话为永久
                return redirect(url_for('index'))
            else:
                print(f"Password mismatch for user: {username}")  # 日志
                print(f"Expected hash: {stored_hash}")  # 日志
                print(f"Received hash: {hash_password}")  # 日志
                return render_template('login.html', error='用户名或密码错误')
            
        except Exception as e:
            print(f"Login error: {str(e)}")  # 日志
            print(f"Error type: {type(e)}")  # 日志
            import traceback
            print(f"Traceback: {traceback.format_exc()}")  # 日志
            return render_template('login.html', error=f'登录失败: {str(e)}')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/api/calendar')
def get_calendar_data():
    try:
        if 'username' not in session:
            return jsonify({'error': 'Unauthorized', 'code': 401}), 401

        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        
        # 获取用户数据
        user = g.db.users.find_one({'username': session['username']})
        if not user:
            return jsonify({'error': 'User not found', 'code': 404}), 404

        # 获取当前月份的日历数据
        cal = calendar.monthcalendar(year, month)
        today = datetime.now()
        
        # 转换日历数据为所需格式
        calendar_data = []
        for week in cal:
            for day in week:
                if day != 0:
                    # 检查是否是今天
                    is_today = (day == today.day and month == today.month and year == today.year)
                    
                    # 获取当天的事件
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    events = user.get('events', {}).get(date_str, [])
                    
                    # 获取当天的备忘录
                    notes = [note for note in user.get('notes', []) if note.get('date') == date_str]
                    
                    calendar_data.append({
                        'day': day,
                        'is_today': is_today,
                        'is_current_month': True,
                        'events': events,
                        'notes': notes
                    })
        
        return jsonify({
            'calendar': calendar_data,
            'month_info': {
                'year': year,
                'month': month
            }
        })
    except Exception as e:
        print(f"Error in get_calendar_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'code': 500}), 500

@app.route('/api/events', methods=['GET'])
def get_events():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401
    
    user = g.db.users.find_one({'username': session['username']})
    if not user:
        return jsonify({'events': {}})
    
    # 将事件列表转换为字典格式
    events_dict = user.get('events', {})
    
    return jsonify({'events': events_dict})

@app.route('/api/events', methods=['POST'])
def add_event():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401
    
    event_data = request.json
    if not event_data or 'date' not in event_data or 'description' not in event_data:
        return jsonify({'error': 'Invalid event data', 'code': 400}), 400
        
    # 验证日期格式
    try:
        date = datetime.strptime(event_data['date'], '%Y-%m-%d')
        event_data['date'] = date.strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format', 'code': 400}), 400
    
    # 添加事件ID
    event_data['id'] = str(datetime.now().timestamp())
    
    result = g.db.users.update_one(
        {'username': session['username']},
        {'$set': {f"events.{event_data['date']}": event_data['description']}}
    )
    
    if result.modified_count > 0:
        return jsonify({'success': True, 'event': event_data})
    else:
        return jsonify({'error': 'Failed to add event', 'code': 500}), 500

@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401
    
    user = g.db.users.find_one({'username': session['username']})
    if not user:
        return jsonify({'error': 'User not found', 'code': 404}), 404
    
    events = user.get('events', {})
    for date, description in events.items():
        if description == event_id:
            result = g.db.users.update_one(
                {'username': session['username']},
                {'$unset': {f"events.{date}": ""}}
            )
            if result.modified_count > 0:
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Event not found', 'code': 404}), 404
    
    return jsonify({'error': 'Event not found', 'code': 404}), 404

@app.route('/api/notes', methods=['GET'])
def get_notes():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401
    
    user = g.db.users.find_one({'username': session['username']})
    if not user:
        return jsonify({'notes': []})
    
    notes = user.get('notes', [])
    return jsonify({'notes': notes})

@app.route('/api/notes', methods=['POST'])
def add_note():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401
    
    note_data = request.json
    if not note_data or 'date' not in note_data or 'content' not in note_data:
        return jsonify({'error': 'Invalid note data', 'code': 400}), 400
        
    # 验证日期格式
    try:
        date = datetime.strptime(note_data['date'], '%Y-%m-%d')
        note_data['date'] = date.strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format', 'code': 400}), 400
    
    # 添加备忘录ID
    note_data['id'] = str(datetime.now().timestamp())
    
    result = g.db.users.update_one(
        {'username': session['username']},
        {'$push': {'notes': note_data}}
    )
    
    if result.modified_count > 0:
        return jsonify({'success': True, 'note': note_data})
    else:
        return jsonify({'error': 'Failed to add note', 'code': 500}), 500

@app.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401
    
    result = g.db.users.update_one(
        {'username': session['username']},
        {'$pull': {'notes': {'id': note_id}}}
    )
    
    if result.modified_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Note not found', 'code': 404}), 404

@app.route('/init_user', methods=['GET'])
def init_user():
    try:
        username = 'infinity'
        password = 'infinity'
        
        # 检查用户是否已存在
        existing_user = g.db.users.find_one({'username': username})
        if existing_user:
            # 如果用户存在，更新密码
            hash_password = hashlib.sha256(password.encode()).hexdigest()
            result = g.db.users.update_one(
                {'username': username},
                {'$set': {
                    'password': hash_password,
                    'updated_at': datetime.utcnow()
                }}
            )
            if result.modified_count > 0:
                return jsonify({
                    'message': '用户密码已更新',
                    'username': username,
                    'password_hash': hash_password
                })
            else:
                return jsonify({'error': '更新密码失败'})
        
        # 创建新用户
        hash_password = hashlib.sha256(password.encode()).hexdigest()
        user = {
            'username': username,
            'password': hash_password,
            'created_at': datetime.utcnow(),
            'events': {},
            'notes': []
        }
        
        # 插入用户
        result = g.db.users.insert_one(user)
        if result.inserted_id:
            return jsonify({
                'message': '初始用户创建成功',
                'username': username,
                'password_hash': hash_password
            })
        else:
            return jsonify({'error': '创建用户失败'})
            
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/check_user', methods=['GET'])
def check_user():
    try:
        # 查找用户
        user = g.db.users.find_one({'username': 'infinity'})
        if not user:
            return jsonify({'error': '用户不存在'})
            
        # 返回用户信息（不包含密码）
        return jsonify({
            'username': user['username'],
            'created_at': user['created_at'],
            'expected_password_hash': hashlib.sha256('infinity'.encode()).hexdigest(),
            'current_password_hash': user['password']
        })
            
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/debug_db', methods=['GET'])
def debug_db():
    try:
        # 列出所有数据库
        databases = client.list_database_names()
        
        # 列出当前数据库中的所有集合
        collections = g.db.list_collection_names()
        
        # 获取用户集合中的所有文档
        users = list(g.db.users.find({}, {'_id': 0, 'password': 0}))
        
        return jsonify({
            'databases': databases,
            'collections': collections,
            'users': users
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
