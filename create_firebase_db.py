import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import bcrypt

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db_firestore = firestore.client()

# Crear usuario administrador si no existe
usuarios_ref = db_firestore.collection('usuarios')
query = usuarios_ref.where(filter=FieldFilter('username', '==', 'admin')).limit(1)

if not any(query.stream()):
    hashed_password = bcrypt.hashpw('jhosmar1967'.encode('utf-8'), bcrypt.gensalt())
    admin_data = {
        'username': 'admin',
        'password': hashed_password.decode('utf-8'),
        'es_admin': True
    }
    usuarios_ref.add(admin_data)
    print("Usuario administrador creado: admin / ")