from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from sqlalchemy.orm import relationship

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __init__(self, username, email, is_active=True, role_id=None):
        self.username = username
        self.email = email
        self.is_active = is_active
        if role_id:
            self.role_id = role_id
            
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login methods
    # get_id is provided by UserMixin by default, using self.id
    # is_authenticated: provided by UserMixin, returns True if user is logged in
    # is_active: can be customized, e.g. if users can be deactivated. Default is True.
    # is_anonymous: provided by UserMixin, returns True if user is not logged in.

    # Back-reference for DataChangeRequest reviewer
    # Using a simpler relationship to avoid circular imports
    # The actual relationship will be set up in the application factory
    # after all models are loaded
    reviewed_data_changes = None


    def __repr__(self):
        return f'<User {self.username}>'
