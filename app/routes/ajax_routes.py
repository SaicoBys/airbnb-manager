"""
AIRBNB MANAGER V3.0 - RUTAS AJAX
Contiene todas las rutas AJAX para operaciones en tiempo real y formularios dinámicos
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from datetime import datetime, date, timedelta
from collections import Counter
import re

from app.extensions import db
from app.models import (User, Room, Client, Stay, Payment, Expense, Supply, 
                       CashClosure, EmployeeDelivery, SupplyUsage, DashboardStats)
from app.yield_management import YieldManagementEngine, BookingRequest
from app.forms import (ClientForm, ExpenseForm, StayForm, PaymentForm, 
                      SupplyForm, UpdateStockForm, UnifiedStayForm, 
                      CashClosureForm, EmployeeDeliveryForm, MonthYearForm)
from app.decorators import role_required, owner_required, management_required, permission_required, log_user_action

bp = Blueprint('ajax', __name__, url_prefix='/ajax')

# =====================================================================
# FUNCIONES AUXILIARES INTERNAS
# =====================================================================

def clean_phone(phone_number):
    """Limpia el número de teléfono eliminando caracteres no numéricos."""
    if not phone_number:
        return ""
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
    
    # Solución 2: Habitaciones que se liberarán pronto
    today = date.today()
    soon_available = Stay.query.filter(
        Stay.room_id.in_(unavailable_room_ids),
        Stay.check_out_date.isnot(None),
        func.date(Stay.check_out_date) <= today + timedelta(days=3),
        func.date(Stay.check_out_date) < check_in.date() if isinstance(check_in, datetime) else check_in
    ).all()
    
    if soon_available:
        rooms_info = []
        for stay in soon_available:
            rooms_info.append({
                'id': stay.room.id,
                'name': stay.room.name,
                'available_date': stay.check_out_date.strftime('%d/%m/%Y'),
                'client': stay.client.full_name
            })
        
        solutions.append({
            'type': 'soon_available',
            'title': 'Se Liberarán Pronto',
            'description': f'{len(rooms_info)} habitación(es) se liberarán antes de la fecha',
            'rooms': rooms_info,
            'priority': 'medium'
        })
    
    # Solución 3: Sugerir fechas alternativas
    if not available_rooms:
        # Buscar la próxima fecha disponible
        next_week = check_in + timedelta(days=7) if isinstance(check_in, datetime) else datetime.combine(check_in, datetime.min.time()) + timedelta(days=7)
        future_availability = check_room_availability(next_week, next_week + (check_out - check_in))
        future_available_rooms = [room for room in all_rooms if room.id not in future_availability]
        
        if future_available_rooms:
            solutions.append({
                'type': 'alternative_dates',
                'title': 'Fechas Alternativas',
                'description': f'Disponibilidad la próxima semana ({next_week.strftime("%d/%m/%Y")})',
                'rooms': [{'id': r.id, 'name': r.name, 'tier': r.get_tier_display()} for r in future_available_rooms],
                'suggested_date': next_week.strftime('%Y-%m-%d'),
                'priority': 'low'
            })
    
    return solutions

# =====================================================================
# RUTAS AJAX PARA OBTENCIÓN DE DATOS
# =====================================================================

@bp.route('/get_availability_grid')
@login_required
def get_availability_grid():
    """Obtiene la grilla de disponibilidad de habitaciones para los próximos días"""
    try:
        days = int(request.args.get('days', 14))
        today = date.today()
        date_range = [today + timedelta(days=i) for i in range(days)]
        
        rooms = Room.query.order_by(Room.name).all()
        availability_data = []
        
        for room in rooms:
            room_data = {
                'room_id': room.id,
                'room_name': room.name,
                'tier': room.get_tier_display(),
                'availability': []
            }
            
            for check_date in date_range:
                # Verificar si hay estancia activa en esta fecha
                stay = Stay.query.filter(
                    Stay.room_id == room.id,
                    Stay.check_in_date <= datetime.combine(check_date, datetime.max.time()),
                    or_(
                        Stay.check_out_date.is_(None),
                        Stay.check_out_date >= datetime.combine(check_date, datetime.min.time())
                    )
                ).first()
                
                if stay:
                    status = 'occupied'
                    client_name = stay.client.full_name
                    details = f"Cliente: {client_name}"
                    if stay.check_out_date:
                        details += f" (Sale: {stay.check_out_date.strftime('%d/%m')})"
                else:
                    status = 'available'
                    client_name = None
                    details = "Disponible"
                
                room_data['availability'].append({
                    'date': check_date.strftime('%Y-%m-%d'),
                    'date_display': check_date.strftime('%d/%m'),
                    'status': status,
                    'client_name': client_name,
                    'details': details
                })
            
            availability_data.append(room_data)
        
        return jsonify({
            'success': True,
            'date_headers': [d.strftime('%d/%m') for d in date_range],
            'rooms': availability_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/client_search')
@login_required 
def client_search():
    """Búsqueda de clientes por término"""
    term = request.args.get('term', '').strip()
    if len(term) < 2:
        return jsonify([])
    
    clients = Client.query.filter(
        or_(
            Client.full_name.ilike(f'%{term}%'),
            Client.phone_number.ilike(f'%{term}%'),
            Client.email.ilike(f'%{term}%')
        )
    ).limit(10).all()
    
    results = []
    for client in clients:
        results.append({
            'id': client.id,
            'label': f"{client.full_name} - {client.phone_number}",
            'value': client.full_name,
            'phone': client.phone_number,
            'email': client.email or '',
            'visit_count': client.visit_count()
        })
    
    return jsonify(results)

@bp.route('/check_room_availability')
@login_required
def ajax_check_room_availability():
    """AJAX endpoint para verificar disponibilidad de habitaciones"""
    try:
        check_in_str = request.args.get('check_in')
        check_out_str = request.args.get('check_out')
        
        if not check_in_str or not check_out_str:
            return jsonify({'success': False, 'error': 'Fechas requeridas'})
        
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d')
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d')
        
        if check_in >= check_out:
            return jsonify({'success': False, 'error': 'La fecha de salida debe ser posterior a la de entrada'})
        
        unavailable_room_ids = check_room_availability(check_in, check_out)
        all_rooms = Room.query.all()
        
        rooms_data = []
        for room in all_rooms:
            is_available = room.id not in unavailable_room_ids
            rooms_data.append({
                'id': room.id,
                'name': room.name,
                'tier': room.get_tier_display(),
                'available': is_available,
                'status': 'Disponible' if is_available else 'Ocupada'
            })
        
        # Buscar soluciones si no hay habitaciones disponibles
        solutions = find_booking_solutions(check_in, check_out) if unavailable_room_ids else []
        
        return jsonify({
            'success': True,
            'rooms': rooms_data,
            'available_count': len([r for r in rooms_data if r['available']]),
            'total_count': len(rooms_data),
            'solutions': solutions
        })
        
    except ValueError:
        return jsonify({'success': False, 'error': 'Formato de fecha inválido'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/supply_alerts')
@login_required
def supply_alerts():
    """Obtiene alertas de inventario en tiempo real"""
    try:
        inventory_status = Supply.get_inventory_status()
        
        return jsonify({
            'success': True,
            'critical_count': inventory_status['critical_count'],
            'warning_count': inventory_status['warning_count'],
            'alerts': inventory_status['alerts'][:10]  # Limitar a 10 alertas
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/find_booking_solutions', methods=['POST'])
@login_required
def ajax_find_booking_solutions():
    """FASE 4.0 V4.0: Endpoint para el Motor de Yield Management"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data.get('check_in') or not data.get('check_out'):
            return jsonify({'success': False, 'error': 'Fechas de entrada y salida requeridas'})
        
        # Parsear fechas
        check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        
        if check_in >= check_out:
            return jsonify({'success': False, 'error': 'La fecha de salida debe ser posterior a la de entrada'})
        
        # Crear solicitud de reserva
        booking_request = BookingRequest(
            check_in=check_in,
            check_out=check_out,
            guests=int(data.get('guests', 2)),
            preferred_tier=data.get('preferred_tier'),
            max_budget=float(data['max_budget']) if data.get('max_budget') else None,
            client_id=int(data['client_id']) if data.get('client_id') else None,
            notes=data.get('notes')
        )
        
        # Ejecutar motor de yield management
        engine = YieldManagementEngine()
        solutions = engine.find_booking_solutions(booking_request)
        
        # Formatear soluciones para JSON
        formatted_solutions = []
        for solution in solutions:
            formatted_solution = {
                'solution_type': solution.solution_type.value,
                'priority': solution.priority.value,
                'title': solution.title,
                'description': solution.description,
                'rooms': solution.rooms,
                'estimated_price': solution.estimated_price,
                'confidence_score': solution.confidence_score,
                'additional_info': solution.additional_info or {}
            }
            
            # Agregar campos opcionales
            if solution.savings:
                formatted_solution['savings'] = solution.savings
            if solution.upgrade_benefit:
                formatted_solution['upgrade_benefit'] = solution.upgrade_benefit
            if solution.reallocation_details:
                formatted_solution['reallocation_details'] = solution.reallocation_details
            
            formatted_solutions.append(formatted_solution)
        
        return jsonify({
            'success': True,
            'solutions_count': len(solutions),
            'solutions': formatted_solutions,
            'request_summary': {
                'check_in': check_in.strftime('%d/%m/%Y'),
                'check_out': check_out.strftime('%d/%m/%Y'),
                'nights': (check_out - check_in).days,
                'guests': booking_request.guests,
                'preferred_tier': booking_request.preferred_tier
            }
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Error en formato de datos: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error del sistema: {str(e)}'})

# =====================================================================
# RUTAS AJAX PARA OPERACIONES CRUD
# =====================================================================

@bp.route('/quick_stay', methods=['POST'])
@login_required
def ajax_quick_stay():
    """Crear una estancia rápida vía AJAX"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['client_id', 'room_id', 'check_in_date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo requerido: {field}'})
        
        # Crear la estancia
        stay = Stay(
            client_id=data['client_id'],
            room_id=data['room_id'],
            check_in_date=datetime.strptime(data['check_in_date'], '%Y-%m-%d'),
            check_out_date=datetime.strptime(data['check_out_date'], '%Y-%m-%d') if data.get('check_out_date') else None,
            booking_channel=data.get('booking_channel', 'Directo'),
            status='Activa'
        )
        
        db.session.add(stay)
        db.session.flush()  # Para obtener el ID
        
        # Crear pago inicial si se proporciona
        if data.get('initial_payment') and float(data['initial_payment']) > 0:
            payment = Payment(
                stay_id=stay.id,
                amount=float(data['initial_payment']),
                method=data.get('payment_method', 'Efectivo'),
                payment_date=datetime.now()
            )
            db.session.add(payment)
        
        # === FASE 2 V3.0: DEDUCCIÓN AUTOMÁTICA DE INVENTARIO ===
        supply_results = apply_room_package_to_stay(stay, current_user.id)
        
        db.session.commit()
        
        # Obtener datos del cliente y habitación para la respuesta
        client = Client.query.get(stay.client_id)
        room = Room.query.get(stay.room_id)
        
        # Preparar información de suministros aplicados
        supply_info = ""
        if supply_results['applied_count'] > 0:
            supply_info = f" | {supply_results['applied_count']} suministros aplicados"
            if supply_results['warnings']:
                supply_info += f" | {len(supply_results['warnings'])} alertas"
        
        return jsonify({
            'success': True,
            'message': f'Estancia creada para {client.full_name} en {room.name}{supply_info}',
            'stay_id': stay.id,
            'client_name': client.full_name,
            'room_name': room.name,
            'supply_results': supply_results
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/quick_expense', methods=['POST'])
@login_required
def quick_expense():
    """Registrar un gasto rápido vía AJAX"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data.get('description') or not data.get('amount'):
            return jsonify({'success': False, 'error': 'Descripción y monto son requeridos'})
        
        expense = Expense(
            description=data['description'],
            amount=float(data['amount']),
            category=data.get('category', 'General'),
            paid_by_user_id=current_user.id,
            payment_method=data.get('payment_method', 'Efectivo'),
            expense_date=datetime.now()
        )
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Gasto registrado: DOP {expense.amount:,.2f}',
            'expense_id': expense.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/update_stock', methods=['POST'])
@login_required
@permission_required('can_manage_supplies')
def ajax_update_stock():
    """Actualizar stock de suministro vía AJAX"""
    try:
        data = request.get_json()
        
        supply_id = data.get('supply_id')
        action = data.get('action')  # 'add' o 'subtract'
        quantity = int(data.get('quantity', 0))
        
        if not supply_id or not action or quantity <= 0:
            return jsonify({'success': False, 'error': 'Datos inválidos'})
        
        supply = Supply.query.get_or_404(supply_id)
        
        if action == 'add':
            supply.current_stock += quantity
            message = f'Agregado {quantity} unidades a {supply.name}'
        elif action == 'subtract':
            if supply.current_stock < quantity:
                return jsonify({'success': False, 'error': 'Stock insuficiente'})
            supply.current_stock -= quantity
            message = f'Descontado {quantity} unidades de {supply.name}'
        else:
            return jsonify({'success': False, 'error': 'Acción inválida'})
        
        supply.last_updated = datetime.now()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'new_stock': supply.current_stock,
            'is_low_stock': supply.is_low_stock(),
            'status': supply.stock_status()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/dashboard_stats')
@login_required
def ajax_dashboard_stats():
    """Obtiene estadísticas actualizadas del dashboard"""
    try:
        stats = DashboardStats.get_panel_statistics()
        
        # Formatear datos para JSON
        return jsonify({
            'success': True,
            'stats': {
                'total_clients': stats['total_clients'],
                'active_stays': stats['active_stays'],
                'low_stock_count': stats['low_stock_count'],
                'monthly_income': f"DOP {stats['monthly_income']:,.2f}",
                'monthly_expenses': f"DOP {stats['monthly_expenses']:,.2f}",
                'monthly_profit': f"DOP {stats['monthly_profit']:,.2f}"
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# =====================================================================
# RUTAS AJAX PARA GESTIÓN DE ESTANCIAS
# =====================================================================

@bp.route('/close_stay', methods=['POST'])
@login_required
def ajax_close_stay():
    """Cerrar una estancia vía AJAX"""
    try:
        data = request.get_json()
        stay_id = data.get('stay_id')
        
        if not stay_id:
            return jsonify({'success': False, 'error': 'ID de estancia requerido'})
        
        stay = Stay.query.get_or_404(stay_id)
        
        if stay.status == 'Finalizada':
            return jsonify({'success': False, 'error': 'La estancia ya está finalizada'})
        
        # Actualizar estado
        stay.status = 'Finalizada'
        if not stay.check_out_date:
            stay.check_out_date = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Estancia de {stay.client.full_name} finalizada',
            'stay_id': stay.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/extend_stay', methods=['POST'])
@login_required
def ajax_extend_stay():
    """Extender una estancia vía AJAX"""
    try:
        data = request.get_json()
        stay_id = data.get('stay_id')
        new_checkout = data.get('new_checkout_date')
        
        if not stay_id or not new_checkout:
            return jsonify({'success': False, 'error': 'Datos requeridos faltantes'})
        
        stay = Stay.query.get_or_404(stay_id)
        new_date = datetime.strptime(new_checkout, '%Y-%m-%d')
        
        if stay.check_out_date and new_date <= stay.check_out_date:
            return jsonify({'success': False, 'error': 'La nueva fecha debe ser posterior a la actual'})
        
        stay.check_out_date = new_date
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Estancia extendida hasta {new_date.strftime("%d/%m/%Y")}',
            'new_date': new_date.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# =====================================================================
# FUNCIONES AUXILIARES PARA GESTIÓN DE INVENTARIO AUTOMÁTICO
# =====================================================================

def apply_room_package_to_stay(stay, verified_by_user_id=None):
    """
    FASE 2 V3.0: Aplica el paquete de suministros de la habitación a una estancia
    y deduce automáticamente del inventario.
    
    Returns:
        dict: Resultado de la aplicación con estadísticas y alertas
    """
    try:
        from app.models import SupplyUsage, Supply, room_supply_defaults
        
        results = {
            'applied_count': 0,
            'skipped_count': 0,
            'warnings': [],
            'errors': [],
            'items_applied': [],
            'insufficient_stock': []
        }
        
        if not stay.room:
            results['errors'].append('Habitación no encontrada')
            return results
        
        # Obtener paquete de la habitación
        package_items = stay.room.get_mandatory_supplies()  # Solo obligatorios por defecto
        
        if not package_items:
            results['warnings'].append(f'Habitación {stay.room.name} no tiene paquete configurado')
            return results
        
        for package_item in package_items:
            try:
                # V4.0: Verificar si ya existe uso para este suministro en esta estancia
                existing_usage = SupplyUsage.query.filter_by(
                    stay_id=stay.id,
                    supply_id=package_item.id,  # package_item.id es el supply_id
                    room_id=stay.room_id
                ).first()
                
                if existing_usage:
                    results['skipped_count'] += 1
                    continue
                
                # V4.0: Obtener el suministro directamente
                supply = Supply.query.get(package_item.id)  # package_item.id es supply_id
                if not supply:
                    results['errors'].append(f'Suministro ID {package_item.id} no encontrado')
                    continue
                
                # Verificar stock disponible
                if supply.current_stock < package_item.quantity:
                    results['insufficient_stock'].append({
                        'supply_name': supply.name,
                        'required': package_item.quantity,
                        'available': supply.current_stock,
                        'shortage': package_item.quantity - supply.current_stock
                    })
                    
                    # Crear uso con la cantidad disponible si hay algo
                    if supply.current_stock > 0:
                        usage_quantity = supply.current_stock
                        results['warnings'].append(
                            f'{supply.name}: Solo {usage_quantity} de {package_item.quantity} disponibles'
                        )
                    else:
                        results['warnings'].append(f'{supply.name}: Sin stock disponible')
                        continue
                else:
                    usage_quantity = package_item.quantity
                
                # V4.0: Crear registro de uso
                usage = SupplyUsage.create_from_package(
                    stay_id=stay.id,
                    package_item=package_item,
                    usage_type='Automático',
                    verified_by_user_id=verified_by_user_id
                )
                
                # Ajustar cantidad si hay stock insuficiente
                if usage_quantity != package_item.quantity:
                    usage.quantity_used = usage_quantity
                    usage.total_cost = usage.calculate_cost()
                
                # Deducir del inventario
                supply.current_stock -= usage_quantity
                supply.last_updated = datetime.now()
                
                db.session.add(usage)
                
                results['applied_count'] += 1
                results['items_applied'].append({
                    'supply_name': supply.name,
                    'quantity_used': usage_quantity,
                    'quantity_expected': package_item.quantity,
                    'cost': usage.calculate_cost(),
                    'new_stock': supply.current_stock
                })
                
                # Crear alerta si el stock queda bajo
                if supply.is_low_stock():
                    results['warnings'].append(
                        f'{supply.name}: Stock bajo después de deducir ({supply.current_stock} restantes)'
                    )
                
            except Exception as e:
                results['errors'].append(f'Error procesando {package_item.supply.name if package_item.supply else "suministro"}: {str(e)}')
        
        # Agregar resumen
        if results['applied_count'] > 0:
            total_cost = sum(item['cost'] for item in results['items_applied'])
            results['summary'] = {
                'total_items': results['applied_count'],
                'total_cost': total_cost,
                'average_cost_per_item': total_cost / results['applied_count'] if results['applied_count'] > 0 else 0
            }
        
        return results
        
    except Exception as e:
        return {
            'applied_count': 0,
            'skipped_count': 0,
            'warnings': [],
            'errors': [f'Error crítico aplicando paquete: {str(e)}'],
            'items_applied': [],
            'insufficient_stock': []
        }