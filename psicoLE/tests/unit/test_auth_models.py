"""Pruebas unitarias para los modelos de autenticación."""
import pytest
from auth.models import User, Role, Permission
from werkzeug.security import check_password_hash

def test_create_user(db):
    """Test para crear un nuevo usuario."""
    # Crear un rol primero
    role = Role(name='test_role', description='Test Role')
    db.session.add(role)
    db.session.commit()
    
    # Crear usuario con todos los campos requeridos
    user = User(
        username='testuser',
        email='test@example.com',
        first_name='Test',
        last_name='User',
        is_active=True,
        role_id=role.id
    )
    user.set_password('testpass123')
    
    db.session.add(user)
    db.session.commit()
    
    assert user.id is not None
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.check_password('testpass123') is True
    assert user.check_password('wrongpass') is False

def test_user_roles(db):
    """Test para verificar los roles de usuario."""
    # Crear roles
    admin_role = Role(name='admin', description='Administrator')
    user_role = Role(name='user', description='Regular User')
    db.session.add_all([admin_role, user_role])
    db.session.commit()
    
    # Crear usuarios
    admin_user = User(
        username='admin_test',
        email='admin@test.com',
        role_id=admin_role.id
    )
    regular_user = User(
        username='regular_test',
        email='user@test.com',
        role_id=user_role.id
    )
    
    db.session.add_all([admin_user, regular_user])
    db.session.commit()
    
    # Verificar relaciones
    assert admin_user.role.name == 'admin'
    assert regular_user.role.name == 'user'
    assert admin_user.has_role('admin') is True
    assert regular_user.has_role('admin') is False

def test_permission_checks(db):
    """Test para verificar los permisos de usuario."""
    # Crear roles y permisos
    admin_role = Role(name='admin_role', description='Admin Role')
    user_role = Role(name='user_role', description='User Role')
    
    admin_perm = Permission(name='admin', description='Admin Access')
    user_perm = Permission(name='user', description='User Access')
    
    admin_role.permissions.append(admin_perm)
    user_role.permissions.append(user_perm)
    
    db.session.add_all([admin_role, user_role, admin_perm, user_perm])
    db.session.commit()
    
    # Crear usuarios
    admin_user = User(
        username='admin_test',
        email='admin@test.com',
        role_id=admin_role.id
    )
    regular_user = User(
        username='regular_test',
        email='user@test.com',
        role_id=user_role.id
    )
    
    db.session.add_all([admin_user, regular_user])
    db.session.commit()
    
    # Verificar permisos
    assert admin_user.has_permission('admin') is True
    assert regular_user.has_permission('user') is True
    assert regular_user.has_permission('admin') is False

def test_user_representation(db):
    """Test para la representación en cadena del usuario."""
    role = Role(name='test_role', description='Test Role')
    db.session.add(role)
    db.session.commit()
    
    user = User(
        username='testuser',
        email='test@example.com',
        role_id=role.id
    )
    db.session.add(user)
    db.session.commit()
    
    assert str(user) == f'<User {user.username}>'
    assert repr(user) == f'<User {user.username}>'

def test_password_hashing(db):
    """Test para verificar el hashing de contraseñas."""
    role = Role(name='test_role', description='Test Role')
    db.session.add(role)
    db.session.commit()
    
    user = User(
        username='testhash',
        email='testhash@example.com',
        role_id=role.id
    )
    password = 'testpass123'
    user.set_password(password)
    
    # Verificar que la contraseña se ha hasheado correctamente
    assert user.password_hash is not None
    assert user.password_hash != password
    assert user.check_password(password) is True
    assert user.check_password('wrongpass') is False
