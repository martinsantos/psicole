from psicoLE.configuraciones.utils import get_config_value, set_config_value
from psicoLE.database import db
from .models import Factura # To check if an invoice number already exists, just in case
from sqlalchemy import func
from datetime import date

def generate_next_invoice_number():
    """
    Generates the next invoice number.
    Uses 'invoice_prefix' and 'invoice_last_sequence' from Configurations.
    Example: F001-2023-00001
    """
    prefix = get_config_value('invoice_prefix', 'F001')
    last_sequence_str = get_config_value('invoice_last_sequence', '0')
    
    try:
        last_sequence = int(last_sequence_str)
    except ValueError:
        last_sequence = 0 # Fallback if config value is invalid

    current_year = str(date.today().year)
    
    # Check if the year has changed to reset sequence (optional, depends on business rule)
    # For now, we assume a global sequence number, but prefix includes year for uniqueness.
    # A more robust system might store last_sequence per year or have a more complex prefix.
    
    next_sequence = last_sequence + 1
    
    # Simple loop to ensure uniqueness, though database constraint should handle it
    # This is a fallback, not a primary method for ensuring uniqueness.
    # The numero_factura field in Factura model has unique=True.
    while True:
        new_invoice_number = f"{prefix}-{current_year}-{next_sequence:05d}"
        existing = Factura.query.filter_by(numero_factura=new_invoice_number).first()
        if not existing:
            break
        next_sequence += 1 # If somehow it exists, try next one

    # Update the last sequence in configuration
    set_config_value('invoice_last_sequence', str(next_sequence))
    
    return new_invoice_number

# It's good practice to pre-populate these config values if they don't exist
# This can be done in main.py's initialization block
def ensure_invoice_config_exists():
    if get_config_value('invoice_prefix') is None:
        set_config_value('invoice_prefix', 'F001', 'Prefix for generated invoice numbers (e.g., F001).')
    if get_config_value('invoice_last_sequence') is None:
        set_config_value('invoice_last_sequence', '0', 'Last used sequence number for invoices (global or per year depending on generation logic).')
