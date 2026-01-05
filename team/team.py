from functools import wraps
from flask import Flask, request, jsonify
from flasgger import Swagger
from datetime import datetime
import logging
from database.models import *

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
            "route": '/teams/apispec.json',
        }
    ],
    "static_url_path": "/teams/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/teams/docs/"
}

swagger = Swagger(app, config=swagger_config, template={
    "info": {
        "title": "Team Service API",
        "version": "1.0",
        "description": "API for managing teams and team members"
    },
    "basePath": "/teams",
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
    """
    return jsonify({'status': 'healthy', 'service': 'team-service'}), 200


@app.route('/teams', methods=['GET'])
def get_all_teams():
    """Get all teams
    ---
    tags:
      - Teams
    responses:
      200:
        description: List of all teams
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              description:
                type: string
              created_at:
                type: string
              members:
                type: array
                items:
                  type: integer
    """
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
    """Get team by name
    ---
    tags:
      - Teams
    parameters:
      - name: team_name
        in: path
        type: string
        required: true
        description: Team name
        example: engineering
    responses:
      200:
        description: Team found
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            description:
              type: string
            created_at:
              type: string
            members:
              type: array
              items:
                type: string
      404:
        description: Team not found
    """
    team = Team.query.filter_by(name=team_name).first()
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    team_members = [member.user.username for member in TeamMember.query.filter_by(team_id=team.id).all()]
    team_data = {
        'id': team.id,
        'name': team.name,
        'description': team.description,
        'created_at': team.created_at,
        'members': team_members
    }
    return jsonify(team_data), 200

@app.route('/teams', methods=['POST'])
@get_user_from_headers
def create_team(user_name):
    """Create a new team
    ---
    tags:
      - Teams
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
              example: engineering
            description:
              type: string
              example: Engineering team
    responses:
      201:
        description: Team created
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            description:
              type: string
      400:
        description: Missing team name or team already exists
    """
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Team name is required'}), 400
    if Team.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Team name already exists'}), 400
    
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    team = Team(
        name=data['name'],
        description=data.get('description', '')
    )
    db.session.add(team)
    db.session.flush()
    
    # Add creator as first member with 'owner' role
    team_member = TeamMember(team_id=team.id, user_id=user.id, role='owner')
    db.session.add(team_member)
    db.session.commit()
    
    return jsonify({
        'id': team.id,
        'name': team.name,
        'description': team.description
    }), 201

@app.route('/teams/<int:team_id>', methods=['PUT'])
@get_user_from_headers
def update_team(user_name, team_id):
    """Update a team
    ---
    tags:
      - Teams
    parameters:
      - name: team_id
        in: path
        type: integer
        required: true
        description: Team ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            description:
              type: string
    responses:
      200:
        description: Team updated
      403:
        description: Unauthorized - user not a member
      404:
        description: Team not found
    """
    team = Team.query.get(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    member_ids = [member.user_id for member in team.members]
    if user.id not in member_ids:
        return jsonify({'error': 'Unauthorized to update this team. User is not a member'}), 403
    
    team.name = data.get('name', team.name)
    team.description = data.get('description', team.description)
    db.session.commit()
    
    return jsonify({
        'id': team.id,
        'name': team.name,
        'description': team.description
    }), 200


@app.route('/teams/<int:team_id>', methods=['DELETE'])
@get_user_from_headers
def delete_team(user_name, team_id):
    """Delete a team
    ---
    tags:
      - Teams
    parameters:
      - name: team_id
        in: path
        type: integer
        required: true
        description: Team ID
    responses:
      200:
        description: Team deleted successfully
      403:
        description: Unauthorized - user not a member
      404:
        description: Team not found
    """
    team = Team.query.get(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    member_ids = [member.user_id for member in team.members]
    if user.id not in member_ids:
        return jsonify({'error': 'Unauthorized to delete this team. User is not a member'}), 403
    
    db.session.delete(team)
    db.session.commit()
    return jsonify({'message': 'Team deleted successfully'}), 200

@app.route('/teams/<int:team_id>/members', methods=['POST'])
@get_user_from_headers
def add_member(user_name, team_id):
    """Add a member to a team
    ---
    tags:
      - Team Members
    parameters:
      - name: team_id
        in: path
        type: integer
        required: true
        description: Team ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - member_id
          properties:
            member_id:
              type: integer
              description: User ID to add
            role:
              type: string
              description: Role in the team
              example: member
    responses:
      200:
        description: Member added successfully
      400:
        description: Missing member ID or member already exists
      403:
        description: Unauthorized - user not a member
      404:
        description: Team or user not found
    """
    team = Team.query.get(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    data = request.get_json()
    if not data or not data.get('member_id'):
        return jsonify({'error': 'Member ID is required'}), 400
    
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    member_ids = [member.user_id for member in team.members]
    if user.id not in member_ids:
        return jsonify({'error': 'Unauthorized to add members to this team. User is not a member'}), 403

    new_member = User.query.get(data['member_id'])
    if not new_member:
        return jsonify({'error': 'User to add not found'}), 404
    
    if data['member_id'] in member_ids:
        return jsonify({'error': 'User is already a member'}), 400
    
    team_member = TeamMember(
        team_id=team_id,
        user_id=data['member_id'],
        role=data.get('role', 'member')
    )
    db.session.add(team_member)
    db.session.commit()
    
    return jsonify({'message': 'Member added successfully'}), 200

@app.route('/teams/<int:team_id>/members/<int:member_id>', methods=['DELETE'])
@get_user_from_headers
def remove_member(user_name, team_id, member_id):
    """Remove a member from a team
    ---
    tags:
      - Team Members
    parameters:
      - name: team_id
        in: path
        type: integer
        required: true
        description: Team ID
      - name: member_id
        in: path
        type: integer
        required: true
        description: User ID to remove
    responses:
      200:
        description: Member removed successfully
      403:
        description: Unauthorized - user not a member
      404:
        description: Team or member not found
    """
    team = Team.query.get(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    member_ids = [member.user_id for member in team.members]
    if user.id not in member_ids:
        return jsonify({'error': 'Unauthorized to remove members from this team. User is not a member'}), 403

    team_member = TeamMember.query.filter_by(team_id=team_id, user_id=member_id).first()
    if not team_member:
        return jsonify({'error': 'Member not found in team'}), 404
    
    db.session.delete(team_member)
    db.session.commit()
    return jsonify({'message': 'Member removed successfully'}), 200

@app.route('/teams/<int:team_id>/tasks', methods=['GET'])
def get_team_tasks(team_id):
    """Get all tasks for a team
    ---
    tags:
      - Team Resources
    parameters:
      - name: team_id
        in: path
        type: integer
        required: true
        description: Team ID
    responses:
      200:
        description: List of team tasks
        schema:
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
      404:
        description: Team not found
    """
    team = Team.query.get(team_id)
    if not team:
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

@app.route('/teams/<int:team_id>/notes', methods=['GET'])
def get_team_notes(team_id):
    """Get all notes for a team's tasks
    ---
    tags:
      - Team Resources
    parameters:
      - name: team_id
        in: path
        type: integer
        required: true
        description: Team ID
    responses:
      200:
        description: List of notes associated with team's tasks
        schema:
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
              author_id:
                type: integer
      404:
        description: Team not found
    """
    team = Team.query.get(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    tasks = Task.query.filter_by(team=team_id).all()
    task_notes = TaskNote.query.filter(TaskNote.task_id.in_([task.id for task in tasks])).all()
    notes_list = []
    for task_note in task_notes:
        note = Note.query.get(task_note.note_id)
        if note:
            notes_list.append({
                'id': note.id,
                'content': note.content,
                'created_at': note.created_at,
                'author_id': note.created_by
            })
    return jsonify(notes_list), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)