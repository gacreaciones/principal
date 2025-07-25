from datetime import datetime

class FirebaseModel:
    @classmethod
    def collection_name(cls):
        return cls.__name__.lower() + 's'

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
    def __init__(self, nombre, cedula, cliente_direccion, cliente_telefono, cliente_email):
        self.nombre = nombre
        self.cedula = cedula
        self.cliente_direccion = cliente_direccion
        self.cliente_telefono = cliente_telefono
        self.cliente_email = cliente_email
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'cedula': self.cedula,
            'cliente_direccion': self.cliente_direccion,
            'cliente_telefono': self.cliente_telefono,
            'cliente_email': self.cliente_email
        }

class Producto(FirebaseModel):
    def __init__(self, nombre, cantidad, precio, categoria, imagen_url, fecha=None):
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio = precio
        self.categoria = categoria  # Nueva columna
        self.imagen_url = imagen_url  # Nueva columna
        self.fecha = fecha or datetime.utcnow()
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'cantidad': self.cantidad,
            'precio': self.precio,
            'categoria': self.categoria,
            'imagen_url': self.imagen_url,
            'fecha': self.fecha
        }

class Deuda(FirebaseModel):
    def __init__(self, cliente_id, cliente_cedula, estado='pendiente', fecha=None):
        self.cliente_id = cliente_id
        self.cliente_cedula = cliente_cedula
        self.estado = estado
        self.fecha = fecha or datetime.utcnow()
    
    def to_dict(self):
        return {
            'cliente_id': self.cliente_id,
            'cliente_cedula': self.cliente_cedula,
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
    
class Empresa(FirebaseModel):
    def __init__(self, nombre, direccion, telefono, facebook=None, instagram=None, twitter=None, logo_url=None):
        self.nombre = nombre
        self.direccion = direccion
        self.telefono = telefono
        self.facebook = facebook
        self.instagram = instagram
        self.twitter = twitter
        self.logo_url = logo_url
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'direccion': self.direccion,
            'telefono': self.telefono,
            'facebook': self.facebook,
            'instagram': self.instagram,
            'twitter': self.twitter,
            'logo_url': self.logo_url
        }
    
# Añadir al final de models.py
class Pedido(FirebaseModel):
    def __init__(self, cliente_nombre, cliente_direccion, cliente_telefono, cliente_email, total, estado='pendiente', fecha=None):
        self.cliente_nombre = cliente_nombre
        self.cliente_direccion = cliente_direccion
        self.cliente_telefono = cliente_telefono
        self.cliente_email = cliente_email
        self.total = total
        self.estado = estado
        self.fecha = fecha or datetime.utcnow()
    
    def to_dict(self):
        return {
            'cliente_nombre': self.cliente_nombre,
            'cliente_direccion': self.cliente_direccion,
            'cliente_telefono': self.cliente_telefono,
            'cliente_email': self.cliente_email,
            'total': self.total,
            'estado': self.estado,
            'fecha': self.fecha
        }

class ItemPedido(FirebaseModel):
    def __init__(self, pedido_id, producto_id, producto_nombre, precio, cantidad):
        self.pedido_id = pedido_id
        self.producto_id = producto_id
        self.producto_nombre = producto_nombre
        self.precio = precio
        self.cantidad = cantidad
    
    def to_dict(self):
        return {
            'pedido_id': self.pedido_id,
            'producto_id': self.producto_id,
            'producto_nombre': self.producto_nombre,
            'precio': self.precio,
            'cantidad': self.cantidad
        }