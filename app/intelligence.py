"""
AIRBNB MANAGER V3.0 - MOTOR DE INTELIGENCIA PARA RESERVAS
Sistema inteligente para análisis de disponibilidad, optimización de reservas y sugerencias automáticas
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math
from collections import defaultdict
from sqlalchemy import func, and_, or_

from app.extensions import db
from app.models import Room, Stay, Client, Payment, room_supply_defaults


class PriorityLevel(Enum):
    """Niveles de prioridad para las sugerencias"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium" 
    LOW = "low"
    INFO = "info"


class SuggestionType(Enum):
    """Tipos de sugerencias que puede generar el motor"""
    AVAILABLE_ROOM = "available_room"
    ALTERNATIVE_DATES = "alternative_dates"
    ROOM_UPGRADE = "room_upgrade"
    EARLY_CHECKIN = "early_checkin"
    LATE_CHECKOUT = "late_checkout"
    SPLIT_STAY = "split_stay"
    WAITING_LIST = "waiting_list"
    PRICE_OPTIMIZATION = "price_optimization"


@dataclass
class BookingRequest:
    """Estructura de datos para una solicitud de reserva"""
    check_in: date
    check_out: date
    guests: int = 2
    preferred_tier: Optional[str] = None
    max_budget: Optional[float] = None
    client_id: Optional[int] = None
    flexible_dates: bool = False
    flexible_days: int = 3
    

@dataclass
class AvailabilitySuggestion:
    """Estructura de datos para una sugerencia de disponibilidad"""
    suggestion_type: SuggestionType
    priority: PriorityLevel
    title: str
    description: str
    room_id: Optional[int] = None
    room_name: Optional[str] = None
    alternative_dates: Optional[Tuple[date, date]] = None
    estimated_price: Optional[float] = None
    confidence_score: float = 0.0
    savings: Optional[float] = None
    upgrade_value: Optional[str] = None
    additional_info: Dict = None


