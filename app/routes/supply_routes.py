"""
AIRBNB MANAGER V3.0 - RUTAS DE GESTIÓN DE PAQUETES DE SUMINISTROS
Contiene las rutas para gestionar paquetes de suministros por habitación
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime

from app.extensions import db
from app.models import Room, Supply, SupplyUsage, room_supply_defaults
from app.decorators import permission_required, management_required

bp = Blueprint('supply_packages', __name__, url_prefix='/supply-packages')

# =====================================================================
# RUTAS PRINCIPALES DE GESTIÓN DE PAQUETES
# =====================================================================

@bp.route('/')
@login_required
@permission_required('can_manage_supplies')
def index():
    """Panel principal de gestión de paquetes de suministros"""
    rooms = Room.query.order_by(Room.name).all()
    supplies = Supply.query.order_by(Supply.category, Supply.name).all()
    
    # Obtener estadísticas de paquetes
    rooms_with_packages = []
    for room in rooms:
        package_summary = room.get_package_summary()
        rooms_with_packages.append({
            'room': room,
            'summary': package_summary
        })
    
    return render_template('supply_packages/index.html',
                         title='Gestión de Paquetes de Suministros',
                         rooms_with_packages=rooms_with_packages,
                         total_rooms=len(rooms),
                         total_supplies=len(supplies))

@bp.route('/room/<int:room_id>')
@login_required
@permission_required('can_manage_supplies')
def room_package(room_id):
    """Gestionar paquete de suministros para una habitación específica"""
    room = Room.query.get_or_404(room_id)
    package_items = room.get_supply_package()
    available_supplies = Supply.query.order_by(Supply.category, Supply.name).all()
    
    # Suministros ya incluidos en el paquete
    included_supply_ids = [item.supply_id for item in package_items]
    available_supplies = [s for s in available_supplies if s.id not in included_supply_ids]
    
    package_summary = room.get_package_summary()
    
    return render_template('supply_packages/room_package.html',
                         title=f'Paquete de {room.name}',
                         room=room,
                         package_items=package_items,
                         available_supplies=available_supplies,
                         package_summary=package_summary)

@bp.route('/analytics')
@login_required
@permission_required('can_view_reports')
def analytics():
    """Panel de análisis de uso de paquetes de suministros"""
    
    # Estadísticas generales
    total_packages = db.session.query(func.count(room_supply_defaults.c.room_id)).scalar() or 0
    rooms_with_packages = db.session.query(func.count(func.distinct(room_supply_defaults.c.room_id))).scalar() or 0
    total_rooms = Room.query.count()
    
    # Top suministros más usados
    supply_usage_stats = db.session.query(
        Supply.name,
        Supply.category,
        func.count(room_supply_defaults.c.room_id).label('room_count'),
        func.sum(room_supply_defaults.c.quantity).label('total_quantity')
    ).join(room_supply_defaults, Supply.id == room_supply_defaults.c.supply_id)\
     .group_by(Supply.id, Supply.name, Supply.category)\
     .order_by(func.count(room_supply_defaults.c.room_id).desc()).limit(10).all()
    
    # Costos promedio por habitación
    room_costs = []
    for room in Room.query.all():
        cost = room.calculate_package_cost()
        if cost > 0:
            room_costs.append({
                'room_name': room.name,
                'tier': room.get_tier_display(),
                'package_cost': cost,
                'item_count': len(room.get_supply_package())
            })
    
    room_costs.sort(key=lambda x: x['package_cost'], reverse=True)
    
    # Estadísticas de uso reciente (últimos 30 días)
    recent_usages = SupplyUsage.query.filter(
        SupplyUsage.usage_date >= func.date('now', '-30 days')
    ).count()
    
    return render_template('supply_packages/analytics.html',
                         title='Análisis de Paquetes de Suministros',
                         total_packages=total_packages,
                         rooms_with_packages=rooms_with_packages,
                         total_rooms=total_rooms,
                         coverage_percentage=(rooms_with_packages/total_rooms*100) if total_rooms > 0 else 0,
                         supply_usage_stats=supply_usage_stats,
                         room_costs=room_costs,
                         recent_usages=recent_usages)

# =====================================================================
# RUTAS AJAX PARA OPERACIONES CRUD
# =====================================================================

@bp.route('/ajax/add_item', methods=['POST'])
@login_required
@permission_required('can_manage_supplies')
def ajax_add_item():
    """Agregar un suministro al paquete de una habitación"""
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        supply_id = data.get('supply_id')
        quantity = int(data.get('quantity', 1))
        is_mandatory = data.get('is_mandatory', True)
        usage_type = data.get('usage_type', 'Automático')
        notes = data.get('notes', '')
        
        # Validaciones
        if not room_id or not supply_id:
            return jsonify({'success': False, 'error': 'Room ID y Supply ID son requeridos'})
        
        room = Room.query.get(room_id)
        supply = Supply.query.get(supply_id)
        
        if not room or not supply:
            return jsonify({'success': False, 'error': 'Habitación o suministro no encontrado'})
        
        # V4.0: Verificar si ya existe usando tabla de asociación
        existing = db.session.execute(
            room_supply_defaults.select().where(
                (room_supply_defaults.c.room_id == room_id) & 
                (room_supply_defaults.c.supply_id == supply_id)
            )
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Este suministro ya está en el paquete'})
        
        # Crear nuevo item del paquete usando insert
        db.session.execute(
            room_supply_defaults.insert().values(
                room_id=room_id,
                supply_id=supply_id,
                quantity=quantity,
                is_mandatory=is_mandatory,
                usage_type=usage_type,
                notes=notes,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        )
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{supply.name} agregado al paquete de {room.name}',
            'item': {
                'supply_name': supply.name,
                'quantity': quantity,
                'is_mandatory': is_mandatory,
                'cost': quantity * (supply.unit_price or 0)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/ajax/update_item', methods=['POST'])
@login_required
@permission_required('can_manage_supplies')
def ajax_update_item():
    """Actualizar un item del paquete - TEMPORALMENTE DESHABILITADO V4.0"""
    return jsonify({'success': False, 'error': 'Función temporalmente deshabilitada en V4.0'})

@bp.route('/ajax/remove_item', methods=['POST'])
@login_required
@permission_required('can_manage_supplies')
def ajax_remove_item():
    """Eliminar un item del paquete - TEMPORALMENTE DESHABILITADO V4.0"""
    return jsonify({'success': False, 'error': 'Función temporalmente deshabilitada en V4.0'})

@bp.route('/ajax/copy_package', methods=['POST'])
@login_required
@permission_required('can_manage_supplies')
def ajax_copy_package():
    """Copiar paquete de una habitación a otra - TEMPORALMENTE DESHABILITADO V4.0"""
    return jsonify({'success': False, 'error': 'Función temporalmente deshabilitada en V4.0'})

@bp.route('/ajax/get_package_summary/<int:room_id>')
@login_required
@permission_required('can_manage_supplies')
def ajax_get_package_summary(room_id):
    """Obtener resumen del paquete de una habitación"""
    try:
        room = Room.query.get_or_404(room_id)
        summary = room.get_package_summary()
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# =====================================================================
# RUTAS DE PLANTILLAS PREDEFINIDAS
# =====================================================================

@bp.route('/templates')
@login_required
@management_required
def templates():
    """Gestionar plantillas predefinidas de paquetes"""
    
    # Por ahora, mostrar paquetes existentes que pueden servir como plantillas
    template_packages = []
    for room in Room.query.all():
        if room.has_supply_package():
            summary = room.get_package_summary()
            template_packages.append({
                'room': room,
                'summary': summary
            })
    
    return render_template('supply_packages/templates.html',
                         title='Plantillas de Paquetes',
                         template_packages=template_packages)

@bp.route('/ajax/apply_template', methods=['POST'])
@login_required
@management_required
def ajax_apply_template():
    """Aplicar una plantilla a múltiples habitaciones"""
    try:
        data = request.get_json()
        template_room_id = data.get('template_room_id')
        target_room_ids = data.get('target_room_ids', [])
        overwrite = data.get('overwrite', False)
        
        template_room = Room.query.get_or_404(template_room_id)
        template_package = template_room.get_supply_package()
        
        if not template_package:
            return jsonify({'success': False, 'error': 'La plantilla no tiene paquete configurado'})
        
        applied_count = 0
        for target_room_id in target_room_ids:
            target_room = Room.query.get(target_room_id)
            if not target_room:
                continue
            
            # Verificar si ya tiene paquete
            if not overwrite and target_room.has_supply_package():
                continue
            
            # Eliminar paquete existente si overwrite
            if overwrite:
                RoomSupplyDefault.query.filter_by(room_id=target_room_id).delete()
            
            # Copiar items
            for template_item in template_package:
                existing = RoomSupplyDefault.query.filter_by(
                    room_id=target_room_id,
                    supply_id=template_item.supply_id
                ).first()
                
                if not existing:
                    new_item = RoomSupplyDefault(
                        room_id=target_room_id,
                        supply_id=template_item.supply_id,
                        quantity=template_item.quantity,
                        is_mandatory=template_item.is_mandatory,
                        usage_type=template_item.usage_type,
                        notes=f"Aplicado desde plantilla: {template_room.name}"
                    )
                    db.session.add(new_item)
            
            applied_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Plantilla aplicada a {applied_count} habitaciones',
            'applied_count': applied_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})