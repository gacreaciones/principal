from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.Client()

deudas_ref = db.collection('deudas').stream()
for deuda in deudas_ref:
    deuda_data = deuda.to_dict()
    
    # Actualizar cliente_id a referencia si es necesario
    if isinstance(deuda_data.get('cliente_id'), str):
        cliente_ref = db.collection('clientes').document(deuda_data['cliente_id'])
        if cliente_ref.get().exists:
            deuda.reference.update({'cliente_id': cliente_ref})
    
    # Actualizar productos en productos_deuda
    productos_deuda_ref = db.collection('productos_deuda').where('deuda_id', '==', deuda.id).stream()
    for pdeuda in productos_deuda_ref:
        pdeuda_data = pdeuda.to_dict()
        if isinstance(pdeuda_data.get('producto_id'), str):
            producto_ref = db.collection('productos').document(pdeuda_data['producto_id'])
            if producto_ref.get().exists:
                pdeuda.reference.update({
                    'deuda_id': deuda.reference,
                    'producto_id': producto_ref
                })