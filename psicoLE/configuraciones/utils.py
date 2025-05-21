from .models import Configuration
from psicoLE.database import db # To handle potential app context issues if called early

def get_config_value(key, default=None):
    """
    Retrieves a configuration value by its key.
    Returns the default value if the key is not found or if there's an error.
    """
    try:
        # This might be called outside an active Flask app context sometimes,
        # e.g., during initial setup or tests.
        # A more robust way would be to ensure app_context or use current_app.
        config_entry = Configuration.query.filter_by(key=key).first()
        if config_entry:
            return config_entry.value
        return default
    except Exception as e:
        # Log the error (e.g., print or use a proper logger)
        print(f"Error accessing config key '{key}': {e}")
        # This can happen if db is not available or no app context
        # For example, if called before db is initialized or app is fully set up.
        return default

def set_config_value(key, value, description=None):
    """
    Sets or updates a configuration value.
    If the key exists, it updates its value and optionally its description.
    If the key does not exist, it creates a new configuration entry.
    """
    try:
        config_entry = Configuration.query.filter_by(key=key).first()
        if config_entry:
            config_entry.value = str(value) # Ensure value is string
            if description is not None:
                config_entry.description = description
        else:
            config_entry = Configuration(key=key, value=str(value), description=description)
            db.session.add(config_entry)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error setting config key '{key}': {e}")
        return False

def ensure_config_exists(key, default_value, description):
    """Helper to ensure a specific config key exists."""
    if get_config_value(key) is None:
        set_config_value(key, default_value, description)
        print(f"Configuration '{key}' set to default: '{default_value}'.")
