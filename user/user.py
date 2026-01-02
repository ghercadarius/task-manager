from flask import Flask, Blueprint, request, jsonify
from datetime import datetime
import logging

app = Flask(__name__)
api = Blueprint('api', __name__, url_prefix='/users')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# Example GET endpoint
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    logger.info(f'Fetching user {user_id}')
    return jsonify({
        'id': user_id,
        'name': 'John Doe',
        'email': 'john@example.com'
    }), 200

# Example POST endpoint
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    logger.info(f'Creating user: {data}')
    return jsonify({
        'id': 1,
        'message': 'User created successfully',
        'data': data
    }), 201

# Error handler
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)