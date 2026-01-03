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

@app.route('/teams/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'team-service'}), 200


@app.route('/teams', methods=['GET'])
def get_all_teams():
    teams = Team.query.all()
    teams_list = []
    for team in teams:
        teams_list.append({
            'id': team.id,
            'name': team.name,
            'description': team.description,
            'created_at': team.created_at,
            'members': [member.user_id for member in team.members]
        })
    return jsonify(teams_list), 200


@app.route('/teams/<team_name>', methods=['GET'])
def get_team(team_name):
    team = Team.query.filter_by(name=team_name).first()
    team_members = [user.username for user in TeamMember.query.filter_by(team_id=team.id).all()]
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    team_data = {
        'id': team.id,
        'name': team.name,
        'description': team.description,
        'created_at': team.created_at,
        'members': team_members
    }
    return jsonify(team_data), 200

@app.route('/teams', methods=['POST'])
def create_team():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Team name is required'}), 400
    if Team.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Team name already exists'}), 400
    team = Team(
        name=data['name'],
        description=data.get('description', ''),
        members=data.get('members', [])
    )
    db.session.add(team)
    db.session.commit()
    return jsonify(team), 201

@app.route('/teams/<team_id>', methods=['PUT'])
@get_user_from_headers
def update_team(user_name, team_id):
    if team_id not in teams:
        return jsonify({'error': 'Team not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    team = Team.query.filter_by(id=team_id).first()
    team.name = data.get('name', team.name)
    team.description = data.get('description', team.description)
    team.members = data.get('members', team.members)
    user_id = User.query.filter_by(username=user_name).first().id
    if user_id in team.members:
        db.session.commit()
        return jsonify(team), 200
    else:
        return jsonify({'error': 'Unauthorized to update this team. User is not a member'}), 403


@app.route('/teams/<team_id>', methods=['DELETE'])
@get_user_from_headers
def delete_team(user_name, team_id):
    if team_id not in teams:
        return jsonify({'error': 'Team not found'}), 404
    
    team = Team.query.filter_by(id=team_id).first()
    user_id = User.query.filter_by(username=user_name).first().id
    if user_id in team.members:
        db.session.delete(team)
        db.session.commit()
        return jsonify({'message': 'Team deleted successfully'}), 200
    else:
        return jsonify({'error': 'Unauthorized to delete this team. User is not a member'}), 403

@app.route('/teams/<team_id>/members', methods=['POST'])
@get_user_from_headers
def add_member(user_name, team_id):
    if team_id not in Team.query.with_entities(Team.id).all():
        return jsonify({'error': 'Team not found'}), 404
    
    data = request.get_json()
    if not data or not data.get('member_id'):
        return jsonify({'error': 'Member ID is required'}), 400
    
    user_id = User.query.filter_by(username=user_name).first().id
    if user_id not in Team.query.filter_by(id=team_id).first().members:
        return jsonify({'error': 'Unauthorized to add members to this team. User is not a member'}), 403

    member_id = data['member_id']
    if member_id not in Team.query.filter_by(id=team_id).first().members:
        Team.query.filter_by(id=team_id).first().members.append(member_id)
    db.session.commit()
    return jsonify(Team.query.filter_by(id=team_id).first()), 200

@app.route('/teams/<team_id>/members/<member_id>', methods=['DELETE'])
@get_user_from_headers
def remove_member(user_name, team_id, member_id):
    if team_id not in Team.query.with_entities(Team.id).all():
        return jsonify({'error': 'Team not found'}), 404
    
    user_id = User.query.filter_by(username=user_name).first().id
    if user_id not in Team.query.filter_by(id=team_id).first().members:
        return jsonify({'error': 'Unauthorized to remove members from this team. User is not a member'}), 403

    if member_id in Team.query.filter_by(id=team_id).first().members:
        Team.query.filter_by(id=team_id).first().members.remove(member_id)
    db.session.commit()
    return jsonify(Team.query.filter_by(id=team_id).first()), 200

@app.route('/teams/<team_id>/tasks', methods=['GET'])
def get_team_tasks(team_id):
    if team_id not in Team.query.with_entities(Team.id).all():
        return jsonify({'error': 'Team not found'}), 404
    
    tasks = Task.query.filter_by(team=team_id).all()
    tasks_list = []
    for task in tasks:
        tasks_list.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'created_at': task.created_at,
            'due_date': task.due_date
        })
    return jsonify(tasks_list), 200

@app.route('/teams/<team_id>/notes', methods=['GET'])
def get_team_notes(team_id):
    if team_id not in Team.query.with_entities(Team.id).all():
        return jsonify({'error': 'Team not found'}), 404
    
    tasks = Task.query.filter_by(team=team_id).all()
    notes_ids = TaskNote.query.filter(TaskNote.task_id.in_([task.id for task in tasks])).all()
    notes_list = []
    for ids in notes_ids:
        note = Note.query.filter_by(id=ids.note_id).first()
        notes_list.append({
            'id': note.id,
            'content': note.content,
            'created_at': note.created_at,
            'author_id': note.author_id
        })
    return jsonify(notes_list), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)