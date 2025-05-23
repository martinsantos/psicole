from flask import Flask, session # Added session
from database import db # Import the shared db instance
from flask_login import LoginManager # Added LoginManager

# Import models to ensure they are registered with SQLAlchemy's metadata
from psicoLE.auth.models import User, Role
from psicoLE.profesionales.models import Professional
from psicoLE.configuraciones.models import Configuration
from psicoLE.cobranzas.models import Cuota, Pago
from psicoLE.facturacion.models import Factura # Import Factura

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///psicole.db' # Using SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key' # Added a secret key for session management, etc.

# Initialize SQLAlchemy with the app using the shared db instance
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login' # The login route (using blueprint name 'auth')
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register Blueprints
from psicoLE.auth.views import auth_bp 
app.register_blueprint(auth_bp, url_prefix='/auth')

from psicoLE.profesionales.views import profesionales_bp
app.register_blueprint(profesionales_bp, url_prefix='/profesionales')

from psicoLE.configuraciones.views import configuraciones_bp
app.register_blueprint(configuraciones_bp, url_prefix='/configuraciones')

from psicoLE.cobranzas.views import cobranzas_bp
app.register_blueprint(cobranzas_bp, url_prefix='/cobranzas')

from psicoLE.facturacion.views import facturacion_bp
app.register_blueprint(facturacion_bp, url_prefix='/facturacion')

from psicoLE.reports.views import reports_bp
app.register_blueprint(reports_bp, url_prefix='/reports')

from psicoLE.autogestion.views import autogestion_bp
app.register_blueprint(autogestion_bp, url_prefix='/autogestion')


@app.route('/')
def hello_world():
    # Using current_user from Flask-Login
    if current_user.is_authenticated:
        user_info = f"{current_user.username} (Role: {current_user.role.name if current_user.role else 'N/A'})"
    else:
        user_info = "Guest"
    
    return f'Hello, PsicoLE! You are logged in as: {user_info}. Database setup is correct.'

@app.context_processor
def inject_utility_functions():
    def get_professional_by_user_id_fn(user_id):
        if user_id is None:
            return None
        return Professional.query.filter_by(user_id=user_id).first()
    return dict(get_professional_by_user_id=get_professional_by_user_id_fn)

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

    app.run(debug=True, host='0.0.0.0', port=5001)
