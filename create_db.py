# create_db.py
from app import app
from extensions import db
from models import Usuario, Cliente, Producto, Deuda, ProductoDeuda, Pago
import bcrypt

with app.app_context():
    # Crear todas las tablas
    db.create_all()
    
    # Crear usuario administrador si no existe
    if not db.session.execute(db.select(Usuario)).scalars().first():
        hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        admin = Usuario(username='admin', password=hashed_password.decode('utf-8'), es_admin=True)
        db.session.add(admin)
        db.session.commit()
        print("Usuario administrador creado: admin / admin123")