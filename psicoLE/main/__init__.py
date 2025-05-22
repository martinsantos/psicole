import os
from flask import Blueprint

# Get the directory of the current module
current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, 'templates')

# Create the main blueprint with template folder
main_bp = Blueprint(
    'main',
    __name__,
    template_folder=template_dir
)


# Import routes after creating the blueprint to avoid circular imports
from . import routes

# Import test routes only in development
import os
if os.environ.get('FLASK_ENV') == 'development':
    from . import test_routes
