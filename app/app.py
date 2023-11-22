from flask import Flask, jsonify
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient("mongodb://root:6156_project@mongodb:27017/")
db = client.testdb

@app.route('/')
def hello_world():
    db.testcollection.insert_one({"message": "Hello, World!"})
    message = db.testcollection.find_one({"message": "Hello, World!"})
    return jsonify(message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
