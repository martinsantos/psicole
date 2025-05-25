import os
import tempfile
import pytest
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, desc, event
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import StaticPool
from app import create_app
from database import db as _db
from auth.models import User, Role, Permission

# Use an in-memory SQLite database for testing
TEST_DATABASE_URI = 'sqlite:///:memory:'

# Mock Cuota model to avoid circular imports
class Cuota(_db.Model):
    __tablename__ = 'cuotas'
    id = Column(Integer, primary_key=True)
    periodo = Column(String(50), nullable=False)
    profesional_id = Column(Integer, ForeignKey('professionals.id'))

# Mock Professional model to avoid circular imports
class Professional(_db.Model):
    __tablename__ = 'professionals'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    cuotas = relationship('Cuota', backref='profesional', lazy='dynamic',
                         order_by=lambda: desc(Cuota.periodo))
    user = relationship('User', backref='professional')

# Create all tables in the test database
@pytest.fixture(scope='session')
def app():
    """Create and configure a new test app."""
    # Create a test app with in-memory SQLite database
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': TEST_DATABASE_URI,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })

    # Create all tables
    with app.app_context():
        _db.create_all()

    yield app

    # Clean up
    with app.app_context():
        _db.drop_all()

@pytest.fixture(scope='function')
def db(app):
    """Provide a clean database for each test with proper transaction handling."""
    with app.app_context():
        # Start a transaction
        connection = _db.engine.connect()
        transaction = connection.begin()
        
        # Create a session using the connection
        session_factory = sessionmaker(bind=connection)
        session = session_factory()
        
        # Bind the session to the app
        _db.session = session
        
        # Create all tables if they don't exist
        _db.create_all()
        
        # Create default roles and permissions
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator')
            _db.session.add(admin_role)
        
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular User')
            _db.session.add(user_role)
        
        # Create permissions if they don't exist
        admin_perm = Permission.query.filter_by(name='admin').first()
        if not admin_perm:
            admin_perm = Permission(name='admin', description='Admin Access')
            _db.session.add(admin_perm)
        
        user_perm = Permission.query.filter_by(name='user').first()
        if not user_perm:
            user_perm = Permission(name='user', description='User Access')
            _db.session.add(user_perm)
        
        # Assign permissions to roles
        if admin_perm not in admin_role.permissions:
            admin_role.permissions.append(admin_perm)
        if user_perm not in user_role.permissions:
            user_role.permissions.append(user_perm)
        
        _db.session.commit()
        
        yield _db
        
        # Clean up
        _db.session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope='function')
def client(app, db):
    """A test client for the app."""
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture(scope='function')
def test_role(db):
    """Create a test role."""
    role = Role(name='test_role', description='Test Role')
    db.session.add(role)
    db.session.commit()
    return role

@pytest.fixture(scope='function')
def admin_role(db):
    """Get or create an admin role."""
    role = Role.query.filter_by(name='admin').first()
    if not role:
        role = Role(name='admin', description='Administrator')
        db.session.add(role)
        db.session.commit()
    return role

@pytest.fixture(scope='function')
def user_role(db):
    """Get or create a regular user role."""
    role = Role.query.filter_by(name='user').first()
    if not role:
        role = Role(name='user', description='Regular User')
        db.session.add(role)
        db.session.commit()
    return role

@pytest.fixture
def admin_user(db):
    """Crea un usuario administrador para pruebas."""
    user = User(
        username='testadmin',
        email='admin@test.com',
        first_name='Test',
        last_name='Admin',
        is_active=True,
        is_superuser=True,
        is_staff=True
    )
    user.set_password('testpass123')
    
    # Obtener el rol de administrador
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role:
        user.role = admin_role
    
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def regular_user(db):
    """Crea un usuario regular para pruebas."""
    user = User(
        username='testuser',
        email='user@test.com',
        first_name='Test',
        last_name='User',
        is_active=True
    )
    user.set_password('testpass123')
    
    # Obtener el rol de usuario
    user_role = Role.query.filter_by(name='user').first()
    if user_role:
        user.role = user_role
    
    db.session.add(user)
    db.session.commit()
    return user
