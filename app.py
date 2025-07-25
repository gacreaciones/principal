from flask import Flask, render_template, redirect, url_for, flash, request, session, abort, jsonify
from extensions import db, bcrypt, login_manager
from flask_login import login_user, logout_user, login_required, current_user, UserMixin, LoginManager, AnonymousUserMixin
from forms import ConsultaDeudaForm, PagoForm, LoginForm, ProductoForm, DeudaForm, ProductoDeudaForm, ClienteForm, DeudaForm, ProductoDeudaForm, ChangePasswordForm, EmpresaForm,EmptyForm, CheckoutForm
from models import Cliente, Producto, Deuda, ProductoDeuda
from config import Config
from sqlalchemy import select
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import time
from google.cloud.firestore_v1 import Increment
from google.cloud.firestore import FieldFilter
from google.cloud.firestore_v1 import DocumentReference
from datetime import datetime, timezone
import os
import base64
import tempfile

# Configuración de Firebase usando variable de entorno
if not firebase_admin._apps:
    encoded_key = os.environ.get('FIREBASE_SERVICE_ACCOUNT_BASE64')
    
    if encoded_key:
        # Decodificar y crear archivo temporal
        decoded_key = base64.b64decode(encoded_key)
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(decoded_key)
            temp_path = temp_file.name
        
        cred = credentials.Certificate(temp_path)
        firebase_admin.initialize_app(cred)
    else:
        # Para desarrollo local
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)

db_firestore = firestore.client()

app = Flask(__name__)
app.config.from_object(Config)

login_manager.init_app(app)
login_manager.login_view = 'login'

from google.cloud.firestore_v1 import Increment

# Función para generar IDs secuenciales
def get_next_sequence(collection_name):
    counter_ref = db_firestore.collection('counters').document(collection_name)
    try:
        @firestore.transactional
        def update_counter(transaction):
            snapshot = counter_ref.get(transaction=transaction)
            if snapshot.exists:
                seq = snapshot.get('seq') + 1
                transaction.update(counter_ref, {'seq': seq})
                return seq
            else:
                transaction.set(counter_ref, {'seq': 1})
                return 1
        return update_counter(db_firestore.transaction())
    except Exception as e:
        print(f"Error getting sequence: {e}")
        return int(time.time())


# Configurar LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Definir la clase UsuarioFirebase
class UsuarioFirebase(UserMixin):
    def __init__(self, user_data, user_id):
        self.user_data = user_data
        self.id = user_id
    
    @property
    def username(self):
        return self.user_data.get('username', '')
    
    @property
    def es_admin(self):
        return self.user_data.get('es_admin', False)

# Clase personalizada para usuarios anónimos
class AnonymousUser(AnonymousUserMixin):
    @property
    def username(self):
        return "Invitado"
    
    @property
    def es_admin(self):
        return False

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    doc_ref = db_firestore.collection('usuarios').document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        user_data = doc.to_dict()
        return UsuarioFirebase(user_data, user_id)
    return None
    
@property
def username(self):
    return self.user_data['username']
    
@property
def password(self):
    return self.user_data['password']
    
@property
def es_admin(self):
    return self.user_data.get('es_admin', True)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Obtener productos con stock
    productos = []
    query = db_firestore.collection('productos').where(filter=FieldFilter('cantidad', '>', 0))
    
    for doc in query.stream():
        producto = doc.to_dict()
        producto['id'] = doc.id
        productos.append(producto)
    
    return render_template('index.html', productos=productos, form=ConsultaDeudaForm())

@app.route('/tienda', endpoint='tienda_page')
def tienda():
    # Obtener productos con stock
    productos = []
    query = db_firestore.collection('productos').where(filter=FieldFilter('cantidad', '>', 0))
    
    for doc in query.stream():
        producto = doc.to_dict()
        producto['id'] = doc.id
        productos.append(producto)
    
    return render_template('tienda.html', productos=productos)

