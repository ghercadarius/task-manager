from functools import wraps
from flask import Flask, request, jsonify
from flasgger import Swagger
from datetime import datetime
import logging
from database.models import *

# configure database and flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgrespassword@postgres.default.svc.cluster.local:5432/taskdb"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/users/apispec.json',
        }
    ],
    "static_url_path": "/users/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/users/docs/"
}

swagger = Swagger(app, config=swagger_config, template={
    "info": {
        "title": "User Service API",
        "version": "1.0",
        "description": "API for managing users and their resources"
    },
    "basePath": "/users",
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer {token}'"
        }
    },
    "security": [
        {"Bearer": []}
    ]
})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with app.app_context():
    db.create_all()
    logger.info("Database tables created")

def get_user_from_headers(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_name = request.headers.get('X-User')
        return f(user_name, *args, **kwargs)
    return decorated

@app.route('/users/health', methods=['GET'])
def health():
    """Health check endpoint
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
            service:
              type: string
            timestamp:
              type: string
    """
    return jsonify({
        'status': 'healthy',
        'service': 'user-service',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/users/<string:user_name>', methods=['GET'])
def get_user(user_name):
    """Get user by username
    ---
    tags:
      - Users
    parameters:
      - name: user_name
        in: path
        type: string
        required: true
        description: Username to fetch
        example: johndoe
    responses:
      200:
        description: User found
        schema:
          type: object
          properties:
            id:
              type: integer
            firstName:
              type: string
            lastName:
              type: string
            email:
              type: string
            created_at:
              type: string
            location:
              type: string
      404:
        description: User not found
    """
    logger.info(f'Fetching user {user_name}')
    result_user = User.query.filter_by(username=user_name).first()
    if not result_user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({
        'id': result_user.id,
        'firstName': result_user.firstName if result_user.firstName else 'Not provided',
        'lastName': result_user.lastName if result_user.lastName else 'Not provided',
        'email': result_user.email if result_user.email else 'Not provided',
        'created_at': result_user.created_at,
        'location': result_user.location if result_user.location else 'Not provided'
    }), 200

@app.route('/users/colleagues', methods=['GET'])
@get_user_from_headers
def get_colleagues(user_name):
    """Get colleagues from all teams
    ---
    tags:
      - Users
    responses:
      200:
        description: List of colleagues grouped by team
        schema:
          type: object
          properties:
            colleagues:
              type: object
              additionalProperties:
                type: array
                items:
                  type: array
      404:
        description: User not found
    """
    logger.info(f'Fetching colleagues for user {user_name}')
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    user_id = user.id
    team_memberships = TeamMember.query.filter_by(user_id=user_id).all()
    team_colleagues = {}
    
    for membership in team_memberships:
        team = Team.query.get(membership.team_id)
        if team.name not in team_colleagues:
            team_colleagues[team.name] = []
        members = TeamMember.query.filter_by(team_id=membership.team_id).all()
        for member in members:
            if member.user.username != user_name:
                team_colleagues[team.name].append({
                    'username': member.user.username,
                    'firstName': member.user.firstName,
                    'lastName': member.user.lastName,
                    'role': member.role
                })
    
    logger.info(f'Colleagues found: {team_colleagues}')
    return jsonify({'colleagues': team_colleagues}), 200

@app.route('/users/tasks', methods=['GET'])
@get_user_from_headers
def get_user_tasks(user_name):
    """Get tasks assigned to current user
    ---
    tags:
      - Users
    responses:
      200:
        description: List of tasks assigned to user
        schema:
          type: object
          properties:
            tasks:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  title:
                    type: string
                  description:
                    type: string
                  status:
                    type: string
                  created_at:
                    type: string
                  due_date:
                    type: string
                  team:
                    type: string
      404:
        description: User not found
    """
    logger.info(f'Fetching tasks for user {user_name}')
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    assignments = TaskAssignment.query.filter_by(user_id=user.id).all()
    tasks = []
    for assignment in assignments:
        task = assignment.task
        tasks.append({
            'id': task.id,
            'title': task.title,
            'description': task.description if task.description else 'Not provided',
            'status': task.status,
            'created_at': task.created_at,
            'due_date': task.due_date if task.due_date else 'Not provided',
            'team': task.team_rel.name
        })
    logger.info(f'Tasks found: {tasks}')
    return jsonify({'tasks': tasks}), 200

@app.route('/users/notes', methods=['GET'])
@get_user_from_headers
def get_user_notes(user_name):
    """Get notes created by current user
    ---
    tags:
      - Users
    responses:
      200:
        description: List of notes created by user
        schema:
          type: object
          properties:
            notes:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  content:
                    type: string
                  created_at:
                    type: string
                  updated_at:
                    type: string
      404:
        description: User not found
    """
    logger.info(f'Fetching notes created by user {user_name}')
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    notes = Note.query.filter_by(created_by=user.id).all()
    result_notes = []
    for note in notes:
        result_notes.append({
            'id': note.id,
            'content': note.content,
            'created_at': note.created_at,
            'updated_at': note.updated_at
        })
    logger.info(f'Notes found: {result_notes}')
    return jsonify({f'notes made by user {user_name}': result_notes}), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)