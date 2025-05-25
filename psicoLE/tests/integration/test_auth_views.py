"""Pruebas de integración para las vistas de autenticación."""
import pytest
from flask import url_for

# Pruebas para el inicio de sesión
def test_login_page(client):
    """Test que verifica que la página de inicio de sesión se carga correctamente."""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'Iniciar sesi\xc3\xb3n' in response.data

# Prueba de inicio de sesión exitoso
def test_successful_login(client, regular_user):
    """Test para un inicio de sesión exitoso."""
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Inicio de sesi\xc3\xb3n exitoso' in response.data

# Prueba de inicio de sesión fallido
def test_failed_login(client, regular_user):
    """Test para un inicio de sesión fallido."""
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Usuario o contrase\xc3\xb1a inv\xc3\xa1lidos' in response.data

# Prueba de cierre de sesión
def test_logout(client, admin_user):
    """Test para el cierre de sesión."""
    # Iniciar sesión primero
    client.post('/auth/login', data={
        'username': 'testadmin',
        'password': 'testpass123'
    }, follow_redirects=True)
    
    # Cerrar sesión
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Has cerrado sesi\xc3\xb3n correctamente' in response.data

# Prueba de acceso a ruta protegida sin autenticación
def test_protected_route_unauthorized(client):
    """Test que verifica el acceso denegado a rutas protegidas sin autenticación."""
    response = client.get('/admin/', follow_redirects=True)
    assert b'Por favor inicia sesi\xc3\xb3n para acceder a esta p\xc3\xa1gina' in response.data

# Prueba de acceso a ruta protegida con usuario sin permisos
def test_protected_route_forbidden(client, regular_user):
    """Test que verifica el acceso denegado a rutas protegidas sin permisos suficientes."""
    # Iniciar sesión como usuario regular
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, follow_redirects=True)
    
    # Intentar acceder al panel de administración
    response = client.get('/admin/', follow_redirects=True)
    assert response.status_code == 403  # Forbidden
    assert b'No tienes permiso para acceder a esta p\xc3\xa1gina' in response.data
