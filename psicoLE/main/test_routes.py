from flask import Blueprint, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from auth.models import User, Role

# Create a Blueprint for test routes
test_bp = Blueprint('test', __name__)

@test_bp.route('/test/db')
def test_db():
    """Test database connection and basic queries"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        # Test User model
        users_count = User.query.count()
        roles_count = Role.query.count()
        
        return jsonify({
            'status': 'success',
            'database': 'connected',
            'users_count': users_count,
            'roles_count': roles_count
        })
    except Exception as e:
        current_app.logger.error(f"Database test failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@test_bp.route('/test/auth')
@login_required
def test_auth():
    """Test authentication and user session"""
    return jsonify({
        'status': 'success',
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'role': current_user.role.name if current_user.role else None,
            'is_authenticated': current_user.is_authenticated
        }
    })

@test_bp.route('/test/error')
def test_error():
    """Test error handling"""
    # This will trigger a division by zero error
    result = 1 / 0
    return str(result)
