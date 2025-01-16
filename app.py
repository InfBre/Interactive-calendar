import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
    # 验证连接
    client.admin.command('ping')
    db = client.calendar25_db
    print("Successfully connected to MongoDB")
except Exception as e:
    print(f"MongoDB connection error: {str(e)}")
    raise

@app.route('/')
def index():
    try:
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template('index.html')
    except Exception as e:
        print(f"Index error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            
            if not username or not password:
                return render_template('register.html', error='用户名和密码不能为空')
            
            # 检查连接
            client.admin.command('ping')
            
            if db.users.find_one({'username': username}):
                return render_template('register.html', error='用户名已存在')
            
            hash_password = hashlib.sha256(password.encode()).hexdigest()
            result = db.users.insert_one({
                'username': username,
                'password': hash_password
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
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            
            if not username or not password:
                return render_template('login.html', error='用户名和密码不能为空')
            
            # 检查连接
            client.admin.command('ping')
            
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
        except Exception as e:
            print(f"Login error: {str(e)}")
            return render_template('login.html', error=f'登录失败: {str(e)}')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal error: {str(error)}")
    return jsonify({'error': str(error)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    app.run()