@app.route('/pagar/<string:deuda_id>', methods=['GET', 'POST'])
def pagar_deuda(deuda_id):
    deuda_ref = db_firestore.collection('deudas').document(deuda_id)
    deuda = deuda_ref.get().to_dict()
    
    if not deuda:
        abort(404)
        
    form = PagoForm()
    
    if form.validate_on_submit():
        # Crear pago
        pago_data = {
            'deuda_id': deuda_id,
            'referencia': form.referencia.data,
            'banco_origen': form.banco_origen.data,
            'monto_bs': form.monto_bs.data,
            'monto_usd': form.monto_usd.data,
            'fecha': datetime.utcnow()
        }
        db_firestore.collection('pagos').add(pago_data)
        
        # Actualizar estado de deuda
        deuda_ref.update({'estado': 'pagada'})
        
        flash('Pago registrado exitosamente', 'success')
        return redirect(url_for('index'))
    
    return render_template('pagar.html', deuda=deuda, form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            # Buscar usuario en Firestore usando FieldFilter
            query = db_firestore.collection('usuarios').where(
                filter=FieldFilter('username', '==', form.username.data)
            ).limit(1)
            
            docs = query.stream()
            user_doc = next(docs, None)
            
            if user_doc:
                user_data = user_doc.to_dict()
                if bcrypt.check_password_hash(user_data['password'], form.password.data):
                    user = UsuarioFirebase(user_data, user_doc.id)
                    login_user(user)
                    return redirect(url_for('dashboard'))
            
            flash('Usuario o contraseña incorrectos', 'danger')
        except Exception as e:
            print(f"Login error: {e}")
            flash('Error en el sistema, intente nuevamente', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        try:
            user_ref = db_firestore.collection('usuarios').document(current_user.id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                if bcrypt.check_password_hash(user_data['password'], form.old_password.data):
                    hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
                    user_ref.update({'password': hashed_password})
                    flash('Contraseña actualizada exitosamente', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Contraseña actual incorrecta', 'danger')
            else:
                flash('Usuario no encontrado', 'danger')
        except Exception as e:
            print(f"Error al cambiar contraseña: {e}")
            flash('Error al cambiar la contraseña', 'danger')
    
    return render_template('change_password.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    # Obtener productos
    productos = []
    productos_ref = db_firestore.collection('productos').stream()
    for doc in productos_ref:
        prod = doc.to_dict()
        prod['id'] = doc.id
        productos.append(prod)
    
    # Obtener productos con bajo stock (<5 unidades)
    productos_bajo_stock = []
    for prod in productos:
        try:
            if int(prod.get('cantidad', 0)) < 5:
                productos_bajo_stock.append(prod)
        except (ValueError, TypeError):
            pass
    
    # Obtener clientes
    clientes = []
    clientes_ref = db_firestore.collection('clientes').stream()
    for doc in clientes_ref:
        cliente = doc.to_dict()
        cliente['id'] = doc.id
        clientes.append(cliente)
    
    # Calcular estadísticas
    total_stock = 0
    total_value = 0.0
    for prod in productos:
        try:
            cantidad = int(prod.get('cantidad', 0))
            precio = float(prod.get('precio', 0.0))
        except (ValueError, TypeError):
            cantidad = 0
            precio = 0.0
        total_stock += cantidad
        total_value += cantidad * precio
    
    # Obtener top 5 deudores con deudas más antiguas
    top_deudores = []
    deudas_query = db_firestore.collection('deudas') \
        .where('estado', '==', 'pendiente') \
        .order_by('fecha') \
        .limit(5) \
        .stream()
    
    for deuda_doc in deudas_query:
        deuda_data = deuda_doc.to_dict()
        cliente_ref = deuda_data.get('cliente_id')
        
        # Manejar diferentes tipos de referencia
        if isinstance(cliente_ref, DocumentReference):
            cliente_id = cliente_ref.id
        elif isinstance(cliente_ref, str):
            cliente_id = cliente_ref
        else:
            continue
        
        cliente_doc = db_firestore.collection('clientes').document(cliente_id).get()
        if cliente_doc.exists:
            cliente = cliente_doc.to_dict()
            saldo = obtener_saldo_pendiente(deuda_doc.id)
            top_deudores.append({
                'cedula': cliente.get('cedula', ''),
                'fecha': deuda_data.get('fecha'),
                'saldo': saldo
            })
    
    # Calcular total pendiente por cobrar
    total_pendiente = 0.0
    deudas_pendientes = db_firestore.collection('deudas').where('estado', '==', 'pendiente').stream()
    for deuda_doc in deudas_pendientes:
        total_pendiente += obtener_saldo_pendiente(deuda_doc.id)
    
    return render_template('dashboard.html', 
                           productos=productos[:6], 
                           productos_bajo_stock=productos_bajo_stock,
                           clientes=clientes[:3],
                           total_stock=total_stock,
                           total_value=total_value,
                           deudas_pendientes=len(list(deudas_pendientes)),
                           top_deudores=top_deudores,
                           total_pendiente=total_pendiente,
                           form=EmptyForm())


@app.route('/registrar_cliente', methods=['GET', 'POST'])
@login_required
def registrar_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        try:
            # Obtener próximo ID secuencial
            next_id = get_next_sequence('clientes')
            cliente_data = {
                'nombre': request.form.get('nombre'),
                'cedula': request.form.get('cedula'),
                'direccion': request.form.get('direccion'),
                'telefono': request.form.get('telefono'),
                'email': request.form.get('email')
            }
            
            # Actualizar contador
            counter_ref = db_firestore.collection('counters').document('clientes')
            counter_ref.update({'seq': Increment(1)})
            
            # Guardar cliente con ID secuencial
            db_firestore.collection('clientes').document(str(next_id)).set(cliente_data)
            
            flash('Cliente registrado exitosamente', 'success')
            return redirect(url_for('listar_clientes'))
        except Exception as e:
            print(f"Error al registrar cliente: {e}")
            flash('Error al registrar el cliente', 'danger')
    return render_template('registrar_cliente.html', form=form)

@app.route('/clientes')
@login_required
def listar_clientes():
    try:
        # Usar FieldFilter explícito
        query = db_firestore.collection('clientes')
        docs = query.stream()
        
        clientes = []
        for doc in docs:
            cliente_data = doc.to_dict()
            cliente_data['id'] = doc.id
            clientes.append(cliente_data)
        
        return render_template('clientes.html', clientes=clientes, form=EmptyForm())
    except Exception as e:
        print(f"Error listing clients: {e}")
        flash('Error al cargar los clientes', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/editar_cliente/<string:id>', methods=['POST'])
@login_required
def editar_cliente(id):
    doc_ref = db_firestore.collection('clientes').document(id)
    doc = doc_ref.get()
    
    if not doc.exists:
        abort(404)
    
    # Actualizar el cliente
    doc_ref.update({
        'nombre': request.form.get('nombre'),
        'cedula': request.form.get('cedula'),
        'direccion': request.form.get('direccion'),
        'telefono': request.form.get('telefono'),
        'email': request.form.get('email')
    })
    flash('Cliente actualizado exitosamente', 'success')
    return redirect(url_for('listar_clientes'))

@app.route('/eliminar_cliente/<string:id>', methods=['POST'])
@login_required
def eliminar_cliente(id):
    db_firestore.collection('clientes').document(id).delete()
    flash('Cliente eliminado correctamente', 'success')
    return redirect(url_for('listar_clientes'))

@app.route('/registrar_producto', methods=['GET', 'POST'])
@login_required
def registrar_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        try:
            # Crear documento con ID secuencial
            next_id = get_next_sequence('productos')
            producto_data = {
                'nombre': form.nombre.data,
                'cantidad': form.cantidad.data,
                'precio': form.precio.data,
                'categoria': form.categoria.data,  # Nuevo campo
                'imagen_url': form.imagen_url.data,  # Nuevo campo
                'fecha': datetime.utcnow()
            }
            
            # Actualizar contador
            db_firestore.collection('counters').document('productos').update({'seq': Increment(1)})
            
            # Guardar producto
            db_firestore.collection('productos').document(str(next_id)).set(producto_data)
            
            flash('Producto registrado exitosamente', 'success')
            return redirect(url_for('listar_productos'))
        except Exception as e:
            print(f"Error al registrar producto: {e}")
            flash('Error al registrar el producto', 'danger')
    return render_template('registrar_producto.html', form=form)

@app.route('/productos')
@login_required
def listar_productos():
    try:
        productos = []
        docs = db_firestore.collection('productos').stream()
        
        for doc in docs:
            prod = doc.to_dict()
            prod['id'] = doc.id
            productos.append(prod)
        
        # Ordenar por ID numérico
        productos.sort(key=lambda x: int(x['id']))
        
        return render_template('productos.html', productos=productos, form=EmptyForm())
    except Exception as e:
        print(f"Error al listar productos: {e}")
        flash('Error al cargar productos', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/editar_producto/<string:id>', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    doc_ref = db_firestore.collection('productos').document(id)
    doc = doc_ref.get()
    
    if not doc.exists:
        abort(404)
    
    if request.method == 'POST':
        # Validar cantidad no negativa
        if int(request.form.get('cantidad', 0)) < 0:
            flash('La cantidad no puede ser negativa', 'danger')
            return redirect(url_for('editar_producto', id=id))
        
        # Actualizar el producto
        doc_ref.update({
            'nombre': request.form.get('nombre'),
            'cantidad': int(request.form.get('cantidad', 0)),
            'precio': float(request.form.get('precio', 0.0)),
            'categoria': request.form.get('categoria'),
            'imagen_url': request.form.get('imagen_url')
        })
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('listar_productos'))
    
    # Mostrar formulario con datos actuales
    producto = doc.to_dict()
    form = ProductoForm()
    form.nombre.data = producto.get('nombre', '')
    form.cantidad.data = producto.get('cantidad', 0)
    form.precio.data = producto.get('precio', 0.0)
    form.categoria.data = producto.get('categoria', '') 
    form.imagen_url.data = producto.get('imagen_url', '')
    
    return render_template('editar_producto.html', form=form, producto_id=id)

@app.route('/registrar_deuda', methods=['GET', 'POST'])
@login_required
def registrar_deuda():
    # Obtener clientes
    clientes = []
    clientes_docs = db_firestore.collection('clientes').stream()
    for doc in clientes_docs:
        cliente = doc.to_dict()
        cliente['id'] = doc.id
        clientes.append(cliente)
    
    # Obtener productos
    productos = []
    productos_docs = db_firestore.collection('productos').stream()
    for doc in productos_docs:
        prod = doc.to_dict()
        prod['id'] = doc.id
        productos.append(prod)
    
    # Crear formularios
    deuda_form = DeudaForm()
    producto_form = ProductoDeudaForm()
    
    # Poblar opciones del formulario
    deuda_form.cliente_id.choices = [(c['id'], f"{c['nombre']} ({c['cedula']})") for c in clientes]
    producto_form.producto_id.choices = [(p['id'], p['nombre']) for p in productos]
    
    # Inicializar lista de productos en sesión
    if 'productos_deuda' not in session:
        session['productos_deuda'] = []
    
    # Manejar agregar producto
    if producto_form.agregar.data and producto_form.validate():
        # USAR ESTE BLOQUE DE VALIDACIÓN DE STOCK
        selected_product_id = str(producto_form.producto_id.data)
        cantidad = producto_form.cantidad.data

        # Verificar stock disponible
        producto_ref = db_firestore.collection('productos').document(selected_product_id)
        producto_doc = producto_ref.get()
        
        if producto_doc.exists:
            producto_data = producto_doc.to_dict()
            stock_actual = producto_data.get('cantidad', 0)
            
            if cantidad > stock_actual:
                flash(f'No hay suficiente stock. Disponible: {stock_actual}', 'danger')
                return redirect(url_for('registrar_deuda'))
        
        # Agregar producto si hay stock suficiente
        session['productos_deuda'].append({
            'producto_id': selected_product_id,
            'cantidad': cantidad
        })
        session.modified = True
        return redirect(url_for('registrar_deuda'))
    
    # Manejar guardar deuda
    if deuda_form.guardar.data and deuda_form.validate():
        try:
            # Obtener próximo ID secuencial - ESTA ES LA LÍNEA FALTANTE
            next_id = get_next_sequence('deudas')
            
            # Obtener cliente
            cliente_ref = db_firestore.collection('clientes').document(str(deuda_form.cliente_id.data))
            cliente_doc = cliente_ref.get()
            if not cliente_doc.exists:
                flash('Cliente no encontrado', 'danger')
                return redirect(url_for('registrar_deuda'))
            
            cliente_data = cliente_doc.to_dict()
            
            # Crear datos de deuda
            deuda_data = {
                'cliente_id': cliente_ref,  # Almacena como referencia
                'cliente_cedula': cliente_data.get('cedula', ''),
                'fecha': datetime.utcnow(),
                'estado': 'pendiente'
            }
            
            # Guardar deuda en Firestore
            deuda_ref = db_firestore.collection('deudas').document(str(next_id))
            deuda_ref.set(deuda_data)
            
            # Guardar productos asociados
            for item in session['productos_deuda']:
                producto_ref = db_firestore.collection('productos').document(str(item['producto_id']))
                
                producto_deuda_data = {
                'deuda_id': str(next_id),  # Guardar como string, no como referencia
                'producto_id': str(item['producto_id']),  # Guardar como string
                'cantidad': item['cantidad']
}
                
                db_firestore.collection('productos_deuda').add(producto_deuda_data)
                
                # Actualizar inventario (reducir cantidad)
                producto_ref.update({
                    'cantidad': firestore.Increment(-item['cantidad'])
                })
            
            # Actualizar contador
            counter_ref = db_firestore.collection('counters').document('deudas')
            counter_ref.update({'seq': Increment(1)})
            
            # Limpiar sesión
            session.pop('productos_deuda', None)
            
            flash('Deuda registrada exitosamente', 'success')
            return redirect(url_for('consultar_deudas'))
            
        except Exception as e:
            print(f"Error al registrar deuda: {e}")
            flash('Error al registrar la deuda', 'danger')
    
    # Obtener detalles de productos para mostrar
    productos_en_deuda = []
    for item in session['productos_deuda']:
        producto_ref = db_firestore.collection('productos').document(str(item['producto_id']))
        producto_doc = producto_ref.get()
        if producto_doc.exists:
            producto = producto_doc.to_dict()
            precio = producto.get('precio', 0)
            cantidad = item['cantidad']
            subtotal = precio * cantidad
            
            productos_en_deuda.append({
                'id': item['producto_id'],
                'nombre': producto.get('nombre', ''),
                'cantidad': cantidad,
                'precio': precio,
                'subtotal': subtotal
            })
        else:
            productos_en_deuda.append({
                'id': item['producto_id'],
                'nombre': 'Producto eliminado',
                'cantidad': item['cantidad'],
                'precio': 0,
                'subtotal': 0
            })
    
    # Calcular el total de la deuda
    total_deuda = sum(item['subtotal'] for item in productos_en_deuda)
    
    return render_template('registrar_deuda.html', 
                          deuda_form=deuda_form,
                          producto_form=producto_form,
                          productos_deuda=productos_en_deuda,
                          total=total_deuda,
                          form=EmptyForm())

@app.route('/consultar_deudas')
@login_required
def consultar_deudas():
    try:
        # Obtener parámetros de filtro
        estado_filtro = request.args.get('estado', 'todos')
        cedula_filtro = request.args.get('cedula', '').strip().lower()
        
        # Construir consulta base
        deudas_ref = db_firestore.collection('deudas')
        
        # Aplicar filtro de estado si no es 'todos'
        if estado_filtro != 'todos':
            deudas_ref = deudas_ref.where(filter=FieldFilter('estado', '==', estado_filtro))
        
        # Ejecutar consulta inicial
        deudas_docs = deudas_ref.stream()
        
        deudas = []
        for deuda_doc in deudas_docs:
            deuda_data = deuda_doc.to_dict()
            deuda = {
                'id': deuda_doc.id,
                'estado': deuda_data.get('estado', 'pendiente'),
                'fecha': deuda_data.get('fecha', None),
                'cliente_cedula': deuda_data.get('cliente_cedula', '')
            }
            
            # Obtener referencia al cliente
            cliente_ref = deuda_data.get('cliente_id')
            cliente_id = None
            if isinstance(cliente_ref, DocumentReference):
                cliente_id = cliente_ref.id
            elif isinstance(cliente_ref, str):
                cliente_id = cliente_ref
            else:
                continue
                
            # Obtener nombre del cliente
            cliente_doc = db_firestore.collection('clientes').document(cliente_id).get()
            if cliente_doc.exists:
                deuda['cliente_nombre'] = cliente_doc.to_dict().get('nombre', '')
            else:
                deuda['cliente_nombre'] = 'Cliente eliminado'
            deuda['cliente_id'] = cliente_id

            # Calcular total de la deuda
            total = 0.0
            productos_query = db_firestore.collection('productos_deuda')\
                .where('deuda_id', '==', deuda_doc.id).stream()
            
            for prod_doc in productos_query:
                prod_data = prod_doc.to_dict()
                producto_id = prod_data.get('producto_id', '')
                cantidad = prod_data.get('cantidad', 0)
                
                if producto_id:
                    if isinstance(producto_id, DocumentReference):
                        producto_ref = producto_id
                    elif isinstance(producto_id, str):
                        producto_ref = db_firestore.collection('productos').document(producto_id)
                    else:
                        continue
                    
                    producto_doc = producto_ref.get()
                    if producto_doc.exists:
                        producto = producto_doc.to_dict()
                        precio = producto.get('precio', 0.0)
                        total += precio * cantidad

            deuda['total'] = total
            
            # Calcular saldo pendiente
            saldo = total
            pagos_query = db_firestore.collection('pagos_parciales')\
                .where('deuda_id', '==', deuda_doc.id).stream()
            
            for pago_doc in pagos_query:
                pago_data = pago_doc.to_dict()
                monto = pago_data.get('monto_usd', 0.0)
                saldo -= monto

            deuda['saldo_pendiente'] = saldo
            
            # Aplicar filtro de cedula (si se proporcionó)
            if cedula_filtro and cedula_filtro not in deuda['cliente_cedula'].lower():
                continue
                
            deudas.append(deuda)
        
        # Ordenar por fecha descendente
        deudas.sort(key=lambda x: x['fecha'] if x['fecha'] else datetime.min, reverse=True)
        
        return render_template('consultar_deudas.html', deudas=deudas, 
                               estado_filtro=estado_filtro, cedula_filtro=cedula_filtro,
                          form=EmptyForm())
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Error al cargar deudas: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/eliminar_producto_temp/<int:index>', methods=['POST'])
@login_required
def eliminar_producto_temp(index):
    if 'productos_deuda' in session and 0 <= index < len(session['productos_deuda']):
        session['productos_deuda'].pop(index)
        session.modified = True
    return redirect(url_for('registrar_deuda'))

@app.route('/consulta_deuda_cliente', methods=['GET', 'POST'])
def consulta_deuda_cliente():
    form = ConsultaDeudaForm()
    if form.validate_on_submit():
        nombre = form.nombre.data.strip()  # Normalizar entrada
        
        # Buscar cliente (insensible a mayúsculas)
        clientes_ref = db_firestore.collection('clientes')
        clientes = []
        for doc in clientes_ref.stream():
            cliente_data = doc.to_dict()
            if cliente_data.get('nombre', '') == nombre:
                cliente = cliente_data
                cliente['id'] = doc.id
                clientes.append(cliente)
        
        if not clientes:
            flash('Cliente no encontrado', 'info')
            return redirect(url_for('index'))
        
        cliente = clientes[0]  # Tomar el primer cliente coincidente
        cliente_id = cliente['id']
        
        # Obtener todas las deudas del cliente
        deudas_ref = db_firestore.collection('deudas')
        deudas_info = []
        total_pendiente = 0.0
        
        for deuda_doc in deudas_ref.stream():
            deuda_data = deuda_doc.to_dict()
            deuda_cliente_ref = deuda_data.get('cliente_id')
            
            # Normalizar la referencia al cliente
            deuda_cliente_id = None
            if isinstance(deuda_cliente_ref, DocumentReference):
                deuda_cliente_id = deuda_cliente_ref.id
            elif isinstance(deuda_cliente_ref, str):
                deuda_cliente_id = deuda_cliente_ref
            else:
                continue
                
            if deuda_cliente_id != cliente_id:
                continue
                
            # Procesar la deuda
            deuda_info = {
                'id': deuda_doc.id,
                'fecha': deuda_data.get('fecha'),
                'estado': deuda_data.get('estado', 'pendiente'),
                'productos': [],
                'pagos_parciales': [],
                'total': 0.0,
                'saldo_pendiente': 0.0
            }
            
            # Obtener productos de la deuda
            productos_query = db_firestore.collection('productos_deuda')\
                .where('deuda_id', '==', deuda_doc.id).stream()
            
            for prod_doc in productos_query:
                prod_data = prod_doc.to_dict()
                producto_id = prod_data.get('producto_id', '')
                cantidad = prod_data.get('cantidad', 0)
                
                if not producto_id:
                    continue
                    
                # Obtener detalles del producto
                if isinstance(producto_id, DocumentReference):
                    producto_ref = producto_id
                elif isinstance(producto_id, str):
                    producto_ref = db_firestore.collection('productos').document(producto_id)
                else:
                    continue
                    
                producto_doc = producto_ref.get()
                if not producto_doc.exists:
                    continue
                    
                producto = producto_doc.to_dict()
                precio = producto.get('precio', 0.0)
                try:
                    precio = float(precio)
                except (TypeError, ValueError):
                    precio = 0.0
                    
                subtotal = precio * cantidad
                deuda_info['productos'].append({
                    'producto': producto,
                    'cantidad': cantidad,
                    'precio': precio,
                    'subtotal': subtotal
                })
                deuda_info['total'] += subtotal
            
            # Obtener pagos parciales
            pagos_query = db_firestore.collection('pagos_parciales')\
                .where('deuda_id', '==', deuda_doc.id).stream()
            
            total_pagos = 0.0
            for pago_doc in pagos_query:
                pago_data = pago_doc.to_dict()
                monto = pago_data.get('monto_usd', 0.0)
                try:
                    monto = float(monto)
                except (TypeError, ValueError):
                    monto = 0.0
                    
                total_pagos += monto
                
                # Convertir fecha si es necesario
                fecha_pago = pago_data.get('fecha')
                if hasattr(fecha_pago, 'timestamp'):
                    pago_data['fecha'] = datetime.fromtimestamp(fecha_pago.timestamp())
                
                deuda_info['pagos_parciales'].append(pago_data)
            
            deuda_info['saldo_pendiente'] = deuda_info['total'] - total_pagos
            
            if deuda_info['estado'] == 'pendiente':
                total_pendiente += deuda_info['saldo_pendiente']
            
            deudas_info.append(deuda_info)
        
        # Ordenar deudas por fecha (más reciente primero)
        deudas_info.sort(key=lambda x: x['fecha'] if x['fecha'] else datetime.min, reverse=True)
        
    # Separar deudas en pendientes y pagadas
        deudas_pendientes = []
        deudas_pagadas = []
        for deuda in deudas_info:
            if deuda['estado'] == 'pendiente':
                deudas_pendientes.append(deuda)
            else:
                deudas_pagadas.append(deuda)
        
        return render_template('consulta_deuda_cliente.html', 
                            cliente=cliente, 
                            deudas_pendientes=deudas_pendientes,
                            deudas_pagadas=deudas_pagadas,
                            total_pendiente=total_pendiente,
                            form=EmptyForm())
    
    return redirect(url_for('index'))
            

@app.route('/editar_deuda/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_deuda(id):
    deuda = db.session.get(Deuda, id) or abort(404)
    
    # Obtener todos los clientes
    clientes = db.session.execute(select(Cliente)).scalars().all()
    
    # Crear formulario
    deuda_form = DeudaForm()
    deuda_form.cliente_id.choices = [(c.id, f"{c.nombre} ({c.cedula})") for c in clientes]
    deuda_form.cliente_id.data = deuda.cliente_id
    
    # Formulario para agregar productos
    producto_form = ProductoDeudaForm()
    producto_form.producto_id.choices = [(p.id, p.nombre) for p in Producto.query.all()]
    
    # Inicializar la sesión si no existe
    if 'productos_deuda' not in session:
        session['productos_deuda'] = []
        # Cargar productos existentes
        for producto_deuda in deuda.productos:
            session['productos_deuda'].append({
                'producto_id': producto_deuda.producto_id,
                'cantidad': producto_deuda.cantidad
            })
    
    if producto_form.agregar.data and producto_form.validate():
        session['productos_deuda'].append({
            'producto_id': producto_form.producto_id.data,
            'cantidad': producto_form.cantidad.data
        })
        session.modified = True
        return redirect(url_for('editar_deuda', id=id))
    
    if deuda_form.guardar.data and deuda_form.validate():
     new_cliente_id = deuda_form.cliente_id.data
     new_cliente = db.session.get(Cliente, new_cliente_id)
    
    if not new_cliente:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('editar_deuda', id=id))
    
    # Actualizar cliente asociado
    deuda.cliente_id = new_cliente_id
    deuda.cliente_cedula = new_cliente.cedula
    
    # Eliminar productos antiguos
    ProductoDeuda.query.filter_by(deuda_id=deuda.id).delete()
    
    # Agregar nuevos productos
    for item in session['productos_deuda']:
        producto_deuda = ProductoDeuda(
            deuda_id=deuda.id,
            producto_id=item['producto_id'],
            cantidad=item['cantidad']
        )
        db.session.add(producto_deuda)
    
     # Limpiar sesión
    session.pop('productos_deuda', None)
    db.session.commit()
    

    flash('Deuda actualizada exitosamente', 'success')
    return redirect(url_for('consultar_deudas'))

@app.route('/gestion_deudas/<string:cliente_id>', methods=['GET'])
@login_required
def gestion_deudas(cliente_id):
    # Obtener cliente
    cliente_ref = db_firestore.collection('clientes').document(cliente_id)
    cliente_doc = cliente_ref.get()
    
    if not cliente_doc.exists:
        abort(404)
    
    cliente = cliente_doc.to_dict()
    cliente['id'] = cliente_id
    
    # Obtener todas las deudas del cliente
    query = db_firestore.collection('deudas').where(
    filter=FieldFilter('cliente_id', '==', cliente_ref))
    deudas_pendientes = []
    deudas_pagadas = []
    
    for deuda_doc in query.stream():
        deuda_data = deuda_doc.to_dict()
        deuda = {
            'id': deuda_doc.id,
            'estado': deuda_data.get('estado', 'pendiente'),
            'cliente_cedula': deuda_data.get('cliente_cedula', '')
        }
        
        # Manejo de fechas
        fecha = deuda_data.get('fecha')
        if fecha:
            if hasattr(fecha, 'timestamp'):
                deuda['fecha'] = datetime.fromtimestamp(fecha.timestamp(), tz=timezone.utc).replace(tzinfo=None)
            else:
                deuda['fecha'] = fecha
        else:
            deuda['fecha'] = None
        
        # Obtener productos de la deuda
        deuda['productos'] = []
        total_deuda = 0.0
        productos_query = db_firestore.collection('productos_deuda').where('deuda_id', '==', deuda_doc.id).stream()
        
        for prod_doc in productos_query:
            prod_data = prod_doc.to_dict()
            producto_id = prod_data.get('producto_id', '')
            cantidad = prod_data.get('cantidad', 0)
            
            if producto_id:
                if isinstance(producto_id, DocumentReference):
                    producto_ref = producto_id
                elif isinstance(producto_id, str):
                    producto_ref = db_firestore.collection('productos').document(producto_id)
                else:
                    continue
                
                producto_doc = producto_ref.get()
                if producto_doc.exists:
                    producto = producto_doc.to_dict()
                    precio = producto.get('precio', 0.0)
                    subtotal = precio * cantidad
                    total_deuda += subtotal
                    
                    deuda['productos'].append({
                        'producto': producto,
                        'cantidad': cantidad,
                        'subtotal': subtotal
                    })
        
        deuda['total'] = total_deuda
        
        # Obtener pagos parciales
        deuda['pagos_parciales'] = []
        saldo_pendiente = total_deuda
        pagos_query = db_firestore.collection('pagos_parciales').where('deuda_id', '==', deuda_doc.id).stream()
        
        for pago_doc in pagos_query:
            pago_data = pago_doc.to_dict()
            monto = pago_data.get('monto_usd', 0.0)
            try:
                monto = float(monto)
            except (TypeError, ValueError):
                monto = 0.0
            saldo_pendiente -= monto
            
            # Manejo de fechas para pagos
            if 'fecha' in pago_data and hasattr(pago_data['fecha'], 'timestamp'):
                pago_data['fecha'] = datetime.fromtimestamp(pago_data['fecha'].timestamp(), tz=timezone.utc).replace(tzinfo=None)
            deuda['pagos_parciales'].append(pago_data)
        
        deuda['saldo_pendiente'] = saldo_pendiente
        
        # Separar deudas en pendientes y pagadas
        if deuda['estado'] == 'pendiente':
            deudas_pendientes.append(deuda)
        else:
            deudas_pagadas.append(deuda)
    
    return render_template('gestion_deudas.html', 
                          cliente=cliente, 
                          deudas_pendientes=deudas_pendientes,
                          deudas_pagadas=deudas_pagadas)

@app.route('/marcar_pagada/<string:deuda_id>', methods=['POST'])
@login_required
def marcar_pagada(deuda_id):
    deuda_ref = db_firestore.collection('deudas').document(deuda_id)
    if deuda_ref.get().exists:
        deuda_ref.update({'estado': 'pagada'})
        flash('Deuda marcada como pagada', 'success')
    else:
        flash('Deuda no encontrada', 'danger')
    return redirect(url_for('consultar_deudas'))

@app.route('/eliminar_producto/<string:id>', methods=['POST'])
@login_required
def eliminar_producto(id):
    try:
        doc_ref = db_firestore.collection('productos').document(id)
        if doc_ref.get().exists:
            doc_ref.delete()
            flash('Producto eliminado correctamente', 'success')
        else:
            flash('Producto no encontrado', 'danger')
    except Exception as e:
        print(f"Error al eliminar producto: {e}")
        flash('Error al eliminar el producto', 'danger')
    return redirect(url_for('listar_productos'))


@app.route('/registrar_pago_parcial/<string:deuda_id>', methods=['POST'])
@login_required
def registrar_pago_parcial(deuda_id):
    try:
        # Obtener datos del formulario
        monto = float(request.form.get('monto'))
        descripcion = request.form.get('descripcion', 'Pago parcial')
        cliente_id = request.form.get('cliente_id')
        
        # Validar cliente_id
        if not cliente_id:
            flash('Cliente no especificado', 'danger')
            return redirect(url_for('dashboard'))
        
        # Obtener saldo pendiente actual
        saldo_pendiente = obtener_saldo_pendiente(deuda_id)
        
        if monto <= 0:
            flash('El monto debe ser mayor a cero', 'danger')
            return redirect(url_for('gestion_deudas', cliente_id=cliente_id))
        
        # Validar que el monto no exceda el saldo pendiente
        if monto > saldo_pendiente:
            flash(f'El monto no puede exceder el saldo pendiente (${saldo_pendiente:.2f})', 'danger')
            return redirect(url_for('gestion_deudas', cliente_id=cliente_id))
        
        # Crear pago parcial
        pago_data = {
            'deuda_id': deuda_id,
            'monto_usd': monto,
            'descripcion': descripcion,
            'fecha': datetime.utcnow()
        }
        db_firestore.collection('pagos_parciales').add(pago_data)
        
        # Verificar si la deuda queda saldada
        nuevo_saldo = saldo_pendiente - monto
        if nuevo_saldo <= 0.01:  # Tolerancia para errores de redondeo
            db_firestore.collection('deudas').document(deuda_id).update({'estado': 'pagada'})
        
        flash('Pago parcial registrado exitosamente', 'success')
        return redirect(url_for('gestion_deudas', cliente_id=cliente_id))
    except Exception as e:
        print(f"Error al registrar pago parcial: {e}")
        flash('Error al registrar el pago', 'danger')
        return redirect(url_for('dashboard'))

def obtener_saldo_pendiente(deuda_id):
    """Calcula el saldo pendiente de una deuda"""
    # Calcular total de la deuda
    total = 0.0
    productos_query = db_firestore.collection('productos_deuda').where(
    filter=FieldFilter('deuda_id', '==', deuda_id)).stream()
    for prod_doc in productos_query:
        prod_data = prod_doc.to_dict()
        producto_id = prod_data.get('producto_id', '')
        cantidad = prod_data.get('cantidad', 0)
        
        if producto_id:
            # Manejar referencia o string
            if isinstance(producto_id, DocumentReference):
                producto_ref = producto_id
            elif isinstance(producto_id, str):
                producto_ref = db_firestore.collection('productos').document(producto_id)
            else:
                continue
            
            producto_doc = producto_ref.get()
            if producto_doc.exists:
                producto = producto_doc.to_dict()
                precio = producto.get('precio', 0.0)
                total += precio * cantidad
    
    # Restar pagos parciales existentes
    pagos_query = db_firestore.collection('pagos_parciales').where(
    filter=FieldFilter('deuda_id', '==', deuda_id)).stream()
    for pago_doc in pagos_query:
        pago_data = pago_doc.to_dict()
        monto = pago_data.get('monto_usd', 0.0)
        total -= monto
    
    return total

@app.route('/eliminar_deuda/<int:id>', methods=['POST'])
@login_required
def eliminar_deuda(id):
    deuda = db.session.get(Deuda, id) or abort(404)
    
    # Eliminar productos asociados
    ProductoDeuda.query.filter_by(deuda_id=id).delete()
    
    # Eliminar la deuda
    db.session.delete(deuda)
    db.session.commit()
    
    flash('Deuda eliminada correctamente', 'success')
    return redirect(url_for('consultar_deudas'))

@app.route('/mi_cuenta', methods=['GET', 'POST'])
@login_required
def mi_cuenta():
    # Obtener información existente de la empresa
    empresa_ref = db_firestore.collection('empresa').document('info')
    empresa_doc = empresa_ref.get()
    empresa_data = empresa_doc.to_dict() if empresa_doc.exists else None
    
    form = EmpresaForm()
    
    # Cargar datos existentes en el formulario
    if request.method == 'GET' and empresa_data:
        form.nombre.data = empresa_data.get('nombre', '')
        form.direccion.data = empresa_data.get('direccion', '')
        form.telefono.data = empresa_data.get('telefono', '')
        form.facebook.data = empresa_data.get('facebook', '')
        form.instagram.data = empresa_data.get('instagram', '')
        form.twitter.data = empresa_data.get('twitter', '')
        form.logo_url.data = empresa_data.get('logo_url', '')
    
    if form.validate_on_submit():
        # Guardar/actualizar información
        empresa_data = {
            'nombre': form.nombre.data,
            'direccion': form.direccion.data,
            'telefono': form.telefono.data,
            'facebook': form.facebook.data,
            'instagram': form.instagram.data,
            'twitter': form.twitter.data,
            'logo_url': form.logo_url.data
        }
        
        empresa_ref.set(empresa_data)
        flash('Información de la empresa actualizada correctamente', 'success')
        return redirect(url_for('mi_cuenta'))
    
    return render_template('mi_cuenta.html', form=form, empresa=empresa_data)

# Función para inyectar datos de la empresa en todas las plantillas
@app.context_processor
def inject_empresa():
    empresa_ref = db_firestore.collection('empresa').document('info')
    empresa_doc = empresa_ref.get()
    if empresa_doc.exists:
        return {'empresa': empresa_doc.to_dict()}
    return {'empresa': None}

# Ruta para la tienda (nueva página principal)
@app.route('/tienda')
def tienda():
    # Obtener productos con stock
    productos = []
    query = db_firestore.collection('productos').where('cantidad', '>', 0)
    
    for doc in query.stream():
        producto = doc.to_dict()
        producto['id'] = doc.id
        productos.append(producto)
    
    return render_template('tienda.html', productos=productos)

@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    total = 0
    
    # Calcular el total y añadir información adicional
    cart_items = []
    for product_id, item in cart.items():
        # Obtener información actualizada del producto
        product_ref = db_firestore.collection('productos').document(product_id)
        product_doc = product_ref.get()
        
        if product_doc.exists:
            product = product_doc.to_dict()
            item['name'] = product['nombre']
            item['price'] = float(product['precio'])
            item['image'] = product.get('imagen_url', '')
            item['max_quantity'] = product['cantidad']  # Stock disponible
            
            # Calcular subtotal
            item['subtotal'] = item['price'] * item['quantity']
            total += item['subtotal']
            
            cart_items.append(item)
    
    return render_template('cart.html', cart_items=cart_items, total=total)

# Ruta para añadir al carrito
@app.route('/add_to_cart/<string:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    
    # Obtener información del producto
    product_ref = db_firestore.collection('productos').document(product_id)
    product_doc = product_ref.get()
    
    if not product_doc.exists:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('index'))
    
    product = product_doc.to_dict()
    
    # Verificar stock
    if quantity > product['cantidad']:
        flash(f'No hay suficiente stock. Disponible: {product["cantidad"]}', 'danger')
        return redirect(url_for('index'))
    
    # Inicializar carrito en sesión
    if 'cart' not in session:
        session['cart'] = {}
    
    # Añadir o actualizar producto en carrito
    if product_id in session['cart']:
        new_quantity = session['cart'][product_id]['quantity'] + quantity
        if new_quantity > product['cantidad']:
            flash(f'No puedes agregar más de {product["cantidad"]} unidades', 'danger')
            return redirect(url_for('index'))
        
        session['cart'][product_id]['quantity'] = new_quantity
    else:
        session['cart'][product_id] = {
            'quantity': quantity,
            'name': product['nombre'],
            'price': float(product['precio']),
            'image': product.get('imagen_url', '')
        }
    
    session.modified = True
    flash(f'Producto {product["nombre"]} añadido al carrito', 'success')
    session['cart_updated'] = datetime.utcnow().isoformat()
    return redirect(url_for('index'))

# Ruta para actualizar cantidad en el carrito
@app.route('/update_cart_quantity/<string:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    new_quantity = int(request.form.get('quantity', 1))
    
    if 'cart' not in session or product_id not in session['cart']:
        flash('Producto no encontrado en el carrito', 'danger')
        return redirect(url_for('view_cart'))
    
    # Obtener información actual del producto
    product_ref = db_firestore.collection('productos').document(product_id)
    product_doc = product_ref.get()
    
    if not product_doc.exists:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('view_cart'))
    
    product = product_doc.to_dict()
    
    # Verificar stock
    if new_quantity > product['cantidad']:
        flash(f'No hay suficiente stock. Disponible: {product["cantidad"]}', 'danger')
        return redirect(url_for('view_cart'))
    
    session['cart'][product_id]['quantity'] = new_quantity
    session.modified = True
    session['cart_updated'] = datetime.utcnow().isoformat()
    return redirect(url_for('view_cart'))

# Ruta para eliminar del carrito
@app.route('/remove_from_cart/<string:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'cart' in session and product_id in session['cart']:
        del session['cart'][product_id]
        session.modified = True
        flash('Producto eliminado del carrito', 'success')
        session['cart_updated'] = datetime.utcnow().isoformat()
    return redirect(url_for('view_cart'))

# Ruta para obtener contador del carrito
@app.route('/cart_count')
def cart_count():
    count = 0
    if 'cart' in session:
        count = sum(item['quantity'] for item in session['cart'].values())
    return jsonify({'count': count})

@app.route('/cart_sidebar_partial')
def cart_sidebar_partial():
    cart = session.get('cart', {})
    total = 0
    cart_items = []
    
    for product_id, item in cart.items():
        product_ref = db_firestore.collection('productos').document(product_id)
        product_doc = product_ref.get()
        
        if product_doc.exists:
            product = product_doc.to_dict()
            item['name'] = product['nombre']
            item['price'] = float(product['precio'])
            item['image'] = product.get('imagen_url', '')
            item['subtotal'] = item['price'] * item['quantity']
            total += item['subtotal']
            cart_items.append({
                'id': product_id,
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'subtotal': item['subtotal'],
                'image': item['image']
            })
    
    return render_template('partials/cart_sidebar.html', 
                          cart_items=cart_items, 
                          total=total)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Obtener el carrito de la sesión
    cart = session.get('cart', {})
    
    if not cart:
        flash('Tu carrito está vacío', 'warning')
        return redirect(url_for('index'))
    
    # Obtener información actualizada de los productos
    cart_items = []
    total = 0
    
    for product_id, item in cart.items():
        product_ref = db_firestore.collection('productos').document(product_id)
        product_doc = product_ref.get()
        
        if product_doc.exists:
            product = product_doc.to_dict()
            # Crear un nuevo objeto con la información necesaria
            cart_item = {
                'id': product_id,
                'name': item['name'],
                'price': float(product['precio']),
                'quantity': item['quantity'],
                'subtotal': float(product['precio']) * item['quantity'],
                'image': item.get('image', '')
            }
            total += cart_item['subtotal']
            cart_items.append(cart_item)
    
    form = CheckoutForm()
    
    if form.validate_on_submit():
        try:
            # Crear un nuevo pedido en Firestore
            pedido_data = {
                'cliente_nombre': form.nombre.data,
                'cliente_direccion': form.direccion.data,
                'cliente_telefono': form.telefono.data,
                'cliente_email': form.email.data,
                'notas': form.notas.data,
                'total': total,
                'estado': 'pendiente',
                'fecha': datetime.utcnow()
            }
            
            # Guardar el pedido
            pedido_ref = db_firestore.collection('pedidos').document()
            pedido_ref.set(pedido_data)
            pedido_id = pedido_ref.id
            
            # Guardar los items del pedido
            for item in cart_items:
                item_data = {
                    'pedido_id': pedido_id,
                    'producto_id': item['id'],
                    'producto_nombre': item['name'],
                    'precio': item['price'],
                    'cantidad': item['quantity']
                }
                db_firestore.collection('items_pedido').add(item_data)
                
                # Actualizar el stock
                product_ref = db_firestore.collection('productos').document(item['id'])
                product_ref.update({
                    'cantidad': firestore.Increment(-item['quantity'])
                })
            
            # Vaciar el carrito
            session.pop('cart', None)
            
            flash('Pedido realizado con éxito. ¡Gracias!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Error al realizar el pedido: {e}")
            flash('Error al procesar el pedido', 'danger')
    
    return render_template('checkout.html', form=form, total=total, cart_items=cart_items)



@app.route('/pedidos')
@login_required
def listar_pedidos():
    # Obtener todos los pedidos
    pedidos = []
    pedidos_ref = db_firestore.collection('pedidos').order_by('fecha', direction=firestore.Query.DESCENDING)
    
    for pedido_doc in pedidos_ref.stream():
        pedido = pedido_doc.to_dict()
        pedido['id'] = pedido_doc.id
        pedidos.append(pedido)
    
    # Crear un formulario vacío
    from forms import EmptyForm  # Importa un formulario vacío
    return render_template('pedidos.html', pedidos=pedidos, form=EmptyForm())

@app.route('/pedido/<string:pedido_id>')
@login_required
def ver_pedido(pedido_id):
    # Obtener el pedido
    pedido_ref = db_firestore.collection('pedidos').document(pedido_id)
    pedido_doc = pedido_ref.get()
    
    if not pedido_doc.exists:
        abort(404)
    
    pedido = pedido_doc.to_dict()
    pedido['id'] = pedido_id
    
    # Obtener los items del pedido
    items = []
    items_query = db_firestore.collection('items_pedido').where(
    filter=FieldFilter('pedido_id', '==', pedido_id))
    
    for item_doc in items_query.stream():
        item = item_doc.to_dict()
        item['id'] = item_doc.id
        items.append(item)
    
    return render_template('detalle_pedido.html', pedido=pedido, items=items)

if __name__ == '__main__':
    # Configuración para acceso en red local:
    app.run(
        host='0.0.0.0',  # Escucha en todas las interfaces de red
        port=5001,        # Puerto (puedes cambiarlo si necesitas)
        debug=True        # Solo para desarrollo!
    )
