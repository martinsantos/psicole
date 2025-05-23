from psicoLE.configuraciones.utils import get_config_value, set_config_value
from database import db
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

def generate_next_credit_note_number():
    """
    Generates the next credit note number.
    Uses 'credit_note_prefix' and 'credit_note_last_sequence' from Configurations.
    Example: NCF-2023-00001
    """
    prefix = get_config_value('credit_note_prefix', 'NCF')
    last_sequence_str = get_config_value('credit_note_last_sequence', '0')
    
    try:
        last_sequence = int(last_sequence_str)
    except ValueError:
        last_sequence = 0

    current_year = str(date.today().year)
    next_sequence = last_sequence + 1
    
    # This import should be at the top level of the module, but for now:
    from .models import NotaCredito 

    while True:
        new_credit_note_number = f"{prefix}-{current_year}-{next_sequence:05d}"
        existing = NotaCredito.query.filter_by(numero_nota_credito=new_credit_note_number).first()
        if not existing:
            break
        next_sequence += 1

    set_config_value('credit_note_last_sequence', str(next_sequence))
    
    return new_credit_note_number

def ensure_credit_note_config_exists():
    """
    Ensures that the necessary configuration values for credit note numbering exist.
    """
    if get_config_value('credit_note_prefix') is None:
        set_config_value('credit_note_prefix', 'NCF', 'Prefix for generated credit note numbers (e.g., NCF).')
    if get_config_value('credit_note_last_sequence') is None:
        set_config_value('credit_note_last_sequence', '0', 'Last used sequence number for credit notes.')

def generate_next_debit_note_number():
    """
    Generates the next debit note number.
    Uses 'debit_note_prefix' and 'debit_note_last_sequence' from Configurations.
    Example: NDF-2023-00001
    """
    prefix = get_config_value('debit_note_prefix', 'NDF')
    last_sequence_str = get_config_value('debit_note_last_sequence', '0')
    
    try:
        last_sequence = int(last_sequence_str)
    except ValueError:
        last_sequence = 0

    current_year = str(date.today().year)
    next_sequence = last_sequence + 1
    
    from .models import NotaDebito # Import locally to avoid circular dependency issues at startup

    while True:
        new_debit_note_number = f"{prefix}-{current_year}-{next_sequence:05d}"
        existing = NotaDebito.query.filter_by(numero_nota_debito=new_debit_note_number).first()
        if not existing:
            break
        next_sequence += 1

    set_config_value('debit_note_last_sequence', str(next_sequence))
    
    return new_debit_note_number

def ensure_debit_note_config_exists():
    """
    Ensures that the necessary configuration values for debit note numbering exist.
    """
    if get_config_value('debit_note_prefix') is None:
        set_config_value('debit_note_prefix', 'NDF', 'Prefix for generated debit note numbers (e.g., NDF).')
    if get_config_value('debit_note_last_sequence') is None:
        set_config_value('debit_note_last_sequence', '0', 'Last used sequence number for debit notes.')
