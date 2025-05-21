from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField
from wtforms.validators import Optional, DataRequired
from wtforms_sqlalchemy.fields import QuerySelectField
from psicoLE.profesionales.models import Professional
from psicoLE.cobranzas.models import Pago # To get distinct payment methods

# Helper to get professionals for QuerySelectField
def get_all_professionals_for_reports():
    return Professional.query.order_by(Professional.last_name, Professional.first_name)

# Helper to get distinct payment methods
def get_distinct_payment_methods():
    # This might be slow on large datasets. Consider a predefined list or caching.
    # For now, query distinct values.
    methods = db.session.query(Pago.metodo_pago).distinct().order_by(Pago.metodo_pago).all()
    return [('', '-- All Methods --')] + [(method[0], method[0].replace('_', ' ').title()) for method in methods if method[0]]

class DateRangeForm(FlaskForm):
    start_date = DateField('Start Date', validators=[Optional()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[Optional()], format='%Y-%m-%d')
    submit_filter = SubmitField('Filter') # Generic submit for filters

class ProfessionalReportForm(FlaskForm):
    professional_id = QuerySelectField('Select Professional',
                                     query_factory=get_all_professionals_for_reports,
                                     get_label=lambda p: f"{p.last_name}, {p.first_name} ({p.matricula})",
                                     allow_blank=False,
                                     validators=[DataRequired()])
    submit_report = SubmitField('Generate Report')

class PaymentReportFiltersForm(DateRangeForm): # Inherits start_date, end_date, submit_filter
    payment_method = SelectField('Payment Method', 
                                 choices=[], # To be populated in __init__ or view
                                 validators=[Optional()])
    # submit_filter is inherited

    def __init__(self, *args, **kwargs):
        super(PaymentReportFiltersForm, self).__init__(*args, **kwargs)
        # Populate choices dynamically or use a static list
        # Static list for now as dynamic can be slow or complex for form init
        self.payment_method.choices = [
            ('', '-- All Methods --'),
            ('cash', 'Cash (Efectivo)'),
            ('transfer', 'Transferencia Bancaria'),
            ('cheque', 'Cheque'),
            ('card_debit', 'Tarjeta de Débito'),
            ('card_credit', 'Tarjeta de Crédito'),
            ('online_mp', 'MercadoPago (Online)'),
            ('gateway_mercadopago', 'MercadoPago (Gateway)'), # If used distinctly
            ('other_manual', 'Otro Manual')
        ]
        # If you want dynamic choices:
        # self.payment_method.choices = get_distinct_payment_methods()