class AvailabilityEngine:
    """Motor principal de análisis de disponibilidad inteligente"""
    
    def __init__(self):
        self.confidence_weights = {
            'historical_data': 0.3,
            'current_occupancy': 0.25,
            'seasonal_patterns': 0.2,
            'room_tier_demand': 0.15,
            'price_sensitivity': 0.1
        }
    
    def analyze_availability(self, request: BookingRequest) -> List[AvailabilitySuggestion]:
        """
        Análisis principal de disponibilidad con múltiples estrategias inteligentes
        """
        suggestions = []
        
        # 1. Verificar disponibilidad directa
        direct_availability = self._check_direct_availability(request)
        suggestions.extend(direct_availability)
        
        # 2. Si no hay disponibilidad directa, buscar alternativas
        if not any(s.suggestion_type == SuggestionType.AVAILABLE_ROOM for s in direct_availability):
            
            # 2.1 Fechas alternativas flexibles
            if request.flexible_dates:
                date_alternatives = self._find_flexible_date_alternatives(request)
                suggestions.extend(date_alternatives)
            
            # 2.2 Upgrades disponibles
            upgrade_suggestions = self._find_upgrade_opportunities(request)
            suggestions.extend(upgrade_suggestions)
            
            # 2.3 Estancias divididas
            split_suggestions = self._find_split_stay_options(request)
            suggestions.extend(split_suggestions)
            
            # 2.4 Check-in temprano / Check-out tardío
            timing_suggestions = self._find_timing_optimizations(request)
            suggestions.extend(timing_suggestions)
        
        # 3. Optimizaciones de precio
        price_suggestions = self._find_price_optimizations(request, suggestions)
        suggestions.extend(price_suggestions)
        
        # 4. Ordenar por prioridad y confianza
        suggestions = self._rank_suggestions(suggestions)
        
        return suggestions[:10]  # Limitar a las 10 mejores sugerencias
    
    def _check_direct_availability(self, request: BookingRequest) -> List[AvailabilitySuggestion]:
        """Verifica disponibilidad directa para las fechas exactas"""
        suggestions = []
        
        # Obtener habitaciones ocupadas en el período
        occupied_rooms = self._get_occupied_rooms(request.check_in, request.check_out)
        
        # Filtrar habitaciones disponibles
        available_rooms = Room.query.filter(~Room.id.in_(occupied_rooms)).all()
        
        # Aplicar filtros de preferencia
        if request.preferred_tier:
            available_rooms = [r for r in available_rooms if r.tier == request.preferred_tier]
        
        for room in available_rooms:
            # Calcular precio estimado
            estimated_price = self._estimate_room_price(room, request)
            
            # Verificar presupuesto
            if request.max_budget and estimated_price > request.max_budget:
                continue
            
            # Calcular confianza basada en datos históricos
            confidence = self._calculate_room_confidence(room, request)
            
            suggestion = AvailabilitySuggestion(
                suggestion_type=SuggestionType.AVAILABLE_ROOM,
                priority=PriorityLevel.HIGH,
                title=f"✅ {room.name} Disponible",
                description=f"{room.get_tier_display()} disponible para las fechas solicitadas",
                room_id=room.id,
                room_name=room.name,
                estimated_price=estimated_price,
                confidence_score=confidence,
                additional_info={
                    'tier': room.tier,
                    'nights': (request.check_out - request.check_in).days,
                    'tier_display': room.get_tier_display()
                }
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _find_flexible_date_alternatives(self, request: BookingRequest) -> List[AvailabilitySuggestion]:
        """Encuentra alternativas con fechas flexibles"""
        suggestions = []
        stay_duration = (request.check_out - request.check_in).days
        
        # Buscar en un rango de días flexibles antes y después
        for offset in range(-request.flexible_days, request.flexible_days + 1):
            if offset == 0:  # Ya verificamos las fechas exactas
                continue
                
            alt_check_in = request.check_in + timedelta(days=offset)
            alt_check_out = alt_check_in + timedelta(days=stay_duration)
            
            # Crear request alternativo
            alt_request = BookingRequest(
                check_in=alt_check_in,
                check_out=alt_check_out,
                guests=request.guests,
                preferred_tier=request.preferred_tier,
                max_budget=request.max_budget,
                client_id=request.client_id
            )
            
            # Verificar disponibilidad
            occupied_rooms = self._get_occupied_rooms(alt_check_in, alt_check_out)
            available_rooms = Room.query.filter(~Room.id.in_(occupied_rooms)).all()
            
            if request.preferred_tier:
                available_rooms = [r for r in available_rooms if r.tier == request.preferred_tier]
            
            for room in available_rooms[:3]:  # Limitar a 3 mejores opciones por fecha
                estimated_price = self._estimate_room_price(room, alt_request)
                
                if request.max_budget and estimated_price > request.max_budget:
                    continue
                
                # Calcular penalización por cambio de fecha
                date_penalty = abs(offset) * 0.1
                confidence = self._calculate_room_confidence(room, alt_request) - date_penalty
                
                direction = "antes" if offset < 0 else "después"
                days_diff = abs(offset)
                
                suggestion = AvailabilitySuggestion(
                    suggestion_type=SuggestionType.ALTERNATIVE_DATES,
                    priority=PriorityLevel.MEDIUM,
                    title=f"📅 {room.name} - {days_diff} día(s) {direction}",
                    description=f"{room.get_tier_display()} disponible {alt_check_in.strftime('%d/%m')} - {alt_check_out.strftime('%d/%m')}",
                    room_id=room.id,
                    room_name=room.name,
                    alternative_dates=(alt_check_in, alt_check_out),
                    estimated_price=estimated_price,
                    confidence_score=confidence,
                    additional_info={
                        'date_offset': offset,
                        'tier': room.tier,
                        'original_dates': (request.check_in, request.check_out)
                    }
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _find_upgrade_opportunities(self, request: BookingRequest) -> List[AvailabilitySuggestion]:
        """Encuentra oportunidades de upgrade a habitaciones superiores"""
        suggestions = []
        
        # Jerarquía de tiers (de menor a mayor)
        tier_hierarchy = ['Económica', 'Estándar', 'Superior', 'Suite']
        
        if not request.preferred_tier:
            return suggestions
        
        try:
            current_tier_index = tier_hierarchy.index(request.preferred_tier)
        except ValueError:
            return suggestions
        
        # Buscar tiers superiores disponibles
        for higher_tier in tier_hierarchy[current_tier_index + 1:]:
            occupied_rooms = self._get_occupied_rooms(request.check_in, request.check_out)
            upgrade_rooms = Room.query.filter(
                and_(Room.tier == higher_tier, ~Room.id.in_(occupied_rooms))
            ).all()
            
            for room in upgrade_rooms:
                base_price = self._estimate_room_price(room, request, tier=request.preferred_tier)
                upgrade_price = self._estimate_room_price(room, request)
                upgrade_cost = upgrade_price - base_price
                
                if request.max_budget and upgrade_price > request.max_budget:
                    continue
                
                # Calcular valor del upgrade
                tier_diff = tier_hierarchy.index(higher_tier) - current_tier_index
                confidence = self._calculate_room_confidence(room, request) + (tier_diff * 0.05)
                
                suggestion = AvailabilitySuggestion(
                    suggestion_type=SuggestionType.ROOM_UPGRADE,
                    priority=PriorityLevel.MEDIUM,
                    title=f"⭐ Upgrade a {room.name}",
                    description=f"Upgrade de {request.preferred_tier} a {higher_tier} (+DOP {upgrade_cost:,.0f})",
                    room_id=room.id,
                    room_name=room.name,
                    estimated_price=upgrade_price,
                    confidence_score=confidence,
                    upgrade_value=f"+{tier_diff} nivel(es)",
                    additional_info={
                        'original_tier': request.preferred_tier,
                        'upgrade_tier': higher_tier,
                        'upgrade_cost': upgrade_cost,
                        'tier_levels_up': tier_diff
                    }
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _find_split_stay_options(self, request: BookingRequest) -> List[AvailabilitySuggestion]:
        """Encuentra opciones de dividir la estancia entre múltiples habitaciones"""
        suggestions = []
        stay_duration = (request.check_out - request.check_in).days
        
        # Solo considerar split para estancias de 3+ días
        if stay_duration < 3:
            return suggestions
        
        # Probar dividir la estancia en 2 partes
        mid_point = request.check_in + timedelta(days=stay_duration // 2)
        
        # Primera parte
        occupied_rooms_1 = self._get_occupied_rooms(request.check_in, mid_point)
        available_rooms_1 = Room.query.filter(~Room.id.in_(occupied_rooms_1)).all()
        
        # Segunda parte  
        occupied_rooms_2 = self._get_occupied_rooms(mid_point, request.check_out)
        available_rooms_2 = Room.query.filter(~Room.id.in_(occupied_rooms_2)).all()
        
        # Filtrar por tier preferido
        if request.preferred_tier:
            available_rooms_1 = [r for r in available_rooms_1 if r.tier == request.preferred_tier]
            available_rooms_2 = [r for r in available_rooms_2 if r.tier == request.preferred_tier]
        
        # Crear combinaciones
        for room1 in available_rooms_1[:3]:
            for room2 in available_rooms_2[:3]:
                if room1.id == room2.id:  # Misma habitación, no es split
                    continue
                
                # Calcular precios
                price1 = self._estimate_room_price(room1, request, override_dates=(request.check_in, mid_point))
                price2 = self._estimate_room_price(room2, request, override_dates=(mid_point, request.check_out))
                total_price = price1 + price2
                
                if request.max_budget and total_price > request.max_budget:
                    continue
                
                confidence = (self._calculate_room_confidence(room1, request) + 
                            self._calculate_room_confidence(room2, request)) / 2 - 0.2  # Penalizar split
                
                suggestion = AvailabilitySuggestion(
                    suggestion_type=SuggestionType.SPLIT_STAY,
                    priority=PriorityLevel.LOW,
                    title=f"🔄 Split: {room1.name} + {room2.name}",
                    description=f"Primera mitad en {room1.name}, segunda en {room2.name}",
                    estimated_price=total_price,
                    confidence_score=confidence,
                    additional_info={
                        'room1_id': room1.id,
                        'room1_name': room1.name,
                        'room2_id': room2.id,
                        'room2_name': room2.name,
                        'split_date': mid_point,
                        'price1': price1,
                        'price2': price2
                    }
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _find_timing_optimizations(self, request: BookingRequest) -> List[AvailabilitySuggestion]:
        """Encuentra optimizaciones de horarios (check-in temprano, check-out tardío)"""
        suggestions = []
        
        # Check-in temprano (el día anterior)
        early_checkin = request.check_in - timedelta(days=1)
        early_checkout = request.check_out
        
        occupied_early = self._get_occupied_rooms(early_checkin, early_checkout)
        available_early = Room.query.filter(~Room.id.in_(occupied_early)).all()
        
        if request.preferred_tier:
            available_early = [r for r in available_early if r.tier == request.preferred_tier]
        
        for room in available_early[:2]:
            extra_night_cost = self._estimate_room_price(room, request, override_dates=(early_checkin, request.check_in))
            total_price = self._estimate_room_price(room, request) + extra_night_cost
            
            confidence = self._calculate_room_confidence(room, request) - 0.1
            
            suggestion = AvailabilitySuggestion(
                suggestion_type=SuggestionType.EARLY_CHECKIN,
                priority=PriorityLevel.LOW,
                title=f"🌅 Check-in temprano - {room.name}",
                description=f"Check-in el {early_checkin.strftime('%d/%m')} (+1 noche)",
                room_id=room.id,
                room_name=room.name,
                estimated_price=total_price,
                confidence_score=confidence,
                additional_info={
                    'extra_nights': 1,
                    'extra_cost': extra_night_cost,
                    'early_checkin_date': early_checkin
                }
            )
            suggestions.append(suggestion)
        
        # Check-out tardío (un día después)
        late_checkin = request.check_in
        late_checkout = request.check_out + timedelta(days=1)
        
        occupied_late = self._get_occupied_rooms(late_checkin, late_checkout)
        available_late = Room.query.filter(~Room.id.in_(occupied_late)).all()
        
        if request.preferred_tier:
            available_late = [r for r in available_late if r.tier == request.preferred_tier]
        
        for room in available_late[:2]:
            extra_night_cost = self._estimate_room_price(room, request, override_dates=(request.check_out, late_checkout))
            total_price = self._estimate_room_price(room, request) + extra_night_cost
            
            confidence = self._calculate_room_confidence(room, request) - 0.1
            
            suggestion = AvailabilitySuggestion(
                suggestion_type=SuggestionType.LATE_CHECKOUT,
                priority=PriorityLevel.LOW,
                title=f"🌙 Check-out tardío - {room.name}",
                description=f"Check-out el {late_checkout.strftime('%d/%m')} (+1 noche)",
                room_id=room.id,
                room_name=room.name,
                estimated_price=total_price,
                confidence_score=confidence,
                additional_info={
                    'extra_nights': 1,
                    'extra_cost': extra_night_cost,
                    'late_checkout_date': late_checkout
                }
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _find_price_optimizations(self, request: BookingRequest, existing_suggestions: List[AvailabilitySuggestion]) -> List[AvailabilitySuggestion]:
        """Encuentra optimizaciones de precio basadas en patrones históricos"""
        suggestions = []
        
        # Solo si hay un cliente específico con historial
        if not request.client_id:
            return suggestions
        
        client = Client.query.get(request.client_id)
        if not client:
            return suggestions
        
        # Analizar patrones de gasto histórico
        historical_spending = self._analyze_client_spending_patterns(client)
        
        if not historical_spending:
            return suggestions
        
        # Buscar habitaciones que estén en el rango de precio del cliente
        avg_spending = historical_spending['average_per_night']
        price_tolerance = avg_spending * 0.3  # 30% de tolerancia
        
        for suggestion in existing_suggestions:
            if suggestion.estimated_price and suggestion.suggestion_type == SuggestionType.AVAILABLE_ROOM:
                price_diff = suggestion.estimated_price - avg_spending
                
                # Si está significativamente por debajo del promedio histórico
                if price_diff < -price_tolerance:
                    savings = abs(price_diff)
                    nights = (request.check_out - request.check_in).days
                    total_savings = savings * nights
                    
                    price_suggestion = AvailabilitySuggestion(
                        suggestion_type=SuggestionType.PRICE_OPTIMIZATION,
                        priority=PriorityLevel.INFO,
                        title=f"💰 Ahorro en {suggestion.room_name}",
                        description=f"DOP {total_savings:,.0f} menos que tu promedio histórico",
                        room_id=suggestion.room_id,
                        room_name=suggestion.room_name,
                        estimated_price=suggestion.estimated_price,
                        confidence_score=0.8,
                        savings=total_savings,
                        additional_info={
                            'historical_average': avg_spending,
                            'savings_per_night': savings,
                            'total_nights': nights
                        }
                    )
                    suggestions.append(price_suggestion)
        
        return suggestions
    
    # === MÉTODOS AUXILIARES ===
    
    def _get_occupied_rooms(self, check_in: date, check_out: date) -> List[int]:
        """Obtiene IDs de habitaciones ocupadas en el período dado"""
        overlapping_stays = Stay.query.filter(
            Stay.status.in_(['Activa', 'Pendiente de Cierre']),
            Stay.check_in_date < check_out,
            or_(
                Stay.check_out_date.is_(None),
                Stay.check_out_date > check_in
            )
        ).all()
        
        return [stay.room_id for stay in overlapping_stays]
    
    def _estimate_room_price(self, room: Room, request: BookingRequest, tier: str = None, override_dates: Tuple[date, date] = None) -> float:
        """Estima el precio de una habitación basado en tier y duración"""
        # Precios base por tier (por noche)
        base_prices = {
            'Económica': 2000,
            'Estándar': 3000,
            'Superior': 4500,
            'Suite': 6000
        }
        
        tier_to_use = tier or room.tier
        base_price = base_prices.get(tier_to_use, 3000)
        
        # Calcular duración
        if override_dates:
            start_date, end_date = override_dates
        else:
            start_date, end_date = request.check_in, request.check_out
        
        nights = (end_date - start_date).days
        
        # Aplicar modificadores
        
        # Descuento por estancias largas
        if nights >= 7:
            base_price *= 0.9  # 10% descuento
        elif nights >= 14:
            base_price *= 0.85  # 15% descuento
        
        # Modificador estacional (ejemplo básico)
        if start_date.month in [12, 1, 2, 7, 8]:  # Temporada alta
            base_price *= 1.2
        
        return base_price * nights
    
    def _calculate_room_confidence(self, room: Room, request: BookingRequest) -> float:
        """Calcula score de confianza para una habitación basado en varios factores"""
        confidence = 0.5  # Base
        
        # Factor: Historial de ocupación de la habitación
        recent_stays = Stay.query.filter(
            Stay.room_id == room.id,
            Stay.check_in_date >= datetime.now() - timedelta(days=90)
        ).count()
        
        if recent_stays > 10:
            confidence += 0.2
        elif recent_stays > 5:
            confidence += 0.1
        
        # Factor: Estado de la habitación
        if room.status == 'Limpia':
            confidence += 0.2
        elif room.status == 'Ocupada':
            confidence -= 0.3
        
        # Factor: Paquete de suministros configurado
        if room.has_supply_package():
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _analyze_client_spending_patterns(self, client: Client) -> Optional[Dict]:
        """Analiza patrones de gasto histórico del cliente"""
        stays = client.stays.all()
        
        if not stays:
            return None
        
        payments = []
        nights = []
        
        for stay in stays:
            stay_payments = stay.total_paid()
            stay_nights = (stay.check_out_date.date() - stay.check_in_date.date()).days if stay.check_out_date else 1
            
            if stay_payments > 0 and stay_nights > 0:
                payments.append(stay_payments)
                nights.append(stay_nights)
        
        if not payments:
            return None
        
        total_spent = sum(payments)
        total_nights = sum(nights)
        average_per_night = total_spent / total_nights
        
        return {
            'total_spent': total_spent,
            'total_nights': total_nights,
            'average_per_night': average_per_night,
            'num_stays': len(payments)
        }
    
    def _rank_suggestions(self, suggestions: List[AvailabilitySuggestion]) -> List[AvailabilitySuggestion]:
        """Ordena sugerencias por prioridad y confianza"""
        priority_weights = {
            PriorityLevel.CRITICAL: 5,
            PriorityLevel.HIGH: 4,
            PriorityLevel.MEDIUM: 3,
            PriorityLevel.LOW: 2,
            PriorityLevel.INFO: 1
        }
        
        def suggestion_score(suggestion):
            priority_score = priority_weights.get(suggestion.priority, 1)
            confidence_score = suggestion.confidence_score
            return (priority_score * 2) + confidence_score
        
        return sorted(suggestions, key=suggestion_score, reverse=True)


# === CLASE DE UTILIDAD PARA ANÁLISIS DE PATRONES ===

class BookingPatternAnalyzer:
    """Analizador de patrones de reserva para optimizaciones predictivas"""
    
    @staticmethod
    def analyze_seasonal_patterns() -> Dict:
        """Analiza patrones estacionales de ocupación"""
        # Obtener datos de los últimos 12 meses
        one_year_ago = datetime.now() - timedelta(days=365)
        
        monthly_occupancy = db.session.query(
            func.extract('month', Stay.check_in_date).label('month'),
            func.count(Stay.id).label('bookings'),
            func.avg(func.julianday(Stay.check_out_date) - func.julianday(Stay.check_in_date)).label('avg_duration')
        ).filter(Stay.check_in_date >= one_year_ago).group_by('month').all()
        
        patterns = {}
        for row in monthly_occupancy:
            patterns[int(row.month)] = {
                'bookings': row.bookings,
                'avg_duration': float(row.avg_duration) if row.avg_duration else 0
            }
        
        return patterns
    
    @staticmethod
    def get_room_tier_demand() -> Dict:
        """Analiza demanda por tier de habitación"""
        demand_data = db.session.query(
            Room.tier,
            func.count(Stay.id).label('bookings'),
            func.avg(Payment.amount).label('avg_payment')
        ).join(Stay).join(Payment).group_by(Room.tier).all()
        
        return {
            row.tier: {
                'bookings': row.bookings,
                'avg_payment': float(row.avg_payment) if row.avg_payment else 0
            }
            for row in demand_data
        }
    
    @staticmethod
    def predict_optimal_pricing(room: Room, target_date: date) -> float:
        """Predice precio óptimo basado en patrones históricos"""
        # Análisis básico de precios históricos para esta habitación
        historical_data = db.session.query(
            func.avg(Payment.amount).label('avg_payment'),
            func.count(Stay.id).label('bookings')
        ).join(Stay).filter(
            Stay.room_id == room.id,
            Stay.check_in_date >= datetime.now() - timedelta(days=180)
        ).first()
        
        if not historical_data.avg_payment:
            # Fallback a precios base por tier
            base_prices = {
                'Económica': 2000,
                'Estándar': 3000,
                'Superior': 4500,
                'Suite': 6000
            }
            return base_prices.get(room.tier, 3000)
        
        base_price = float(historical_data.avg_payment)
        
        # Ajuste estacional
        if target_date.month in [12, 1, 2, 7, 8]:  # Temporada alta
            base_price *= 1.15
        
        # Ajuste por demanda histórica
        if historical_data.bookings > 20:  # Alta demanda
            base_price *= 1.1
        
        return base_price