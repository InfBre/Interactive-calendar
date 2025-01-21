from pymongo import MongoClient
import json
import os
from dotenv import load_dotenv
import hashlib

# 加载环境变量
load_dotenv()

# MongoDB 连接
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.calendar25
users_collection = db.users
events_collection = db.events
notes_collection = db.notes

def migrate_users():
    # 读取用户数据
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            users = json.load(f)
            
        # 迁移每个用户
        for username, user_data in users.items():
            # 检查用户是否已存在
            if not users_collection.find_one({'username': username}):
                users_collection.insert_one({
                    'username': username,
                    'password': user_data['password']
                })
                print(f'Migrated user: {username}')

def migrate_user_data(username):
    # 迁移事件数据
    events_file = os.path.join('user_data', username, 'events.json')
    if os.path.exists(events_file):
        with open(events_file, 'r') as f:
            events = json.load(f)
            events_collection.update_one(
                {'username': username},
                {'$set': {'events': events}},
                upsert=True
            )
            print(f'Migrated events for user: {username}')
    
    # 迁移备忘录数据
    notes_file = os.path.join('user_data', username, 'notes.json')
    if os.path.exists(notes_file):
        with open(notes_file, 'r') as f:
            notes = json.load(f)
            notes_list = []
            for date, content in notes.items():
                notes_list.append({
                    'date': date,
                    'content': content
                })
            notes_collection.update_one(
                {'username': username},
                {'$set': {'notes': notes_list}},
                upsert=True
            )
            print(f'Migrated notes for user: {username}')

def main():
    # 迁移用户账号
    migrate_users()
    
    # 迁移用户数据
    if os.path.exists('user_data'):
        for username in os.listdir('user_data'):
            if os.path.isdir(os.path.join('user_data', username)):
                migrate_user_data(username)

if __name__ == '__main__':
    main()
    print('Migration completed!')
