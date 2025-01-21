from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_connection():
    try:
        # 获取连接字符串
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            print("Error: MONGODB_URI environment variable is not set")
            return False
        
        print("Connecting to MongoDB...")
        client = MongoClient(mongodb_uri)
        
        # 测试连接
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        
        # 测试数据库和集合
        db = client.calendar25
        
        # 测试插入
        test_doc = {"test": "connection"}
        result = db.test_collection.insert_one(test_doc)
        print(f"Successfully inserted test document with id: {result.inserted_id}")
        
        # 测试查询
        found = db.test_collection.find_one({"test": "connection"})
        print(f"Successfully found test document: {found}")
        
        # 清理测试数据
        db.test_collection.delete_one({"test": "connection"})
        print("Successfully cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        return False

if __name__ == "__main__":
    if test_connection():
        print("\nAll MongoDB connection tests passed!")
    else:
        print("\nMongoDB connection tests failed!")
