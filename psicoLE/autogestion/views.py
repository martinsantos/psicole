from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import current_user
from psicoLE.auth.decorators import roles_required
from psicoLE.profesionales.models import Professional
from psicoLE.cobranzas.models import Cuota, Pago
from psicoLE.facturacion.models import Factura
from database import db # For potential direct queries if needed, though relationships are preferred

autogestion_bp = Blueprint('autogestion', __name__,
                           template_folder='templates/autogestion',
                           url_prefix='/autogestion')

@autogestion_bp.route('/financials')
@roles_required('professional')
def financial_dashboard():
    if not current_user.professional:
        flash('No professional profile linked to your user account. Please contact support.', 'warning')
        return redirect(url_for('hello_world')) # Or a more appropriate redirect

    professional = current_user.professional
    
    # Fetch fees, payments, and invoices for the logged-in professional
    # Using relationships defined in Professional model
    
    fees = professional.cuotas.order_by(Cuota.periodo.desc()).all()
    # Alternative if relationship is not ordered or for complex ordering:
    # fees = Cuota.query.filter_by(professional_id=professional.id).order_by(Cuota.periodo.desc()).all()
    
    payments = professional.pagos.order_by(Pago.fecha_pago.desc()).all()
    # payments = Pago.query.filter_by(professional_id=professional.id).order_by(Pago.fecha_pago.desc()).all()

    invoices = professional.facturas.order_by(Factura.fecha_emision.desc()).all()
    # invoices = Factura.query.filter_by(professional_id=professional.id).order_by(Factura.fecha_emision.desc()).all()

    return render_template('autogestion_financials.html', 
                           professional=professional,
                           fees=fees,
                           payments=payments,
                           invoices=invoices,
                           title='My Financial Dashboard')
