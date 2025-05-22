import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
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
    
    # Use a local SQLite database with absolute path
    import os
    from pathlib import Path
    
    # Get the absolute path to the project directory
    project_dir = Path(__file__).parent.absolute()
    
    # Create a 'data' directory if it doesn't exist
    data_dir = project_dir / 'data'
    data_dir.mkdir(exist_ok=True, mode=0o755)
    
    # Set the database path
    db_path = data_dir / 'psicole.db'
    db_uri = f'sqlite:///{db_path}'
    
    # Ensure the data directory is writable
    try:
        os.chmod(data_dir, 0o755)
        print(f"Using database at: {db_path}")
        print(f"Database URI: {db_uri}")
        print(f"Database directory: {data_dir}")
        print(f"Database directory permissions: {oct(data_dir.stat().st_mode)[-3:]}")
        print(f"Database file exists: {db_path.exists()}")
        
        # Create an empty database file if it doesn't exist
        if not db_path.exists():
            db_path.touch()
            os.chmod(db_path, 0o666)
        else:
            os.chmod(db_path, 0o666)
            
        print(f"Database file permissions: {oct(db_path.stat().st_mode)[-3:]}")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        raise
    
    # Load default configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', db_uri),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-123'),
        # Email configuration
        MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
        MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
        MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true',
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME', ''),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', ''),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', ''),
        # File uploads
        UPLOAD_FOLDER=os.path.join('instance', 'uploads'),
        ALLOWED_EXTENSIONS={'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'}
    )
    
    # Override with any custom config passed in
    if config is not None:
        app.config.update(config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except OSError as e:
        print(f"Error creating instance/upload folders: {e}")
    
    # Initialize extensions with app
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    
    # Register blueprints
    register_blueprints(app)
    
    with app.app_context():
        try:
            # Import models here to avoid circular imports
            from auth.models import User, Role
            
            # Create database tables first
            db.create_all()
            
            # Now set up relationships if they don't exist
            if not hasattr(User, 'reviewed_data_changes'):
                try:
                    from autogestion.models import DataChangeRequest
                    User.reviewed_data_changes = db.relationship(
                        'DataChangeRequest',
                        foreign_keys='DataChangeRequest.reviewer_id',
                        backref=db.backref('reviewer', lazy='joined'),
                        lazy='dynamic'
                    )
                except Exception as e:
                    print(f"Warning: Could not set up User.reviewed_data_changes: {e}")
            
            # Set up Professional relationships if the model exists
            try:
                from profesionales.models import Professional
                
                # Only set up relationships if they don't exist
                if not hasattr(Professional, 'data_change_requests'):
                    try:
                        Professional.data_change_requests = db.relationship(
                            'DataChangeRequest',
                            foreign_keys='DataChangeRequest.professional_id',
                            backref=db.backref('professional_assoc', lazy='joined'),
                            lazy='dynamic',
                            order_by='DataChangeRequest.requested_at.desc()'
                        )
                    except Exception as e:
                        print(f"Warning: Could not set up Professional.data_change_requests: {e}")
                
                if not hasattr(Professional, 'documentos'):
                    try:
                        from autogestion.models import DocumentoProfesional
                        Professional.documentos = db.relationship(
                            'DocumentoProfesional',
                            backref=db.backref('professional_doc', lazy='joined'),
                            lazy='dynamic',
                            order_by='DocumentoProfesional.fecha_carga.desc()',
                            cascade="all, delete-orphan"
                        )
                    except Exception as e:
                        print(f"Warning: Could not set up Professional.documentos: {e}")
                        
            except ImportError:
                print("Warning: Professional model not found, skipping relationship setup")
            
        except Exception as e:
            print(f"Error during app initialization: {e}")
            raise
        
        # Import models after db is initialized to avoid circular imports
        from auth.models import User, Role
        
        # Create default roles and admin user if they don't exist
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            db.session.commit()
            
        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role_id=admin_role.id
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Created default admin user with username: admin, password: admin123")
    
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
    # Import blueprints here to avoid circular imports
    from auth.views import auth_bp
    from main import main_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    
    # Other blueprints (lazy loading)
    blueprints = [
        ('.profesionales.views', 'profesionales_bp', '/profesionales'),
        ('.cobranzas.views', 'cobranzas_bp', '/cobranzas'),
        ('.facturacion.views', 'facturacion_bp', '/facturacion'),
        ('.configuraciones.views', 'configuraciones_bp', '/configuraciones'),
        ('.autogestion.views', 'autogestion_bp', '/autogestion'),
        ('.admin_dashboard.views', 'admin_dashboard_bp', '/admin'),
        ('.reports.views', 'reports_bp', '/reports')
    ]
    
    for module_path, bp_name, url_prefix in blueprints:
        try:
            # Try relative import first
            try:
                module = __import__(f'psicoLE{module_path}', fromlist=[bp_name])
            except ImportError:
                # Fall back to direct import
                module = __import__(module_path.lstrip('.'), fromlist=[bp_name])
                
            bp = getattr(module, bp_name, None)
            if bp is not None:
                if hasattr(bp, 'url_prefix'):
                    app.register_blueprint(bp)
                else:
                    app.register_blueprint(bp, url_prefix=url_prefix)
        except ImportError as e:
            print(f"Warning: Could not import {bp_name} from {module_path}: {e}")
        except Exception as e:
            print(f"Error registering {bp_name}: {e}")

# Load environment variables
load_dotenv()

# Create app instance
app = create_app()

# Utility functions
@app.template_filter('datetime')
def format_datetime(value, format='medium'):
    if format == 'full':
        format = "%A, %d de %B de %Y a las %H:%M"
    elif format == 'medium':
        format = "%d/%m/%Y %H:%M"
    return value.strftime(format)

# Context processors
@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.utcnow()}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
