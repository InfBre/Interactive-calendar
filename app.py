from flask import Flask, render_template, request, redirect, url_for, session
import hashlib
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# MongoDB 配置
client = MongoClient('mongodb+srv://calendar25_admin:8MkdzNgbXAJkcCo8@cluster0.eisbw.mongodb.net/?retryWrites=true&w=majority')
db = client.calendar25_db

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('register.html', error='用户名和密码不能为空')
        
        if db.users.find_one({'username': username}):
            return render_template('register.html', error='用户名已存在')
        
        hash_password = hashlib.sha256(password.encode()).hexdigest()
        db.users.insert_one({
            'username': username,
            'password': hash_password
        })
        
        session['username'] = username
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
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

if __name__ == '__main__':
    app.run()
