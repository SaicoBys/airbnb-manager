from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import func, extract, or_
from datetime import datetime
from calendar import monthrange
from collections import Counter

from app.extensions import db
from app.forms import LoginForm, ClientForm, ExpenseForm, StayForm, PaymentForm, SupplyForm, UpdateStockForm, UnifiedStayForm, CashClosureForm, EmployeeDeliveryForm, MonthYearForm
from app.models import User, Room, Task, Client, Expense, Stay, Payment, Supply, CashClosure, EmployeeDelivery, SupplyUsage
from app.decorators import role_required, owner_required, management_required, permission_required, log_user_action

bp = Blueprint('main', __name__)

# =====================================================================
# RUTA PRINCIPAL (PANEL DE CONTROL UNIFICADO)
# =====================================================================

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    """Panel de Control Unificado v3.0 - Lógica de negocio centralizada en modelos"""
    from app.models import DashboardStats
    
    # Obtener todas las estadísticas desde la clase centralizada
    stats = DashboardStats.get_panel_statistics()
    
    return render_template('control_panel.html', 
                         title='Panel de Control',
                         **stats)

# =====================================================================
# RUTAS DE REPORTES Y ANÁLISIS
# =====================================================================

@bp.route('/reports')
@login_required
@permission_required('can_view_reports')
def reports():
    total_income_dop = db.session.query(func.sum(Payment.amount)).scalar() or 0.0
    total_expenses_dop = db.session.query(func.sum(Expense.amount)).scalar() or 0.0
    profit_dop = total_income_dop - total_expenses_dop
    
    exchange_rate = current_app.config.get('TASA_CAMBIO_DOP_USD', 1.0)
    total_income_usd = total_income_dop / exchange_rate if exchange_rate > 0 else 0
    total_expenses_usd = total_expenses_dop / exchange_rate if exchange_rate > 0 else 0
    profit_usd = profit_dop / exchange_rate if exchange_rate > 0 else 0

    income_by_room_query = db.session.query(Room.name, func.sum(Payment.amount).label('total_generated')).select_from(Payment).join(Stay).join(Room).group_by(Room.name).order_by(func.sum(Payment.amount).desc()).all()
    income_chart_labels = [row.name for row in income_by_room_query]
    income_chart_data = [row.total_generated for row in income_by_room_query]

    expenses_by_category_query = db.session.query(Expense.category, func.sum(Expense.amount).label('total_spent')).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()
    expense_chart_labels = [row.category for row in expenses_by_category_query]
    expense_chart_data = [row.total_spent for row in expenses_by_category_query]

    current_year = datetime.utcnow().year
    monthly_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    income_by_month_query = db.session.query(extract('month', Payment.payment_date).label('month'), func.sum(Payment.amount)).filter(extract('year', Payment.payment_date) == current_year).group_by('month').all()
    monthly_income_data = [0] * 12
    for row in income_by_month_query: monthly_income_data[row.month - 1] = row[1]

    expense_by_month_query = db.session.query(extract('month', Expense.expense_date).label('month'), func.sum(Expense.amount)).filter(extract('year', Expense.expense_date) == current_year).group_by('month').all()
    monthly_expense_data = [0] * 12
    for row in expense_by_month_query: monthly_expense_data[row.month - 1] = row[1]

    monthly_profit_data = [(inc - exp) for inc, exp in zip(monthly_income_data, monthly_expense_data)]
    
    client_frequency = db.session.query(Client.full_name, func.count(Stay.id).label('stay_count')).join(Stay).group_by(Client.full_name).order_by(func.count(Stay.id).desc()).all()

    return render_template('reports.html', title='Reporte Financiero', total_income_dop=total_income_dop, total_expenses_dop=total_expenses_dop, profit_dop=profit_dop, total_income_usd=total_income_usd, total_expenses_usd=total_expenses_usd, profit_usd=profit_usd, income_by_room=income_by_room_query, income_chart_labels=income_chart_labels, income_chart_data=income_chart_data, expense_chart_labels=expense_chart_labels, expense_chart_data=expense_chart_data, monthly_labels=monthly_labels, monthly_income_data=monthly_income_data, monthly_expense_data=monthly_expense_data, monthly_profit_data=monthly_profit_data, client_frequency=client_frequency)

@bp.route('/monthly_report')
@login_required
@permission_required('can_view_monthly_report')
def monthly_report():
    year = datetime.utcnow().year
    month = datetime.utcnow().month
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)

    incomes = Payment.query.filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date).order_by(Payment.payment_date.desc()).all()
    expenses = Expense.query.filter(Expense.expense_date >= start_date, Expense.expense_date <= end_date).order_by(Expense.expense_date.desc()).all()
    employee_expenses = [e for e in expenses if e.affects_cash_closure()]

    total_income_dop = sum(p.amount for p in incomes)
    total_expenses_dop = sum(e.amount for e in employee_expenses)
    profit_dop = total_income_dop - total_expenses_dop

    exchange_rate = current_app.config.get('TASA_CAMBIO_DOP_USD', 1.0)
    total_income_usd = total_income_dop / exchange_rate if exchange_rate > 0 else 0
    total_expenses_usd = total_expenses_dop / exchange_rate if exchange_rate > 0 else 0
    profit_usd = total_income_usd - total_expenses_usd
    
    total_all_expenses_dop = sum(e.amount for e in expenses)
    
    return render_template(
        'monthly_report.html',
        title='Reporte de Cierre de Mes',
        incomes=incomes,
        expenses=expenses,
        employee_expenses=employee_expenses,
        total_income_dop=total_income_dop,
        total_expenses_dop=total_expenses_dop,
        total_all_expenses_dop=total_all_expenses_dop,
        profit_dop=profit_dop,
        total_income_usd=total_income_usd,
        total_expenses_usd=total_expenses_usd,
        profit_usd=profit_usd,
        report_month=start_date.strftime('%B %Y')
    )

# =====================================================================
# FUNCIONES AUXILIARES
# =====================================================================

def clean_phone(phone_number):
    """Limpia el número de teléfono eliminando caracteres no numéricos."""
    if not phone_number:
        return ""
    import re
    return re.sub(r'[^\d]', '', phone_number)

def check_room_availability(check_in, check_out):
    """Verifica qué habitaciones están ocupadas en el rango de fechas dado."""
    if not check_in or not check_out:
        return []
    
    # Buscar estancias que se solapen con el rango de fechas
    overlapping_stays = Stay.query.filter(
        Stay.check_in_date < check_out,
        or_(
            Stay.check_out_date.is_(None),  # Estancias sin check-out
            Stay.check_out_date > check_in
        )
    ).all()
    
    return [stay.room_id for stay in overlapping_stays]

