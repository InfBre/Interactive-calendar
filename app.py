from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import hashlib
import os
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 固定密钥，不使用环境变量

# MongoDB 配置
try:
    client = MongoClient('mongodb+srv://calendar25_admin:8MkdzNgbXAJkcCo8@cluster0.eisbw.mongodb.net/?retryWrites=true&w=majority')
    db = client.calendar25_db
except Exception as e:
    print(f"MongoDB connection error: {str(e)}")
    raise

# 路由：主页
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# 路由：注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # 验证输入
        if not username or not password:
            return render_template('register.html', error='用户名和密码不能为空')
        
        # 检查用户名是否存在
        if db.users.find_one({'username': username}):
            return render_template('register.html', error='用户名已存在')
        
        # 创建新用户
        user = {
            'username': username,
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'created_at': datetime.utcnow()
        }
        
        try:
            db.users.insert_one(user)
            session['username'] = username
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return render_template('register.html', error='注册失败，请重试')
    
    return render_template('register.html')

# 路由：登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template('login.html', error='用户名和密码不能为空')
        
        # 验证用户
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = db.users.find_one({
            'username': username,
            'password': hashed_password
        })
        
        if user:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')

# 路由：登出
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# 路由：添加事件
@app.route('/add_event', methods=['POST'])
def add_event():
    if 'username' not in session:
        return jsonify({'success': False, 'error': '未登录'})
    
    try:
        data = request.get_json()
        event = {
            'date': data.get('date'),
            'title': data.get('title'),
            'type': 'event'
        }
        
        db.users.update_one(
            {'username': session['username']},
            {'$push': {'events': event}}
        )
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Add event error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# 路由：添加笔记
@app.route('/add_note', methods=['POST'])
def add_note():
    if 'username' not in session:
        return jsonify({'success': False, 'error': '未登录'})
    
    try:
        data = request.get_json()
        note = {
            'date': data.get('date'),
            'content': data.get('content'),
            'type': 'note'
        }
        
        db.users.update_one(
            {'username': session['username']},
            {'$push': {'notes': note}}
        )
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Add note error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# 路由：获取事件
@app.route('/get_events', methods=['GET'])
def get_events():
    if 'username' not in session:
        return jsonify({'success': False, 'error': '未登录'})
    
    try:
        user = db.users.find_one({'username': session['username']})
        events = user.get('events', [])
        return jsonify({'success': True, 'events': events})
    except Exception as e:
        print(f"Get events error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# 路由：获取笔记
@app.route('/get_notes', methods=['GET'])
def get_notes():
    if 'username' not in session:
        return jsonify({'success': False, 'error': '未登录'})
    
    try:
        user = db.users.find_one({'username': session['username']})
        notes = user.get('notes', [])
        return jsonify({'success': True, 'notes': notes})
    except Exception as e:
        print(f"Get notes error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
