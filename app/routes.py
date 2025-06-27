from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import func, extract, or_
from datetime import datetime
from calendar import monthrange
from collections import Counter

from app.extensions import db
from app.forms import LoginForm, ClientForm, ExpenseForm, StayForm, PaymentForm, SupplyForm, UpdateStockForm, UnifiedStayForm, CashClosureForm, EmployeeDeliveryForm, MonthYearForm
from app.models import User, Room, Task, Client, Expense, Stay, Payment, Supply, CashClosure, EmployeeDelivery
from app.decorators import role_required, owner_required, management_required, permission_required, log_user_action

bp = Blueprint('main', __name__)

# =====================================================================
# RUTA PRINCIPAL (PANEL DE CONTROL UNIFICADO)
# =====================================================================

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    # --- Datos para las estadísticas del panel ---
    total_clients = Client.query.count()
    active_stays = Stay.query.filter(Stay.check_out_date.is_(None)).count()
    low_stock_supplies = Supply.query.filter(Supply.current_stock <= Supply.minimum_stock).all()
    low_stock_count = len(low_stock_supplies)
    
    # --- Datos financieros del mes actual ---
    current_date = datetime.now()
    start_of_month = datetime(current_date.year, current_date.month, 1)
    
    monthly_income = db.session.query(func.sum(Payment.amount)).filter(Payment.payment_date >= start_of_month).scalar() or 0.0
    
    elizabeth_expenses = db.session.query(func.sum(Expense.amount)).join(User).filter(User.role == 'empleada', Expense.expense_date >= start_of_month).scalar() or 0.0
    alejandrina_expenses = db.session.query(func.sum(Expense.amount)).join(User).filter(User.role == 'socia', Expense.expense_date >= start_of_month).scalar() or 0.0
    owner_expenses = db.session.query(func.sum(Expense.amount)).join(User).filter(User.role == 'dueño', Expense.expense_date >= start_of_month).scalar() or 0.0
    total_expenses = elizabeth_expenses + alejandrina_expenses + owner_expenses
    monthly_profit = monthly_income - total_expenses
    
    # --- Top clientes ---
    all_clients_for_ranking = Client.query.all()
    top_clients = sorted(all_clients_for_ranking, key=lambda x: x.total_spent(), reverse=True)
    
    # --- Datos para los formularios en las pestañas ---
    clients = Client.query.order_by(Client.full_name).all()
    rooms = Room.query.order_by(Room.name).all()
    users = User.query.all()
    supplies = Supply.query.order_by(Supply.name).all()
    recent_stays = Stay.query.order_by(Stay.check_in_date.desc()).limit(15).all()
    recent_expenses = Expense.query.order_by(Expense.expense_date.desc()).limit(15).all()
    
    return render_template('control_panel.html', 
                         title='Panel de Control',
                         total_clients=total_clients, active_stays=active_stays,
                         low_stock_count=low_stock_count, low_stock_supplies=low_stock_supplies,
                         monthly_income=monthly_income, monthly_expenses=total_expenses,
                         elizabeth_expenses=elizabeth_expenses, alejandrina_expenses=alejandrina_expenses,
                         owner_expenses=owner_expenses, total_expenses=total_expenses,
                         monthly_profit=monthly_profit, top_clients=top_clients,
                         clients=clients, rooms=rooms, users=users, supplies=supplies,
                         recent_stays=recent_stays, recent_expenses=recent_expenses)

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

@bp.route('/clients')
@login_required
def clients():
    all_clients = Client.query.order_by(Client.full_name).all()
    return render_template('clients.html', title='Clientes', clients=all_clients)

@bp.route('/add_client', methods=['GET', 'POST'])
@login_required
def add_client():
    form = ClientForm()
    if form.validate_on_submit():
        email_data = form.email.data or None
        if email_data and Client.query.filter_by(email=email_data).first():
            flash('Ya existe un cliente con ese correo electrónico.', 'danger')
            return redirect(url_for('main.add_client'))
        new_client = Client(
            full_name=form.full_name.data,
            phone_number=form.phone_number.data,
            email=email_data,
            notes=form.notes.data
        )
        db.session.add(new_client)
        db.session.commit()
        flash('¡Nuevo cliente añadido con éxito!', 'success')
        return redirect(url_for('main.clients'))
    return render_template('add_client.html', title='Añadir Cliente', form=form)

@bp.route('/expenses')
@login_required
def expenses():
    all_expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    return render_template('expenses.html', title='Gastos', expenses=all_expenses)

@bp.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    form = ExpenseForm()
    form.paid_by.choices = [(user.id, user.get_display_name()) for user in User.query.all()]
    
    if form.validate_on_submit():
        new_expense = Expense(
            description=form.description.data, 
            amount=form.amount.data, 
            category=form.category.data,
            payment_method=form.payment_method.data,
            paid_by_user_id=form.paid_by.data
        )
        db.session.add(new_expense)
        db.session.commit()
        
        paid_by_user = User.query.get(form.paid_by.data)
        if form.payment_method.data == 'Efectivo':
            flash(f'Gasto en efectivo registrado. Pagado por {paid_by_user.get_display_name()}. Afectará el cuadre de caja.', 'info')
        else:
            flash(f'Gasto registrado. Pagado por {paid_by_user.get_display_name()} con {form.payment_method.data}. NO afecta el cuadre de caja.', 'success')
        
        log_user_action("Registró gasto", f"{form.description.data}: DOP {form.amount.data:,.2f} - {form.payment_method.data}")
        return redirect(url_for('main.expenses'))
    
    return render_template('add_expense.html', title='Añadir Gasto', form=form)

@bp.route('/stays')
@login_required
def stays():
    all_stays = Stay.query.join(Client).join(Room).order_by(Stay.check_in_date.desc()).all()
    return render_template('stays.html', title='Estancias', stays=all_stays)

@bp.route('/add_stay', methods=['GET', 'POST'])
@login_required
def add_stay():
    form = StayForm()
    form.client.choices = [(c.id, c.full_name) for c in Client.query.order_by(Client.full_name).all()]
    form.room.choices = [(r.id, r.name) for r in Room.query.order_by(Room.name).all()]
    if form.validate_on_submit():
        new_stay = Stay(client_id=form.client.data, room_id=form.room.data, booking_channel=form.booking_channel.data, check_in_date=form.check_in_date.data, check_out_date=form.check_out_date.data)
        db.session.add(new_stay)
        db.session.commit()
        flash('¡Nueva estancia registrada con éxito!', 'success')
        return redirect(url_for('main.stays'))
    return render_template('add_stay.html', title='Registrar Estancia', form=form)

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