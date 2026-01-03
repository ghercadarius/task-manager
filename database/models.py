from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    firstName = db.Column(db.String(120), nullable=True)
    lastName = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    location = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'
    

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<Team {self.name}>'
    
class TeamMember(db.Model): # team <-> user
    __tablename__ = 'team_members'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), nullable=True)
    joined_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    team = db.relationship('Team', backref=db.backref('members', lazy=True))
    user = db.relationship('User', backref=db.backref('teams', lazy=True))

    def __repr__(self):
        return f'<TeamMember UserID: {self.user_id} TeamID: {self.team_id}>'
    
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    due_date = db.Column(db.DateTime, nullable=True)
    team = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    team_rel = db.relationship('Team', backref=db.backref('tasks', lazy=True))

    def __repr__(self):
        return f'<Task {self.title} Status: {self.status}>'
    

class TaskAssignment(db.Model): # task <-> user
    __tablename__ = 'task_assignments'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    task = db.relationship('Task', backref=db.backref('assignments', lazy=True))
    user = db.relationship('User', backref=db.backref('tasks_assigned', lazy=True))

    def __repr__(self):
        return f'<TaskAssignment TaskID: {self.task_id} UserID: {self.user_id}>'
    
class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    created_by_rel = db.relationship('User', backref=db.backref('notes_created', lazy=True))

    def __repr__(self):
        return f'<Note ID: {self.id} TaskID: {self.task_id} UserID: {self.user_id}>'
    
class UserNote(db.Model): # note <-> user
    __tablename__ = 'user_notes'
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('notes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    note = db.relationship('Note', backref=db.backref('user_notes', lazy=True))
    user = db.relationship('User', backref=db.backref('notes', lazy=True))

    def __repr__(self):
        return f'<UserNote NoteID: {self.note_id} UserID: {self.user_id}>'
    
class TaskNote(db.Model): # note <-> task
    __tablename__ = 'task_notes'
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('notes.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)

    note = db.relationship('Note', backref=db.backref('task_notes', lazy=True))
    task = db.relationship('Task', backref=db.backref('notes', lazy=True))

    def __repr__(self):
        return f'<TaskNote NoteID: {self.note_id} TaskID: {self.task_id}>'