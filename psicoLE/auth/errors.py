"""Error handlers for the auth blueprint."""
from flask import render_template, request, jsonify
from werkzeug.exceptions import HTTPException

def forbidden(e):
    """Handle 403 Forbidden errors."""
    if request.accept_mimetypes.accept_json and \
       not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('auth/errors/403.html'), 403

def not_found(e):
    """Handle 404 Not Found errors."""
    if request.accept_mimetypes.accept_json and \
       not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('auth/errors/404.html'), 404

def internal_server_error(e):
    """Handle 500 Internal Server errors."""
    if request.accept_mimetypes.accept_json and \
       not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('auth/errors/500.html'), 500

# Register error handlers
def register_error_handlers(app):
    """Register error handlers with the Flask application."""
    app.errorhandler(403)(forbidden)
    app.errorhandler(404)(not_found)
    app.errorhandler(500)(internal_server_error)
    return app
