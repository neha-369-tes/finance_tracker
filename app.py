import json
import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Firebase Initialization - Manual Credentials
try:
    firebase_creds = {
        "apiKey": "AIzaSyDueqWta1lDz8C_3xeyl9OZoolqhzHUJtg",
        "authDomain": "finance-tracker-834bf.firebaseapp.com",
        "projectId": "finance-tracker-834bf",
        "storageBucket": "finance-tracker-834bf.firebasestorage.app",
        "messagingSenderId": "771731647058",
        "appId": "1:771731647058:web:538f8ab5a44d3d68500d8b",
        "measurementId": "G-PE1CNYFH5B"
    }
    
    # Manually create a Firebase service account credential using the dictionary
    cred_dict = firebase_creds
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    
except Exception as e:
    print(f"Firebase initialization error: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html', firebase_api_key=os.environ.get('FIREBASE_API_KEY'))

@app.route('/verify_token', methods=['POST'])
def verify_token():
    try:
        id_token = request.json['idToken']
        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token['uid']
        session['user_id'] = user_id
        return jsonify({"status": "success"})
    except auth.InvalidIdTokenError as e:
        return jsonify({"error": f"Invalid ID token: {str(e)}"}), 400
    except auth.ExpiredIdTokenError as e:
        return jsonify({"error": f"Expired ID token: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Token verification failed: {str(e)}"}), 400

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.pop('user_id', None)
    return jsonify({"status": "logged out"})

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    try:
        data = request.json
        transaction = {
            'amount': float(data['amount']),
            'category': data['category'],
            'transaction_type': data['type'],
            'description': data.get('description', ''),
            'user_id': session['user_id'],
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        db.collection('transactions').add(transaction)
        return jsonify({"status": "success"}), 201
    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid value provided: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to add transaction: {str(e)}"}), 400

@app.route('/get_transactions')
@login_required
def get_transactions():
    try:
        user_id = session['user_id']
        today = datetime.now()
        start_of_month = datetime(today.year, today.month, 1)
        if today.month == 12:
            start_of_next_month = datetime(today.year + 1, 1, 1)
        else:
            start_of_next_month = datetime(today.year, today.month + 1, 1)
        transactions_ref = db.collection('transactions')
        query = transactions_ref.where('user_id', '==', user_id)\
                                .where('timestamp', '>=', start_of_month)\
                                .where('timestamp', '<', start_of_next_month)\
                                .order_by('timestamp', direction=firestore.Query.DESCENDING)
        results = query.stream()
        transactions = []
        for transaction in results:
            trans_data = transaction.to_dict()
            trans_data['id'] = transaction.id
            if 'timestamp' in trans_data and trans_data['timestamp']:
                trans_data['timestamp'] = trans_data['timestamp'].isoformat()
            transactions.append(trans_data)
        return jsonify(transactions), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch transactions: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(debug=True)
