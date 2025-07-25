from extensions import db 
from flask_login import UserMixin
from datetime import datetime
from google.cloud import firestore  # Agregar esta importación

class FirebaseModel:
    @classmethod
    def collection_name(cls):
        return cls.__name__.lower() + 's'
    
    @staticmethod
    def convert_date(date_value):
        """Convierte datetime a formato Firestore y viceversa"""
        if isinstance(date_value, firestore.DatetimeWithNanoseconds):
            return date_value
        if isinstance(date_value, datetime):
            return firestore.SERVER_TIMESTAMP
        return date_value

class Usuario(FirebaseModel):
    def __init__(self, username, password, es_admin=True):
        self.username = username
        self.password = password
        self.es_admin = es_admin
    
    def to_dict(self):
        return {
            'username': self.username,
            'password': self.password,
            'es_admin': self.es_admin
        }

class Cliente(FirebaseModel):
    def __init__(self, nombre, apodo):
        self.nombre = nombre
        self.apodo = apodo
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'apodo': self.apodo
        }

class Producto(FirebaseModel):
    def __init__(self, nombre, cantidad, precio, fecha=None):
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio = precio
        self.fecha = fecha or datetime.utcnow()
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'cantidad': self.cantidad,
            'precio': self.precio,
            'fecha': self.convert_date(self.fecha)
        }

class Deuda(FirebaseModel):
    def __init__(self, cliente_id, cliente_apodo, estado='pendiente', fecha=None):
        self.cliente_id = cliente_id
        self.cliente_apodo = cliente_apodo
        self.estado = estado
        self.fecha = fecha or datetime.utcnow()
    
    def to_dict(self):
        return {
            'cliente_id': self.cliente_id,
            'cliente_apodo': self.cliente_apodo,
            'estado': self.estado,
            'fecha': self.fecha
        }

class ProductoDeuda(FirebaseModel):
    def __init__(self, deuda_id, producto_id, cantidad):
        self.deuda_id = deuda_id
        self.producto_id = producto_id
        self.cantidad = cantidad
    
    def to_dict(self):
        return {
            'deuda_id': self.deuda_id,
            'producto_id': self.producto_id,
            'cantidad': self.cantidad
        }

class PagoParcial(FirebaseModel):
    def __init__(self, deuda_id, monto_usd, descripcion='', fecha=None):
        self.deuda_id = deuda_id
        self.monto_usd = monto_usd
        self.descripcion = descripcion
        self.fecha = fecha or datetime.utcnow()
    
    def to_dict(self):
        return {
            'deuda_id': self.deuda_id,
            'monto_usd': self.monto_usd,
            'descripcion': self.descripcion,
            'fecha': self.fecha
        }

class ProductoDeuda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deuda_id = db.Column(db.Integer, db.ForeignKey('deuda.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    producto = db.relationship('Producto')

    @property
    def subtotal(self):
        return self.cantidad * self.producto['precio']

class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deuda_id = db.Column(db.Integer, db.ForeignKey('deuda.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    referencia = db.Column(db.String(50), nullable=False)
    banco_origen = db.Column(db.String(50), nullable=False)
    monto_bs = db.Column(db.Float, nullable=False)
    monto_usd = db.Column(db.Float, nullable=False)
    es_parcial = db.Column(db.Boolean, default=False)