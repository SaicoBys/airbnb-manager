from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin 
from datetime import datetime, timezone
from sqlalchemy import func
from calendar import monthrange

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(10), index=True, nullable=False)
    
    tasks = db.relationship('Task', backref='assignee', lazy='dynamic')
    expenses_paid = db.relationship('Expense', foreign_keys='Expense.paid_by_user_id', backref='paid_by', lazy='dynamic')
    cash_deliveries = db.relationship('EmployeeDelivery', foreign_keys='EmployeeDelivery.delivered_by_user_id', backref='delivered_by', lazy='dynamic')
    cash_receipts = db.relationship('EmployeeDelivery', foreign_keys='EmployeeDelivery.received_by_user_id', backref='received_by', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_owner(self):
        return self.role == 'dueño'
    
    def is_partner(self):
        return self.role == 'socia'

    def is_employee(self):
        return self.role == 'empleada'
    
    def can_view_reports(self):
        return self.role in ['dueño', 'socia']

    def can_manage_finances(self):
        return self.role in ['dueño', 'socia']

    def can_view_monthly_report(self):
        return True
        
    def can_manage_users(self):
        return self.role == 'dueño'

    def can_delete_data(self):
        return self.role == 'dueño'

    def can_manage_supplies(self):
        return True

    def get_role_display(self):
        role_names = {'dueño': 'Dueño', 'socia': 'Socia', 'empleada': 'Empleada'}
        return role_names.get(self.role, self.role.title())
    
    def get_display_name(self):
        return self.username.title()
    
    def __repr__(self):
        return f'<User {self.username}>'

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, unique=True, nullable=False)
    status = db.Column(db.String(64), index=True, nullable=False, default='Limpia')
    tier = db.Column(db.String(50), nullable=False, default='Estándar')
    notes = db.Column(db.Text)
    stays = db.relationship('Stay', backref='room', lazy='dynamic')

    def get_tier_display(self):
        tier_icons = {
            'Económica': '💰 Económica',
            'Estándar': '🏠 Estándar', 
            'Superior': '⭐ Superior',
            'Suite': '👑 Suite'
        }
        return tier_icons.get(self.tier, self.tier)

    def __repr__(self):
        return f'<Room {self.name}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(64), nullable=False, default='Pendiente')
    created_at = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Task {self.description}>'

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(128), index=True, nullable=False)
    phone_number = db.Column(db.String(32), index=True, nullable=False, unique=True)
    email = db.Column(db.String(128), index=True, unique=True)
    notes = db.Column(db.Text)
    stays = db.relationship('Stay', backref='client', lazy='dynamic')
    
    def visit_count(self):
        return self.stays.count()
    
    def total_spent(self):
        return sum(stay.total_paid() for stay in self.stays)
    
    def last_visit(self):
        last_stay = self.stays.order_by(Stay.check_in_date.desc()).first()
        return last_stay.check_in_date if last_stay else None
    
    def get_display_name(self):
        return self.full_name.title()

    def __repr__(self):
        return f'<Client {self.full_name}>'

class Stay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    check_in_date = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    check_out_date = db.Column(db.DateTime, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    booking_channel = db.Column(db.String(64), nullable=False, default='Directo')
    payments = db.relationship('Payment', backref='stay', lazy='dynamic')

    def total_paid(self):
        total = db.session.query(func.sum(Payment.amount)).filter(Payment.stay_id == self.id).scalar()
        return total or 0.0

    def __repr__(self):
        return f'<Stay of Client {self.client_id} in Room {self.room_id}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    method = db.Column(db.String(64), default='Efectivo')
    stay_id = db.Column(db.Integer, db.ForeignKey('stay.id'), nullable=False)

    def __repr__(self):
        return f'<Payment ${self.amount}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(256), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(64), index=True)
    expense_date = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    paid_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    payment_method = db.Column(db.String(32), nullable=False, default='Efectivo')
    
    def affects_cash_closure(self):
        if not self.paid_by:
            return False
        return self.paid_by.is_employee()

    def get_paid_by_display(self):
        return self.paid_by.get_display_name() if self.paid_by else "No especificado"

    def get_payment_method_display(self):
        methods = {'Efectivo': '💵 Efectivo', 'Tarjeta': '💳 Tarjeta', 'Transferencia': '🏦 Transferencia'}
        return methods.get(self.payment_method, self.payment_method)

    def __repr__(self):
        return f'<Expense ${self.amount} for {self.description}>'

class Supply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    category = db.Column(db.String(64), index=True, nullable=False)
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=5)
    unit_price = db.Column(db.Float, nullable=True)
    supplier = db.Column(db.String(128))
    notes = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock

    # --- ¡MÉTODO CORREGIDO/AÑADIDO! ---
    def stock_status(self):
        """Retorna el estado del stock como texto."""
        if self.current_stock == 0:
            return "Agotado"
        elif self.is_low_stock():
            return "Stock Bajo"
        else:
            return "Stock Normal"

    def __repr__(self):
        return f'<Supply {self.name} - Stock: {self.current_stock}>'

class CashClosure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    closure_date = db.Column(db.DateTime, index=True, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_income = db.Column(db.Float, nullable=False, default=0.0)
    total_expenses = db.Column(db.Float, nullable=False, default=0.0)
    net_amount = db.Column(db.Float, nullable=False, default=0.0)
    is_delivered = db.Column(db.Boolean, default=False)
    delivered_date = db.Column(db.DateTime, index=True)
    delivered_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    received_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relaciones explícitas
    delivered_by = db.relationship('User', foreign_keys=[delivered_by_user_id], backref='cash_deliveries_made')
    received_by = db.relationship('User', foreign_keys=[received_by_user_id], backref='cash_deliveries_received')
    
    def get_period_display(self):
        months = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        return f"{months[self.month]} {self.year}"
    
    def is_overdue(self):
        if self.is_delivered: return False
        from datetime import date
        today = date.today()
        next_month = self.month + 1 if self.month < 12 else 1
        next_year = self.year if self.month < 12 else self.year + 1
        try:
            due_date = date(next_year, next_month, 5)
            return today > due_date
        except:
            return False

    def __repr__(self):
        return f'<CashClosure {self.get_period_display()}>'

class EmployeeDelivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cash_closure_id = db.Column(db.Integer, db.ForeignKey('cash_closure.id'), nullable=False)
    delivered_amount = db.Column(db.Float, nullable=False)
    expected_amount = db.Column(db.Float, nullable=False)
    difference = db.Column(db.Float, nullable=False, default=0.0)
    delivery_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    delivered_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    received_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text)
    
    cash_closure = db.relationship('CashClosure', backref='deliveries')
    
    def get_status(self):
        if self.difference == 0: return "Exacto"
        return "Exceso" if self.difference > 0 else "Faltante"

    def __repr__(self):
        return f'<Delivery DOP {self.delivered_amount:,.2f}>'
