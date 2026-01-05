from functools import wraps
from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
from datetime import datetime
import logging
from database.models import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgrespassword@postgres.default.svc.cluster.local:5432/taskdb"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/tasks/apispec.json',
        }
    ],
    "static_url_path": "/tasks/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/tasks/docs/"
}

swagger = Swagger(app, config=swagger_config, template={
    "info": {
        "title": "Task Service API",
        "version": "1.0",
        "description": "API for managing tasks"
    },
    "basePath": "/tasks",
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

db.init_app(app)

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

@app.route('/tasks/health', methods=['GET'])
def health_check():
    """Health check endpoint
    ---
    responses:
      200:
        description: Service is healthy
    """
    return jsonify({'status': 'healthy', 'service': 'task-service'}), 200

@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    """Get all tasks
    ---
    responses:
      200:
        description: List of tasks
    """
    tasks = Task.query.all()
    return jsonify([{
        'id': t.id,
        'title': t.name,
        'description': t.description,
        'status': t.status,
        'created_at': t.created_at,
        'due_date': t.due_date,
        'team_id': t.team,
    } for t in tasks]), 200

@app.route('/tasks/my-tasks', methods=['GET'])
@get_user_from_headers
def get_user_tasks(user_name):
    """Get tasks assigned to current user
    ---
    responses:
      200:
        description: User's tasks
      404:
        description: User not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    assignments = TaskAssignment.query.filter_by(user_id=user.id).all()
    return jsonify([{
        'id': Task.query.get(a.task_id).id,
        'title': Task.query.get(a.task_id).title,
        'description': Task.query.get(a.task_id).description,
        'status': Task.query.get(a.task_id).status,
        'team_id': Task.query.get(a.task_id).team,
    } for a in assignments]), 200

@app.route('/tasks', methods=['POST'])
@get_user_from_headers
def create_task(user_name):
    """Create a new task
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - title
            - team_id
          properties:
            title:
              type: string
            description:
              type: string
            status:
              type: string
              enum: [pending, in_progress, completed]
            team_id:
              type: integer
    responses:
      201:
        description: Task created
      400:
        description: Missing required fields
      403:
        description: Unauthorized
      404:
        description: User or team not found
    """
    data = request.get_json()
    if not data or not data.get('title') or not data.get('team_id'):
        return jsonify({'error': 'Title and Team ID are required'}), 400

    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    team = Team.query.get(data['team_id'])
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    if user.id not in [m.user_id for m in team.members]:
        return jsonify({'error': 'Unauthorized'}), 403

    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        status=data.get('status', 'pending'),
        due_date=data.get('due_date'),
        team=data['team_id']
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({'id': task.id, 'title': task.title}), 201

@app.route('/tasks/<int:task_id>/assign/<int:user_id>', methods=['POST'])
@get_user_from_headers
def assign_task(user_name, task_id, user_id):
    """Assign a task to a user
    ---
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      201:
        description: Task assigned
      403:
        description: Unauthorized
      404:
        description: Task or user not found
    """
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    team = Team.query.get(task.team)
    if user.id not in [m.user_id for m in team.members]:
        return jsonify({'error': 'Unauthorized'}), 403

    assignee = User.query.get(user_id)
    if not assignee or assignee.id not in [m.user_id for m in team.members]:
        return jsonify({'error': 'Invalid assignee'}), 403

    assignment = TaskAssignment(task_id=task.id, user_id=assignee.id)
    db.session.add(assignment)
    db.session.commit()
    return jsonify({'task_id': task.id, 'user_id': assignee.id}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)