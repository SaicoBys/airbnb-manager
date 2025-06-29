"""
AIRBNB MANAGER V3.0 - RUTAS PRINCIPALES DE GESTIÓN
Contiene las rutas principales para gestión de clientes, estancias, pagos, suministros, etc.
Este blueprint será gradualmente migrado a los otros blueprints modulares.
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import func, extract, or_
from datetime import datetime, date, timedelta
from calendar import monthrange
from collections import Counter

from app.extensions import db
from app.forms import (LoginForm, ClientForm, ExpenseForm, StayForm, PaymentForm, 
                      SupplyForm, UpdateStockForm, UnifiedStayForm, CashClosureForm, 
                      EmployeeDeliveryForm, MonthYearForm)
from app.models import (User, Room, Task, Client, Expense, Stay, Payment, Supply, 
                       CashClosure, EmployeeDelivery, SupplyUsage)
from app.decorators import (role_required, owner_required, management_required, 
                           permission_required, log_user_action)

bp = Blueprint('main', __name__)

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
        solutions.append({
            'type': 'available',
            'title': 'Habitaciones Disponibles',
            'description': f'{len(available_rooms)} habitación(es) completamente libre(s)',
            'rooms': [{'id': r.id, 'name': r.name, 'tier': r.get_tier_display()} for r in available_rooms],
            'priority': 'high'
        })
    
    return solutions

# =====================================================================
# RUTAS DE GESTIÓN DE PAGOS
# =====================================================================

@bp.route('/add_payment/<int:stay_id>', methods=['GET', 'POST'])
@login_required
def add_payment(stay_id):
    """Agregar pago a una estancia específica"""
    stay = Stay.query.get_or_404(stay_id)
    form = PaymentForm()
    
    if form.validate_on_submit():
        try:
            payment = Payment(
                stay_id=stay.id,
                amount=form.amount.data,
                method=form.method.data,
                payment_date=form.payment_date.data or datetime.now()
            )
            
            db.session.add(payment)
            db.session.commit()
            
            flash(f'Pago de DOP {payment.amount:,.2f} agregado a la estancia de {stay.client.full_name}', 'success')
            return redirect(url_for('panel.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar pago: {str(e)}', 'error')
    
    return render_template('add_payment.html', form=form, stay=stay)

# =====================================================================
# RUTAS DE GESTIÓN DE SUMINISTROS
# =====================================================================

@bp.route('/supplies')
@login_required
@permission_required('can_manage_supplies')
def supplies():
    """Lista de suministros con gestión de inventario"""
    supplies = Supply.query.order_by(Supply.category, Supply.name).all()
    low_stock_supplies = [s for s in supplies if s.is_low_stock()]
    
    return render_template('supplies.html', 
                         title='Gestión de Suministros',
                         supplies=supplies,
                         low_stock_count=len(low_stock_supplies))

@bp.route('/add_supply', methods=['GET', 'POST'])
@login_required
@permission_required('can_manage_supplies')
def add_supply():
    """Agregar nuevo suministro al inventario"""
    form = SupplyForm()
    
    if form.validate_on_submit():
        try:
            supply = Supply(
                name=form.name.data,
                category=form.category.data,
                current_stock=form.current_stock.data,
                minimum_stock=form.minimum_stock.data,
                unit_price=form.unit_price.data,
                supplier=form.supplier.data,
                notes=form.notes.data
            )
            
            db.session.add(supply)
            db.session.commit()
            
            flash(f'Suministro "{supply.name}" agregado exitosamente', 'success')
            return redirect(url_for('main.supplies'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar suministro: {str(e)}', 'error')
    
    return render_template('add_supply.html', form=form)

@bp.route('/update_stock/<int:supply_id>', methods=['GET', 'POST'])
@login_required
@permission_required('can_manage_supplies')
def update_stock(supply_id):
    """Actualizar stock de un suministro específico"""
    supply = Supply.query.get_or_404(supply_id)
    form = UpdateStockForm()
    
    if form.validate_on_submit():
        try:
            old_stock = supply.current_stock
            action = form.action.data
            quantity = form.quantity.data
            
            if action == 'add':
                supply.current_stock += quantity
                action_text = f"Agregado {quantity}"
            elif action == 'subtract':
                if supply.current_stock >= quantity:
                    supply.current_stock -= quantity
                    action_text = f"Descontado {quantity}"
                else:
                    flash('Stock insuficiente para la operación', 'error')
                    return redirect(url_for('main.update_stock', supply_id=supply_id))
            else:
                supply.current_stock = quantity
                action_text = f"Stock ajustado a {quantity}"
            
            supply.last_updated = datetime.now()
            db.session.commit()
            
            flash(f'{action_text} unidades de {supply.name}. Stock anterior: {old_stock}, Nuevo stock: {supply.current_stock}', 'success')
            return redirect(url_for('main.supplies'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar stock: {str(e)}', 'error')
    
    return render_template('update_stock.html', form=form, supply=supply)

@bp.route('/edit_supply/<int:supply_id>', methods=['GET', 'POST'])
@login_required
@permission_required('can_manage_supplies')
def edit_supply(supply_id):
    """Editar información de un suministro"""
    supply = Supply.query.get_or_404(supply_id)
    form = SupplyForm(obj=supply)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(supply)
            supply.last_updated = datetime.now()
            db.session.commit()
            
            flash(f'Suministro "{supply.name}" actualizado exitosamente', 'success')
            return redirect(url_for('main.supplies'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar suministro: {str(e)}', 'error')
    
    return render_template('edit_supply.html', form=form, supply=supply)

@bp.route('/delete_supply/<int:supply_id>', methods=['POST'])
@login_required
@owner_required
def delete_supply(supply_id):
    """Eliminar un suministro (solo dueños)"""
    supply = Supply.query.get_or_404(supply_id)
    
    try:
        supply_name = supply.name
        db.session.delete(supply)
        db.session.commit()
        
        flash(f'Suministro "{supply_name}" eliminado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar suministro: {str(e)}', 'error')
    
    return redirect(url_for('main.supplies'))

# =====================================================================
# RUTAS DE GESTIÓN DE CIERRES DE CAJA
# =====================================================================

@bp.route('/cash_closures')
@login_required
@permission_required('can_view_monthly_report')
def cash_closures():
    """Lista de cierres de caja mensuales"""
    closures = CashClosure.query.order_by(CashClosure.year.desc(), CashClosure.month.desc()).all()
    return render_template('cash_closures.html', 
                         title='Cierres de Caja Mensuales',
                         closures=closures)

@bp.route('/create_cash_closure', methods=['GET', 'POST'])
@login_required
@management_required
def create_cash_closure():
    """Crear un nuevo cierre de caja mensual"""
    form = CashClosureForm()
    
    if form.validate_on_submit():
        try:
            year = form.year.data
            month = form.month.data
            
            # Verificar si ya existe un cierre para este período
            existing_closure = CashClosure.query.filter_by(year=year, month=month).first()
            if existing_closure:
                flash(f'Ya existe un cierre de caja para {existing_closure.get_period_display()}', 'warning')
                return redirect(url_for('main.cash_closures'))
            
            # Calcular ingresos y gastos del período
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
            
            # Ingresos del mes
            monthly_income = db.session.query(func.sum(Payment.amount)).filter(
                Payment.payment_date >= start_date,
                Payment.payment_date <= end_date
            ).scalar() or 0.0
            
            # Gastos de empleadas que afectan el cuadre
            employee_expenses = db.session.query(func.sum(Expense.amount)).join(User).filter(
                User.role == 'empleada',
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date
            ).scalar() or 0.0
            
            net_amount = monthly_income - employee_expenses
            
            # Crear el cierre
            closure = CashClosure(
                closure_date=datetime.now(),
                month=month,
                year=year,
                total_income=monthly_income,
                total_expenses=employee_expenses,
                net_amount=net_amount,
                notes=form.notes.data
            )
            
            db.session.add(closure)
            db.session.commit()
            
            flash(f'Cierre de caja creado para {closure.get_period_display()}: DOP {net_amount:,.2f}', 'success')
            return redirect(url_for('main.cash_closures'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear cierre de caja: {str(e)}', 'error')
    
    return render_template('create_cash_closure.html', form=form)

@bp.route('/view_cash_closure/<int:closure_id>')
@login_required
@permission_required('can_view_monthly_report')
def view_cash_closure(closure_id):
    """Ver detalles de un cierre de caja específico"""
    closure = CashClosure.query.get_or_404(closure_id)
    return render_template('view_cash_closure.html', closure=closure)

@bp.route('/deliver_cash/<int:closure_id>', methods=['GET', 'POST'])
@login_required
@management_required
def deliver_cash(closure_id):
    """Registrar entrega de efectivo de un cierre de caja"""
    closure = CashClosure.query.get_or_404(closure_id)
    form = EmployeeDeliveryForm()
    
    # Poblar choices de usuarios
    form.received_by_user_id.choices = [(u.id, u.get_display_name()) for u in User.query.all()]
    
    if form.validate_on_submit():
        try:
            delivery = EmployeeDelivery(
                cash_closure_id=closure.id,
                delivered_amount=form.delivered_amount.data,
                expected_amount=closure.net_amount,
                difference=form.delivered_amount.data - closure.net_amount,
                delivered_by_user_id=current_user.id,
                received_by_user_id=form.received_by_user_id.data,
                notes=form.notes.data
            )
            
            # Marcar el cierre como entregado
            closure.is_delivered = True
            closure.delivered_date = datetime.now()
            closure.delivered_by_user_id = current_user.id
            closure.received_by_user_id = form.received_by_user_id.data
            
            db.session.add(delivery)
            db.session.commit()
            
            difference_text = ""
            if delivery.difference > 0:
                difference_text = f" (Exceso: DOP {delivery.difference:,.2f})"
            elif delivery.difference < 0:
                difference_text = f" (Faltante: DOP {abs(delivery.difference):,.2f})"
            
            flash(f'Entrega registrada exitosamente: DOP {delivery.delivered_amount:,.2f}{difference_text}', 'success')
            return redirect(url_for('main.cash_closures'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar entrega: {str(e)}', 'error')
    
    return render_template('deliver_cash.html', form=form, closure=closure)

# =====================================================================
# RUTAS DE GESTIÓN DE ESTANCIAS
# =====================================================================

@bp.route('/close_stay/<int:stay_id>', methods=['GET', 'POST'])
@login_required
def close_stay(stay_id):
    """FASE 2 V3.0: Cerrar/finalizar una estancia con verificación completa de inventario"""
    stay = Stay.query.get_or_404(stay_id)
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            action = request.form.get('action', 'close')
            verify_supplies = request.form.get('verify_supplies') == 'on'
            supply_adjustments = request.form.getlist('supply_adjustments[]')
            adjustment_notes = request.form.get('adjustment_notes', '')
            
            # Procesar ajustes de suministros si se requiere verificación
            if verify_supplies and stay.has_supply_usage():
                process_supply_adjustments(stay, supply_adjustments, current_user.id, adjustment_notes)
            
            # Actualizar fecha de salida si no está establecida
            if not stay.check_out_date:
                stay.check_out_date = datetime.now()
            
            # Cambiar estado según la acción
            if action == 'close':
                stay.status = 'Finalizada'
                stay.room.status = 'Por Limpiar'
                message = f'Estancia de {stay.client.full_name} en {stay.room.name} finalizada exitosamente'
            elif action == 'pending':
                stay.status = 'Pendiente de Cierre'
                message = f'Estancia de {stay.client.full_name} marcada como pendiente de cierre'
            
            db.session.commit()
            
            flash(message, 'success')
            return redirect(url_for('panel.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar estancia: {str(e)}', 'error')
    
    # === OBTENER INFORMACIÓN COMPLETA PARA LA VISTA ===
    
    # Uso de suministros y resumen
    supply_usage_summary = stay.get_supply_usage_summary()
    supply_variances = stay.get_supply_variances()
    needs_verification = stay.needs_supply_verification()
    
    # Información del paquete de la habitación
    room_package_summary = stay.room.get_package_summary() if stay.room else None
    
    # Cálculos financieros
    total_supply_cost = stay.calculate_supply_cost()
    total_payments = stay.total_paid()
    
    # Alertas e información adicional
    alerts = []
    if supply_variances:
        alerts.append({
            'type': 'warning',
            'message': f'Se encontraron {len(supply_variances)} varianzas en el uso de suministros'
        })
    
    if supply_usage_summary and supply_usage_summary['total_cost'] > 0:
        alerts.append({
            'type': 'info',
            'message': f'Costo total de suministros: DOP {supply_usage_summary["total_cost"]:,.2f}'
        })
    
    # Verificar si hay suministros con stock bajo después de esta estancia
    low_stock_supplies = []
    if stay.has_supply_usage():
        for usage in stay.supply_usages:
            if usage.supply and usage.supply.is_low_stock():
                low_stock_supplies.append(usage.supply)
    
    if low_stock_supplies:
        alerts.append({
            'type': 'warning', 
            'message': f'{len(low_stock_supplies)} suministros quedaron con stock bajo'
        })
    
    return render_template('close_stay_v3.html', 
                         stay=stay,
                         supply_usage_summary=supply_usage_summary,
                         supply_variances=supply_variances,
                         needs_verification=needs_verification,
                         room_package_summary=room_package_summary,
                         total_supply_cost=total_supply_cost,
                         total_payments=total_payments,
                         alerts=alerts,
                         low_stock_supplies=low_stock_supplies)

# =====================================================================
# RUTAS AUXILIARES
# =====================================================================

@bp.route('/update_room_status/<int:room_id>', methods=['POST'])
@login_required
def update_room_status(room_id):
    """Actualizar el estado de una habitación"""
    room = Room.query.get_or_404(room_id)
    new_status = request.form.get('status')
    
    if new_status in ['Limpia', 'Ocupada', 'Mantenimiento', 'Por Limpiar']:
        try:
            old_status = room.status
            room.status = new_status
            db.session.commit()
            
            flash(f'Estado de {room.name} cambiado de "{old_status}" a "{new_status}"', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar estado: {str(e)}', 'error')
    else:
        flash('Estado inválido', 'error')
    
    return redirect(url_for('panel.index'))

@bp.route('/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    """Marcar una tarea como completada"""
    task = Task.query.get_or_404(task_id)
    
    try:
        task.status = 'Completada'
        db.session.commit()
        
        flash(f'Tarea "{task.description}" marcada como completada', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al completar tarea: {str(e)}', 'error')
    
    return redirect(url_for('panel.index'))

# =====================================================================
# FUNCIONES AUXILIARES PARA GESTIÓN DE ESTANCIAS V3.0
# =====================================================================

def process_supply_adjustments(stay, supply_adjustments, verified_by_user_id, notes):
    """
    Procesa los ajustes de suministros durante el cierre de estancia.
    
    Args:
        stay: Objeto Stay
        supply_adjustments: Lista de ajustes en formato 'usage_id:new_quantity'
        verified_by_user_id: ID del usuario que verifica
        notes: Notas adicionales
    """
    try:
        for adjustment in supply_adjustments:
            if not adjustment:
                continue
                
            # Parsear el ajuste (formato: usage_id:new_quantity)
            parts = adjustment.split(':')
            if len(parts) != 2:
                continue
                
            usage_id, new_quantity_str = parts
            try:
                usage_id = int(usage_id)
                new_quantity = int(new_quantity_str)
            except ValueError:
                continue
            
            # Obtener el registro de uso
            usage = SupplyUsage.query.get(usage_id)
            if not usage or usage.stay_id != stay.id:
                continue
            
            # Calcular diferencia
            old_quantity = usage.quantity_used
            quantity_diff = new_quantity - old_quantity
            
            if quantity_diff == 0:
                # No hay cambio, solo marcar como verificado
                usage.is_confirmed = True
                usage.verified_by_user_id = verified_by_user_id
                usage.verified_at = datetime.now()
                continue
            
            # Verificar stock disponible para ajustes positivos
            if quantity_diff > 0:
                if usage.supply.current_stock < quantity_diff:
                    # No hay suficiente stock para el incremento
                    flash(f'Stock insuficiente para ajustar {usage.supply.name}', 'warning')
                    continue
                    
                # Deducir stock adicional
                usage.supply.current_stock -= quantity_diff
                
            elif quantity_diff < 0:
                # Devolver stock
                usage.supply.current_stock += abs(quantity_diff)
            
            # Actualizar el uso
            usage.quantity_used = new_quantity
            usage.total_cost = usage.calculate_cost()
            usage.usage_type = 'Verificado'
            usage.is_confirmed = True
            usage.verified_by_user_id = verified_by_user_id
            usage.verified_at = datetime.now()
            
            if notes:
                usage.notes = f"Ajustado en cierre: {notes}"
            
            # Actualizar timestamp del suministro
            usage.supply.last_updated = datetime.now()
            
            # Crear registro adicional del ajuste si es significativo
            if abs(quantity_diff) > 0:
                adjustment_usage = SupplyUsage(
                    supply_id=usage.supply_id,
                    stay_id=stay.id,
                    quantity_used=quantity_diff,
                    usage_type='Ajuste',
                    usage_source='Estancia',
                    verified_by_user_id=verified_by_user_id,
                    cost_per_unit=usage.cost_per_unit,
                    is_confirmed=True,
                    notes=f"Ajuste durante cierre de estancia. Original: {old_quantity}, Nuevo: {new_quantity}"
                )
                adjustment_usage.total_cost = adjustment_usage.calculate_cost()
                db.session.add(adjustment_usage)
        
    except Exception as e:
        raise Exception(f"Error procesando ajustes de suministros: {str(e)}")