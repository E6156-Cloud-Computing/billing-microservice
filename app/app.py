import boto3
from botocore.exceptions import ClientError
import json
import datetime
import schedule
import asyncio
from flask import Flask, jsonify, request, Response
from pymongo import MongoClient
from bson import ObjectId
from flask_cors import CORS

def serialize_doc(doc):
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

app = Flask(__name__)
client = MongoClient("mongodb://root:6156_project@mongodb:27017/")
db = client.rentaldb
billing_collection = db.billing # store billing info by apt_id or email
billing_transactions = db.transactions # store transaction info by apt_id
billing_history = db.history # store transaction history

def invoke_lambda_email_service(recipient_email, recipient_name, due_date, balance):
    """Invoke the lambda function to send email to the rentor"""
    ses_client = boto3.client('ses')
    payload = {
        'recipient_email': recipient_email,
        'recipient_name': recipient_name,
        'due_date': due_date,
        'balance': balance
    }
    try:
        response = ses_client.invoke(
            FunctionName='arn:aws:lambda:us-east-1:281091205399:function:lambda_email_sender',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

def generate_monthly_billing():
    """Generate monthly billing for each apartment based on the billing info stored in the billing_collection, this function will be scheduled to be called every day"""
    current_date = datetime.datetime.now()
    billings = billing_collection.find({})

    for billing in billings:
        due_date = billing["next_due_date"]
        payment_deadline = due_date + datetime.timedelta(days=7) # rentor has 7 days to pay the bill

        try:
            if billing_transactions.find_one({"apartment_id": billing["apartment_id"]}): # if there is an existing transaction, update it
                if current_date > due_date and current_date <= payment_deadline:
                    if billing_transactions.find_one({"apartment_id": billing["apartment_id"], "status": "paid"}):
                        continue
                    else:
                        billing_transactions.update_one(
                            {"apartment_id": billing["apartment_id"]},
                            {"$set": {"status": "unpaid"}}
                        )
                        invoke_lambda_email_service(billing["email"], billing["rentor_name"], due_date.strftime("%m/%d/%Y"), str(billing["rental_price"]))
                        # send email to the rentor via lambda function
                elif current_date > payment_deadline:
                    if billing_transactions.find_one({"apartment_id": billing["apartment_id"], "status": "paid"}):
                        # This means the lease has ended, and the entry is deleted from the database
                        pass
                    else:
                        billing_transactions.update_one(
                            {"_id": new_billing_transaction["_id"]},
                            {"$set": {"status": "violated"}}
                        )
            else:
                new_billing_transaction = {
                    "apartment_id": billing["apartment_id"],
                    "rental_price": billing["rental_price"],
                    "due_date": due_date,
                    "payment_deadline": payment_deadline,
                    "status": "unpaid",  # Initially marked as unpaid
                    "rentor_name": billing["rentor_name"],
                    "email": billing["email"]
                }
                billing_transactions.insert_one(new_billing_transaction)
        except Exception as e:
            print(e)

# schedule the monthly generating job to run every day at midnight
schedule.every().day.at("00:00").do(generate_monthly_billing) # schedule the job to run every day at midnight

@app.route('/api/billing/history/', methods=['GET', 'DELETE'])
def billing_history_api():
    """ Search transaction history by user email, and delete transaction history by email"""
    if request.method == 'GET':
        """transaction history by apartment number"""
        try:
            data = request.json
            start_num = data.get('start_num', 0)
            end_num = data.get('end_num', 4)
            email = data.get('email')
            transactions = billing_history.find({"email": email}).sort("payment_date", -1).skip(start_num).limit(end_num - start_num)
            return jsonify(transactions), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'DELETE':
        """Delete transaction history from MongoDB by apartment id"""
        try:
            # Delete transaction history from MongoDB
            email = request.json.get('email')
            billing_history_entry = billing_history.find_one({"email": email})
            if billing_history_entry:
                billing_history.delete_many({"email": email})
                return jsonify({"message": "Transaction history deleted successfully"}), 200
            else:
                return jsonify({"error": "Transaction history not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/billing/pay_rent/<string:apt_num>', methods=['GET', 'PUT'])
def transaction_api(apt_num):
    if request.method == 'GET':
        """Get billing status from MongoDB by apartment id"""
        try:
            # Get transaction info from MongoDB
            transaction = billing_transactions.find_one({"apartment_id": apt_num})
            if transaction:
                transaction = serialize_doc(transaction)
                return jsonify(transaction), 200
            else:
                return jsonify({"error": f"Bill of {apt_num} not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "PUT":
        """ Update the bill stuts to be paid, and log the transaction history """
        try:
            entry = billing_transactions.find_one({"apartment_id": apt_num})
            if (not entry):
                return jsonify({"error": f"No transaction info found for the apartment {apt_num}"}), 404
            
            if entry["status"] == "paid":
                return jsonify({"error": "The bill has been paid"}), 400
            
            billing_info_entry = billing_collection.find_one({"apartment_id": apt_num})
            lease_end_date = billing_info_entry["rental_start_time"] + datetime.timedelta(days=30 * billing_info_entry["lease_period"])

            if datetime.datetime.now() > lease_end_date:
                billing_transactions.delete_one({"apartment_id": apt_num})
                return jsonify({"error": "The lease has ended, and the entry is deleted from the database"}), 400
            
            if entry["due_date"] + datetime.timedelta(days=31) > lease_end_date:
                new_due_date = entry["due_date"]
            else:
                new_due_date = entry["due_date"] + datetime.timedelta(days=30)

            # Update the entry in billing_transactions
            billing_transactions.update_one(
                {"apartment_id": apt_num},
                {"$set": {"status": "paid"}}
            )

            # Update the entry in billing_collection
            result = billing_collection.update_one(
                {"apartment_id": apt_num},
                {"$set": {"next_due_date": new_due_date}}
            )

            # Log the transaction history
            billing_history_entry = {
                "apartment_id": apt_num,
                "rental_price": entry["rental_price"],
                "rentor_name": entry["rentor_name"],
                "payment_date": datetime.datetime.now(),
                "email": entry["email"]
            }
            billing_history.insert_one(billing_history_entry)

            if result.matched_count == 0:
                return jsonify({"error": "No transaction info found for the given apartment number"}), 404

            return jsonify({"message": "Transaction info updated successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/billing/apt/<string:apt_num>', methods=['POST', 'GET', 'PUT', 'DELETE'])
def billing_info_api(apt_num):
    """ This function is used for initial billing information insertion, update billing info, and delete billing info"""
    if request.method == 'POST':
        """Insert billing info into MongoDB(apt_id, rental price, rental start date, lease period), return the id of the inserted document"""
        try:
            # Parse the JSON data from request
            data = request.json
            rental_price = data['rental_price']
            rental_start_time = data.get('rental_start_time', datetime.datetime.now())
            lease_period = data.get('lease_period', 12)
            rentor_name = data.get('rentor_name', 'Anonymous')
            email = data.get('email') 
            next_due_date = rental_start_time

            # Insert into MongoDB
            billing_info = {
                "apartment_id": apt_num,
                "rental_price": rental_price,
                "rental_start_time": rental_start_time,
                "next_due_date": next_due_date, # next due date is 30 days after rental start date
                "lease_period": lease_period, # in months
                "rentor_name": rentor_name,
                "email": email
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
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'PUT':
        """Update billing info in MongoDB by apartment id"""
        try:
            # Parse the JSON data from request
            data = request.json
            update_data = {}

            # Check if the apartment exists before updating
            if not billing_collection.find_one({"apartment_id": apt_num}):
                return jsonify({"error": "No billing info found for the given apartment number"}), 404

            # Update fields if they exist in the request
            if 'rental_price' in data:
                update_data['rental_price'] = data['rental_price']
            if 'rental_start_time' in data:
                update_data['rental_start_time'] = data['rental_start_time']
            if 'lease_period' in data:
                update_data['lease_period'] = data['lease_period']
            if 'rentor_name' in data:
                update_data['rentor_name'] = data['rentor_name']

            # Update the entry in MongoDB
            result = billing_collection.update_one(
                {"apartment_id": apt_num},
                {"$set": update_data}
            )
            if result.matched_count == 0:
                return jsonify({"error": "No billing info found for the given apartment number"}), 404

            return jsonify({"message": "Billing info updated successfully"}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'DELETE':
        """ Delete billing info from MongoDB by apartment id """
        try:
            # Delete billing info from MongoDB
            billing_info = billing_collection.find_one({"apartment_id": apt_num})
            if billing_info:
                billing_collection.delete_one({"apartment_id": apt_num})
                if billing_history.find_one({"apartment_id": apt_num}):
                    # delete all the history of the apartment
                    billing_history.delete_many({"apartment_id": apt_num})
                if billing_transactions.find_one({"apartment_id": apt_num}):
                    billing_transactions.delete_one({"apartment_id": apt_num})
                return jsonify({"message": "Billing info deleted successfully"}), 200
            else:
                return jsonify({"error": "Billing info not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/billing/get_balance/', methods=['GET'])
async def get_billing_info_by_email():
    try:
        # Get current balance from MongoDB
        email = request.args.get('email')
        unpaid_transactions = billing_transactions.find({"email": email, "status": "unpaid"}) 
        if unpaid_transactions:
            balance = sum([transaction["rental_price"] for transaction in unpaid_transactions])
            return jsonify({"balance": balance}), 200
        else:
            return jsonify({"balance": 0}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    CORS(app)
    app.run(host='0.0.0.0', debug=True, ssl_context='adhoc')
