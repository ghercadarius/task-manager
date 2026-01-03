from flask import Flask, request, jsonify
import jwt
from datetime import datetime, timedelta
from functools import wraps
import logging
import bcrypt
import cryptography
from database.models import db, User

# Configure database and FLask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgrespassword@postgres.default.svc.cluster.local:5432/taskdb"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Load RSA keys for JWT
with open('/etc/certs/private_key.pem', 'r') as f:
    PRIVATE_KEY = f.read()
with open('/etc/certs/public_key.pem', 'r') as f:
    PUBLIC_KEY = f.read()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

with app.app_context():
    db.create_all()
    if User.query.filter_by(username='admin').first() is None:
        admin_user = User(username='admin', password_hash=bcrypt.hashpw(b'password', bcrypt.gensalt()))
        db.session.add(admin_user)
        db.session.commit()
    logger.info("Database tables created and added admin user")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header
            data = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'], issuer='task-manager')
            current_user = data['user']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            logger.error(f'Token validation error: {e}')
            return jsonify({'message': 'Token is invalid'}), 401
        user_name = request.headers.get('X-User') 
        return f(user_name, *args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing credentials'}), 400
    
    if data['username'] in [user.username for user in User.query.with_entities(User.username).all()]:
        return jsonify({'message': 'User already exists'}), 400
    
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    new_user = User(username=data['username'], password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing credentials'}), 400
    
    if User.query.filter_by(username=data['username']).first() is None:
        return jsonify({'message': 'Invalid credentials'}), 401
    
    if not bcrypt.checkpw(data['password'].encode('utf-8'), User.query.filter_by(username=data['username']).first().password_hash):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    token = jwt.encode({
        'user': data['username'],
        'iss': 'task-manager',
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, PRIVATE_KEY, algorithm='RS256', headers={'kid': '1'})
    
    return jsonify({'token': token}), 200

@app.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': f'Hello {current_user}'}), 200
    
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'login-service'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)