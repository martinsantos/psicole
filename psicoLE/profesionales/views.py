from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response, current_app, send_from_directory
from flask_login import current_user
from sqlalchemy import func, case
import os
from psicoLE.database import db
from .models import Professional, DocumentoProfesional # Import DocumentoProfesional
from .forms import ProfessionalForm, ProfessionalFilterForm, SpecializationReportFilterForm
from .pdf import generate_register_pdf 
from psicoLE.auth.decorators import roles_required

profesionales_bp = Blueprint('profesionales', __name__, 
                             template_folder='templates/profesionales',
                             url_prefix='/profesionales') # Added url_prefix here

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
            cbu=form.cbu.data,
            autoriza_debito_automatico=form.autoriza_debito_automatico.data
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
    # Instantiate the filter form, populating it from request.args
    filter_form = ProfessionalFilterForm(request.args, meta={'csrf': False}) # Disable CSRF for GET form

    query = Professional.query
    
    # Search from form
    if filter_form.search.data:
        search_term = filter_form.search.data
        search_filter = db.or_(
            Professional.first_name.ilike(f'%{search_term}%'),
            Professional.last_name.ilike(f'%{search_term}%'),
            Professional.matricula.ilike(f'%{search_term}%')
        )
        query = query.filter(search_filter)

    # Filtering from form
    if filter_form.status_matricula.data:
        query = query.filter(Professional.status_matricula == filter_form.status_matricula.data)
    
    if filter_form.specialization.data:
        query = query.filter(Professional.specialization.ilike(f'%{filter_form.specialization.data}%'))
        
    if filter_form.university.data:
        query = query.filter(Professional.university.ilike(f'%{filter_form.university.data}%'))
        
    if filter_form.title.data:
        query = query.filter(Professional.title.ilike(f'%{filter_form.title.data}%'))

    professionals_list = query.order_by(Professional.last_name, Professional.first_name).paginate(page=page, per_page=10)
    
    # Pass the form to the template
    return render_template('list.html', professionals=professionals_list, 
                           filter_form=filter_form, title="Professionals List")


@profesionales_bp.route('/reports/email-list', methods=['GET'])
@roles_required('admin', 'staff')
def generate_email_list():
    filter_form = ProfessionalFilterForm(request.args, meta={'csrf': False})
    query = Professional.query

    email_list_str = ""
    email_count = 0

    # Apply filters only if the form is submitted (or has parameters)
    # For this specific view, we might want to generate emails only when specific filters are applied,
    # or always generate based on current filters. Let's assume we generate based on current filters.
    
    if filter_form.search.data:
        search_term = filter_form.search.data
        query = query.filter(db.or_(
            Professional.first_name.ilike(f'%{search_term}%'),
            Professional.last_name.ilike(f'%{search_term}%'),
            Professional.matricula.ilike(f'%{search_term}%')
        ))
    
    if filter_form.status_matricula.data:
        query = query.filter(Professional.status_matricula == filter_form.status_matricula.data)
    
    if filter_form.specialization.data:
        query = query.filter(Professional.specialization.ilike(f'%{filter_form.specialization.data}%'))
        
    if filter_form.university.data:
        query = query.filter(Professional.university.ilike(f'%{filter_form.university.data}%'))
        
    if filter_form.title.data:
        query = query.filter(Professional.title.ilike(f'%{filter_form.title.data}%'))

    # Fetch only email addresses
    # Only proceed to fetch emails if there are some filters applied, or if 'submit' is in request.args
    # This prevents loading all emails by default if no filters are chosen.
    # However, the requirement is to use the form to filter, so we assume the user will interact with the form.
    # If request.args is empty (first load), email_list will be empty.
    
    # We should only generate the list if some form fields are filled or a specific action (like a submit button for this form) is taken.
    # For simplicity, if any filter is active, we generate. Or, we can add a specific button in the template for "Generate".
    # Let's assume that if the page is accessed with filters, it should display the filtered list.
    
    filtered_professionals_emails = query.with_entities(Professional.email).all()
    
    if filtered_professionals_emails:
        emails = [email[0] for email in filtered_professionals_emails if email[0]] # Ensure email is not None
        email_list_str = "\n".join(emails)
        email_count = len(emails)
        if not email_list_str and request.args: # if filters were applied but no results
             flash('No professionals found matching your criteria.', 'info')
        elif email_list_str:
             flash(f'{email_count} email(s) generated based on the criteria.', 'success')


    return render_template('generate_email_list.html', 
                           filter_form=filter_form, 
                           email_list_str=email_list_str, 
                           email_count=email_count,
                           title="Generate Professional Email List")


