# This file ensures models are properly imported and registered with SQLAlchemy

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import all models to ensure they are registered with SQLAlchemy
try:
    from auth.models import User, Role
    print("Imported User and Role models from auth")
except ImportError as e:
    print(f"Error importing auth models: {e}")

# Import Professional model with proper path handling
try:
    from profesionales.models import Professional
    print("Imported Professional model from profesionales")
except ImportError as e:
    print(f"Error importing profesionales models: {e}")
    # Try alternative import path
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
        from profesionales.models import Professional
        print("Imported Professional model using alternative path")
    except ImportError as e2:
        print(f"Alternative import also failed: {e2}")

try:
    from cobranzas.models import Cuota, Pago
    print("Imported Cuota and Pago models from cobranzas")
except ImportError as e:
    print(f"Error importing cobranzas models: {e}")

def init_models():
    """Initialize all models and return them as a dictionary."""
    from database import db
    
    # This will ensure all models are imported and registered with SQLAlchemy
    models = {}
    
    try:
        # Import models here to ensure they're available
        from auth.models import User, Role
        models['User'] = User
        models['Role'] = Role
        print("Added User and Role to models dictionary")
    except ImportError as e:
        print(f"Error importing auth models in init_models: {e}")
    
    try:
        from profesionales.models import Professional
        models['Professional'] = Professional
        print("Added Professional to models dictionary")
    except ImportError as e:
        print(f"Error importing Professional in init_models: {e}")
    
    try:
        from cobranzas.models import Cuota, Pago
        models['Cuota'] = Cuota
        models['Pago'] = Pago
        print("Added Cuota and Pago to models dictionary")
    except ImportError as e:
        print(f"Error importing cobranzas models in init_models: {e}")
    
    return models
