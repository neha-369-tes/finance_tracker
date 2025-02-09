import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json
from dotenv import load_dotenv
app = Flask(__name__)
CORS(app)
# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variable
firebase_creds = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
cred = credentials.Certificate(firebase_creds)



# Firebase Initialization
try:
    # Get credentials from environment variable
    firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_creds_json:
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    else:
        raise ValueError("Firebase credentials not found in environment variables")
except Exception as e:
    print(f"Firebase initialization error: {e}")

# Firestore Client
db = firestore.client()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    try:
        data = request.json
        transaction = {
            'amount': float(data['amount']),
            'category': data['category'],
            'transaction_type': data['type'],
            'description': data.get('description', ''),
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        # Add to Firestore
        transactions_ref = db.collection('transactions')
        doc_ref = transactions_ref.add(transaction)
        
        return jsonify({
            'id': doc_ref[1].id,
            **transaction
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/transactions', methods=['GET'])
def get_transactions():
    try:
        transactions_ref = db.collection('transactions')
        transactions = transactions_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        
        transaction_list = []
        for transaction in transactions:
            trans_dict = transaction.to_dict()
            trans_dict['id'] = transaction.id
            transaction_list.append(trans_dict)
        
        return jsonify(transaction_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/transaction/<transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    try:
        db.collection('transactions').document(transaction_id).delete()
        return jsonify({'message': 'Transaction deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