@profesionales_bp.route('/reports/register', methods=['GET'])
@roles_required('admin', 'staff')
def generate_professional_register():
    filter_form = ProfessionalFilterForm(request.args, meta={'csrf': False})
    query = Professional.query

    # Default to 'active' status if no status filter is applied
    status_to_filter = filter_form.status_matricula.data
    if not status_to_filter and not request.args.get('status_matricula'): # if not set in form or query params
        status_to_filter = 'active'
        filter_form.status_matricula.data = 'active' # Update form data to reflect default

    if filter_form.search.data:
        search_term = filter_form.search.data
        query = query.filter(db.or_(
            Professional.first_name.ilike(f'%{search_term}%'),
            Professional.last_name.ilike(f'%{search_term}%'),
            Professional.matricula.ilike(f'%{search_term}%')
        ))
    
    if status_to_filter: # Use the potentially defaulted status
        query = query.filter(Professional.status_matricula == status_to_filter)
    
    if filter_form.specialization.data:
        query = query.filter(Professional.specialization.ilike(f'%{filter_form.specialization.data}%'))
        
    if filter_form.university.data:
        query = query.filter(Professional.university.ilike(f'%{filter_form.university.data}%'))
        
    if filter_form.title.data:
        query = query.filter(Professional.title.ilike(f'%{filter_form.title.data}%'))

    # Fetch full professional objects
    professionals_list = query.order_by(Professional.last_name, Professional.first_name).all()
    
    if not professionals_list and request.args:
        flash('No professionals found matching your criteria.', 'info')
    elif not request.args:
        flash('Displaying active professionals by default. Use filters for more specific results.', 'info')


    return render_template('professional_register.html', 
                           filter_form=filter_form, 
                           professionals=professionals_list,
                           title="Updated Professional Register")


@profesionales_bp.route('/reports/register/pdf', methods=['GET'])
@roles_required('admin', 'staff')
def download_professional_register_pdf():
    # Use request.args directly as it's already a MultiDict
    filter_args = request.args 
    
    # We need to instantiate the form to easily access validated data and defaults if needed,
    # but primarily we'll use filter_args for passing to PDF generation and for querying.
    filter_form = ProfessionalFilterForm(filter_args, meta={'csrf': False})
    query = Professional.query

    # Default to 'active' status if no status filter is applied
    status_to_filter = filter_form.status_matricula.data # or filter_args.get('status_matricula')
    if not status_to_filter and not filter_args.get('status_matricula'):
        status_to_filter = 'active'
        # No need to update form.data here as it's only for this request processing

    if filter_form.search.data: # or filter_args.get('search')
        search_term = filter_form.search.data
        query = query.filter(db.or_(
            Professional.first_name.ilike(f'%{search_term}%'),
            Professional.last_name.ilike(f'%{search_term}%'),
            Professional.matricula.ilike(f'%{search_term}%')
        ))
    
    if status_to_filter:
        query = query.filter(Professional.status_matricula == status_to_filter)
    
    if filter_form.title.data: # or filter_args.get('title')
        query = query.filter(Professional.title.ilike(f'%{filter_form.title.data}%'))

    if filter_form.specialization.data: # or filter_args.get('specialization')
        query = query.filter(Professional.specialization.ilike(f'%{filter_form.specialization.data}%'))
        
    if filter_form.university.data: # or filter_args.get('university')
        query = query.filter(Professional.university.ilike(f'%{filter_form.university.data}%'))
        
    professionals_list = query.order_by(Professional.last_name, Professional.first_name).all()

    # Prepare filter_params for display in PDF (user-friendly names)
    # This dictionary is passed to generate_register_pdf
    active_filter_params = {
        'search': filter_args.get('search', ''),
        'status_matricula': status_to_filter, # Already defaulted to 'active'
        'title': filter_args.get('title', ''),
        'specialization': filter_args.get('specialization', ''),
        'university': filter_args.get('university', '')
    }
    # Remove empty filters for cleaner display in PDF
    active_filter_params = {k: v for k, v in active_filter_params.items() if v}


    if not professionals_list:
        flash('No professionals found matching your criteria to generate PDF. Please try different filters.', 'warning')
        # Redirect back to the HTML report page, preserving original filters
        return redirect(url_for('profesionales.generate_professional_register', **filter_args))

    try:
        pdf_bytes = generate_register_pdf(professionals_list, active_filter_params)
        
        filename = "padron_profesionales.pdf"
        return Response(pdf_bytes,
                        mimetype='application/pdf',
                        headers={'Content-Disposition': f'attachment;filename={filename}'})
    except Exception as e:
        # Log the error properly in a real application
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('profesionales.generate_professional_register', **filter_args))


@profesionales_bp.route('/reports/by-specialization', methods=['GET', 'POST']) # Allow POST for form submission
@roles_required('admin', 'staff')
def report_by_specialization():
    form = SpecializationReportFilterForm(request.form if request.method == 'POST' else request.args)
    
    # Default to 'active' if form is not submitted or status is empty
    # The form field itself has a default='active', this handles initial GET or if user selects "All" then submits
    selected_status = form.status_matricula.data
    if request.method == 'GET' and not selected_status and 'status_matricula' not in request.args:
        selected_status = 'active'
        form.status_matricula.data = 'active' # Ensure form displays the default on first load

    # Define the specialization label for NULL or empty strings
    specialization_label = case(
        (Professional.specialization == None, 'Not Specified'),
        (Professional.specialization == '', 'Not Specified'),
        else_=Professional.specialization
    ).label('specialization_group')

    query = db.session.query(
        specialization_label,
        func.count(Professional.id).label('count')
    )

    if selected_status: # If a status is selected (or defaulted to active)
        query = query.filter(Professional.status_matricula == selected_status)
    
    # If selected_status is empty string (meaning "All Statuses"), don't filter by status.
    
    report_data = query.group_by('specialization_group').order_by('specialization_group').all()

    return render_template('report_by_specialization.html',
                           form=form,
                           report_data=report_data,
                           selected_status=selected_status, # Pass this for links
                           title="Professionals by Specialization")


