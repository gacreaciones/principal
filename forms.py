from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, EqualTo, Email

class ConsultaDeudaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    consultar = SubmitField('Consultar Deuda')

class PagoForm(FlaskForm):
    referencia = StringField('Número de Referencia', validators=[DataRequired()])
    banco_origen = StringField('Banco de Origen', validators=[DataRequired()])
    monto_usd = FloatField('Monto en Dólares', validators=[DataRequired(), NumberRange(min=0.01)])
    pagar = SubmitField('Registrar Pago')

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class ProductoForm(FlaskForm):
    nombre = StringField('Nombre del Producto', validators=[DataRequired()])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1)])
    precio = FloatField('Precio (USD)', validators=[DataRequired(), NumberRange(min=0.01)])
    categoria = StringField('Categoría', validators=[DataRequired()])  # Nuevo campo
    imagen_url = StringField('URL de la Imagen', validators=[DataRequired()])  # Nuevo campo
    submit = SubmitField('Guardar Producto')

class ClienteForm(FlaskForm):
    nombre = StringField('Nombre Completo', validators=[DataRequired()])
    cedula = StringField('Cedula', validators=[DataRequired(), Length(min=6, max=8)])
    direccion = StringField('Dirección', validators=[DataRequired()])
    telefono = StringField('Teléfono', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Guardar Cliente')

class DeudaForm(FlaskForm):
    cliente_id = SelectField('Cliente', coerce=str)
    guardar = SubmitField('Guardar Deuda')

class ProductoDeudaForm(FlaskForm):
    producto_id = SelectField('Producto', coerce=str)
    cantidad = IntegerField('Cantidad', validators=[DataRequired()])
    agregar = SubmitField('Agregar Producto')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Contraseña Actual', validators=[DataRequired()])
    new_password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Nueva Contraseña', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Cambiar Contraseña')

class EmpresaForm(FlaskForm):
    nombre = StringField('Nombre de la Empresa', validators=[DataRequired()])
    direccion = StringField('Dirección', validators=[DataRequired()])
    telefono = StringField('Teléfono', validators=[DataRequired()])
    facebook = StringField('Facebook (URL)')
    instagram = StringField('Instagram (URL)')
    twitter = StringField('Twitter (URL)')
    logo_url = StringField('URL del Logo')
    submit = SubmitField('Guardar Información')

class CheckoutForm(FlaskForm):
    nombre = StringField('Nombre Completo', validators=[DataRequired()])
    direccion = StringField('Dirección', validators=[DataRequired()])
    telefono = StringField('Teléfono', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    notas = TextAreaField('Notas adicionales (opcional)')
    submit = SubmitField('Realizar Pedido')

class EmptyForm(FlaskForm):
    pass