import json
import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # for session management
CORS(app)

# Firebase Initialization
try:
    firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_creds_json:
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    else:
        raise ValueError("Firebase credentials not found")
except Exception as e:
    print(f"Firebase initialization error: {e}")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/verify_token', methods=['POST'])
def verify_token():
    try:
        id_token = request.json['idToken']
        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token['uid']
        session['user_id'] = user_id
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/get_transactions')
@login_required
def get_transactions():
    try:
        user_id = session['user_id']
        transactions = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .stream()
        
        return jsonify([{
            'id': doc.id,
            **doc.to_dict(),
            'timestamp': doc.to_dict()['timestamp'].timestamp() if doc.to_dict()['timestamp'] else None
        } for doc in transactions])
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
