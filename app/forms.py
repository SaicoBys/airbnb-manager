from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, SelectField, DateField, IntegerField, DateTimeField
from wtforms.validators import DataRequired, Email, Optional, NumberRange, ValidationError

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class ClientForm(FlaskForm):
    full_name = StringField('Nombre Completo', validators=[DataRequired()])
    phone_number = StringField('Número de Teléfono', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    notes = TextAreaField('Notas')
    submit = SubmitField('Guardar Cliente')

class ExpenseForm(FlaskForm):
    description = StringField('Descripción del Gasto', validators=[DataRequired()])
    amount = FloatField('Monto', validators=[DataRequired()])
    category = SelectField('Categoría', choices=[('Suministros', 'Suministros'), ('Servicios', 'Servicios'), ('Mantenimiento', 'Mantenimiento'), ('Marketing', 'Marketing'), ('Otro', 'Otro')], validators=[DataRequired()])
    
    # ¡NUEVOS CAMPOS! Para control de pagos
    payment_method = SelectField('Método de Pago', choices=[
        ('Efectivo', '💵 Efectivo (de la caja)'),
        ('Tarjeta', '💳 Tarjeta personal'),
        ('Transferencia', '🏦 Transferencia personal')
    ], validators=[DataRequired()], default='Efectivo')
    
    paid_by = SelectField('Pagado por', coerce=int, validators=[DataRequired()])
    
    submit = SubmitField('Registrar Gasto')

class StayForm(FlaskForm):
    client = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    room = SelectField('Habitación', coerce=int, validators=[DataRequired()])
    # --- ¡NUEVO CAMPO! ---
    booking_channel = SelectField('Canal de Reserva', choices=[
        ('Directo', 'Directo'),
        ('Airbnb', 'Airbnb'),
        ('Booking.com', 'Booking.com'),
        ('Otro', 'Otro')
    ], validators=[DataRequired()])
    check_in_date = DateField('Fecha de Entrada', format='%Y-%m-%d', validators=[DataRequired()])
    check_out_date = DateField('Fecha de Salida', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Registrar Estancia')

class PaymentForm(FlaskForm):
    amount = FloatField('Monto del Pago', validators=[DataRequired()])
    method = SelectField('Método de Pago', choices=[('Efectivo', 'Efectivo'), ('Transferencia', 'Transferencia'), ('Tarjeta', 'Tarjeta')], validators=[DataRequired()])
    submit = SubmitField('Registrar Pago')

class SupplyForm(FlaskForm):
    name = StringField('Nombre del Suministro', validators=[DataRequired()])
    category = SelectField('Categoría', choices=[
        ('Limpieza', 'Productos de Limpieza'),
        ('Amenities', 'Amenities para Huéspedes'),
        ('Cocina', 'Suministros de Cocina'),
        ('Baño', 'Suministros de Baño'),
        ('Ropa de Cama', 'Ropa de Cama y Toallas'),
        ('Mantenimiento', 'Herramientas y Mantenimiento'),
        ('Otro', 'Otro')
    ], validators=[DataRequired()])
    current_stock = IntegerField('Stock Actual', validators=[DataRequired(), NumberRange(min=0)])
    minimum_stock = IntegerField('Stock Mínimo', validators=[DataRequired(), NumberRange(min=0)], default=5)
    unit_price = FloatField('Precio Unitario (DOP)', validators=[Optional(), NumberRange(min=0)])
    supplier = StringField('Proveedor')
    notes = TextAreaField('Notas')
    submit = SubmitField('Guardar Suministro')

class UpdateStockForm(FlaskForm):
    """Formulario para actualizar solo el stock de un suministro."""
    current_stock = IntegerField('Nuevo Stock', validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('Notas del Cambio')
    submit = SubmitField('Actualizar Stock')

class UnifiedStayForm(FlaskForm):
    """Formulario unificado SPA para registro inteligente de estancias."""
    
    # === BÚSQUEDA INTELIGENTE DE CLIENTE ===
    phone_search = StringField('Número de Teléfono', 
                              validators=[DataRequired()],
                              render_kw={
                                  "placeholder": "(809) 000-0000", 
                                  "id": "phone_search",
                                  "class": "phone-mask"
                              })
    
    # === DATOS DEL CLIENTE (Auto-rellenables) ===
    client_name = StringField('Nombre Completo', 
                             validators=[DataRequired()],
                             render_kw={"id": "client_name"})
    client_email = StringField('Email', 
                              validators=[Optional(), Email()],
                              render_kw={
                                  "placeholder": "cliente@ejemplo.com",
                                  "id": "client_email"
                              })
    client_notes = TextAreaField('Notas del Cliente',
                                render_kw={
                                    "placeholder": "Preferencias, alergias, etc.",
                                    "id": "client_notes"
                                })
    
    # === FECHAS DE ESTANCIA (Con validación inteligente) ===
    check_in_date = DateField('Check-in', 
                             validators=[DataRequired()],
                             render_kw={"id": "check_in_date"})
    check_out_date = DateField('Check-out', 
                              validators=[Optional()],
                              render_kw={"id": "check_out_date"})
    
    # === SELECCIÓN DE HABITACIÓN (Con disponibilidad) ===
    room_selection = SelectField('Habitación Asignada', 
                                coerce=int, 
                                validators=[DataRequired()],
                                render_kw={"id": "room_selection"})
    
    # === CANAL DE RESERVA ===
    booking_channel = SelectField('Canal de Reserva', 
                                 choices=[
                                     ('Directo', '🏠 Directo'),
                                     ('Airbnb', '🏠 Airbnb'),
                                     ('Booking.com', '🌐 Booking.com'),
                                     ('Expedia', '✈️ Expedia'),
                                     ('WhatsApp', '💬 WhatsApp'),
                                     ('Otro', '📱 Otro')
                                 ], 
                                 validators=[DataRequired()],
                                 default='Directo')
    
    # === INFORMACIÓN DE PAGO ===
    payment_amount = FloatField('Monto del Pago (DOP)', 
                               validators=[DataRequired(), NumberRange(min=0.01)],
                               render_kw={
                                   "placeholder": "0.00",
                                   "step": "0.01",
                                   "id": "payment_amount"
                               })
    payment_method = SelectField('Método de Pago', 
                                choices=[
                                    ('Efectivo', '💵 Efectivo'),
                                    ('Transferencia', '🏦 Transferencia'),
                                    ('Tarjeta', '💳 Tarjeta'),
                                    ('Pago Móvil', '📱 Pago Móvil')
                                ], 
                                validators=[DataRequired()],
                                default='Efectivo')
    
    # === BOTONES DE ACCIÓN ===
    save_client_only = SubmitField('💾 Guardar Solo Cliente',
                                  render_kw={"class": "btn-secondary"})
    save_full_stay = SubmitField('🏨 Guardar Estancia Completa',
                                render_kw={"class": "btn-primary"})
    
    # === VALIDACIONES PERSONALIZADAS ===
    def validate_check_out_date(self, field):
        if field.data and self.check_in_date.data:
            if field.data <= self.check_in_date.data:
                raise ValidationError('La fecha de check-out debe ser posterior al check-in.')
    
    def validate_payment_amount(self, field):
        if field.data and field.data <= 0:
            raise ValidationError('El monto del pago debe ser mayor a cero.')

class CashClosureForm(FlaskForm):
    """Formulario para crear un cierre de caja manual."""
    month = SelectField('Mes', choices=[
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ], coerce=int, validators=[DataRequired()])
    year = IntegerField('Año', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    notes = TextAreaField('Notas del Cierre')
    submit = SubmitField('Crear Cierre de Caja')

class EmployeeDeliveryForm(FlaskForm):
    """Formulario para registrar entrega de empleada."""
    delivered_amount = FloatField('Monto Entregado', validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('Notas de la Entrega')
    submit = SubmitField('Registrar Entrega')

class MonthYearForm(FlaskForm):
    """Formulario para seleccionar mes/año para reportes."""
    month = SelectField('Mes', choices=[
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ], coerce=int, validators=[DataRequired()])
    year = IntegerField('Año', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    submit = SubmitField('Ver Reporte')
