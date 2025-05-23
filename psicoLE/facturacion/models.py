from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Date, Text, JSON
from sqlalchemy.orm import relationship
from database import db
from datetime import date as dt_date # Renamed to avoid conflict with model field

class Factura(db.Model):
    __tablename__ = 'facturas'
    id = Column(Integer, primary_key=True)
    professional_id = Column(Integer, ForeignKey('professionals.id'), nullable=True)
    pago_id = Column(Integer, ForeignKey('pagos.id'), unique=True, nullable=True) # unique=True for one-to-one with Pago
    
    cliente_nombre = Column(String(255), nullable=False)
    cliente_identificacion = Column(String(50), nullable=True)
    fecha_emision = Column(Date, nullable=False, default=dt_date.today)
    numero_factura = Column(String(50), nullable=False, unique=True)
    monto_total = Column(Numeric(10, 2), nullable=False)
    detalles = Column(Text, nullable=False) # Could be JSON if structured details are needed: db.Column(JSON)
    estado = Column(String(20), nullable=False, default='emitida') # emitida, anulada

    # Relationships
    professional = relationship('Professional', back_populates='facturas')
    pago = relationship('Pago', back_populates='factura', uselist=False) # uselist=False for one-to-one

    def __init__(self, cliente_nombre, numero_factura, monto_total, detalles, 
                 professional_id=None, pago_id=None, cliente_identificacion=None, 
                 fecha_emision=None, estado='emitida'):
        self.professional_id = professional_id
        self.pago_id = pago_id
        self.cliente_nombre = cliente_nombre
        self.cliente_identificacion = cliente_identificacion
        if fecha_emision:
            self.fecha_emision = fecha_emision
        else:
            self.fecha_emision = dt_date.today()
        self.numero_factura = numero_factura
        self.monto_total = monto_total
        self.detalles = detalles
        self.estado = estado

    def __repr__(self):
        return f'<Factura {self.numero_factura} - {self.cliente_nombre} - Estado: {self.estado}>'


class NotaCredito(db.Model):
    __tablename__ = 'notas_credito'
    id = Column(Integer, primary_key=True)
    factura_original_id = Column(Integer, ForeignKey('facturas.id'), nullable=False)
    numero_nota_credito = Column(String(50), unique=True, nullable=False)
    fecha_emision = Column(Date, nullable=False, default=dt_date.today)
    monto_total = Column(Numeric(10, 2), nullable=False)
    motivo = Column(Text, nullable=False)
    detalles_adicionales = Column(Text, nullable=True)
    estado = Column(String(20), nullable=False, default='emitida') # emitida, anulada, aplicada
    
    # Information denormalized from Factura for easier access, or if NC can be independent
    professional_id = Column(Integer, ForeignKey('professionals.id'), nullable=True) 
    cliente_nombre = Column(String(255), nullable=False)
    cliente_identificacion = Column(String(50), nullable=True)

    # Relationships
    factura_original = relationship('Factura', backref=db.backref('notas_credito', lazy='dynamic', cascade="all, delete-orphan"))
    professional = relationship('Professional') # Assuming direct link to Professional, adjust if needed

    def __init__(self, factura_original_id, numero_nota_credito, monto_total, motivo, 
                 cliente_nombre, cliente_identificacion=None, professional_id=None, 
                 detalles_adicionales=None, fecha_emision=None, estado='emitida'):
        self.factura_original_id = factura_original_id
        self.numero_nota_credito = numero_nota_credito
        self.monto_total = monto_total
        self.motivo = motivo
        self.detalles_adicionales = detalles_adicionales
        if fecha_emision:
            self.fecha_emision = fecha_emision
        else:
            self.fecha_emision = dt_date.today()
        self.estado = estado
        self.professional_id = professional_id
        self.cliente_nombre = cliente_nombre
        self.cliente_identificacion = cliente_identificacion

    def __repr__(self):
        return f'<NotaCredito {self.numero_nota_credito} para Factura ID {self.factura_original_id} - Monto: {self.monto_total}>'


class NotaDebito(db.Model):
    __tablename__ = 'notas_debito'
    id = Column(Integer, primary_key=True)
    factura_original_id = Column(Integer, ForeignKey('facturas.id'), nullable=False)
    numero_nota_debito = Column(String(50), unique=True, nullable=False)
    fecha_emision = Column(Date, nullable=False, default=dt_date.today)
    monto_total = Column(Numeric(10, 2), nullable=False)
    motivo = Column(Text, nullable=False) # e.g., Intereses por mora, Ajuste de precio, Gastos adicionales
    detalles_adicionales = Column(Text, nullable=True)
    estado = Column(String(20), nullable=False, default='emitida') # emitida, anulada, pagada

    # Denormalized information from Factura
    professional_id = Column(Integer, ForeignKey('professionals.id'), nullable=True)
    cliente_nombre = Column(String(255), nullable=False)
    cliente_identificacion = Column(String(50), nullable=True)

    # Relationships
    factura_original = relationship('Factura', backref=db.backref('notas_debito', lazy='dynamic', cascade="all, delete-orphan"))
    professional = relationship('Professional')

    def __init__(self, factura_original_id, numero_nota_debito, monto_total, motivo,
                 cliente_nombre, cliente_identificacion=None, professional_id=None,
                 detalles_adicionales=None, fecha_emision=None, estado='emitida'):
        self.factura_original_id = factura_original_id
        self.numero_nota_debito = numero_nota_debito
        self.monto_total = monto_total
        self.motivo = motivo
        self.detalles_adicionales = detalles_adicionales
        if fecha_emision:
            self.fecha_emision = fecha_emision
        else:
            self.fecha_emision = dt_date.today()
        self.estado = estado
        self.professional_id = professional_id
        self.cliente_nombre = cliente_nombre
        self.cliente_identificacion = cliente_identificacion

    def __repr__(self):
        return f'<NotaDebito {self.numero_nota_debito} para Factura ID {self.factura_original_id} - Monto: {self.monto_total}>'
