from app import db_firestore

empresa_ref = db_firestore.collection('empresa').document('info')

if not empresa_ref.get().exists:
    empresa_ref.set({
        'nombre': 'Mi Empresa',
        'direccion': 'Dirección de la empresa',
        'telefono': '+1234567890',
        'logo_url': ''
    })
    print("Datos iniciales de empresa creados")