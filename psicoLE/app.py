import os
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from dotenv import load_dotenv
from pathlib import Path

# Initialize extensions
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Initialize Migrate without db (will be initialized in create_app)
migrate = Migrate()

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
    
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
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
        # File uploads
        UPLOAD_FOLDER=os.path.join('instance', 'uploads'),
        ALLOWED_EXTENSIONS={'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'}
    )
    
    # Load configuration from config.py if it exists
    if config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(config)
    
    # Ensure the SECRET_KEY is set
    if 'SECRET_KEY' not in app.config:
        app.config['SECRET_KEY'] = os.urandom(24).hex()
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configure email settings
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Initialize database
    from database import db
    db.init_app(app)
    
    # Ensure migrations directory exists
    migrations_dir = data_dir / 'migrations'
    migrations_dir.mkdir(exist_ok=True, mode=0o755)
    
    # Initialize Flask-Migrate
    migrate.init_app(app, db, directory=str(migrations_dir))
    
    # Initialize extensions with app
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Initialize auth module
    from auth import init_app as init_auth
    init_auth(app, db)
    
    # Register other blueprints
    register_blueprints(app, skip_auth=True)
    
    # Set up the database in the app context
    with app.app_context():
        # Make sure the database is properly set up
        app.extensions['sqlalchemy'] = {'db': db, 'Model': db.Model}
        
        # Import models to ensure they are registered with SQLAlchemy
        try:
            # Import all models explicitly to ensure they are registered
            print("Importing models...")
            
            # Import auth models first
            from auth.models import User, Role
            print("Imported User and Role from auth.models")
            
            # Import profesionales models
            from profesionales.models import Professional
            print("Imported Professional from profesionales.models")
            
            # Import cobranzas models
            from cobranzas.models import Cuota, Pago
            print("Imported Cuota and Pago from cobranzas.models")
            
            # Create tables if they don't exist
            print("Creating database tables...")
            db.create_all()
            print("Database tables created/verified.")
            
        except ImportError as e:
            print(f"Error importing models: {e}")
            import traceback
            traceback.print_exc()
            raise
        except Exception as e:
            print(f"Error creating database tables: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # Register blueprints (except auth which is already registered by init_auth)
    register_blueprints(app, skip_auth=True)
    
    # Create admin user if it doesn't exist
    with app.app_context():
        try:
            from auth import db as auth_db
            from auth.models import User, Role
            
            # Get or create admin role
            admin_role = Role.query.filter_by(name='admin').first()
            if not admin_role:
                admin_role = Role(name='admin')
                auth_db.session.add(admin_role)
                auth_db.session.commit()
                
            # Create admin user if it doesn't exist
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@example.com',
                    role_id=admin_role.id,
                    is_verified=True
                )
                admin_user.set_password('admin123')
                auth_db.session.add(admin_user)
                auth_db.session.commit()
                print("Created default admin user with username: admin, password: admin123")
                
        except Exception as e:
            print(f"Error initializing admin user: {e}")
            if 'auth_db' in locals() and hasattr(auth_db.session, 'rollback'):
                auth_db.session.rollback()
            # Don't raise here to allow the app to start even if admin creation fails
    
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

def is_blueprint_registered(app, name):
    """Check if a blueprint is already registered with the given name."""
    return name in app.blueprints

def register_blueprints(app, skip_auth=False):
    """Register all blueprints with the Flask application."""
    try:
        # Register auth blueprint if not skipped
        if not skip_auth:
            try:
                if not is_blueprint_registered(app, 'auth'):
                    from auth import auth_bp
                    app.register_blueprint(auth_bp, url_prefix='/auth')
                    app.logger.info("Registered auth blueprint")
                else:
                    app.logger.info("Auth blueprint already registered, skipping...")
            except Exception as e:
                app.logger.error(f"Failed to register auth blueprint: {str(e)}")
                raise

        # Register main blueprint
        try:
            if not is_blueprint_registered(app, 'main'):
                from main import main_bp
                app.register_blueprint(main_bp)
                app.logger.info("Registered main blueprint")
            else:
                app.logger.info("Main blueprint already registered, skipping...")
        except Exception as e:
            app.logger.error(f"Failed to register main blueprint: {str(e)}")
            raise

        # Register profesionales blueprint
        try:
            if not is_blueprint_registered(app, 'profesionales'):
                from profesionales.views import profesionales_bp
                app.register_blueprint(profesionales_bp, url_prefix='/profesionales')
                app.logger.info("Registered profesionales blueprint")
            else:
                app.logger.info("Profesionales blueprint already registered, skipping...")
        except ImportError:
            app.logger.warning("Profesionales blueprint not found, skipping...")
        except Exception as e:
            app.logger.error(f"Failed to register profesionales blueprint: {str(e)}")
            
        # Initialize admin dashboard
        try:
            from admin_dashboard import init_app as init_admin_dashboard
            init_admin_dashboard(app)
            app.logger.info("Initialized admin dashboard")
        except ImportError as e:
            app.logger.warning(f"Admin dashboard not found, skipping... {str(e)}")
        except Exception as e:
            app.logger.error(f"Failed to initialize admin dashboard: {str(e)}", exc_info=True)
        
        return True
    except Exception as e:
        app.logger.error(f"Error registering blueprints: {str(e)}")
        return False

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
