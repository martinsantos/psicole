import os
import sys
from flask import Flask, session, render_template
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Initialize extensions
db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config=None):
    """Application factory function"""
    # Create the Flask application
    app = Flask(__name__, instance_relative_config=True)
    
    # Load default configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///instance/psicole.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-123'),
        # Email configuration
        MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
        MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
        MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true',
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME', ''),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', ''),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', '')
    )
    
    # Override with any custom config passed in
    if config is not None:
        app.config.update(config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError as e:
        print(f"Error creating instance folder: {e}")
    
    # Initialize extensions with app
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    
    # Register blueprints
    from auth.views import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Import and register main blueprint
    try:
        from main import main_bp
        app.register_blueprint(main_bp)
    except ImportError as e:
        print(f"Warning: Could not import main blueprint: {e}")
    
    # Register other blueprints
    register_blueprints(app)
    
    # Configure database
    with app.app_context():
        db.create_all()
    
    # User loader function
    from auth.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Add test routes in development
    if app.config.get('FLASK_ENV') == 'development':
        from main.test_routes import test_bp
        app.register_blueprint(test_bp, url_prefix='/test')
    
    # Simple route for testing
    @app.route('/')
    def index():
        return '¡Bienvenido a PsicoLE! <a href="/auth/login">Iniciar sesión</a>'
    
    return app

def register_blueprints(app):
    """Register all blueprints"""
    blueprints = [
        ('profesionales.views', 'profesionales_bp', '/profesionales'),
        ('cobranzas.views', 'cobranzas_bp', '/cobranzas'),
        ('facturacion.views', 'facturacion_bp', '/facturacion'),
        ('configuraciones.views', 'configuraciones_bp', '/configuraciones'),
        ('autogestion.views', 'autogestion_bp', '/autogestion'),
        ('admin_dashboard.views', 'admin_dashboard_bp', '/admin'),
        ('reports.views', 'reports_bp', '/reports')
    ]
    
    for module_path, bp_name, url_prefix in blueprints:
        try:
            module = __import__(module_path, fromlist=[bp_name])
            bp = getattr(module, bp_name, None)
            if bp and hasattr(bp, 'url_prefix'):
                app.register_blueprint(bp)
            else:
                app.register_blueprint(bp, url_prefix=url_prefix)
        except ImportError as e:
            print(f"Warning: Could not import {bp_name} from {module_path}: {e}")

# Load environment variables
load_dotenv()

# Create app instance
app = create_app()

# File Upload Configuration
def get_upload_folder():
    """Get the upload folder path"""
    upload_folder_name = 'professional_documents'
    upload_folder = os.path.join(app.instance_path, 'uploads', upload_folder_name)
    
    # Ensure the upload folder exists
    try:
        os.makedirs(upload_folder, exist_ok=True)
    except OSError as e:
        print(f"Error creating upload folder: {e}")
    
    return upload_folder

# Configure upload folder in app config
app.config['UPLOAD_FOLDER'] = get_upload_folder()
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'}

# Utility function for file uploads
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Make allowed_file available in templates or views if needed by adding to app context
@app.context_processor
def utility_processor():
    return dict(allowed_file=allowed_file)

@app.context_processor
def inject_utility_functions():
    def get_professional_by_user_id_fn(user_id):
        if user_id is None:
            return None
        return Professional.query.filter_by(user_id=user_id).first()
    
    # Context processor for pending data changes count
    # Moved here as it needs to be registered with the app
    from psicoLE.autogestion.models import DataChangeRequest # Import here to avoid circular if used early
    def pending_data_changes_count_fn():
        if current_user.is_authenticated and current_user.role and current_user.role.name in ['admin', 'staff']:
            return DataChangeRequest.query.filter_by(status='pending').count()
        return 0

    return dict(
        get_professional_by_user_id=get_professional_by_user_id_fn,
        pending_data_changes_count=pending_data_changes_count_fn
    )

def initialize_default_configurations():
    from psicoLE.configuraciones.utils import set_config_value, get_config_value
    
    # Define default configurations
    default_configs = {
        'default_professional_role_name': ('professional', 'The default role name assigned to new professional registrations.'),
        'items_per_page': ('10', 'Default number of items to display per page in paginated lists.'),
        'site_name': ('PsicoLE', 'The name of the website, displayed in titles and headers.'),
        'admin_email': ('admin@example.com', 'Email address for administrative notifications.')
    }
    
    for key, (value, description) in default_configs.items():
        if get_config_value(key) is None: # Check if key already exists
            set_config_value(key, value, description)
            print(f"Configuration '{key}' set to '{value}'.")

    # Ensure invoice specific configurations exist
    from psicoLE.facturacion.services import ensure_invoice_config_exists
    ensure_invoice_config_exists() # This is already called by initialize_default_configurations if facturacion.services is imported there.
                                 # Let's ensure it's robust.
    
    # Ensure Mercado Pago configurations exist
    def ensure_config_exists(key, default_value, description):
        from psicoLE.configuraciones.utils import get_config_value, set_config_value
        if get_config_value(key) is None:
            set_config_value(key, default_value, description)
            print(f"Configuration '{key}' set to '{default_value}'")
    ensure_config_exists('mercadopago_access_token', 'YOUR_SANDBOX_ACCESS_TOKEN', 'Mercado Pago Sandbox Access Token.')
    ensure_config_exists('mercadopago_public_key', 'YOUR_SANDBOX_PUBLIC_KEY', 'Mercado Pago Sandbox Public Key.')
    print("Mercado Pago configurations checked/initialized.")


# Initialize Mercado Pago SDK
import mercadopago
mp_sdk = None

def get_mp_sdk():
    global mp_sdk
    if mp_sdk is None:
        access_token = get_config_value('mercadopago_access_token')
        if access_token and access_token != 'YOUR_SANDBOX_ACCESS_TOKEN':
            mp_sdk = mercadopago.SDK(access_token)
        else:
            # SDK cannot be initialized without a valid token.
            # Log this or handle as appropriate. For now, mp_sdk remains None.
            print("WARNING: Mercado Pago SDK not initialized. Access token is missing or default.")
    return mp_sdk


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Initialize Roles
        if Role.query.filter_by(name='admin').first() is None:
            db.session.add(Role(name='admin'))
        if Role.query.filter_by(name='staff').first() is None:
            db.session.add(Role(name='staff'))
        if Role.query.filter_by(name='professional').first() is None:
            db.session.add(Role(name='professional'))
        db.session.commit()
        print("Initial roles checked/created.")

        # Initialize Default Configurations (this will also call ensure_invoice_config_exists via facturacion.services import)
        initialize_default_configurations()
        
        # Initialize MP SDK (it will be initialized on first call to get_mp_sdk())
        # You could explicitly initialize it here too if preferred:
        # get_mp_sdk() 

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback() # Rollback session in case of DB error leading to 500
        return render_template('errors/500.html'), 500
    
    app.run(debug=True, host='0.0.0.0', port=5001)
