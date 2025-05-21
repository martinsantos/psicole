from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField, DateField, TextAreaField, HiddenField, IntegerField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField
from psicoLE.profesionales.models import Professional
from datetime import date as dt_date # Renamed to avoid conflict

def get_all_professionals():
    return Professional.query.order_by(Professional.last_name, Professional.first_name)

class InvoiceForm(FlaskForm):
    professional_id = QuerySelectField('Professional (Optional)',
                                     query_factory=get_all_professionals,
                                     get_label=lambda p: f"{p.last_name}, {p.first_name} ({p.matricula})",
                                     allow_blank=True,
                                     blank_text='-- Select Professional (if applicable) --',
                                     validators=[Optional()])
    pago_id = HiddenField('Pago ID', validators=[Optional()]) # Pre-filled if creating from payment
    
    cliente_nombre = StringField('Client Name', validators=[DataRequired(), Length(max=255)])
    cliente_identificacion = StringField('Client Tax ID / DNI', validators=[Optional(), Length(max=50)])
    fecha_emision = DateField('Emission Date', validators=[DataRequired()], default=dt_date.today)
    monto_total = DecimalField('Total Amount', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    detalles = TextAreaField('Invoice Details / Concept', 
                             validators=[DataRequired(), Length(max=1000)],
                             render_kw={"rows": 4},
                             description="Example: Honorarios por servicios profesionales. Consulta mes Enero 2024.")
    
    submit = SubmitField('Generate Invoice')

    def __init__(self, pago=None, professional=None, *args, **kwargs):
        super(InvoiceForm, self).__init__(*args, **kwargs)
        if pago:
            self.pago_id.data = pago.id
            self.monto_total.data = pago.monto
            if pago.cuota:
                self.detalles.data = f"Pago de cuota {pago.cuota.periodo}."
            else:
                self.detalles.data = f"Pago general registrado el {pago.fecha_pago.strftime('%Y-%m-%d')}."
            
            if pago.professional: # If payment is linked to a professional
                self.professional_id.data = pago.professional
                self.cliente_nombre.data = f"{pago.professional.first_name} {pago.professional.last_name}"
                # Consider adding professional's CUIT/DNI to cliente_identificacion if available
        
        elif professional: # If a professional is passed directly (for standalone invoice for a professional)
            self.professional_id.data = professional
            self.cliente_nombre.data = f"{professional.first_name} {professional.last_name}"
        
        # If a professional_id is set (either from pago or direct professional),
        # make the professional_id field behave as if it's pre-selected.
        # QuerySelectField handles this by matching its .data to one of the query_factory results.
        # If we want it to be non-editable when pre-filled:
        # if self.professional_id.data:
        #     self.professional_id.render_kw = {'disabled': True} # but this prevents submission
        # A better way is to display it as text or ensure it's validated correctly if it can't be changed.
        # For now, it's just pre-selected.
