"""
AIRBNB MANAGER V3.0 - RUTAS DEL MOTOR DE INTELIGENCIA
Endpoints para el sistema inteligente de sugerencias y análisis de disponibilidad
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required
from datetime import datetime, date, timedelta
from typing import Dict, List

from app.extensions import db
from app.models import Room, Stay, Client
from app.intelligence import AvailabilityEngine, BookingRequest, BookingPatternAnalyzer
from app.intelligence_notifications import get_notifications_for_dashboard
from app.decorators import permission_required

bp = Blueprint('intelligence', __name__, url_prefix='/intelligence')

# =====================================================================
# RUTAS PRINCIPALES DEL MOTOR DE INTELIGENCIA
# =====================================================================

@bp.route('/suggest_availability', methods=['POST'])
@login_required
def suggest_availability():
    """
    Endpoint principal para obtener sugerencias inteligentes de disponibilidad
    """
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        check_in_str = data.get('check_in')
        check_out_str = data.get('check_out')
        
        if not check_in_str or not check_out_str:
            return jsonify({
                'success': False, 
                'error': 'Fechas de check-in y check-out son requeridas'
            })
        
        # Parsear fechas
        try:
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False, 
                'error': 'Formato de fecha inválido (YYYY-MM-DD)'
            })
        
        # Validar fechas
        if check_in >= check_out:
            return jsonify({
                'success': False, 
                'error': 'La fecha de check-out debe ser posterior al check-in'
            })
        
        if check_in < date.today():
            return jsonify({
                'success': False, 
                'error': 'La fecha de check-in no puede ser en el pasado'
            })
        
        # Crear solicitud de reserva
        booking_request = BookingRequest(
            check_in=check_in,
            check_out=check_out,
            guests=data.get('guests', 2),
            preferred_tier=data.get('preferred_tier'),
            max_budget=float(data.get('max_budget')) if data.get('max_budget') else None,
            client_id=int(data.get('client_id')) if data.get('client_id') else None,
            flexible_dates=data.get('flexible_dates', False),
            flexible_days=int(data.get('flexible_days', 3))
        )
        
        # Ejecutar motor de inteligencia
        engine = AvailabilityEngine()
        suggestions = engine.analyze_availability(booking_request)
        
        # Formatear respuesta
        formatted_suggestions = []
        for suggestion in suggestions:
            formatted_suggestion = {
                'type': suggestion.suggestion_type.value,
                'priority': suggestion.priority.value,
                'title': suggestion.title,
                'description': suggestion.description,
                'confidence_score': round(suggestion.confidence_score, 2),
                'room_id': suggestion.room_id,
                'room_name': suggestion.room_name,
                'estimated_price': suggestion.estimated_price,
                'savings': suggestion.savings,
                'upgrade_value': suggestion.upgrade_value
            }
            
            # Agregar fechas alternativas si existen
            if suggestion.alternative_dates:
                formatted_suggestion['alternative_dates'] = {
                    'check_in': suggestion.alternative_dates[0].strftime('%Y-%m-%d'),
                    'check_out': suggestion.alternative_dates[1].strftime('%Y-%m-%d'),
                    'check_in_display': suggestion.alternative_dates[0].strftime('%d/%m/%Y'),
                    'check_out_display': suggestion.alternative_dates[1].strftime('%d/%m/%Y')
                }
            
            # Agregar información adicional
            if suggestion.additional_info:
                formatted_suggestion['additional_info'] = suggestion.additional_info
            
            formatted_suggestions.append(formatted_suggestion)
        
        # Estadísticas de la consulta
        stats = {
            'total_suggestions': len(suggestions),
            'high_priority_count': len([s for s in suggestions if s.priority.value == 'high']),
            'direct_availability_count': len([s for s in suggestions if s.suggestion_type.value == 'available_room']),
            'alternative_options_count': len(suggestions) - len([s for s in suggestions if s.suggestion_type.value == 'available_room']),
            'nights_requested': (check_out - check_in).days
        }
        
        return jsonify({
            'success': True,
            'suggestions': formatted_suggestions,
            'stats': stats,
            'request_summary': {
                'check_in': check_in.strftime('%d/%m/%Y'),
                'check_out': check_out.strftime('%d/%m/%Y'),
                'nights': (check_out - check_in).days,
                'guests': booking_request.guests,
                'preferred_tier': booking_request.preferred_tier,
                'flexible_dates': booking_request.flexible_dates
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Error interno: {str(e)}'
        })

@bp.route('/quick_availability_check', methods=['POST'])
@login_required
def quick_availability_check():
    """
    Verificación rápida de disponibilidad sin sugerencias complejas
    """
    try:
        data = request.get_json()
        
        check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        
        # Obtener habitaciones ocupadas
        overlapping_stays = Stay.query.filter(
            Stay.status.in_(['Activa', 'Pendiente de Cierre']),
            Stay.check_in_date < check_out,
            db.or_(
                Stay.check_out_date.is_(None),
                Stay.check_out_date > check_in
            )
        ).all()
        
        occupied_room_ids = [stay.room_id for stay in overlapping_stays]
        
        # Obtener habitaciones disponibles
        available_rooms = Room.query.filter(~Room.id.in_(occupied_room_ids)).all()
        
        # Formatear respuesta
        rooms_data = []
        for room in available_rooms:
            # Calcular precio estimado básico
            nights = (check_out - check_in).days
            base_prices = {
                'Económica': 2000, 'Estándar': 3000, 
                'Superior': 4500, 'Suite': 6000
            }
            estimated_price = base_prices.get(room.tier, 3000) * nights
            
            rooms_data.append({
                'id': room.id,
                'name': room.name,
                'tier': room.tier,
                'tier_display': room.get_tier_display(),
                'status': room.status,
                'estimated_price': estimated_price,
                'has_package': room.has_supply_package()
            })
        
        return jsonify({
            'success': True,
            'available_rooms': rooms_data,
            'total_available': len(available_rooms),
            'total_rooms': Room.query.count(),
            'occupancy_rate': round((len(occupied_room_ids) / Room.query.count()) * 100, 1)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/analyze_patterns')
@login_required
@permission_required('can_view_reports')
def analyze_patterns():
    """
    Análisis de patrones de reserva para insights de negocio
    """
    try:
        analyzer = BookingPatternAnalyzer()
        
        # Patrones estacionales
        seasonal_patterns = analyzer.analyze_seasonal_patterns()
        
        # Demanda por tier
        tier_demand = analyzer.get_room_tier_demand()
        
        # Estadísticas generales
        total_rooms = Room.query.count()
        active_stays = Stay.query.filter(Stay.status == 'Activa').count()
        
        # Tendencias de los últimos 30 días
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_bookings = Stay.query.filter(
            Stay.check_in_date >= thirty_days_ago
        ).count()
        
        # Análisis de duración promedio de estancias
        avg_duration_query = db.session.query(
            db.func.avg(
                db.func.julianday(Stay.check_out_date) - 
                db.func.julianday(Stay.check_in_date)
            ).label('avg_duration')
        ).filter(
            Stay.check_out_date.isnot(None),
            Stay.check_in_date >= thirty_days_ago
        ).first()
        
        avg_duration = round(float(avg_duration_query.avg_duration), 1) if avg_duration_query.avg_duration else 0
        
        return jsonify({
            'success': True,
            'patterns': {
                'seasonal': seasonal_patterns,
                'tier_demand': tier_demand,
                'recent_trends': {
                    'bookings_last_30_days': recent_bookings,
                    'current_occupancy': active_stays,
                    'occupancy_rate': round((active_stays / total_rooms) * 100, 1),
                    'avg_stay_duration': avg_duration
                }
            },
            'insights': generate_business_insights(seasonal_patterns, tier_demand, active_stays, total_rooms)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/optimize_pricing/<int:room_id>')
@login_required
@permission_required('can_view_reports')
def optimize_pricing(room_id):
    """
    Sugerencias de optimización de precios para una habitación específica
    """
    try:
        room = Room.query.get_or_404(room_id)
        analyzer = BookingPatternAnalyzer()
        
        # Obtener precio optimizado para los próximos 30 días
        pricing_suggestions = []
        today = date.today()
        
        for i in range(30):
            target_date = today + timedelta(days=i)
            optimal_price = analyzer.predict_optimal_pricing(room, target_date)
            
            # Verificar disponibilidad
            is_available = not Stay.query.filter(
                Stay.room_id == room_id,
                Stay.status.in_(['Activa', 'Pendiente de Cierre']),
                Stay.check_in_date <= target_date,
                db.or_(
                    Stay.check_out_date.is_(None),
                    Stay.check_out_date > target_date
                )
            ).first()
            
            pricing_suggestions.append({
                'date': target_date.strftime('%Y-%m-%d'),
                'date_display': target_date.strftime('%d/%m'),
                'optimal_price': round(optimal_price, 0),
                'is_available': is_available,
                'day_of_week': target_date.strftime('%A'),
                'is_weekend': target_date.weekday() >= 5
            })
        
        # Estadísticas históricas de la habitación
        historical_stats = db.session.query(
            db.func.count(Stay.id).label('total_bookings'),
            db.func.avg(Payment.amount).label('avg_payment'),
            db.func.sum(Payment.amount).label('total_revenue')
        ).join(Stay).join(Payment).filter(
            Stay.room_id == room_id,
            Stay.check_in_date >= datetime.now() - timedelta(days=365)
        ).first()
        
        return jsonify({
            'success': True,
            'room': {
                'id': room.id,
                'name': room.name,
                'tier': room.tier,
                'tier_display': room.get_tier_display()
            },
            'pricing_suggestions': pricing_suggestions,
            'historical_stats': {
                'total_bookings': historical_stats.total_bookings or 0,
                'avg_payment': round(float(historical_stats.avg_payment), 2) if historical_stats.avg_payment else 0,
                'total_revenue': round(float(historical_stats.total_revenue), 2) if historical_stats.total_revenue else 0
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/client_insights/<int:client_id>')
@login_required
def client_insights(client_id):
    """
    Insights personalizados para un cliente específico
    """
    try:
        client = Client.query.get_or_404(client_id)
        
        # Historial de estancias
        stays = client.stays.order_by(Stay.check_in_date.desc()).limit(10).all()
        
        # Calcular patrones del cliente
        total_stays = client.visit_count()
        total_spent = client.total_spent()
        avg_per_stay = total_spent / total_stays if total_stays > 0 else 0
        
        # Preferencias detectadas
        tier_preferences = {}
        channel_preferences = {}
        duration_patterns = []
        
        for stay in stays:
            # Tier preferido
            if stay.room:
                tier_preferences[stay.room.tier] = tier_preferences.get(stay.room.tier, 0) + 1
            
            # Canal de reserva preferido
            channel_preferences[stay.booking_channel] = channel_preferences.get(stay.booking_channel, 0) + 1
            
            # Duración de estancias
            if stay.check_out_date:
                duration = (stay.check_out_date.date() - stay.check_in_date.date()).days
                duration_patterns.append(duration)
        
        # Tier más usado
        preferred_tier = max(tier_preferences.items(), key=lambda x: x[1])[0] if tier_preferences else None
        
        # Canal más usado
        preferred_channel = max(channel_preferences.items(), key=lambda x: x[1])[0] if channel_preferences else None
        
        # Duración promedio
        avg_duration = sum(duration_patterns) / len(duration_patterns) if duration_patterns else 0
        
        # Generar recomendaciones personalizadas
        recommendations = []
        
        if preferred_tier:
            recommendations.append(f"Cliente prefiere habitaciones {preferred_tier}")
        
        if avg_duration > 5:
            recommendations.append("Cliente hace estancias largas - ofrecer descuentos por semana")
        
        if total_spent > 50000:  # Cliente VIP
            recommendations.append("Cliente VIP - considerar upgrades automáticos")
        
        return jsonify({
            'success': True,
            'client': {
                'id': client.id,
                'name': client.full_name,
                'total_stays': total_stays,
                'total_spent': total_spent,
                'avg_per_stay': round(avg_per_stay, 2)
            },
            'preferences': {
                'preferred_tier': preferred_tier,
                'preferred_channel': preferred_channel,
                'avg_duration': round(avg_duration, 1),
                'tier_distribution': tier_preferences,
                'channel_distribution': channel_preferences
            },
            'recommendations': recommendations,
            'recent_stays': [
                {
                    'check_in': stay.check_in_date.strftime('%d/%m/%Y'),
                    'room_name': stay.room.name if stay.room else 'N/A',
                    'tier': stay.room.tier if stay.room else 'N/A',
                    'amount_paid': stay.total_paid(),
                    'booking_channel': stay.booking_channel
                }
                for stay in stays[:5]
            ]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/dashboard_notifications')
@login_required
def dashboard_notifications():
    """
    Obtiene notificaciones inteligentes para el dashboard
    """
    try:
        notifications_data = get_notifications_for_dashboard()
        return jsonify({
            'success': True,
            'data': notifications_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# =====================================================================
# FUNCIONES AUXILIARES
# =====================================================================

def generate_business_insights(seasonal_patterns: Dict, tier_demand: Dict, active_stays: int, total_rooms: int) -> List[str]:
    """
    Genera insights de negocio basados en los patrones analizados
    """
    insights = []
    
    # Análisis de ocupación
    occupancy_rate = (active_stays / total_rooms) * 100
    if occupancy_rate > 80:
        insights.append("🔥 Alta ocupación actual - considerar aumentar precios")
    elif occupancy_rate < 30:
        insights.append("📉 Baja ocupación - implementar promociones")
    
    # Análisis estacional
    if seasonal_patterns:
        current_month = datetime.now().month
        current_month_data = seasonal_patterns.get(current_month, {})
        
        # Comparar con promedio
        avg_bookings = sum(data.get('bookings', 0) for data in seasonal_patterns.values()) / len(seasonal_patterns)
        current_bookings = current_month_data.get('bookings', 0)
        
        if current_bookings > avg_bookings * 1.2:
            insights.append("📈 Temporada alta detectada - optimizar precios")
        elif current_bookings < avg_bookings * 0.8:
            insights.append("📊 Temporada baja - activar estrategias de marketing")
    
    # Análisis de demanda por tier
    if tier_demand:
        max_demand_tier = max(tier_demand.items(), key=lambda x: x[1].get('bookings', 0))[0]
        insights.append(f"⭐ Mayor demanda en tier: {max_demand_tier}")
        
        # Identificar tier con mejor rentabilidad
        tier_profitability = {
            tier: data.get('avg_payment', 0) * data.get('bookings', 0)
            for tier, data in tier_demand.items()
        }
        most_profitable = max(tier_profitability.items(), key=lambda x: x[1])[0]
        insights.append(f"💰 Tier más rentable: {most_profitable}")
    
    return insights