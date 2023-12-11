import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    ses_client = boto3.client('ses')
    sender_email = "administrator@building6156.com"
    
    # Retrieve the recipient email from the event object
    recipient_email = event.get('recipient_email')
    recipient_name = event.get('recipient_name')
    due_date = event.get('due_date')
    balance = event.get('balance')

    subject = "A reminder from Building6156"
    body = {
        "Text": {
            "Data": "Hi " + recipient_name + ",\n\nThis is a reminder that your rent is due on " + due_date + ".\n\nYour current balance is $" + balance + ".\n\nThank you,\nBuilding6156"
        }
    }

    try:
        response = ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [recipient_email]},
            Message={'Subject': {'Data': subject}, 'Body': body}
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])