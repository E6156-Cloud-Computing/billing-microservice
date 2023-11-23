import datetime
from flask import Flask, jsonify, request, Response
from pymongo import MongoClient
from bson import ObjectId

def serialize_doc(doc):
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

app = Flask(__name__)
client = MongoClient("mongodb://root:6156_project@mongodb:27017/")
db = client.rentaldb
billing_collection = db.billing # store billing info
transaction_collection = db.transactions # store transaction info by apt_id

@app.route('/api/billing/transaction/', methods=['GET', 'POST'])
def transactions():
    pass

@app.route('/api/billing/transaction/<string:transaction_id>', methods=['GET', 'PUT', 'DELETE'])
def transaction(transaction_id):
    pass

@app.route('/api/billing/transaction/apt/<string:apt_num>', methods=['GET', 'DELETE', 'POST'])
def insert_billing(apt_num):
    if request.method == 'POST':
        """Insert billing info into MongoDB(apt_id, rental price, rental start date, lease period), return the id of the inserted document"""
        try:
            # Parse the JSON data from request
            data = request.json
            rental_price = data['rental_price']
            rental_start_time = data.get('rental_start_time', datetime.datetime.now())
            lease_period = data.get('lease_period', 12)

            # Insert into MongoDB
            billing_info = {
                "apartment_id": apt_num,
                "rental_price": rental_price,
                "rental_start_time": rental_start_time,
                "lease_period": lease_period # in months
            }
            result = billing_collection.insert_one(billing_info)

            return jsonify({"message": "Billing info inserted successfully", "id": str(result.inserted_id)}), 201

        except Exception as e:
            # Handle errors
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'GET':
        """Get billing info from MongoDB by apartment id"""
        try:
            # Get billing info from MongoDB
            billing_info = billing_collection.find_one({"apartment_id": apt_num})
            if billing_info:
                billing_info = serialize_doc(billing_info)
                return jsonify(billing_info), 200
            else:
                return jsonify({"error": "Billing info not found"}), 404

        except Exception as e:
            # Handle errors
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'DELETE':
        """Delete billing info from MongoDB by apartment id"""
        try:
            # Delete billing info from MongoDB
            billing_info = billing_collection.find_one({"apartment_id": apt_num})
            if billing_info:
                billing_collection.delete_one({"apartment_id": apt_num})
                return jsonify({"message": "Billing info deleted successfully"}), 200
            else:
                return jsonify({"error": "Billing info not found"}), 404

        except Exception as e:
            # Handle errors
            return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
