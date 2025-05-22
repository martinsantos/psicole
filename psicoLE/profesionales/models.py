from psicoLE.database import db # Corrected import
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
# Ensure User model is imported if it's referenced by Professional model for relationships
# from ..auth.models import User # This relative import is tricky with how Flask discovers models.
# A direct import like 'from auth.models import User' might be needed depending on PYTHONPATH and app structure.
# For now, we rely on SQLAlchemy to resolve the 'users.id' string.

class Professional(db.Model):
    __tablename__ = 'professionals'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    matricula = Column(String(50), unique=True, nullable=False)
    status_matricula = Column(String(50), nullable=False) # e.g., 'active', 'inactive', 'pending'
    vigencia_matricula = Column(Date)
    email = Column(String(120), unique=True, nullable=False)
    phone_number = Column(String(20))
    address = Column(String(200))
    title = Column(String(100)) # e.g., 'Licenciado en Psicología'
    specialization = Column(String(100)) # e.g., 'Psicología Clínica'
    university = Column(String(100))
    cbu = Column(String(50)) # Bank account for payments
    autoriza_debito_automatico = Column(db.Boolean, nullable=False, default=False)

    # The relationship should be defined referencing the class name `User` if it's imported,
    # or the table name 'users' as a string if not.
    # Assuming User class will be available in the SQLAlchemy metadata context.
    user = relationship('User', backref=db.backref('professional', uselist=False))

    # Back-references for Cobranzas
    cuotas = relationship('Cuota', back_populates='professional', lazy='dynamic', order_by='Cuota.periodo.desc()')
    pagos = relationship('Pago', back_populates='professional', lazy='dynamic', order_by='Pago.fecha_pago.desc()')

    # Back-reference for Facturacion
    facturas = relationship('Factura', back_populates='professional', lazy='dynamic', order_by='Factura.fecha_emision.desc()')

    # Back-reference for DataChangeRequest
    data_change_requests = relationship('DataChangeRequest', back_populates='professional', lazy='dynamic', order_by='DataChangeRequest.requested_at.desc()')

    # Back-reference for DocumentoProfesional
    documentos = relationship('DocumentoProfesional', back_populates='professional', lazy='dynamic', order_by='DocumentoProfesional.fecha_carga.desc()', cascade="all, delete-orphan")


    def __init__(self, first_name, last_name, matricula, status_matricula, email, user_id=None, vigencia_matricula=None, phone_number=None, address=None, title=None, specialization=None, university=None, cbu=None, autoriza_debito_automatico=False):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.matricula = matricula
        self.status_matricula = status_matricula
        self.vigencia_matricula = vigencia_matricula
        self.email = email
        self.phone_number = phone_number
        self.address = address
        self.title = title
        self.specialization = specialization
        self.university = university
        self.cbu = cbu
        self.autoriza_debito_automatico = autoriza_debito_automatico

    def __repr__(self):
        return f'<Professional {self.first_name} {self.last_name} - {self.matricula}>'
