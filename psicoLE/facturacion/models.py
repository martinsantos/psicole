from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Date, Text, JSON
from sqlalchemy.orm import relationship
from psicoLE.database import db
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
