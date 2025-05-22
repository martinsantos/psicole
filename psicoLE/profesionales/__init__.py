from flask import Blueprint

profesionales_bp = Blueprint('profesionales', __name__,
                         template_folder='templates',
                         static_folder='static',
                         url_prefix='/profesionales')

from . import views  # Import routes after blueprint creation to avoid circular imports