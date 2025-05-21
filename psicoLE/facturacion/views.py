from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from psicoLE.database import db
from .models import Factura
from psicoLE.cobranzas.models import Pago # To fetch Pago
from .forms import InvoiceForm
from .services import generate_next_invoice_number
from psicoLE.auth.decorators import roles_required
from decimal import Decimal

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
