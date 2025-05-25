from database import db
from sqlalchemy import Column, Integer, String, Date, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import desc

# Para evitar importaciones circulares, usamos strings para las referencias a los modelos
# SQLAlchemy resolverá estas referencias cuando sea necesario

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

    # Relación con User (usando backref para evitar importación circular)
    user = relationship('User', backref=db.backref('professional', uselist=False))
    
    # Relación con Cuota (sin ordenamiento para simplificar)
    cuotas = relationship('Cuota', back_populates='professional', lazy='dynamic')
    
    # Relación con Pago (sin ordenamiento para simplificar)
    pagos = relationship('Pago', back_populates='professional', lazy='dynamic')
    
    # Relación con Factura (usando string reference para evitar importación circular)
    facturas = relationship('Factura', back_populates='professional', lazy='dynamic',
                         primaryjoin='Professional.id == foreign(Factura.professional_id)',
                         viewonly=True)


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
