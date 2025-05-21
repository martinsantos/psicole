from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Date, DateTime, Boolean
from sqlalchemy.orm import relationship
from psicoLE.database import db
from datetime import datetime
from decimal import Decimal

class Cuota(db.Model):
    __tablename__ = 'cuotas'
    id = Column(Integer, primary_key=True)
    professional_id = Column(Integer, ForeignKey('professionals.id'), nullable=False)
    periodo = Column(String(7), nullable=False)  # YYYY-MM
    monto_esperado = Column(Numeric(10, 2), nullable=False)
    monto_pagado = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    fecha_emision = Column(Date, nullable=False, default=datetime.utcnow)
    fecha_vencimiento = Column(Date, nullable=False)
    estado = Column(String(20), nullable=False, default='pending') # pending, paid, partially_paid, overdue, cancelled

    # Relationships
    professional = relationship('Professional', back_populates='cuotas')
    pagos = relationship('Pago', back_populates='cuota', lazy='dynamic', cascade="all, delete-orphan")

    def __init__(self, professional_id, periodo, monto_esperado, fecha_vencimiento, fecha_emision=None, estado='pending', monto_pagado=None):
        self.professional_id = professional_id
        self.periodo = periodo
        self.monto_esperado = monto_esperado
        self.fecha_vencimiento = fecha_vencimiento
        if fecha_emision:
            self.fecha_emision = fecha_emision
        if monto_pagado is not None:
            self.monto_pagado = monto_pagado
        self.estado = estado
        
    def __repr__(self):
        return f'<Cuota {self.id} - {self.professional.first_name if self.professional else "N/A"} {self.periodo} - {self.estado}>'

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = Column(Integer, primary_key=True)
    cuota_id = Column(Integer, ForeignKey('cuotas.id'), nullable=True) # Nullable for payments not tied to a specific fee initially
    professional_id = Column(Integer, ForeignKey('professionals.id'), nullable=False) # Always link payment to a professional
    fecha_pago = Column(DateTime, nullable=False, default=datetime.utcnow)
    monto = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(50), nullable=False) # e.g., 'cash', 'transfer', 'card', 'gateway_mercadopago'
    referencia_pago = Column(String(100), nullable=True) # Transaction ID, check number, etc.
    confirmado = Column(Boolean, default=True) # True for manual, False for gateway until webhook

    # Relationships
    cuota = relationship('Cuota', back_populates='pagos')
    professional = relationship('Professional', back_populates='pagos')
    factura = relationship('Factura', back_populates='pago', uselist=False) # uselist=False for one-to-one

    def __init__(self, professional_id, monto, metodo_pago, cuota_id=None, fecha_pago=None, referencia_pago=None, confirmado=True):
        self.professional_id = professional_id
        self.monto = monto
        self.metodo_pago = metodo_pago
        self.cuota_id = cuota_id
        if fecha_pago:
            self.fecha_pago = fecha_pago
        self.referencia_pago = referencia_pago
        self.confirmado = confirmado

    def __repr__(self):
        return f'<Pago {self.id} - Prof: {self.professional_id} - {self.monto} - {self.metodo_pago}>'
