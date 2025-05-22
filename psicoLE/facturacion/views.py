from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, make_response
from psicoLE.database import db
from .models import Factura, NotaCredito, NotaDebito # Added NotaDebito
from psicoLE.cobranzas.models import Pago 
from .forms import InvoiceForm, NotaCreditoForm, NotaDebitoForm # Added NotaDebitoForm
from .services import generate_next_invoice_number, generate_next_credit_note_number, generate_next_debit_note_number # Added DN number generation
from .pdf import generate_invoice_pdf_weasyprint, generate_credit_note_pdf, generate_debit_note_pdf # Added DN PDF generation
from psicoLE.auth.decorators import roles_required
from decimal import Decimal
from datetime import date as dt_date # For default dates if needed

facturacion_bp = Blueprint('facturacion', __name__,
                           template_folder='templates/facturacion',
                           url_prefix='/facturacion')

@facturacion_bp.route('/from-payment/<int:pago_id>/create-invoice', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def create_invoice_for_payment(pago_id):
    pago = Pago.query.get_or_404(pago_id)
    if pago.factura: # Check if invoice already exists for this payment
        flash(f'An invoice ({pago.factura.numero_factura}) already exists for this payment.', 'warning')
        return redirect(url_for('facturacion.detail_invoice', factura_id=pago.factura.id))

    form = InvoiceForm(pago=pago) # Pre-fill form with payment data

    if form.validate_on_submit():
        try:
            numero_factura = generate_next_invoice_number()
            nueva_factura = Factura(
                pago_id=pago.id,
                professional_id=pago.professional_id, # Get from payment
                cliente_nombre=form.cliente_nombre.data,
                cliente_identificacion=form.cliente_identificacion.data,
                fecha_emision=form.fecha_emision.data,
                monto_total=form.monto_total.data,
                detalles=form.detalles.data,
                numero_factura=numero_factura,
                estado='emitida'
            )
            db.session.add(nueva_factura)
            db.session.commit()
            flash(f'Invoice {numero_factura} created successfully for payment ID {pago.id}.', 'success')
            return redirect(url_for('facturacion.detail_invoice', factura_id=nueva_factura.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating invoice: {str(e)}', 'danger')
            # Log error e
            
    return render_template('create_edit_invoice.html', form=form, pago=pago, title='Create Invoice for Payment')

@facturacion_bp.route('/create-invoice', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def create_standalone_invoice():
    form = InvoiceForm() # No pago or professional pre-selected by default for truly standalone
    
    if form.validate_on_submit():
        try:
            numero_factura = generate_next_invoice_number()
            
            # Determine professional_id from form if selected
            selected_professional = form.professional_id.data 
            prof_id = selected_professional.id if selected_professional else None

            nueva_factura = Factura(
                professional_id=prof_id,
                pago_id=None, # No direct payment link for standalone
                cliente_nombre=form.cliente_nombre.data,
                cliente_identificacion=form.cliente_identificacion.data,
                fecha_emision=form.fecha_emision.data,
                monto_total=form.monto_total.data,
                detalles=form.detalles.data,
                numero_factura=numero_factura,
                estado='emitida'
            )
            db.session.add(nueva_factura)
            db.session.commit()
            flash(f'Invoice {numero_factura} created successfully.', 'success')
            return redirect(url_for('facturacion.detail_invoice', factura_id=nueva_factura.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating standalone invoice: {str(e)}', 'danger')
            # Log error e
            
    return render_template('create_edit_invoice.html', form=form, title='Create Standalone Invoice')

@facturacion_bp.route('/invoices', methods=['GET']) # Explicitly GET for listing
@roles_required('admin', 'staff')
def list_invoices():
    page = request.args.get('page', 1, type=int)
    # TODO: Implement filters for professional, date range, invoice number
    # For now, simple paginated list
    
    query = Factura.query.order_by(Factura.fecha_emision.desc(), Factura.numero_factura.desc())
    
    # Example filter (to be expanded with a form later)
    search_numero = request.args.get('numero_factura_search', '')
    if search_numero:
        query = query.filter(Factura.numero_factura.ilike(f'%{search_numero}%'))

    # items_per_page = int(get_config_value('items_per_page', 10)) # From config
    items_per_page = 10 # Placeholder
    
    invoices = query.paginate(page=page, per_page=items_per_page)
    
    return render_template('list_invoices.html', invoices=invoices, title='Invoices List', search_numero=search_numero)

@facturacion_bp.route('/invoices/<int:factura_id>')
@roles_required('admin', 'staff')
def detail_invoice(factura_id):
    factura = Factura.query.get_or_404(factura_id)
    return render_template('detail_invoice.html', factura=factura, title='Invoice Details')

@facturacion_bp.route('/invoices/<int:factura_id>/pdf')
@roles_required('admin', 'staff')
def download_invoice_pdf(factura_id):
    factura = Factura.query.get_or_404(factura_id)
    try:
        from .pdf import generate_invoice_pdf_weasyprint # Local import to avoid circular if pdf.py imports models
        pdf_bytes = generate_invoice_pdf_weasyprint(factura)
        
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="factura_{factura.numero_factura}.pdf"'
        # Use 'attachment' instead of 'inline' to force download
        return response
    except ImportError: # Handle if WeasyPrint is not installed or other import errors
        flash("PDF generation library (WeasyPrint) not found or configured correctly.", 'danger')
        return redirect(url_for('facturacion.detail_invoice', factura_id=factura.id))
    except Exception as e:
        flash(f"Error generating PDF: {str(e)}", 'danger')
        # Log error e
        return redirect(url_for('facturacion.detail_invoice', factura_id=factura.id))


# --- Credit Note Views ---

@facturacion_bp.route('/invoice/<int:factura_id>/create-credit-note', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def create_credit_note(factura_id):
    factura_original = Factura.query.get_or_404(factura_id)
    form = NotaCreditoForm()
    
    if request.method == 'GET':
        form.factura_original_id.data = factura_original.id
        # Pre-fill monto_total with original invoice amount as a suggestion
        form.monto_total.data = factura_original.monto_total

    if form.validate_on_submit():
        try:
            numero_nc = generate_next_credit_note_number()
            
            nueva_nota_credito = NotaCredito(
                factura_original_id=factura_original.id,
                numero_nota_credito=numero_nc,
                monto_total=form.monto_total.data,
                motivo=form.motivo.data,
                detalles_adicionales=form.detalles_adicionales.data,
                fecha_emision=dt_date.today(), # Or allow form to set this
                estado='emitida',
                # Copy client and professional info from original invoice
                professional_id=factura_original.professional_id,
                cliente_nombre=factura_original.cliente_nombre,
                cliente_identificacion=factura_original.cliente_identificacion
            )
            db.session.add(nueva_nota_credito)
            
            # Optionally, update original invoice status if fully credited
            # For now, manual status update or further logic can handle this
            # factura_original.estado = 'anulada_con_nc' 
            # db.session.add(factura_original)

            db.session.commit()
            flash(f'Nota de Crédito {numero_nc} creada exitosamente para la Factura {factura_original.numero_factura}.', 'success')
            return redirect(url_for('facturacion.detail_credit_note', credit_note_id=nueva_nota_credito.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la Nota de Crédito: {str(e)}', 'danger')
            # Log error e
            
    return render_template('create_credit_note.html', 
                           form=form, 
                           factura_original=factura_original, 
                           title='Crear Nota de Crédito')

@facturacion_bp.route('/credit-notes', methods=['GET'])
@roles_required('admin', 'staff')
def list_credit_notes():
    page = request.args.get('page', 1, type=int)
    items_per_page = 10 # Placeholder, consider making this configurable
    
    query = NotaCredito.query.order_by(NotaCredito.fecha_emision.desc(), NotaCredito.numero_nota_credito.desc())
    credit_notes_list = query.paginate(page=page, per_page=items_per_page)
    
    return render_template('list_credit_notes.html', 
                           credit_notes=credit_notes_list, 
                           title='Notas de Crédito')

@facturacion_bp.route('/credit-note/<int:credit_note_id>')
@roles_required('admin', 'staff')
def detail_credit_note(credit_note_id):
    credit_note = NotaCredito.query.get_or_404(credit_note_id)
    return render_template('detail_credit_note.html', 
                           credit_note=credit_note, 
                           title='Detalle Nota de Crédito')

@facturacion_bp.route('/credit-note/<int:credit_note_id>/pdf')
@roles_required('admin', 'staff')
def download_credit_note_pdf(credit_note_id):
    credit_note = NotaCredito.query.get_or_404(credit_note_id)
    try:
        pdf_bytes = generate_credit_note_pdf(credit_note)
        
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="nota_credito_{credit_note.numero_nota_credito}.pdf"'
        return response
    except ImportError: 
        flash("Librería de generación de PDF (WeasyPrint) no encontrada o configurada correctamente.", 'danger')
        return redirect(url_for('facturacion.detail_credit_note', credit_note_id=credit_note.id))
    except Exception as e:
        flash(f"Error al generar PDF de Nota de Crédito: {str(e)}", 'danger')
        # Log error e
        return redirect(url_for('facturacion.detail_credit_note', credit_note_id=credit_note.id))


# --- Debit Note Views ---

@facturacion_bp.route('/invoice/<int:factura_id>/create-debit-note', methods=['GET', 'POST'])
@roles_required('admin', 'staff')
def create_debit_note(factura_id):
    factura_original = Factura.query.get_or_404(factura_id)
    form = NotaDebitoForm()
    
    if request.method == 'GET':
        form.factura_original_id.data = factura_original.id
        # Unlike credit notes, monto_total for debit notes is often not pre-filled from original invoice

    if form.validate_on_submit():
        try:
            numero_nd = generate_next_debit_note_number()
            
            nueva_nota_debito = NotaDebito(
                factura_original_id=factura_original.id,
                numero_nota_debito=numero_nd,
                monto_total=form.monto_total.data,
                motivo=form.motivo.data,
                detalles_adicionales=form.detalles_adicionales.data,
                fecha_emision=dt_date.today(), # Or allow form to set this
                estado='emitida',
                # Copy client and professional info from original invoice
                professional_id=factura_original.professional_id,
                cliente_nombre=factura_original.cliente_nombre,
                cliente_identificacion=factura_original.cliente_identificacion
            )
            db.session.add(nueva_nota_debito)
            db.session.commit()
            flash(f'Nota de Débito {numero_nd} creada exitosamente para la Factura {factura_original.numero_factura}.', 'success')
            return redirect(url_for('facturacion.detail_debit_note', debit_note_id=nueva_nota_debito.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la Nota de Débito: {str(e)}', 'danger')
            # Log error e
            
    return render_template('create_debit_note.html', 
                           form=form, 
                           factura_original=factura_original, 
                           title='Crear Nota de Débito')

@facturacion_bp.route('/debit-notes', methods=['GET'])
@roles_required('admin', 'staff')
def list_debit_notes():
    page = request.args.get('page', 1, type=int)
    items_per_page = 10 # Placeholder, consider making this configurable
    
    query = NotaDebito.query.order_by(NotaDebito.fecha_emision.desc(), NotaDebito.numero_nota_debito.desc())
    debit_notes_list = query.paginate(page=page, per_page=items_per_page)
    
    return render_template('list_debit_notes.html', 
                           debit_notes=debit_notes_list, 
                           title='Notas de Débito')

@facturacion_bp.route('/debit-note/<int:debit_note_id>')
@roles_required('admin', 'staff')
def detail_debit_note(debit_note_id):
    debit_note = NotaDebito.query.get_or_404(debit_note_id)
    return render_template('detail_debit_note.html', 
                           debit_note=debit_note, 
                           title='Detalle Nota de Débito')

@facturacion_bp.route('/debit-note/<int:debit_note_id>/pdf')
@roles_required('admin', 'staff')
def download_debit_note_pdf(debit_note_id):
    debit_note = NotaDebito.query.get_or_404(debit_note_id)
    try:
        pdf_bytes = generate_debit_note_pdf(debit_note)
        
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="nota_debito_{debit_note.numero_nota_debito}.pdf"'
        return response
    except ImportError: 
        flash("Librería de generación de PDF (WeasyPrint) no encontrada o configurada correctamente.", 'danger')
        return redirect(url_for('facturacion.detail_debit_note', debit_note_id=debit_note.id))
    except Exception as e:
        flash(f"Error al generar PDF de Nota de Débito: {str(e)}", 'danger')
        # Log error e
        return redirect(url_for('facturacion.detail_debit_note', debit_note_id=debit_note.id))
