from app import db_firestore

collections = ['clientes', 'productos', 'deudas']

for col in collections:
    counter_ref = db_firestore.collection('counters').document(col)
    if not counter_ref.get().exists:
        counter_ref.set({'seq': 0})
        print(f"Contador creado para {col}")