def find_booking_solutions(check_in, check_out):
    """Encuentra soluciones de reserva para el rango de fechas dado."""
    unavailable_room_ids = check_room_availability(check_in, check_out)
    all_rooms = Room.query.all()
    
    solutions = []
    
    # Solución 1: Habitaciones completamente libres
    available_rooms = [room for room in all_rooms if room.id not in unavailable_room_ids]
    if available_rooms:
        for room in available_rooms:
            solutions.append({
                'type': 'single',
                'room_id': room.id,
                'room_name': room.name,
                'tier': room.tier,
                'total_nights': (check_out - check_in).days
            })
    
    # Solución 2: Habitaciones divididas (implementación básica)
    if not available_rooms:
        # Para implementación avanzada: buscar combinaciones de habitaciones
        solutions.append({
            'type': 'split_needed',
            'message': 'No hay habitaciones disponibles para todo el período. Se requiere división de estancia.'
        })
    
    return solutions

def deduct_automatic_supplies(stay):
    """Deduce automáticamente los suministros por defecto de una habitación"""
    try:
        # Obtener el paquete de suministros por defecto de la habitación
        package_data = db.session.execute(
            db.text("""
                SELECT supply_id, quantity 
                FROM room_supply_defaults 
                WHERE room_id = :room_id
            """),
            {"room_id": stay.room_id}
        ).fetchall()
        
        if not package_data:
            # No hay paquete configurado, salir silenciosamente
            return
        
        for supply_id, quantity in package_data:
            supply = Supply.query.get(supply_id)
            if supply and supply.current_stock >= quantity:
                # Crear registro de uso automático
                usage = SupplyUsage(
                    supply_id=supply_id,
                    stay_id=stay.id,
                    quantity_used=quantity,
                    usage_type='Automático',
                    usage_date=datetime.now()
                )
                db.session.add(usage)
                
                # Decrementar stock
                supply.current_stock -= quantity
                supply.last_updated = datetime.now()
                
                log_user_action("Deducción automática de suministros", 
                              f"{supply.name}: -{quantity} (Estancia #{stay.id})")
            else:
                # Stock insuficiente - crear alerta o log
                if supply:
                    log_user_action("Alerta: Stock insuficiente", 
                                  f"{supply.name}: Necesario {quantity}, Disponible {supply.current_stock}")
                
    except Exception as e:
        # Log del error pero no fallar la creación de estancia
        log_user_action("Error en deducción automática", str(e))

# =====================================================================
# RUTAS AJAX PARA EL SISTEMA UNIFICADO
# =====================================================================

