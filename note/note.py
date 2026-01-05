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
            "route": '/notes/apispec.json',
        }
    ],
    "static_url_path": "/notes/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/notes/docs/"
}

swagger = Swagger(app, config=swagger_config, template={
    "info": {
        "title": "Note Service API",
        "version": "1.0",
        "description": "API for managing notes, user notes, and task notes"
    },
    "basePath": "/notes",
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

@app.route('/notes/health', methods=['GET'])
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
    return jsonify({'status': 'healthy', 'service': 'note-service'}), 200

@app.route('/notes', methods=['GET'])
@get_user_from_headers
def get_all_notes(user_name):
    """Get all notes for current user (created and assigned)
    ---
    tags:
      - Notes
    responses:
      200:
        description: List of user's notes
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
                  title:
                    type: string
                  content:
                    type: string
                  created_at:
                    type: string
                  updated_at:
                    type: string
      404:
        description: User not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    notes = Note.query.filter_by(created_by=user.id).all()
    notes_list = []
    seen_ids = set()
    
    for note in notes:
        if note.id not in seen_ids:
            notes_list.append({
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'created_at': note.created_at,
                'updated_at': note.updated_at
            })
            seen_ids.add(note.id)
    
    assigned_notes_ids = [assignment.note_id for assignment in UserNote.query.filter_by(user_id=user.id).all()]
    for note_id in assigned_notes_ids:
        if note_id not in seen_ids:
            note = Note.query.get(note_id)
            if note:
                notes_list.append({
                    'id': note.id,
                    'title': note.title,
                    'content': note.content,
                    'created_at': note.created_at,
                    'updated_at': note.updated_at
                })
                seen_ids.add(note_id)
    
    return jsonify({'notes': notes_list}), 200

@app.route('/notes/<int:note_id>', methods=['GET'])
@get_user_from_headers
def get_note_by_id(user_name, note_id):
    """Get a specific note by ID
    ---
    tags:
      - Notes
    parameters:
      - name: note_id
        in: path
        type: integer
        required: true
        description: Note ID
    responses:
      200:
        description: Note found
        schema:
          type: object
          properties:
            id:
              type: integer
            title:
              type: string
            content:
              type: string
            created_at:
              type: string
            updated_at:
              type: string
      403:
        description: Access denied to this note
      404:
        description: Note or user not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    note = Note.query.get(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    if note.created_by != user.id and not UserNote.query.filter_by(user_id=user.id, note_id=note.id).first():
        return jsonify({'error': 'Access denied to this note'}), 403
    
    return jsonify({
        'id': note.id,
        'title': note.title,
        'content': note.content,
        'created_at': note.created_at,
        'updated_at': note.updated_at
    }), 200

@app.route('/notes/team/<int:team_id>', methods=['GET'])
@get_user_from_headers
def get_team_notes(user_name, team_id):
    """Get all notes for a team's tasks
    ---
    tags:
      - Team Notes
    parameters:
      - name: team_id
        in: path
        type: integer
        required: true
        description: Team ID
    responses:
      200:
        description: List of team notes
        schema:
          type: object
          properties:
            notes:
              type: array
              items:
                type: object
                properties:
                  task_id:
                    type: integer
                  task_title:
                    type: string
                  id:
                    type: integer
                  content:
                    type: string
                  created_at:
                    type: string
                  author_id:
                    type: integer
      403:
        description: User is not a member of this team
      404:
        description: User not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if TeamMember.query.filter_by(team_id=team_id, user_id=user.id).first() is None:
        return jsonify({'error': 'User is not a member of this team'}), 403
    
    tasks = Task.query.filter_by(team=team_id).all()
    notes_list = []
    for task in tasks:
        task_notes = TaskNote.query.filter_by(task_id=task.id).all()
        for task_note in task_notes:
            note = Note.query.get(task_note.note_id)
            if note:
                notes_list.append({
                    'task_id': task.id,
                    'task_title': task.title,
                    'id': note.id,
                    'content': note.content,
                    'created_at': note.created_at,
                    'author_id': note.created_by
                })
    
    return jsonify({'notes': notes_list}), 200

@app.route('/notes/task/<int:task_id>', methods=['GET'])
@get_user_from_headers
def get_task_notes(user_name, task_id):
    """Get all notes for a specific task
    ---
    tags:
      - Task Notes
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
        description: Task ID
    responses:
      200:
        description: List of task notes
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
                  author_id:
                    type: integer
      403:
        description: User is not a member of the team for this task
      404:
        description: Task or user not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if TeamMember.query.filter_by(team_id=task.team, user_id=user.id).first() is None:
        return jsonify({'error': 'User is not a member of the team for this task'}), 403
    
    task_notes = TaskNote.query.filter_by(task_id=task.id).all()
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
    
    return jsonify({'notes': notes_list}), 200

@app.route('/notes', methods=['POST'])
@get_user_from_headers
def create_note(user_name):
    """Create a new note
    ---
    tags:
      - Notes
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - content
          properties:
            title:
              type: string
              example: Meeting notes
            content:
              type: string
              example: Important points from the meeting
    responses:
      201:
        description: Note created successfully
        schema:
          type: object
          properties:
            message:
              type: string
            note_id:
              type: integer
      400:
        description: Content is required
      404:
        description: User not found
    """
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': 'Content is required'}), 400
    
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    note = Note(
        title=data.get('title', ''),
        content=data['content'],
        created_by=user.id
    )
    db.session.add(note)
    db.session.commit()
    
    return jsonify({'message': 'Note created successfully', 'note_id': note.id}), 201

@app.route('/notes/<int:note_id>', methods=['PUT'])
@get_user_from_headers
def update_note(user_name, note_id):
    """Update an existing note
    ---
    tags:
      - Notes
    parameters:
      - name: note_id
        in: path
        type: integer
        required: true
        description: Note ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            title:
              type: string
            content:
              type: string
    responses:
      200:
        description: Note updated successfully
      403:
        description: Only the creator can update this note
      404:
        description: Note or user not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    note = Note.query.get(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    if note.created_by != user.id:
        return jsonify({'error': 'Only the creator can update this note'}), 403
    
    data = request.get_json()
    if data.get('title'):
        note.title = data['title']
    if data.get('content'):
        note.content = data['content']
    note.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'message': 'Note updated successfully'}), 200

@app.route('/notes/<int:note_id>', methods=['DELETE'])
@get_user_from_headers
def delete_note(user_name, note_id):
    """Delete a note
    ---
    tags:
      - Notes
    parameters:
      - name: note_id
        in: path
        type: integer
        required: true
        description: Note ID
    responses:
      200:
        description: Note deleted successfully
      403:
        description: Only the creator can delete this note
      404:
        description: Note or user not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    note = Note.query.get(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    if note.created_by != user.id:
        return jsonify({'error': 'Only the creator can delete this note'}), 403
    
    # Delete related assignments
    UserNote.query.filter_by(note_id=note.id).delete()
    TaskNote.query.filter_by(note_id=note.id).delete()
    
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted successfully'}), 200

@app.route('/notes/<int:note_id>/assign/<int:assignee_user_id>', methods=['POST'])
@get_user_from_headers
def assign_note_to_user(user_name, note_id, assignee_user_id):
    """Assign a note to a user
    ---
    tags:
      - Note Assignments
    parameters:
      - name: note_id
        in: path
        type: integer
        required: true
        description: Note ID
      - name: assignee_user_id
        in: path
        type: integer
        required: true
        description: User ID to assign the note to
    responses:
      200:
        description: Note assigned successfully
      400:
        description: Note already assigned to this user
      403:
        description: Only the creator can assign this note
      404:
        description: Note, user, or assignee not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    note = Note.query.get(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    if note.created_by != user.id:
        return jsonify({'error': 'Only the creator can assign this note'}), 403
    
    assignee_user = User.query.get(assignee_user_id)
    if not assignee_user:
        return jsonify({'error': 'Assignee user not found'}), 404
    
    if UserNote.query.filter_by(note_id=note.id, user_id=assignee_user.id).first():
        return jsonify({'error': 'Note already assigned to this user'}), 400
    
    user_note = UserNote(
        note_id=note.id,
        user_id=assignee_user.id
    )
    db.session.add(user_note)
    db.session.commit()
    
    return jsonify({'message': f'Note {note.id} assigned to user {assignee_user.username} successfully'}), 200

@app.route('/notes/<int:note_id>/link/task/<int:task_id>', methods=['POST'])
@get_user_from_headers
def link_note_to_task(user_name, note_id, task_id):
    """Link a note to a task
    ---
    tags:
      - Task Notes
    parameters:
      - name: note_id
        in: path
        type: integer
        required: true
        description: Note ID
      - name: task_id
        in: path
        type: integer
        required: true
        description: Task ID
    responses:
      200:
        description: Note linked to task successfully
      400:
        description: Note already linked to this task
      403:
        description: User is not a member of the team for this task
      404:
        description: Note, task, or user not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    note = Note.query.get(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if TeamMember.query.filter_by(team_id=task.team, user_id=user.id).first() is None:
        return jsonify({'error': 'User is not a member of the team for this task'}), 403
    
    if TaskNote.query.filter_by(note_id=note.id, task_id=task.id).first():
        return jsonify({'error': 'Note already linked to this task'}), 400
    
    task_note = TaskNote(
        note_id=note.id,
        task_id=task.id
    )
    db.session.add(task_note)
    db.session.commit()
    
    return jsonify({'message': f'Note {note.id} linked to task {task.title} successfully'}), 200

@app.route('/notes/<int:note_id>/unlink/task/<int:task_id>', methods=['DELETE'])
@get_user_from_headers
def unlink_note_from_task(user_name, note_id, task_id):
    """Unlink a note from a task
    ---
    tags:
      - Task Notes
    parameters:
      - name: note_id
        in: path
        type: integer
        required: true
        description: Note ID
      - name: task_id
        in: path
        type: integer
        required: true
        description: Task ID
    responses:
      200:
        description: Note unlinked from task successfully
      403:
        description: User is not a member of the team for this task
      404:
        description: Note, task, or link not found
    """
    user = User.query.filter_by(username=user_name).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    note = Note.query.get(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if TeamMember.query.filter_by(team_id=task.team, user_id=user.id).first() is None:
        return jsonify({'error': 'User is not a member of the team for this task'}), 403
    
    task_note = TaskNote.query.filter_by(note_id=note.id, task_id=task.id).first()
    if not task_note:
        return jsonify({'error': 'Note is not linked to this task'}), 404
    
    db.session.delete(task_note)
    db.session.commit()
    
    return jsonify({'message': f'Note {note.id} unlinked from task {task.title} successfully'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)