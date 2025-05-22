from flask import Blueprint

# Create the blueprint without registering it here
admin_bp = Blueprint('admin_dashboard', __name__,
                   template_folder='templates',
                   static_folder='static',
                   url_prefix='/admin')

def init_app(app):
    """Initialize the admin dashboard with the app."""
    # Import views here to avoid circular imports
    from . import views
    
    # Register the blueprint with the app
    app.register_blueprint(admin_bp)
    
    return app