@bp.route('/ajax/get_client_by_phone', methods=['POST'])
@login_required
def get_client_by_phone():
    """Busca un cliente por número de teléfono."""
    try:
        phone_number = request.form.get('phone_number', '').strip()
        if not phone_number:
            return jsonify({'success': False, 'message': 'Número de teléfono requerido'})
        
        # Limpiar el número de teléfono
        cleaned_phone = clean_phone(phone_number)
        
        # Buscar cliente
        client = Client.query.filter_by(phone_number=cleaned_phone).first()
        
        if client:
            return jsonify({
                'success': True,
                'found': True,
                'client': {
                    'id': client.id,
                    'name': client.full_name,
                    'email': client.email or '',
                    'notes': client.notes or '',
                    'visit_count': client.visit_count(),
                    'total_spent': client.total_spent()
                }
            })
        else:
            return jsonify({
                'success': True,
                'found': False,
                'message': 'Cliente no encontrado. Puedes crear uno nuevo.'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al buscar cliente: {str(e)}'})

@bp.route('/ajax/get_room_availability', methods=['POST'])
@login_required
def get_room_availability():
    """Verifica disponibilidad de habitaciones para fechas específicas."""
    try:
        check_in_str = request.form.get('check_in')
        check_out_str = request.form.get('check_out')
        
        if not check_in_str or not check_out_str:
            return jsonify({'success': False, 'message': 'Fechas de check-in y check-out requeridas'})
        
        # Convertir fechas
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        
        if check_in >= check_out:
            return jsonify({'success': False, 'message': 'La fecha de check-out debe ser posterior al check-in'})
        
        # Obtener habitaciones ocupadas
        unavailable_room_ids = check_room_availability(check_in, check_out)
        
        # Obtener información de todas las habitaciones
        all_rooms = Room.query.all()
        rooms_info = []
        
        for room in all_rooms:
            rooms_info.append({
                'id': room.id,
                'name': room.name,
                'tier': room.tier,
                'tier_display': room.get_tier_display(),
                'available': room.id not in unavailable_room_ids
            })
        
        return jsonify({
            'success': True,
            'unavailable_room_ids': unavailable_room_ids,
            'rooms': rooms_info,
            'total_nights': (check_out - check_in).days
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al verificar disponibilidad: {str(e)}'})

@bp.route('/ajax/find_booking_solutions', methods=['POST'])
@login_required  
def find_booking_solutions_endpoint():
    """Encuentra soluciones inteligentes de reserva."""
    try:
        check_in_str = request.form.get('check_in')
        check_out_str = request.form.get('check_out')
        
        if not check_in_str or not check_out_str:
            return jsonify({'success': False, 'message': 'Fechas requeridas'})
        
        # Convertir fechas
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        
        # Encontrar soluciones
        solutions = find_booking_solutions(check_in, check_out)
        
        return jsonify({
            'success': True,
            'solutions': solutions,
            'check_in': check_in_str,
            'check_out': check_out_str,
            'total_nights': (check_out - check_in).days
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al encontrar soluciones: {str(e)}'})

# =====================================================================
# RUTAS AJAX PARA EL PANEL DE CONTROL (Legacy)
# =====================================================================

@bp.route('/ajax/add_client', methods=['POST'])
@login_required
def add_client_ajax():
    try:
        full_name = request.form.get('full_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        email = request.form.get('email', '').strip() or None
        
        if not full_name or not phone_number:
            return jsonify({'success': False, 'message': 'Nombre y teléfono son requeridos'})
        
        if Client.query.filter_by(phone_number=phone_number).first():
            return jsonify({'success': False, 'message': 'Ya existe un cliente con ese teléfono'})
        
        client = Client(full_name=full_name, phone_number=phone_number, email=email)
        db.session.add(client)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Cliente {full_name} agregado exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al agregar cliente: {str(e)}'})

@bp.route('/ajax/add_stay', methods=['POST'])
@login_required
def add_stay_ajax():
    try:
        stay = Stay(
            client_id=int(request.form.get('client_id')),
            room_id=int(request.form.get('room_id')),
            check_in_date=datetime.fromisoformat(request.form.get('check_in_date').replace('T', ' ')),
            check_out_date=datetime.fromisoformat(request.form.get('check_out_date').replace('T', ' ')) if request.form.get('check_out_date') else None,
            booking_channel=request.form.get('booking_channel', 'Directo')
        )
        db.session.add(stay)
        db.session.commit()
        client = Client.query.get(stay.client_id)
        room = Room.query.get(stay.room_id)
        return jsonify({'success': True, 'message': f'Estancia creada para {client.full_name} en {room.name}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al crear estancia: {str(e)}'})

@bp.route('/ajax/add_expense', methods=['POST'])
@login_required
def add_expense_ajax():
    try:
        expense = Expense(
            description=request.form.get('description', '').strip(),
            amount=float(request.form.get('amount')),
            category=request.form.get('category', 'Limpieza'),
            payment_method=request.form.get('payment_method', 'Efectivo'),
            paid_by_user_id=int(request.form.get('paid_by_user_id')),
            expense_date=datetime.now()
        )
        db.session.add(expense)
        db.session.commit()
        user = User.query.get(expense.paid_by_user_id)
        return jsonify({'success': True, 'message': f'Gasto de DOP {expense.amount} registrado para {user.get_display_name()}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al registrar gasto: {str(e)}'})

@bp.route('/ajax/update_stock', methods=['POST'])
@login_required
def update_stock_ajax():
    try:
        supply = Supply.query.get_or_404(int(request.form.get('supply_id')))
        old_stock = supply.current_stock
        change = int(request.form.get('quantity_change'))
        new_stock = old_stock + change
        
        if new_stock < 0:
            return jsonify({'success': False, 'message': 'El stock no puede ser negativo'})
            
        supply.current_stock = new_stock
        supply.last_updated = datetime.now()
        db.session.commit()
        return jsonify({'success': True, 'message': f'Stock de {supply.name} actualizado: {old_stock} → {new_stock}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al actualizar stock: {str(e)}'})

# =====================================================================
# RUTAS DE AUTENTICACIÓN
# =====================================================================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.index'))
    return render_template('login.html', title='Iniciar Sesión', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado la sesión.', 'info')
    return redirect(url_for('main.login'))

# =====================================================================
# RUTAS DE GESTIÓN (Legacy - mantenidas para compatibilidad)
# =====================================================================

# === Obsolete routes removed after v2.0 migration ===

@bp.route('/add_payment/<int:stay_id>', methods=['GET', 'POST'])
@login_required
def add_payment(stay_id):
    stay = Stay.query.get_or_404(stay_id)
    form = PaymentForm()
    if form.validate_on_submit():
        payment = Payment(
            amount=form.amount.data,
            method=form.method.data,
            stay_id=stay.id
        )
        db.session.add(payment)
        db.session.commit()
        flash(f'Pago de DOP {payment.amount:,.2f} registrado para {stay.client.full_name}', 'success')
        log_user_action("Registró pago", f"DOP {payment.amount:,.2f} - {payment.method} para {stay.client.full_name}")
        return redirect(url_for('main.stays'))
    return render_template('add_payment.html', title='Añadir Pago', form=form, stay=stay)

@bp.route('/quick_stay', methods=['GET', 'POST'])
@login_required
def quick_stay():
    """Formulario unificado SPA para registro inteligente de estancias."""
    from app.forms import UnifiedStayForm
    
    form = UnifiedStayForm()
    
    # Llenar opciones de habitaciones
    rooms = Room.query.order_by(Room.name).all()
    form.room_selection.choices = [(room.id, f"{room.name} - {room.get_tier_display()}") for room in rooms]
    
    if request.method == 'POST':
        # Determinar qué botón fue presionado
        action = request.form.get('action', '')
        
        if action == 'save_client_only':
            return save_client_only(form)
        elif action == 'save_full_stay':
            return save_unified_stay(form)
        else:
            # Validación estándar del formulario
            if form.validate_on_submit():
                return save_unified_stay(form)
    
    return render_template('quick_stay.html', title='Registro Unificado de Estancia', form=form, rooms=rooms)

def save_client_only(form):
    """Guarda solo el cliente sin crear estancia."""
    try:
        phone_cleaned = clean_phone(form.phone_search.data)
        
        # Buscar o crear cliente
        client = Client.query.filter_by(phone_number=phone_cleaned).first()
        if not client:
            client = Client(
                full_name=form.client_name.data,
                phone_number=phone_cleaned,
                email=form.client_email.data,
                notes=form.client_notes.data
            )
            db.session.add(client)
        else:
            # Actualizar cliente existente
            client.full_name = form.client_name.data
            client.email = form.client_email.data
            if form.client_notes.data:
                client.notes = (client.notes or '') + f"\n{datetime.now().strftime('%Y-%m-%d')}: {form.client_notes.data}"
        
        db.session.commit()
        
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': True, 'message': f'Cliente {client.full_name} guardado exitosamente'})
        else:
            flash(f'Cliente {client.full_name} guardado exitosamente', 'success')
            return redirect(url_for('main.quick_stay'))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': f'Error al guardar cliente: {str(e)}'})
        else:
            flash(f'Error al guardar cliente: {str(e)}', 'danger')
            return render_template('quick_stay.html', title='Registro Unificado de Estancia', form=form)

def save_unified_stay(form):
    """Guarda estancia completa con cliente y pago."""
    try:
        phone_cleaned = clean_phone(form.phone_search.data)
        
        # 1. Crear o actualizar cliente
        client = Client.query.filter_by(phone_number=phone_cleaned).first()
        if not client:
            client = Client(
                full_name=form.client_name.data,
                phone_number=phone_cleaned,
                email=form.client_email.data,
                notes=form.client_notes.data
            )
            db.session.add(client)
        else:
            client.full_name = form.client_name.data
            client.email = form.client_email.data
            if form.client_notes.data:
                client.notes = (client.notes or '') + f"\n{datetime.now().strftime('%Y-%m-%d')}: {form.client_notes.data}"
        
        # 2. Crear estancia
        stay = Stay(
            client=client,
            room_id=form.room_selection.data,
            check_in_date=form.check_in_date.data,
            check_out_date=form.check_out_date.data,
            booking_channel=form.booking_channel.data
        )
        db.session.add(stay)
        
        # 3. Crear pago
        payment = Payment(
            amount=form.payment_amount.data,
            method=form.payment_method.data,
            stay=stay
        )
        db.session.add(payment)
        
        # 4. Deducir suministros automáticamente
        deduct_automatic_supplies(stay)
        
        db.session.commit()
        
        # 4. Logging
        log_user_action("Registro unificado de estancia", 
                       f"Cliente: {client.full_name}, Habitación: {stay.room.name}, Pago: DOP {payment.amount:,.2f}")
        
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': True, 
                'message': f'Estancia registrada para {client.full_name}. Pago: DOP {payment.amount:,.2f}'
            })
        else:
            flash(f'¡Estancia registrada para {client.full_name}! Pago de DOP {payment.amount:,.2f} registrado.', 'success')
            return redirect(url_for('main.stays'))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': f'Error al guardar estancia: {str(e)}'})
        else:
            flash(f'Error al guardar estancia: {str(e)}', 'danger')
            return render_template('quick_stay.html', title='Registro Unificado de Estancia', form=form)

@bp.route('/supplies')
@login_required
def supplies():
    all_supplies = Supply.query.order_by(Supply.category, Supply.name).all()
    low_stock_supplies = [s for s in all_supplies if s.is_low_stock()]
    normal_stock_supplies = [s for s in all_supplies if not s.is_low_stock()]
    return render_template('supplies.html', title='Gestión de Suministros', 
                         supplies=all_supplies, 
                         low_stock_supplies=low_stock_supplies,
                         normal_stock_supplies=normal_stock_supplies)

@bp.route('/add_supply', methods=['GET', 'POST'])
@login_required
def add_supply():
    form = SupplyForm()
    if form.validate_on_submit():
        existing_supply = Supply.query.filter_by(name=form.name.data).first()
        if existing_supply:
            flash('Ya existe un suministro con ese nombre.', 'danger')
            return redirect(url_for('main.add_supply'))
        
        new_supply = Supply(
            name=form.name.data,
            category=form.category.data,
            current_stock=form.current_stock.data,
            minimum_stock=form.minimum_stock.data,
            unit_price=form.unit_price.data,
            supplier=form.supplier.data,
            notes=form.notes.data
        )
        db.session.add(new_supply)
        db.session.commit()
        flash(f'¡Suministro "{new_supply.name}" registrado con éxito!', 'success')
        return redirect(url_for('main.supplies'))
    return render_template('add_supply.html', title='Añadir Suministro', form=form)

# =====================================================================
# RUTAS DE GESTIÓN DE CAJA
# =====================================================================

@bp.route('/cash_closures')
@login_required
@permission_required('can_manage_finances')
def cash_closures():
    all_closures = CashClosure.query.order_by(CashClosure.year.desc(), CashClosure.month.desc()).all()
    overdue_closures = [c for c in all_closures if c.is_overdue()]
    pending_closures = [c for c in all_closures if not c.is_delivered and not c.is_overdue()]
    return render_template('cash_closures.html', title='Cierres de Caja', 
                         closures=all_closures, 
                         overdue_closures=overdue_closures,
                         pending_closures=pending_closures)

@bp.route('/create_cash_closure', methods=['GET', 'POST'])
@login_required
@permission_required('can_manage_finances')
def create_cash_closure():
    form = CashClosureForm()
    if form.validate_on_submit():
        existing_closure = CashClosure.query.filter_by(month=form.month.data, year=form.year.data).first()
        if existing_closure:
            flash('Ya existe un cierre para ese mes y año.', 'danger')
            return redirect(url_for('main.create_cash_closure'))
        
        # Calcular totales del mes
        start_date = datetime(form.year.data, form.month.data, 1)
        end_date = datetime(form.year.data, form.month.data, monthrange(form.year.data, form.month.data)[1], 23, 59, 59)
        
        monthly_income = db.session.query(func.sum(Payment.amount)).filter(
            Payment.payment_date >= start_date, 
            Payment.payment_date <= end_date
        ).scalar() or 0.0
        
        monthly_expenses = db.session.query(func.sum(Expense.amount)).join(User).filter(
            User.role == 'empleada',
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        ).scalar() or 0.0
        
        new_closure = CashClosure(
            closure_date=datetime.now(),
            month=form.month.data,
            year=form.year.data,
            total_income=monthly_income,
            total_expenses=monthly_expenses,
            net_amount=monthly_income - monthly_expenses,
            notes=form.notes.data
        )
        db.session.add(new_closure)
        db.session.commit()
        flash(f'Cierre de caja creado para {new_closure.get_period_display()}', 'success')
        return redirect(url_for('main.cash_closures'))
    return render_template('create_cash_closure.html', title='Crear Cierre de Caja', form=form)

@bp.route('/view_cash_closure/<int:closure_id>')
@login_required
@permission_required('can_manage_finances')
def view_cash_closure(closure_id):
    closure = CashClosure.query.get_or_404(closure_id)
    return render_template('view_cash_closure.html', title=f'Cierre {closure.get_period_display()}', closure=closure)

@bp.route('/deliver_cash/<int:closure_id>', methods=['GET', 'POST'])
@login_required
@permission_required('can_manage_finances')
def deliver_cash(closure_id):
    closure = CashClosure.query.get_or_404(closure_id)
    form = EmployeeDeliveryForm()
    if form.validate_on_submit():
        delivery = EmployeeDelivery(
            cash_closure_id=closure.id,
            delivered_amount=form.delivered_amount.data,
            expected_amount=closure.net_amount,
            difference=form.delivered_amount.data - closure.net_amount,
            delivered_by_user_id=current_user.id,
            received_by_user_id=User.query.filter_by(role='dueño').first().id,
            notes=form.notes.data
        )
        closure.is_delivered = True
        closure.delivered_date = datetime.now()
        db.session.add(delivery)
        db.session.commit()
        flash(f'Entrega registrada para {closure.get_period_display()}', 'success')
        return redirect(url_for('main.cash_closures'))
    return render_template('deliver_cash.html', title='Entregar Efectivo', form=form, closure=closure)

# =====================================================================
# RUTAS DE GESTIÓN DE HABITACIONES Y TAREAS
# =====================================================================

@bp.route('/update_room_status/<int:room_id>', methods=['POST'])
@login_required
def update_room_status(room_id):
    room = Room.query.get_or_404(room_id)
    new_status = request.form.get('status')
    if new_status in ['Limpia', 'Sucia', 'Mantenimiento', 'Ocupada']:
        room.status = new_status
        db.session.commit()
        flash(f'Estado de {room.name} actualizado a {new_status}', 'success')
    else:
        flash('Estado inválido', 'danger')
    return redirect(url_for('main.index'))

@bp.route('/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = 'Completada'
    db.session.commit()
    flash(f'Tarea "{task.description}" marcada como completada', 'success')
    return redirect(url_for('main.index'))

# =====================================================================
# RUTAS DE GESTIÓN DE SUMINISTROS
# =====================================================================

@bp.route('/update_stock/<int:supply_id>', methods=['GET', 'POST'])
@login_required
def update_stock(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    form = UpdateStockForm()
    if form.validate_on_submit():
        old_stock = supply.current_stock
        supply.current_stock = form.current_stock.data
        supply.last_updated = datetime.now()
        if form.notes.data:
            supply.notes = (supply.notes or '') + f"\n{datetime.now().strftime('%Y-%m-%d')}: {form.notes.data}"
        db.session.commit()
        flash(f'Stock de {supply.name} actualizado: {old_stock} → {supply.current_stock}', 'success')
        log_user_action("Actualizó stock", f"{supply.name}: {old_stock} → {supply.current_stock}")
        return redirect(url_for('main.supplies'))
    
    form.current_stock.data = supply.current_stock
    return render_template('update_stock.html', title='Actualizar Stock', form=form, supply=supply)

@bp.route('/edit_supply/<int:supply_id>', methods=['GET', 'POST'])
@login_required
def edit_supply(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    form = SupplyForm(obj=supply)
    if form.validate_on_submit():
        form.populate_obj(supply)
        supply.last_updated = datetime.now()
        db.session.commit()
        flash(f'Suministro {supply.name} actualizado exitosamente', 'success')
        log_user_action("Editó suministro", supply.name)
        return redirect(url_for('main.supplies'))
    return render_template('add_supply.html', title='Editar Suministro', form=form, supply=supply)

@bp.route('/delete_supply/<int:supply_id>', methods=['POST'])
@login_required
@permission_required('can_delete_data')
def delete_supply(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    supply_name = supply.name
    db.session.delete(supply)
    db.session.commit()
    flash(f'Suministro {supply_name} eliminado exitosamente', 'success')
    log_user_action("Eliminó suministro", supply_name)
    return redirect(url_for('main.supplies'))

# =====================================================================
# RUTAS DE GESTIÓN DE PAQUETES DE SUMINISTROS
# =====================================================================

@bp.route('/admin/supply_packages', methods=['GET', 'POST'])
@login_required
@permission_required('can_manage_supplies')
def supply_packages():
    """Gestión de paquetes de suministros por habitación"""
    rooms = Room.query.order_by(Room.name).all()
    supplies = Supply.query.order_by(Supply.name).all()
    
    if request.method == 'POST':
        room_id = int(request.form.get('room_id'))
        supply_id = int(request.form.get('supply_id'))
        quantity = int(request.form.get('quantity', 1))
        
        # Verificar si ya existe la relación
        existing = db.session.execute(
            db.text("SELECT quantity FROM room_supply_defaults WHERE room_id = :room_id AND supply_id = :supply_id"),
            {"room_id": room_id, "supply_id": supply_id}
        ).fetchone()
        
        if existing:
            # Actualizar cantidad existente
            db.session.execute(
                db.text("UPDATE room_supply_defaults SET quantity = :quantity WHERE room_id = :room_id AND supply_id = :supply_id"),
                {"quantity": quantity, "room_id": room_id, "supply_id": supply_id}
            )
            flash(f'Cantidad actualizada a {quantity}', 'success')
        else:
            # Insertar nueva relación
            db.session.execute(
                db.text("INSERT INTO room_supply_defaults (room_id, supply_id, quantity) VALUES (:room_id, :supply_id, :quantity)"),
                {"room_id": room_id, "supply_id": supply_id, "quantity": quantity}
            )
            flash(f'Suministro agregado al paquete de la habitación', 'success')
        
        db.session.commit()
        log_user_action("Configuró paquete de suministros", f"Habitación {room_id}, Suministro {supply_id}: {quantity}")
        return redirect(url_for('main.supply_packages'))
    
    return render_template('supply_packages.html', title='Paquetes de Suministros', rooms=rooms, supplies=supplies)

@bp.route('/ajax/get_room_package/<int:room_id>')
@login_required
def get_room_package(room_id):
    """Obtiene el paquete de suministros para una habitación específica"""
    try:
        room = Room.query.get_or_404(room_id)
        package_data = db.session.execute(
            db.text("""
                SELECT rsd.supply_id, rsd.quantity, s.name, s.current_stock 
                FROM room_supply_defaults rsd 
                JOIN supply s ON rsd.supply_id = s.id 
                WHERE rsd.room_id = :room_id
                ORDER BY s.name
            """),
            {"room_id": room_id}
        ).fetchall()
        
        package = [
            {
                "supply_id": row[0],
                "quantity": row[1], 
                "supply_name": row[2],
                "current_stock": row[3]
            }
            for row in package_data
        ]
        
        return jsonify({
            'success': True,
            'room_name': room.name,
            'package': package
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/remove_from_package', methods=['POST'])
@login_required
@permission_required('can_manage_supplies')
def remove_from_package():
    """Remueve un suministro del paquete de una habitación"""
    try:
        room_id = int(request.form.get('room_id'))
        supply_id = int(request.form.get('supply_id'))
        
        db.session.execute(
            db.text("DELETE FROM room_supply_defaults WHERE room_id = :room_id AND supply_id = :supply_id"),
            {"room_id": room_id, "supply_id": supply_id}
        )
        db.session.commit()
        
        log_user_action("Removió suministro del paquete", f"Habitación {room_id}, Suministro {supply_id}")
        return jsonify({'success': True, 'message': 'Suministro removido del paquete'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# =====================================================================
# RUTAS DE CIERRE DE ESTANCIAS E INVENTARIO
# =====================================================================

@bp.route('/close_stay/<int:stay_id>', methods=['GET', 'POST'])
@login_required
def close_stay(stay_id):
    """Cerrar estancia con verificación de inventario"""
    stay = Stay.query.get_or_404(stay_id)
    
    # Verificar que la estancia pueda ser cerrada
    if not stay.can_be_closed():
        flash('Esta estancia no puede ser cerrada en este momento', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtener usos automáticos de suministros
    automatic_usages = stay.get_automatic_supply_usages()
    
    if request.method == 'POST':
        try:
            # Procesar verificación de inventario
            verified_by_user_id = current_user.id
            total_adjustments = 0
            
            for usage in automatic_usages:
                # Obtener cantidad real utilizada del formulario
                field_name = f'real_quantity_{usage.supply_id}'
                real_quantity = int(request.form.get(field_name, usage.quantity_used))
                
                # Calcular diferencia
                difference = real_quantity - usage.quantity_used
                
                if difference != 0:
                    # Crear registro de verificación
                    verification_usage = SupplyUsage(
                        supply_id=usage.supply_id,
                        stay_id=stay.id,
                        quantity_used=difference,
                        usage_type='Verificado',
                        usage_date=datetime.now(),
                        verified_by_user_id=verified_by_user_id,
                        notes=f'Ajuste de verificación: {usage.quantity_used} → {real_quantity}'
                    )
                    db.session.add(verification_usage)
                    
                    # Ajustar stock
                    supply = Supply.query.get(usage.supply_id)
                    if supply:
                        supply.current_stock -= difference  # Si difference > 0, resta más; si < 0, devuelve
                        supply.last_updated = datetime.now()
                        total_adjustments += abs(difference)
                        
                        log_user_action("Verificación de inventario", 
                                      f"{supply.name}: Automático {usage.quantity_used} → Real {real_quantity}")
            
            # Cambiar estado de estancia
            stay.status = 'Finalizada'
            
            # Agregar notas si se proporcionaron
            notes = request.form.get('closure_notes', '').strip()
            if notes:
                # Crear un registro de nota general
                note_usage = SupplyUsage(
                    supply_id=automatic_usages[0].supply_id if automatic_usages else None,
                    stay_id=stay.id,
                    quantity_used=0,
                    usage_type='Manual',
                    usage_date=datetime.now(),
                    verified_by_user_id=verified_by_user_id,
                    notes=f'Notas de cierre: {notes}'
                )
                db.session.add(note_usage)
            
            db.session.commit()
            
            flash(f'Estancia cerrada exitosamente. {total_adjustments} ajustes de inventario aplicados.', 'success')
            log_user_action("Cerró estancia", f"Estancia #{stay.id} - {total_adjustments} ajustes")
            
            return redirect(url_for('main.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al cerrar estancia: {str(e)}', 'danger')
            return redirect(url_for('main.close_stay', stay_id=stay_id))
    
    # GET request - mostrar formulario de verificación
    users = User.query.all()
    return render_template('close_stay.html', 
                         title=f'Cerrar Estancia - {stay.client.full_name}',
                         stay=stay, 
                         automatic_usages=automatic_usages,
                         users=users)

@bp.route('/ajax/set_stay_pending/<int:stay_id>', methods=['POST'])
@login_required
def set_stay_pending(stay_id):
    """Marca una estancia como pendiente de cierre"""
    try:
        stay = Stay.query.get_or_404(stay_id)
        if stay.status == 'Activa':
            stay.status = 'Pendiente de Cierre'
            db.session.commit()
            log_user_action("Marcó estancia como pendiente", f"Estancia #{stay.id}")
            return jsonify({'success': True, 'message': 'Estancia marcada como pendiente de cierre'})
        else:
            return jsonify({'success': False, 'message': 'La estancia no está activa'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# =====================================================================
# ENDPOINTS AJAX PARA PANEL DE CONTROL UNIFICADO v2.0
# =====================================================================

@bp.route('/ajax/get_availability_grid')
@login_required
def get_availability_grid():
    """Genera la grilla de disponibilidad para el calendario visual"""
    try:
        from datetime import date, timedelta
        
        # Configuración de la grilla (30 días hacia adelante)
        start_date = date.today()
        days_count = 30
        dates = [start_date + timedelta(days=i) for i in range(days_count)]
        
        # Obtener todas las habitaciones
        rooms = Room.query.order_by(Room.name).all()
        
        # Obtener todas las estancias activas en el período
        end_date = start_date + timedelta(days=days_count)
        stays = Stay.query.filter(
            Stay.status.in_(['Activa', 'Pendiente de Cierre']),
            Stay.check_in_date <= end_date,
            or_(
                Stay.check_out_date.is_(None),
                Stay.check_out_date >= start_date
            )
        ).all()
        
        # Construir grilla
        grid_data = {
            'dates': [d.strftime('%Y-%m-%d') for d in dates],
            'date_labels': [d.strftime('%d/%m') for d in dates],
            'rooms': [],
            'cells': {}
        }
        
        # Procesar cada habitación
        for room in rooms:
            room_data = {
                'id': room.id,
                'name': room.name,
                'tier': room.get_tier_display(),
                'status': room.status
            }
            grid_data['rooms'].append(room_data)
            
            # Procesar cada fecha para esta habitación
            for date_obj in dates:
                date_str = date_obj.strftime('%Y-%m-%d')
                cell_key = f"{room.id}_{date_str}"
                
                # Encontrar estancia que cubre esta fecha
                occupying_stay = None
                for stay in stays:
                    if stay.room_id == room.id:
                        stay_start = stay.check_in_date.date()
                        stay_end = stay.check_out_date.date() if stay.check_out_date else date.today() + timedelta(days=365)
                        
                        if stay_start <= date_obj <= stay_end:
                            occupying_stay = stay
                            break
                
                # Determinar estado de la celda
                if room.status == 'Mantenimiento':
                    cell_status = 'maintenance'
                    cell_data = {
                        'status': cell_status,
                        'text': 'Mantenimiento',
                        'class': 'cell-maintenance'
                    }
                elif occupying_stay:
                    # Determinar el tipo específico de ocupación
                    stay_start = occupying_stay.check_in_date.date()
                    stay_end = occupying_stay.check_out_date.date() if occupying_stay.check_out_date else None
                    
                    if stay_start == date_obj:
                        cell_status = 'checkin'
                        cell_data = {
                            'status': cell_status,
                            'text': f"Check-in: {occupying_stay.client.full_name}",
                            'class': 'cell-checkin',
                            'stay_id': occupying_stay.id,
                            'client_name': occupying_stay.client.full_name
                        }
                    elif stay_end == date_obj:
                        cell_status = 'checkout'
                        cell_data = {
                            'status': cell_status,
                            'text': f"Check-out: {occupying_stay.client.full_name}",
                            'class': 'cell-checkout',
                            'stay_id': occupying_stay.id,
                            'client_name': occupying_stay.client.full_name
                        }
                    else:
                        cell_status = 'occupied'
                        cell_data = {
                            'status': cell_status,
                            'text': occupying_stay.client.full_name,
                            'class': 'cell-occupied',
                            'stay_id': occupying_stay.id,
                            'client_name': occupying_stay.client.full_name
                        }
                else:
                    # Celda disponible
                    cell_status = 'available'
                    cell_data = {
                        'status': cell_status,
                        'text': '',
                        'class': 'cell-available',
                        'clickable': True
                    }
                
                grid_data['cells'][cell_key] = cell_data
        
        return jsonify({
            'success': True,
            'grid': grid_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/get_expenses')
@login_required
def get_expenses():
    """Obtiene gastos filtrados por período para el widget - v3.0"""
    try:
        period = request.args.get('period', 'today')
        
        # Usar la nueva lógica centralizada
        expenses = Expense.get_expenses_by_period(period)
        
        expenses_data = []
        elizabeth_total = 0.0
        total_amount = 0.0
        
        for expense in expenses:
            expenses_data.append({
                'id': expense.id,
                'description': expense.description,
                'amount': expense.amount,
                'category': expense.category,
                'payment_method': expense.get_payment_method_display(),
                'paid_by': expense.get_paid_by_display(),
                'date': expense.expense_date.strftime('%H:%M'),
                'full_date': expense.expense_date.strftime('%d/%m/%Y %H:%M'),
                'affects_cash': expense.affects_cash_closure()
            })
            
            total_amount += expense.amount
            
            # Calcular gastos de Elizabeth (empleada)
            if expense.paid_by and expense.paid_by.role == 'empleada':
                elizabeth_total += expense.amount
        
        return jsonify({
            'success': True,
            'expenses': expenses_data,
            'total': total_amount,
            'elizabeth': elizabeth_total,
            'count': len(expenses_data),
            'period': period,
            'period_display': {
                'today': 'Hoy',
                'yesterday': 'Ayer',
                'week': 'Últimos 7 días'
            }.get(period, 'Hoy')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/get_relevant_clients')
@login_required
def get_relevant_clients():
    """Obtiene clientes relevantes por categoría para el widget - v3.0"""
    try:
        category = request.args.get('category', 'current')
        
        # Usar la nueva lógica centralizada
        stays = Client.get_relevant_clients_by_category(category)
        
        def format_client_data(stays, detail_func):
            result = []
            for stay in stays:
                result.append({
                    'id': stay.id,
                    'client_id': stay.client.id,
                    'full_name': stay.client.full_name,
                    'phone_number': stay.client.phone_number,
                    'room': stay.room.name,
                    'detail': detail_func(stay),
                    'status': stay.get_status_display(),
                    'total_paid': stay.total_paid(),
                    'visit_count': stay.client.visit_count()
                })
            return result
        
        if category == 'current':
            clients = format_client_data(
                stays, 
                lambda stay: f"Desde {stay.check_in_date.strftime('%d/%m')}"
            )
            
        elif category == 'arriving':
            clients = format_client_data(
                stays,
                lambda stay: f"Check-in {stay.check_in_date.strftime('%H:%M')}"
            )
            
        elif category == 'departing':
            clients = format_client_data(
                stays,
                lambda stay: f"Check-out {stay.check_out_date.strftime('%H:%M')}"
            )
            
        elif category == 'recent':
            clients = format_client_data(
                stays,
                lambda stay: f"Salió {stay.check_out_date.strftime('%d/%m')}"
            )
            
        else:
            clients = []
        
        return jsonify({
            'success': True,
            'clients': clients,
            'category': category,
            'count': len(clients)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/add_quick_expense', methods=['POST'])
@login_required
def add_quick_expense():
    """Añade un gasto rápido desde el widget"""
    try:
        # Aceptar tanto JSON como form data
        if request.is_json:
            data = request.get_json()
            description = data.get('description', '').strip()
            amount = float(data.get('amount', 0))
            category = data.get('category', 'Otro')
            payment_method = data.get('payment_method', 'Efectivo')
            paid_by_user_id = int(data.get('paid_by_user_id', current_user.id))
        else:
            description = request.form.get('description', '').strip()
            amount = float(request.form.get('amount', 0))
            category = request.form.get('category', 'Otro')
            payment_method = request.form.get('payment_method', 'Efectivo')
            paid_by_user_id = int(request.form.get('paid_by_user_id', current_user.id))
        
        if not description or amount <= 0:
            return jsonify({'success': False, 'message': 'Descripción y monto son requeridos'})
        
        # Crear gasto
        expense = Expense(
            description=description,
            amount=amount,
            category=category,
            payment_method=payment_method,
            paid_by_user_id=paid_by_user_id,
            expense_date=datetime.now()
        )
        
        db.session.add(expense)
        db.session.commit()
        
        log_user_action("Gasto rápido registrado", f"{description}: DOP {amount:,.2f}")
        
        return jsonify({
            'success': True,
            'message': f'Gasto registrado: DOP {amount:,.2f}',
            'expense': {
                'id': expense.id,
                'description': expense.description,
                'amount': expense.amount,
                'category': expense.category,
                'payment_method': expense.get_payment_method_display(),
                'paid_by': expense.get_paid_by_display(),
                'date': expense.expense_date.strftime('%H:%M'),
                'affects_cash': expense.affects_cash_closure()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/add_manual_supply_usage', methods=['POST'])
@login_required
def add_manual_supply_usage():
    """Registra uso manual de suministros desde el widget"""
    try:
        supply_id = int(request.form.get('supply_id'))
        quantity = int(request.form.get('quantity', 1))
        notes = request.form.get('notes', '').strip()
        
        supply = Supply.query.get_or_404(supply_id)
        
        if supply.current_stock < quantity:
            return jsonify({
                'success': False, 
                'message': f'Stock insuficiente. Disponible: {supply.current_stock}'
            })
        
        # Crear registro de uso manual
        usage = SupplyUsage(
            supply_id=supply_id,
            stay_id=None,  # Uso manual no está ligado a estancia
            quantity_used=quantity,
            usage_type='Manual',
            verified_by_user_id=current_user.id,
            notes=notes or f'Uso manual registrado por {current_user.username}'
        )
        
        # Actualizar stock
        supply.current_stock -= quantity
        supply.last_updated = datetime.now()
        
        db.session.add(usage)
        db.session.commit()
        
        log_user_action("Uso manual de suministro", f"{supply.name}: -{quantity}")
        
        return jsonify({
            'success': True,
            'message': f'Uso registrado: {supply.name} -{quantity}',
            'supply': {
                'id': supply.id,
                'name': supply.name,
                'current_stock': supply.current_stock,
                'is_low_stock': supply.is_low_stock()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# === Duplicate endpoint removed - using first definition ===

@bp.route('/ajax/search_client_by_phone', methods=['POST'])
@login_required
def search_client_by_phone():
    """Busca un cliente por número de teléfono"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'message': 'Número de teléfono requerido'})
        
        # Limpiar teléfono para búsqueda
        cleaned_phone = phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        
        # Buscar cliente
        client = Client.query.filter(
            or_(
                Client.phone_number == phone,
                Client.phone_number.like(f'%{cleaned_phone}%'),
                func.replace(func.replace(Client.phone_number, '-', ''), ' ', '').like(f'%{cleaned_phone}%')
            )
        ).first()
        
        if client:
            last_visit = client.last_visit()
            return jsonify({
                'success': True,
                'found': True,
                'client': {
                    'id': client.id,
                    'full_name': client.full_name,
                    'phone_number': client.phone_number,
                    'email': client.email,
                    'visit_count': client.visit_count(),
                    'last_visit': last_visit.strftime('%d/%m/%Y') if last_visit else 'Nunca',
                    'total_spent': client.total_spent()
                }
            })
        else:
            return jsonify({
                'success': True,
                'found': False,
                'message': 'Cliente no encontrado'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/quick_stay', methods=['POST'])
@login_required
def ajax_quick_stay():
    """Crea una estancia desde el formulario rápido"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        room_id = data.get('room_id')
        check_in_date = data.get('check_in_date')
        check_out_date = data.get('check_out_date')
        booking_channel = data.get('booking_channel', 'Directo')
        
        if not all([phone, room_id, check_in_date]):
            return jsonify({'success': False, 'message': 'Datos incompletos'})
        
        # Validar habitación
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'success': False, 'message': 'Habitación no válida'})
        
        # Buscar o crear cliente
        cleaned_phone = phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        client = Client.query.filter(
            or_(
                Client.phone_number == phone,
                func.replace(func.replace(Client.phone_number, '-', ''), ' ', '').like(f'%{cleaned_phone}%')
            )
        ).first()
        
        if not client:
            # Crear cliente con número de teléfono únicamente
            client = Client(
                full_name=f'Cliente {phone}',  # Nombre temporal
                phone_number=phone
            )
            db.session.add(client)
            db.session.flush()  # Para obtener el ID
        
        # Validar fechas
        try:
            checkin_dt = datetime.strptime(check_in_date, '%Y-%m-%d')
            checkout_dt = datetime.strptime(check_out_date, '%Y-%m-%d') if check_out_date else None
            
            if checkout_dt and checkout_dt <= checkin_dt:
                return jsonify({'success': False, 'message': 'Check-out debe ser posterior al check-in'})
                
        except ValueError:
            return jsonify({'success': False, 'message': 'Formato de fecha inválido'})
        
        # Verificar conflictos de disponibilidad
        from datetime import timedelta
        conflicts = Stay.query.filter(
            Stay.room_id == room_id,
            Stay.check_in_date <= (checkout_dt or checkin_dt + timedelta(days=365)),
            or_(Stay.check_out_date >= checkin_dt, Stay.check_out_date.is_(None))
        ).all()
        
        if conflicts:
            return jsonify({
                'success': False, 
                'message': f'Conflicto de reserva: habitación ocupada en esas fechas'
            })
        
        # Crear estancia
        stay = Stay(
            client_id=client.id,
            room_id=room_id,
            check_in_date=checkin_dt,
            check_out_date=checkout_dt,
            booking_channel=booking_channel,
            status='Activa'
        )
        
        db.session.add(stay)
        db.session.flush()
        
        # Deducir suministros automáticamente si existe paquete
        deducted_supplies = deduct_automatic_supplies(stay.id, room_id)
        
        db.session.commit()
        
        log_user_action("Estancia rápida creada", f"{client.full_name} en {room.name}")
        
        message = f'Estancia creada para {client.full_name} en {room.name}'
        if deducted_supplies:
            message += f'. Suministros deducidos: {len(deducted_supplies)}'
        
        return jsonify({
            'success': True,
            'message': message,
            'stay': {
                'id': stay.id,
                'client_name': client.full_name,
                'room_name': room.name,
                'check_in': checkin_dt.strftime('%d/%m/%Y'),
                'check_out': checkout_dt.strftime('%d/%m/%Y') if checkout_dt else 'Sin definir'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/save_client_only', methods=['POST'])
@login_required
def save_client_only():
    """Guarda solo información del cliente sin crear estancia"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'message': 'Número de teléfono requerido'})
        
        # Buscar cliente existente
        cleaned_phone = phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        existing_client = Client.query.filter(
            or_(
                Client.phone_number == phone,
                func.replace(func.replace(Client.phone_number, '-', ''), ' ', '').like(f'%{cleaned_phone}%')
            )
        ).first()
        
        if existing_client:
            return jsonify({
                'success': False, 
                'message': f'Cliente ya existe: {existing_client.full_name}'
            })
        
        # Crear nuevo cliente
        client = Client(
            full_name=f'Cliente {phone}',  # Nombre temporal que se puede editar después
            phone_number=phone
        )
        
        db.session.add(client)
        db.session.commit()
        
        log_user_action("Cliente rápido creado", phone)
        
        return jsonify({
            'success': True,
            'message': f'Cliente guardado: {phone}',
            'client': {
                'id': client.id,
                'full_name': client.full_name,
                'phone_number': client.phone_number
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/quick_inventory_update', methods=['POST'])
@login_required
def quick_inventory_update():
    """Actualización rápida de inventario desde el widget"""
    try:
        # Aceptar tanto JSON como form data
        if request.is_json:
            data = request.get_json()
            supply_id = int(data.get('supply_id'))
            quantity = int(data.get('quantity'))
            action = data.get('action', 'add')  # add, use, adjust
            notes = data.get('notes', '').strip()
        else:
            supply_id = int(request.form.get('supply_id'))
            quantity = int(request.form.get('quantity'))
            action = request.form.get('action', 'add')
            notes = request.form.get('notes', '').strip()
        
        if not supply_id or not quantity:
            return jsonify({'success': False, 'message': 'Datos incompletos'})
        
        supply = Supply.query.get_or_404(supply_id)
        old_stock = supply.current_stock
        
        # Calcular nuevo stock según la acción
        if action == 'add':
            new_stock = old_stock + quantity
            action_description = f'Agregó {quantity} unidades'
        elif action == 'use':
            if old_stock < quantity:
                return jsonify({
                    'success': False, 
                    'message': f'Stock insuficiente. Disponible: {old_stock}'
                })
            new_stock = old_stock - quantity
            action_description = f'Uso manual: -{quantity} unidades'
            
            # Crear registro de uso manual
            usage = SupplyUsage(
                supply_id=supply_id,
                stay_id=None,  # Uso manual no está ligado a estancia
                quantity_used=quantity,
                usage_type='Manual',
                verified_by_user_id=current_user.id,
                notes=notes or f'Uso manual desde panel de control'
            )
            db.session.add(usage)
            
        elif action == 'adjust':
            new_stock = quantity  # Ajuste directo al valor especificado
            action_description = f'Ajuste de stock: {old_stock} → {new_stock}'
        else:
            return jsonify({'success': False, 'message': 'Acción no válida'})
        
        # Actualizar stock
        supply.current_stock = new_stock
        supply.last_updated = datetime.now()
        
        # Agregar nota si es necesario
        if notes:
            current_notes = supply.notes or ''
            supply.notes = current_notes + f"\n{datetime.now().strftime('%d/%m/%Y %H:%M')}: {notes}"
        
        db.session.commit()
        
        log_user_action("Actualización rápida de inventario", f"{supply.name}: {action_description}")
        
        # Determinar el estado del stock
        is_critical = new_stock <= supply.minimum_stock
        is_warning = new_stock <= (supply.minimum_stock * 1.5) and not is_critical
        
        return jsonify({
            'success': True,
            'message': f'{supply.name}: {old_stock} → {new_stock}',
            'supply': {
                'id': supply.id,
                'name': supply.name,
                'old_stock': old_stock,
                'current_stock': new_stock,
                'minimum_stock': supply.minimum_stock,
                'is_critical': is_critical,
                'is_warning': is_warning,
                'status': 'critical' if is_critical else ('warning' if is_warning else 'ok')
            },
            'action': action,
            'quantity': quantity
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/ajax/get_inventory_status')
@login_required
def get_inventory_status():
    """Obtiene el estado actual del inventario para el widget - v3.0"""
    try:
        # Usar la nueva lógica centralizada
        inventory_status = Supply.get_inventory_status()
        
        return jsonify({
            'success': True,
            'critical_count': inventory_status['critical_count'],
            'warning_count': inventory_status['warning_count'],
            'alerts': inventory_status['alerts'],
            'last_updated': datetime.now().strftime('%H:%M')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})