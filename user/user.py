from functools import wraps
from flask import Flask, Blueprint, request, jsonify
from datetime import datetime
import logging
from database.models import *

# configure database and flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgrespassword@postgres.default.svc.cluster.local:5432/taskdb"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

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

# Health check endpoint
@app.route('/users/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'user-service',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/users/<string:user_name>', methods=['GET'])
def get_user(user_name):
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
    logger.info(f'Fetching colleagues for user {user_name}')
    user_id = User.query.filter_by(username=user_name).first().id
    teams_ids = [(team.id, team.name) for team in TeamMember.query.filter_by(user_id=user_id).all()]
    team_colleagues = []
    for team_id,team_name in teams_ids:
        if team_colleagues.get(team_name) is None:
            team_colleagues[team_name] = set()
        members = TeamMember.query.filter_by(team_id=team_id).all()
        for member in members:
            if member.user.username != user_name:
                team_colleagues[team_name].add((member.user.username, member.user.firstName, member.user.lastName, member.role))
    logger.info(f'Colleagues found: {team_colleagues}')
    result = {}
    for team_name, colleagues in team_colleagues.items():
        result[team_name] = list(colleagues)
    return jsonify({'colleagues': result}), 200

@app.route('/users/tasks', methods=['GET'])
@get_user_from_headers
def get_user_tasks(user_name):
    logger.info(f'Fetching tasks for user {user_name}')
    user_id = User.query.filter_by(username=user_name).first().id
    assignments = TaskAssignment.query.filter_by(user_id=user_id).all()
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
    logger.info(f'Fetching notes created by user {user_name}')
    user_id = User.query.filter_by(username=user_name).first().id
    notes = Note.query.filter_by(created_by=user_id).all()
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

# Error handler
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)