@profesionales_bp.route('/<int:professional_id>/documents/<int:document_id>/download_admin')
@roles_required('admin', 'staff')
def download_professional_document_admin(professional_id, document_id):
    # Query for the document ensuring it belongs to the professional
    # Also ensure professional exists by querying it first
    professional = Professional.query.get_or_404(professional_id)
    document = DocumentoProfesional.query.filter_by(id=document_id, professional_id=professional.id).first_or_404(
        description=f"Document with id {document_id} not found for professional {professional_id}"
    )
    
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        current_app.logger.error("UPLOAD_FOLDER is not configured.")
        flash('File download configuration error. Please contact support.', 'danger')
        return redirect(url_for('profesionales.detail_professional', professional_id=professional_id))

    # document.archivo_path is expected to be relative to UPLOAD_FOLDER
    # e.g., "professional_documents/PROFESSIONAL_ID/filename.ext"
    try:
        return send_from_directory(
            directory=upload_folder, 
            path=document.archivo_path, 
            as_attachment=True,
            download_name=document.nombre_archivo_original # Use original filename for download
        )
    except FileNotFoundError:
        current_app.logger.error(f"Admin download: File not found for document ID {document.id} at path: {os.path.join(upload_folder, document.archivo_path)}")
        flash('File not found on server. It might have been moved or deleted.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Admin download: Error downloading document ID {document.id}: {str(e)}")
        flash(f'An error occurred while trying to download the file: {str(e)}', 'danger')
    
    return redirect(url_for('profesionales.detail_professional', professional_id=professional_id))


@profesionales_bp.route('/<int:professional_id>/documents/<int:document_id>/delete_admin', methods=['POST'])
@roles_required('admin', 'staff')
def delete_professional_document_admin(professional_id, document_id):
    # Ensure professional context
    professional = Professional.query.get_or_404(professional_id)
    document = DocumentoProfesional.query.filter_by(id=document_id, professional_id=professional.id).first_or_404(
         description=f"Document with id {document_id} not found for professional {professional_id}"
    )
    
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        current_app.logger.error("UPLOAD_FOLDER is not configured for deletion.")
        flash('File deletion configuration error. Please contact support.', 'danger')
        return redirect(url_for('profesionales.detail_professional', professional_id=professional_id))

    file_path_to_delete = os.path.join(upload_folder, document.archivo_path)

    try:
        # 1. Delete the physical file
        if os.path.exists(file_path_to_delete):
            os.remove(file_path_to_delete)
            current_app.logger.info(f"Admin delete: Successfully deleted physical file {file_path_to_delete} for document ID {document.id}")
        else:
            current_app.logger.warning(f"Admin delete: Physical file not found for document {document.id} at {file_path_to_delete}, but proceeding to delete DB record.")
            flash('Physical file not found on server, but the database record will be deleted.', 'warning')

        # 2. Delete the database record
        db.session.delete(document)
        db.session.commit()
        flash(f'Document "{document.nombre_archivo_original}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Admin delete: Error deleting document ID {document.id}: {str(e)}, File: {file_path_to_delete}")
        flash(f'An error occurred while deleting the document: {str(e)}', 'danger')
        
    return redirect(url_for('profesionales.detail_professional', professional_id=professional_id))

@profesionales_bp.route('/<int:professional_id>')
@roles_required('admin', 'staff', 'professional')
def detail_professional(professional_id):
    professional = Professional.query.get_or_404(professional_id)
    
    # Security check: 'professional' role can only see their own profile
    if current_user.role.name == 'professional':
        if professional.user_id is None or professional.user_id != current_user.id:
            flash('You are not authorized to view this professional profile.', 'danger')
            own_professional_profile = Professional.query.filter_by(user_id=current_user.id).first()
            if own_professional_profile:
                 return redirect(url_for('profesionales.detail_professional', professional_id=own_professional_profile.id))
            else: 
                 return redirect(url_for('hello_world')) 

    # Fetch documents for admin/staff view
    documents = []
    if current_user.role.name in ['admin', 'staff']:
        documents = DocumentoProfesional.query.filter_by(professional_id=professional_id).order_by(DocumentoProfesional.fecha_carga.desc()).all()

    return render_template('detail.html', professional=professional, documents=documents, title="Professional Details")

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
        professional.autoriza_debito_automatico = form.autoriza_debito_automatico.data
        
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
