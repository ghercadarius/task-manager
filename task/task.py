from functools import wraps
from flask import Flask, Blueprint, request, jsonify
from datetime import datetime
import logging
from database.models import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgrespassword@postgres.default.svc.cluster.local:5432/taskdb"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
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
    return jsonify({'status': 'healthy', 'service': 'task-service'}), 200

@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    tasks = Task.query.all()
    tasks_list = []
    for task in tasks:
        tasks_list.append({
            'id': task.id,
            'title': task.name,
            'description': task.description,
            'status': task.status,
            'created_at': task.created_at,
            'due_date': task.due_date,
            'team_id': task.team,
        })
    return jsonify(tasks_list), 200

@app.route('/tasks/my-tasks', methods=['GET'])
@get_user_from_headers
def get_user_tasks(user_name):
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    assignments = TaskAssignment.query.filter_by(user_id=user.id).all()
    tasks_list = []
    for assignment in assignments:
        task = Task.query.get(assignment.task_id)
        tasks_list.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'created_at': task.created_at,
            'due_date': task.due_date,
            'team_id': task.team,
        })
    return jsonify(tasks_list), 200

@app.route('/tasks', methods=['POST'])
@get_user_from_headers
def create_task(user_name):
    data = request.get_json()
    if not data or not data.get('title') or not data.get('team_id'):
        return jsonify({'error': 'Title and Team ID are required'}), 400

    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    team = Team.query.get(data['team_id'])
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    if user.id not in [member.user_id for member in team.members]:
        return jsonify({'error': 'Unauthorized to create task for this team. User is not a member'}), 403

    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        status=data.get('status', 'pending'),
        due_date=data.get('due_date', None),
        team=data['team_id']
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'created_at': task.created_at,
        'due_date': task.due_date,
        'team_id': task.team,
    }), 201

@app.route('/tasks/<task_id>/assign/<user_id>', methods=['POST'])
@get_user_from_headers
def assign_task(user_name, task_id, user_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    team = Team.query.get(task.team)
    if user.id not in [member.user_id for member in team.members]:
        return jsonify({'error': 'Unauthorized to assign tasks for this team. User is not a member'}), 403

    assignee = User.query.get(user_id)
    if not assignee:
        return jsonify({'error': 'Assignee user not found'}), 404
    if assignee.id not in [member.user_id for member in team.members]:
        return jsonify({'error': 'Assignee is not a member of the task\'s team'}), 403

    assignment = TaskAssignment(
        task_id=task.id,
        user_id=assignee.id
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify({
        'task_id': assignment.task_id,
        'user_id': assignment.user_id,
        'assigned_at': assignment.assigned_at
    }), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)