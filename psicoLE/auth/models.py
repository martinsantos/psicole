from psicoLE.database import db # Corrected import
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin # Import UserMixin

class Role(db.Model):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    users = relationship('User', backref='role', lazy='dynamic')

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model): # Add UserMixin
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'))

    def __init__(self, username, password_hash, email, role_id=None):
        self.username = username
        self.password_hash = password_hash
        self.email = email
        if role_id:
            self.role_id = role_id

    # Flask-Login methods
    # get_id is provided by UserMixin by default, using self.id
    # is_authenticated: provided by UserMixin, returns True if user is logged in
    # is_active: can be customized, e.g. if users can be deactivated. Default is True.
    # is_anonymous: provided by UserMixin, returns True if user is not logged in.

    # Back-reference for DataChangeRequest reviewer
    reviewed_data_changes = relationship('DataChangeRequest', back_populates='reviewer', lazy='dynamic', foreign_keys='DataChangeRequest.reviewer_id')


    def __repr__(self):
        return f'<User {self.username}>'
