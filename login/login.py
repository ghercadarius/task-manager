from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps
import logging

app = Flask(__name__)
with open('/etc/certs/private_key.pem', 'r') as f:
    PRIVATE_KEY = f.read()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Mock user database (replace with real database)
users = {}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['user']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing credentials'}), 400
    
    if data['username'] in users:
        return jsonify({'message': 'User already exists'}), 400
    
    users[data['username']] = generate_password_hash(data['password'])
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    # if not data or not data.get('username') or not data.get('password'):
        # return jsonify({'message': 'Missing credentials'}), 400
    
    # if data['username'] not in users:
        # return jsonify({'message': 'Invalid credentials'}), 401
    
    # if not check_password_hash(users[data['username']], data['password']):
        # return jsonify({'message': 'Invalid credentials'}), 401
    
    token = jwt.encode({
        'user': 'test',
        'iss': 'task-manager',
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, PRIVATE_KEY, algorithm='RS256')
    
    return jsonify({'token': token}), 200

@app.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': f'Hello {current_user}'}), 200
    
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)