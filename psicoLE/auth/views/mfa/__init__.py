"""MFA authentication views."""
from flask import Blueprint

# Create MFA blueprint
mfa_bp = Blueprint('mfa', __name__, url_prefix='/mfa')

# Import and register all MFA views
from . import verify, setup

# Register blueprints
mfa_bp.register_blueprint(verify.mfa_verify_bp)
mfa_bp.register_blueprint(setup.mfa_setup_bp)  # noqa
