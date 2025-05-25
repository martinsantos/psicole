"""Association tables for many-to-many relationships."""

from datetime import datetime
from database import db

# Association table for users and roles
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column('assigned_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
    db.Column('expires_at', db.DateTime, nullable=True),
    db.Column('is_active', db.Boolean, default=True, nullable=False)
)

# Association table for roles and permissions
role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column('assigned_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
    db.Column('expires_at', db.DateTime, nullable=True),
    db.Column('is_active', db.Boolean, default=True, nullable=False)
)

# Association table for users and groups
user_groups = db.Table(
    'user_groups',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column('assigned_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
    db.Column('expires_at', db.DateTime, nullable=True),
    db.Column('is_active', db.Boolean, default=True, nullable=False)
)

# Association table for users and permissions
user_permissions = db.Table(
    'user_permissions',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    db.Column('granted_at', db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column('granted_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
    db.Column('expires_at', db.DateTime, nullable=True),
    db.Column('is_active', db.Boolean, default=True, nullable=False)
)

# Association table for groups and permissions
group_permissions = db.Table(
    'group_permissions',
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    db.Column('granted_at', db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column('granted_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL')),
    db.Column('expires_at', db.DateTime, nullable=True),
    db.Column('is_active', db.Boolean, default=True, nullable=False)
)
