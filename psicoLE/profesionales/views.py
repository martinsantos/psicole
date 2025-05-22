<<<<<<< HEAD
from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user, login_required
from datetime import datetime
from . import profesionales_bp
from ..database import db
from ..auth.decorators import roles_required
from .models import Professional
from .forms import ProfessionalForm
from ..autogestion.models import DocumentoProfesional
from ..payments.models import Payment

@profesionales_bp.route('/dashboard')
@login_required
@roles_required('professional')
def dashboard():
    # Get the professional's profile
    professional = Professional.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get statistics for the dashboard
    stats = {
        'documentos_pendientes': DocumentoProfesional.query.filter_by(
            professional_id=professional.id, 
            status='pending_review'
        ).count(),
        'pagos_pendientes': Payment.query.filter_by(
            professional_id=professional.id,
            status='pending'
        ).count(),
        'ingresos_totales': sum(
            p.amount for p in Payment.query.filter_by(
                professional_id=professional.id,
                status='completed'
            ).all()
        )
    }
    
    # Get recent documents and payments
    documentos_recientes = DocumentoProfesional.query.filter_by(
        professional_id=professional.id
    ).order_by(DocumentoProfesional.uploaded_at.desc()).limit(5).all()
    
    pagos_recientes = Payment.query.filter_by(
        professional_id=professional.id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    return render_template('profesionales/dashboard.html',
                         title='Panel del Profesional',
                         professional=professional,
                         stats=stats,
                         documentos_recientes=documentos_recientes,
                         pagos_recientes=pagos_recientes)
=======
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from psicoLE.database import db
from .models import Professional
from .forms import ProfessionalForm
from psicoLE.auth.decorators import roles_required # Assuming decorators.py is in auth module

profesionales_bp = Blueprint('profesionales', __name__, 
                             template_folder='templates/profesionales',
                             url_prefix='/profesionales') # Added url_prefix here
>>>>>>> 1eca9da5ea75796c688eecc7b35bab563ae145b2

@profesionales_bp.route('/create', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def create_professional():
    form = ProfessionalForm()
    if form.validate_on_submit():
        # Create new professional instance
        new_professional = Professional(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            matricula=form.matricula.data,
            status_matricula=form.status_matricula.data,
            vigencia_matricula=form.vigencia_matricula.data,
            email=form.email.data,
            phone_number=form.phone_number.data,
            address=form.address.data,
            title=form.title.data,
            specialization=form.specialization.data,
            university=form.university.data,
            cbu=form.cbu.data
            # user_id is not set here, can be linked later if needed
        )
        db.session.add(new_professional)
        db.session.commit()
        flash('Professional created successfully!', 'success')
        return redirect(url_for('profesionales.list_professionals'))
    return render_template('create_edit.html', form=form, title='Create Professional', legend='New Professional')

@profesionales_bp.route('/')
@profesionales_bp.route('/list')
@roles_required('admin', 'staff')
def list_professionals():
    page = request.args.get('page', 1, type=int)
    query = Professional.query
    
    # Search
    search_term = request.args.get('search', '')
    if search_term:
        search_filter = db.or_(
            Professional.first_name.ilike(f'%{search_term}%'),
            Professional.last_name.ilike(f'%{search_term}%'),
            Professional.matricula.ilike(f'%{search_term}%')
        )
        query = query.filter(search_filter)

    # Filtering
    status_filter = request.args.get('status_matricula', '')
    if status_filter:
        query = query.filter(Professional.status_matricula == status_filter)
    
    professionals_list = query.order_by(Professional.last_name, Professional.first_name).paginate(page=page, per_page=10) # 10 items per page
    
    # Choices for the filter dropdown
    status_choices = ProfessionalForm.status_matricula.kwargs.get('choices', [])

    return render_template('list.html', professionals=professionals_list, 
                           search_term=search_term, status_filter=status_filter,
                           status_choices=status_choices, title="Professionals List")

@profesionales_bp.route('/<int:professional_id>')
@roles_required('admin', 'staff', 'professional')
def detail_professional(professional_id):
    professional = Professional.query.get_or_404(professional_id)
    
    # Security check: 'professional' role can only see their own profile
    if current_user.role.name == 'professional':
        if professional.user_id is None or professional.user_id != current_user.id:
            flash('You are not authorized to view this professional profile.', 'danger')
            # Redirect to their own profile if possible, or a general error page/dashboard
            # For now, redirect to an error page or home if we don't have a "my_profile" route
            # Check if this professional is linked to *any* user first
            own_professional_profile = Professional.query.filter_by(user_id=current_user.id).first()
            if own_professional_profile:
                 return redirect(url_for('profesionales.detail_professional', professional_id=own_professional_profile.id))
            else: # Professional user not linked to any professional profile
                 return redirect(url_for('hello_world')) # Or an unauthorized page

    return render_template('detail.html', professional=professional, title="Professional Details")

@profesionales_bp.route('/<int:professional_id>/edit', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def edit_professional(professional_id):
    professional = Professional.query.get_or_404(professional_id)
    # Pass the original matricula to the form for validation
    form = ProfessionalForm(original_matricula=professional.matricula, obj=professional)

    if form.validate_on_submit():
        professional.first_name = form.first_name.data
        professional.last_name = form.last_name.data
        professional.matricula = form.matricula.data
        professional.status_matricula = form.status_matricula.data
        professional.vigencia_matricula = form.vigencia_matricula.data
        professional.email = form.email.data
        professional.phone_number = form.phone_number.data
        professional.address = form.address.data
        professional.title = form.title.data
        professional.specialization = form.specialization.data
        professional.university = form.university.data
        professional.cbu = form.cbu.data
        
        db.session.commit()
        flash('Professional profile updated successfully!', 'success')
        return redirect(url_for('profesionales.detail_professional', professional_id=professional.id))
    
    return render_template('create_edit.html', form=form, title='Edit Professional', 
                           legend=f'Edit {professional.first_name} {professional.last_name}',
                           professional_id=professional.id) # Pass professional_id for action URL if needed

@profesionales_bp.route('/<int:professional_id>/delete', methods=['POST'])
@roles_required('admin')
def delete_professional(professional_id):
    professional = Professional.query.get_or_404(professional_id)
    
    # Future consideration: Check for related data before deleting (e.g., appointments, invoices)
    # and decide on cascade or restrict. For now, direct delete.
    
    # Also, if professional is linked to a User, decide if the User should be deleted or unlinked.
    # For now, we are only deleting the Professional profile.
    # If User.professional backref is set to cascade on delete-orphan for Professional,
    # then user.professional would be set to None. If it's cascade delete, User might be deleted.
    # Current setup: User.professional is a simple backref, no explicit cascade for this scenario.
    # Professional.user is a relationship to User, if Professional is deleted, the FK constraint
    # might cause issues if not handled (e.g. set user_id to NULL if allowed, or delete User).
    # For now, we assume user_id in Professional can be nullified or the User remains.
    
    try:
        db.session.delete(professional)
        db.session.commit()
        flash(f'Professional {professional.first_name} {professional.last_name} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting professional: {str(e)}', 'danger')
        # Log the error e for server-side review
    
    return redirect(url_for('profesionales.list_professionals'))
