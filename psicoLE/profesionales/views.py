from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response, current_app, send_from_directory
from flask_login import current_user, login_required
from sqlalchemy import func, case
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database import db
from .models import Professional
# Import DocumentoProfesional from the correct module
from autogestion.models import DocumentoProfesional
from .forms import ProfessionalForm, ProfessionalFilterForm, SpecializationReportFilterForm

# Create the blueprint
profesionales_bp = Blueprint('profesionales', __name__, template_folder='templates')

# PDF generation is not available since we moved the PDF file
PDF_AVAILABLE = False

try:
    from auth.decorators import roles_required
except ImportError as e:
    print(f"Warning: Could not import roles_required: {e}")
    # Create a dummy decorator if roles_required is not available
    def roles_required(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

# Define a dummy generate_register_pdf function since the PDF module is not available
def generate_register_pdf(professional, output_path=None):
    """Dummy function for PDF generation when the PDF module is not available."""
    raise RuntimeError("PDF generation is not available. Please install the required dependencies.")

# Define routes
@profesionales_bp.route('/')
@login_required
def index():
    """List all professionals."""
    professionals = Professional.query.all()
    return render_template('profesionales/index.html', professionals=professionals)

@profesionales_bp.route('/dashboard')
@login_required
def dashboard():
    """Professional dashboard."""
    # If the current user is a professional, show their own profile
    if hasattr(current_user, 'professional') and current_user.professional:
        professional = current_user.professional
        
        # Get stats for the dashboard
        stats = {
            'documentos_pendientes': DocumentoProfesional.query.filter_by(professional_id=professional.id, status='pendiente').count(),
            'pagos_pendientes': 0  # Will be updated when we implement the payment system
        }
        
        # Try to get pagos_pendientes if the Pago model is available
        try:
            from cobranzas.models import Pago
            stats['pagos_pendientes'] = Pago.query.filter_by(professional_id=professional.id, status='pendiente').count()
        except (ImportError, AttributeError):
            pass
            
        return render_template('profesionales/dashboard.html', professional=professional, stats=stats, title='Panel del Profesional')
    # Otherwise, show a list of all professionals (for admin/staff)
    else:
        return redirect(url_for('profesionales.index'))

@profesionales_bp.route('/profile/<int:id>')
@login_required
def profile(id):
    """Show professional profile."""
    professional = Professional.query.get_or_404(id)
    return render_template('profesionales/profile.html', professional=professional)

@profesionales_bp.route('/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def new():
    """Create a new professional."""
    form = ProfessionalForm()
    if form.validate_on_submit():
        professional = Professional(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            matricula=form.matricula.data,
            status_matricula=form.status_matricula.data,
            email=form.email.data,
            phone_number=form.phone_number.data,
            address=form.address.data,
            title=form.title.data,
            specialization=form.specialization.data,
            university=form.university.data,
            cbu=form.cbu.data,
            autoriza_debito_automatico=form.autoriza_debito_automatico.data
        )
        db.session.add(professional)
        db.session.commit()
        flash('Profesional creado exitosamente.', 'success')
        return redirect(url_for('profesionales.index'))
    return render_template('profesionales/form.html', form=form, title='Nuevo Profesional')
