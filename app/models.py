from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin 
from datetime import datetime, timezone
from sqlalchemy import func
from calendar import monthrange

# FASE 4.0 V4.0: Tabla de asociación para paquetes de suministros (CORREGIDA)
room_supply_defaults = db.Table('room_supply_defaults',
    db.Column('room_id', db.Integer, db.ForeignKey('room.id'), primary_key=True),
    db.Column('supply_id', db.Integer, db.ForeignKey('supply.id'), primary_key=True),
    db.Column('quantity', db.Integer, nullable=False, default=1),
    db.Column('is_mandatory', db.Boolean, default=True),
    db.Column('usage_type', db.String(50), default='Automático'),
    db.Column('notes', db.Text),
    db.Column('created_at', db.DateTime, default=lambda: datetime.now(timezone.utc)),
    db.Column('updated_at', db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
)

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
    tier = db.Column(db.String(50), nullable=False, default='Queen')
    notes = db.Column(db.Text)
    stays = db.relationship('Stay', backref='room', lazy='dynamic')
    
    # FASE 4.0 V4.0: Relación con paquetes de suministros (corregida)
    supply_packages = db.relationship('Supply', secondary=room_supply_defaults, 
                                    backref=db.backref('room_packages', lazy='dynamic'))
    
    def get_tier_display(self):
        """Retorna el tier con iconos - ACTUALIZADO PARA QUEEN/KING"""
        tier_icons = {
            'Queen': '👸 Queen',
            'King': '👑 King'
        }
        return tier_icons.get(self.tier, f'🏨 {self.tier}')
    
    # === V4.0 YIELD MANAGEMENT METHODS ===
    def can_upgrade_to(self, other_room):
        """Verifica si esta habitación puede hacer upgrade a otra"""
        if not other_room:
            return False
        return self.tier == 'Queen' and other_room.tier == 'King'
    
    def get_tier_hierarchy_value(self):
        """Retorna valor numérico para jerarquía de habitaciones"""
        hierarchy = {'Queen': 1, 'King': 2}
        return hierarchy.get(self.tier, 0)
    
    def is_better_than(self, other_room):
        """Compara si esta habitación es mejor que otra"""
        if not other_room:
            return True
        return self.get_tier_hierarchy_value() > other_room.get_tier_hierarchy_value()
    
    def get_upgrade_candidates(self):
        """Obtiene habitaciones a las que esta puede hacer upgrade"""
        if self.tier != 'Queen':
            return []
        return Room.query.filter_by(tier='King').all()
    
    # === V4.0 MÉTODOS PARA GESTIÓN DE PAQUETES DE SUMINISTROS (ACTUALIZADOS) ===
    def get_supply_package(self):
        """Obtiene el paquete completo de suministros para esta habitación"""
        from sqlalchemy import text
        query = text("""
            SELECT s.*, rsd.quantity, rsd.is_mandatory, rsd.usage_type, rsd.notes
            FROM supply s
            JOIN room_supply_defaults rsd ON s.id = rsd.supply_id
            WHERE rsd.room_id = :room_id
        """)
        return db.session.execute(query, {'room_id': self.id}).fetchall()
    
    def get_mandatory_supplies(self):
        """Obtiene solo los suministros obligatorios"""
        from sqlalchemy import text
        query = text("""
            SELECT s.*, rsd.quantity, rsd.is_mandatory, rsd.usage_type, rsd.notes
            FROM supply s
            JOIN room_supply_defaults rsd ON s.id = rsd.supply_id
            WHERE rsd.room_id = :room_id AND rsd.is_mandatory = 1
        """)
        return db.session.execute(query, {'room_id': self.id}).fetchall()
    
    def has_supply_package(self):
        """Verifica si la habitación tiene paquete de suministros configurado"""
        return len(self.supply_packages) > 0
    
    def calculate_package_cost(self):
        """Calcula el costo total del paquete de suministros"""
        package_items = self.get_supply_package()
        total_cost = 0.0
        for item in package_items:
            if hasattr(item, 'unit_price') and item.unit_price:
                total_cost += item.quantity * item.unit_price
        return total_cost
    
    def get_package_summary(self):
        """Obtiene un resumen del paquete de suministros"""
        package = self.get_supply_package()
        if not package:
            return None
            
        mandatory_count = sum(1 for item in package if item.is_mandatory)
        optional_count = len(package) - mandatory_count
            
        return {
            'total_items': len(package),
            'mandatory_items': mandatory_count,
            'optional_items': optional_count,
            'total_cost': self.calculate_package_cost(),
            'items': package
        }

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

    # === V3.0 BUSINESS LOGIC METHODS ===
    @staticmethod
    def get_top_clients(limit=5):
        """Obtiene los clientes que más han gastado"""
        all_clients = Client.query.all()
        return sorted(all_clients, key=lambda x: x.total_spent(), reverse=True)[:limit]
    
    @staticmethod
    def get_relevant_clients_by_category(category='current'):
        """Obtiene clientes por categoría de relevancia"""
        from datetime import date, timedelta
        today = date.today()
        
        if category == 'current':
            # Clientes actualmente hospedados
            return Stay.query.filter(
                Stay.status == 'Activa',
                func.date(Stay.check_in_date) <= today,
                or_(
                    Stay.check_out_date.is_(None),
                    func.date(Stay.check_out_date) > today
                )
            ).join(Client).order_by(Client.full_name).all()
            
        elif category == 'arriving':
            # Clientes que llegan hoy
            return Stay.query.filter(
                func.date(Stay.check_in_date) == today,
                Stay.status == 'Activa'
            ).join(Client).order_by(Stay.check_in_date).all()
            
        elif category == 'departing':
            # Clientes que salen hoy
            return Stay.query.filter(
                func.date(Stay.check_out_date) == today,
                Stay.status.in_(['Activa', 'Pendiente de Cierre'])
            ).join(Client).order_by(Stay.check_out_date).all()
            
        elif category == 'recent':
            # Clientes que se fueron recientemente (últimos 7 días)
            week_ago = today - timedelta(days=7)
            return Stay.query.filter(
                Stay.status == 'Finalizada',
                func.date(Stay.check_out_date) >= week_ago,
                func.date(Stay.check_out_date) < today
            ).join(Client).order_by(Stay.check_out_date.desc()).limit(15).all()
        
        return []

    def __repr__(self):
        return f'<Client {self.full_name}>'

class Stay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    check_in_date = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    check_out_date = db.Column(db.DateTime, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    booking_channel = db.Column(db.String(64), nullable=False, default='Directo')
    status = db.Column(db.String(50), nullable=False, default='Activa')  # 'Activa', 'Pendiente de Cierre', 'Finalizada'
    payments = db.relationship('Payment', backref='stay', lazy='dynamic')

    def total_paid(self):
        total = db.session.query(func.sum(Payment.amount)).filter(Payment.stay_id == self.id).scalar()
        return total or 0.0
    
    def get_status_display(self):
        status_icons = {
            'Activa': '🟢 Activa',
            'Pendiente de Cierre': '🟡 Pendiente de Cierre',
            'Finalizada': '🔴 Finalizada'
        }
        return status_icons.get(self.status, self.status)
    
    def can_be_closed(self):
        """Determina si la estancia puede ser cerrada"""
        return self.status == 'Activa' and self.check_out_date is not None
    
    # === V3.0 MÉTODOS MEJORADOS PARA GESTIÓN DE SUMINISTROS ===
    def get_automatic_supply_usages(self):
        """Obtiene los usos automáticos de suministros para esta estancia"""
        return [usage for usage in self.supply_usages if usage.usage_type == 'Automático']
    
    def get_supply_usage_summary(self):
        """Obtiene resumen completo del uso de suministros"""
        return SupplyUsage.get_stay_usage_summary(self.id)
    
    def has_supply_usage(self):
        """Verifica si la estancia tiene uso de suministros registrado"""
        return len(self.supply_usages) > 0
    
    def apply_room_package(self, usage_type='Automático', verified_by_user_id=None):
        """Aplica el paquete de suministros de la habitación a esta estancia"""
        if not self.room:
            return []
        
        package_items = self.room.get_supply_package()
        created_usages = []
        
        for package_item in package_items:
            # Solo aplicar items automáticos o si es forzado
            if package_item.usage_type == 'Automático' or usage_type != 'Automático':
                # Verificar si ya existe uso para este suministro
                existing_usage = SupplyUsage.query.filter_by(
                    stay_id=self.id,
                    supply_id=package_item.supply_id,
                    room_supply_default_id=package_item.id
                ).first()
                
                if not existing_usage:
                    usage = SupplyUsage.create_from_package(
                        stay_id=self.id,
                        room_supply_default=package_item,
                        usage_type=usage_type,
                        verified_by_user_id=verified_by_user_id
                    )
                    created_usages.append(usage)
        
        return created_usages
    
    def calculate_supply_cost(self):
        """Calcula el costo total de suministros usados en esta estancia"""
        return sum(usage.calculate_cost() for usage in self.supply_usages)
    
    def get_supply_variances(self):
        """Obtiene las varianzas en el uso de suministros"""
        variances = []
        for usage in self.supply_usages:
            if usage.quantity_expected:
                variance = usage.get_variance()
                if variance != 0:
                    variances.append({
                        'supply_name': usage.supply.name,
                        'expected': usage.quantity_expected,
                        'used': usage.quantity_used,
                        'variance': variance,
                        'percentage': usage.get_variance_percentage()
                    })
        return variances
    
    def needs_supply_verification(self):
        """Verifica si la estancia necesita verificación de suministros"""
        unverified_count = len([u for u in self.supply_usages if not u.is_confirmed])
        variances = len(self.get_supply_variances())
        return unverified_count > 0 or variances > 0

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

    # === V3.0 BUSINESS LOGIC METHODS ===
    @staticmethod
    def get_expenses_by_period(period='today'):
        """Obtiene gastos filtrados por período"""
        from datetime import date, timedelta, datetime as dt
        today = date.today()
        
        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = today - timedelta(days=1)
        elif period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        else:
            start_date = today
            end_date = today
        
        # Convertir a datetime para la consulta
        start_datetime = dt.combine(start_date, dt.min.time())
        end_datetime = dt.combine(end_date, dt.max.time())
        
        return Expense.query.filter(
            Expense.expense_date >= start_datetime,
            Expense.expense_date <= end_datetime
        ).order_by(Expense.expense_date.desc()).all()
    
    @staticmethod
    def get_financial_summary():
        """Obtiene resumen financiero del mes actual"""
        from datetime import datetime as dt
        current_date = dt.now()
        start_of_month = dt(current_date.year, current_date.month, 1)
        
        # Ingresos del mes
        monthly_income = db.session.query(func.sum(Payment.amount)).filter(
            Payment.payment_date >= start_of_month
        ).scalar() or 0.0
        
        # Gastos por tipo de usuario
        elizabeth_expenses = db.session.query(func.sum(Expense.amount)).join(User).filter(
            User.role == 'empleada',
            Expense.expense_date >= start_of_month
        ).scalar() or 0.0
        
        alejandrina_expenses = db.session.query(func.sum(Expense.amount)).join(User).filter(
            User.role == 'socia',
            Expense.expense_date >= start_of_month
        ).scalar() or 0.0
        
        owner_expenses = db.session.query(func.sum(Expense.amount)).join(User).filter(
            User.role == 'dueño',
            Expense.expense_date >= start_of_month
        ).scalar() or 0.0
        
        total_expenses = elizabeth_expenses + alejandrina_expenses + owner_expenses
        monthly_profit = monthly_income - total_expenses
        
        return {
            'monthly_income': monthly_income,
            'elizabeth_expenses': elizabeth_expenses,
            'alejandrina_expenses': alejandrina_expenses,
            'owner_expenses': owner_expenses,
            'total_expenses': total_expenses,
            'monthly_profit': monthly_profit
        }

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

    # === V3.0 BUSINESS LOGIC METHODS ===
    @staticmethod
    def get_inventory_status():
        """Obtiene el estado completo del inventario con alertas"""
        supplies = Supply.query.all()
        
        critical_count = 0
        warning_count = 0
        alerts = []
        
        for supply in supplies:
            if supply.current_stock <= supply.minimum_stock:
                critical_count += 1
                alerts.append({
                    'id': supply.id,
                    'name': supply.name,
                    'category': supply.category,
                    'current_stock': supply.current_stock,
                    'minimum_stock': supply.minimum_stock,
                    'status': 'critical'
                })
            elif supply.current_stock <= (supply.minimum_stock * 1.5):
                warning_count += 1
                alerts.append({
                    'id': supply.id,
                    'name': supply.name,
                    'category': supply.category,
                    'current_stock': supply.current_stock,
                    'minimum_stock': supply.minimum_stock,
                    'status': 'warning'
                })
        
        # Ordenar alertas por criticidad
        alerts.sort(key=lambda x: (x['status'] == 'warning', x['current_stock']))
        
        return {
            'critical_count': critical_count,
            'warning_count': warning_count,
            'alerts': alerts
        }
    
    @staticmethod
    def get_low_stock_supplies():
        """Obtiene suministros con stock bajo"""
        return Supply.query.filter(Supply.current_stock <= Supply.minimum_stock).all()

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

class SupplyUsage(db.Model):
    """FASE 2 V3.0: Modelo mejorado para registrar el uso de suministros con mayor detalle"""
    id = db.Column(db.Integer, primary_key=True)
    supply_id = db.Column(db.Integer, db.ForeignKey('supply.id'), nullable=False)
    stay_id = db.Column(db.Integer, db.ForeignKey('stay.id'), nullable=True)  # Nullable para uso manual
    # V4.0: RoomSupplyDefault eliminado, ahora es tabla de asociación
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True)  # Habitación relacionada
    quantity_used = db.Column(db.Integer, nullable=False)
    quantity_expected = db.Column(db.Integer, nullable=True)  # Cantidad esperada según paquete
    usage_type = db.Column(db.String(50), nullable=False)  # 'Automático', 'Verificado', 'Manual', 'Ajuste', 'Devolución'
    usage_source = db.Column(db.String(50), default='Estancia')  # 'Estancia', 'Mantenimiento', 'Limpieza', 'Inventario'
    usage_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    verified_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    cost_per_unit = db.Column(db.Float, nullable=True)  # Costo unitario al momento del uso
    total_cost = db.Column(db.Float, nullable=True)  # Costo total calculado
    is_confirmed = db.Column(db.Boolean, default=False)  # Si el uso ha sido confirmado
    notes = db.Column(db.Text)

    # Relaciones
    supply = db.relationship('Supply', backref='usage_logs')
    stay = db.relationship('Stay', backref='supply_usages')
    verified_by = db.relationship('User', backref='supply_verifications')
    room = db.relationship('Room', backref='supply_usages')
    
    def get_usage_type_display(self):
        usage_icons = {
            'Automático': '🤖 Automático',
            'Verificado': '✅ Verificado',
            'Manual': '✋ Manual',
            'Ajuste': '🔧 Ajuste',
            'Devolución': '↩️ Devolución'
        }
        return usage_icons.get(self.usage_type, self.usage_type)
    
    def get_usage_source_display(self):
        source_icons = {
            'Estancia': '🏨 Estancia',
            'Mantenimiento': '🔧 Mantenimiento',
            'Limpieza': '🧹 Limpieza',
            'Inventario': '📦 Inventario'
        }
        return source_icons.get(self.usage_source, self.usage_source)
    
    def calculate_cost(self):
        """Calcula el costo total basado en la cantidad y precio"""
        if self.cost_per_unit:
            return self.quantity_used * self.cost_per_unit
        elif self.supply and self.supply.unit_price:
            return self.quantity_used * self.supply.unit_price
        return 0.0
    
    def get_variance(self):
        """Calcula la varianza entre cantidad esperada y usada"""
        if self.quantity_expected:
            return self.quantity_used - self.quantity_expected
        return 0
    
    def get_variance_percentage(self):
        """Calcula el porcentaje de varianza"""
        if self.quantity_expected and self.quantity_expected > 0:
            variance = self.get_variance()
            return (variance / self.quantity_expected) * 100
        return 0
    
    def is_over_expected(self):
        """Verifica si se usó más de lo esperado"""
        return self.get_variance() > 0
    
    def is_under_expected(self):
        """Verifica si se usó menos de lo esperado"""
        return self.get_variance() < 0
    
    def get_status_display(self):
        """Retorna el estado del uso con iconos"""
        if not self.quantity_expected:
            return "📊 Sin referencia"
        
        variance = self.get_variance()
        if variance == 0:
            return "✅ Exacto"
        elif variance > 0:
            return f"⚠️ Exceso (+{variance})"
        else:
            return f"⬇️ Menor ({variance})"
    
    # === MÉTODOS ESTÁTICOS PARA ANÁLISIS ===
    @staticmethod
    def create_from_package(stay_id, package_item, usage_type='Automático', verified_by_user_id=None):
        """V4.0: Crea un registro de uso basado en datos del paquete de habitación"""
        # package_item ahora es un resultado de query que contiene los datos
        usage = SupplyUsage(
            supply_id=package_item.id,  # ID del suministro
            stay_id=stay_id,
            room_id=package_item.room_id if hasattr(package_item, 'room_id') else None,
            quantity_used=package_item.quantity,
            quantity_expected=package_item.quantity,
            usage_type=usage_type,
            usage_source='Estancia',
            verified_by_user_id=verified_by_user_id,
            cost_per_unit=package_item.unit_price if hasattr(package_item, 'unit_price') else None
        )
        usage.total_cost = usage.calculate_cost()
        return usage
    
    @staticmethod
    def get_stay_usage_summary(stay_id):
        """Obtiene resumen de uso de suministros para una estancia"""
        usages = SupplyUsage.query.filter_by(stay_id=stay_id).all()
        
        return {
            'total_items': len(usages),
            'total_cost': sum(usage.calculate_cost() for usage in usages),
            'automatic_count': len([u for u in usages if u.usage_type == 'Automático']),
            'verified_count': len([u for u in usages if u.is_confirmed]),
            'over_expected_count': len([u for u in usages if u.is_over_expected()]),
            'under_expected_count': len([u for u in usages if u.is_under_expected()]),
            'usages': usages
        }
    
    @staticmethod
    def get_supply_usage_stats(supply_id, days=30):
        """Obtiene estadísticas de uso para un suministro específico"""
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        usages = SupplyUsage.query.filter(
            SupplyUsage.supply_id == supply_id,
            SupplyUsage.usage_date >= cutoff_date
        ).all()
        
        if not usages:
            return None
            
        total_used = sum(usage.quantity_used for usage in usages)
        average_per_use = total_used / len(usages) if usages else 0
        
        return {
            'total_used': total_used,
            'usage_count': len(usages),
            'average_per_use': average_per_use,
            'total_cost': sum(usage.calculate_cost() for usage in usages),
            'last_used': max(usage.usage_date for usage in usages) if usages else None
        }

    def __repr__(self):
        return f'<SupplyUsage {self.supply.name if self.supply else "Unknown"}: {self.quantity_used} ({self.usage_type})>'


# === V3.0 BUSINESS STATISTICS CLASS ===
class DashboardStats:
    """Clase para manejar todas las estadísticas del dashboard de manera centralizada"""
    
    @staticmethod
    def get_panel_statistics():
        """Obtiene todas las estadísticas necesarias para el panel de control"""
        # Estadísticas básicas
        total_clients = Client.query.count()
        active_stays = Stay.query.filter(Stay.status == 'Activa').count()
        pending_closure_stays = Stay.query.filter(Stay.status == 'Pendiente de Cierre').all()
        
        # Inventario
        inventory_status = Supply.get_inventory_status()
        low_stock_supplies = Supply.get_low_stock_supplies()
        
        # Finanzas
        financial_summary = Expense.get_financial_summary()
        
        # Top clientes
        top_clients = Client.get_top_clients(5)
        
        # Datos para formularios
        clients = Client.query.order_by(Client.full_name).all()
        rooms = Room.query.order_by(Room.name).all()
        users = User.query.all()
        supplies = Supply.query.order_by(Supply.name).all()
        
        # Datos recientes
        recent_stays = Stay.query.order_by(Stay.check_in_date.desc()).limit(15).all()
        recent_expenses = Expense.query.order_by(Expense.expense_date.desc()).limit(15).all()
        
        return {
            # Estadísticas básicas
            'total_clients': total_clients,
            'active_stays': active_stays,
            'pending_closure_stays': pending_closure_stays,
            'low_stock_count': inventory_status['critical_count'],
            'low_stock_supplies': low_stock_supplies,
            
            # Finanzas
            'monthly_income': financial_summary['monthly_income'],
            'monthly_expenses': financial_summary['total_expenses'],
            'elizabeth_expenses': financial_summary['elizabeth_expenses'],
            'alejandrina_expenses': financial_summary['alejandrina_expenses'],
            'owner_expenses': financial_summary['owner_expenses'],
            'total_expenses': financial_summary['total_expenses'],
            'monthly_profit': financial_summary['monthly_profit'],
            
            # Clientes y datos
            'top_clients': top_clients,
            'clients': clients,
            'rooms': rooms,
            'users': users,
            'supplies': supplies,
            'recent_stays': recent_stays,
            'recent_expenses': recent_expenses
        }
