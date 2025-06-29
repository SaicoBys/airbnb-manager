"""
AIRBNB MANAGER V4.0 - YIELD MANAGEMENT SYSTEM
Sistema Inteligente de Optimización de Reservas con Jerarquía Queen/King
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from app.extensions import db
from app.models import Room, Stay, Client, Payment


class SolutionType(Enum):
    """Tipos de soluciones de reserva"""
    PERFECT_MATCH = "perfect_match"          # Habitación única disponible
    SPLIT_STAY = "split_stay"                # Estancia dividida en múltiples habitaciones
    UPGRADE_REALLOCATION = "upgrade_reallocation"  # Reacomodación con upgrade
    WAITING_LIST = "waiting_list"            # Lista de espera


class SolutionPriority(Enum):
    """Prioridades de las soluciones"""
    EXCELLENT = "excellent"    # Solución perfecta
    GOOD = "good"             # Buena solución con beneficios
    ACCEPTABLE = "acceptable"  # Solución viable
    LAST_RESORT = "last_resort"  # Última opción


@dataclass
class BookingRequest:
    """Solicitud de reserva del cliente"""
    check_in: date
    check_out: date
    guests: int = 2
    preferred_tier: Optional[str] = None
    max_budget: Optional[float] = None
    client_id: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class BookingSolution:
    """Solución de reserva encontrada"""
    solution_type: SolutionType
    priority: SolutionPriority
    title: str
    description: str
    rooms: List[Dict]  # Lista de habitaciones con fechas
    estimated_price: float
    savings: Optional[float] = None
    upgrade_benefit: Optional[str] = None
    reallocation_details: Optional[Dict] = None
    confidence_score: float = 0.0
    additional_info: Dict = None


class YieldManagementEngine:
    """Motor principal de Yield Management"""
    
    def __init__(self):
        self.pricing_base = {
            'Queen': 2500,  # Precio base por noche Queen
            'King': 4000    # Precio base por noche King
        }
        self.upgrade_premium = 0.6  # 60% premium por upgrade
    
    def find_booking_solutions(self, request: BookingRequest) -> List[BookingSolution]:
        """
        Encuentra todas las soluciones posibles para una solicitud de reserva
        """
        solutions = []
        
        # 1. Buscar solución perfecta (habitación única)
        perfect_solutions = self._find_perfect_matches(request)
        solutions.extend(perfect_solutions)
        
        # 2. Si no hay solución perfecta, buscar estancias divididas
        if not perfect_solutions:
            split_solutions = self._find_split_stay_solutions(request)
            solutions.extend(split_solutions)
        
        # 3. Buscar oportunidades de reacomodación con upgrade
        reallocation_solutions = self._find_reallocation_solutions(request)
        solutions.extend(reallocation_solutions)
        
        # 4. Ordenar por prioridad y confianza
        solutions = self._rank_solutions(solutions)
        
        return solutions[:8]  # Máximo 8 soluciones
    
    def _find_perfect_matches(self, request: BookingRequest) -> List[BookingSolution]:
        """Busca habitaciones únicas disponibles para todo el período"""
        solutions = []
        
        # Obtener habitaciones ocupadas en el período
        occupied_room_ids = self._get_occupied_rooms(request.check_in, request.check_out)
        
        # Buscar habitaciones disponibles
        available_rooms = Room.query.filter(~Room.id.in_(occupied_room_ids)).all()
        
        # Filtrar por tier preferido si se especifica
        if request.preferred_tier:
            available_rooms = [r for r in available_rooms if r.tier == request.preferred_tier]
        
        for room in available_rooms:
            estimated_price = self._calculate_room_price(room, request)
            
            # Verificar presupuesto
            if request.max_budget and estimated_price > request.max_budget:
                continue
            
            # Determinar prioridad
            priority = SolutionPriority.EXCELLENT
            if not request.preferred_tier:
                # Si no hay preferencia, King es mejor
                if room.tier == 'King':
                    priority = SolutionPriority.EXCELLENT
                else:
                    priority = SolutionPriority.GOOD
            
            solution = BookingSolution(
                solution_type=SolutionType.PERFECT_MATCH,
                priority=priority,
                title=f"✅ {room.name} - Disponible",
                description=f"{room.get_tier_display()} disponible para todo el período",
                rooms=[{
                    'room_id': room.id,
                    'room_name': room.name,
                    'tier': room.tier,
                    'check_in': request.check_in,
                    'check_out': request.check_out,
                    'nights': (request.check_out - request.check_in).days
                }],
                estimated_price=estimated_price,
                confidence_score=0.95,
                additional_info={
                    'tier': room.tier,
                    'is_upgrade': room.tier == 'King' and request.preferred_tier == 'Queen'
                }
            )
            
            solutions.append(solution)
        
        return solutions
    
    def _find_split_stay_solutions(self, request: BookingRequest) -> List[BookingSolution]:
        """Busca combinaciones de habitaciones para estancias divididas"""
        solutions = []
        stay_duration = (request.check_out - request.check_in).days
        
        # Solo considerar split para estancias de 3+ días
        if stay_duration < 3:
            return solutions
        
        # Probar diferentes puntos de división
        for split_day in range(1, stay_duration):
            mid_date = request.check_in + timedelta(days=split_day)
            
            # Primera parte
            occupied_1 = self._get_occupied_rooms(request.check_in, mid_date)
            available_1 = Room.query.filter(~Room.id.in_(occupied_1)).all()
            
            # Segunda parte
            occupied_2 = self._get_occupied_rooms(mid_date, request.check_out)
            available_2 = Room.query.filter(~Room.id.in_(occupied_2)).all()
            
            # Crear combinaciones
            for room1 in available_1[:3]:  # Limitar opciones
                for room2 in available_2[:3]:
                    if room1.id == room2.id:  # Misma habitación, no es split
                        continue
                    
                    # Calcular precios
                    price1 = self._calculate_room_price_partial(room1, request.check_in, mid_date)
                    price2 = self._calculate_room_price_partial(room2, mid_date, request.check_out)
                    total_price = price1 + price2
                    
                    # Verificar presupuesto
                    if request.max_budget and total_price > request.max_budget:
                        continue
                    
                    # Determinar si hay upgrade en la combinación
                    has_upgrade = room1.tier == 'King' or room2.tier == 'King'
                    upgrade_benefit = None
                    if has_upgrade and (not request.preferred_tier or request.preferred_tier == 'Queen'):
                        upgrade_benefit = "Incluye experiencia King"
                    
                    solution = BookingSolution(
                        solution_type=SolutionType.SPLIT_STAY,
                        priority=SolutionPriority.GOOD if has_upgrade else SolutionPriority.ACCEPTABLE,
                        title=f"🔄 Split: {room1.name} + {room2.name}",
                        description=f"Primera parte en {room1.get_tier_display()}, luego {room2.get_tier_display()}",
                        rooms=[
                            {
                                'room_id': room1.id,
                                'room_name': room1.name,
                                'tier': room1.tier,
                                'check_in': request.check_in,
                                'check_out': mid_date,
                                'nights': split_day
                            },
                            {
                                'room_id': room2.id,
                                'room_name': room2.name,
                                'tier': room2.tier,
                                'check_in': mid_date,
                                'check_out': request.check_out,
                                'nights': stay_duration - split_day
                            }
                        ],
                        estimated_price=total_price,
                        upgrade_benefit=upgrade_benefit,
                        confidence_score=0.8,
                        additional_info={
                            'split_point': split_day,
                            'has_upgrade': has_upgrade
                        }
                    )
                    
                    solutions.append(solution)
        
        return solutions
    
    def _find_reallocation_solutions(self, request: BookingRequest) -> List[BookingSolution]:
        """Busca oportunidades de reacomodación con upgrade"""
        solutions = []
        
        # Obtener estancias actuales que podrían moverse
        current_stays = Stay.query.filter(
            Stay.status == 'Activa',
            Stay.check_in_date <= request.check_out,
            Stay.check_out_date >= request.check_in
        ).all()
        
        for stay in current_stays:
            # Solo considerar mover de Queen a King
            if not stay.room or stay.room.tier != 'Queen':
                continue
            
            # Buscar habitaciones King disponibles para el huésped actual
            guest_check_in = max(stay.check_in_date.date(), request.check_in)
            guest_check_out = min(stay.check_out_date.date() if stay.check_out_date else request.check_out, request.check_out)
            
            occupied_for_guest = self._get_occupied_rooms(guest_check_in, guest_check_out, exclude_stay=stay.id)
            available_kings = Room.query.filter(
                Room.tier == 'King',
                ~Room.id.in_(occupied_for_guest)
            ).all()
            
            for king_room in available_kings:
                # Verificar si la Queen original quedaría disponible para el nuevo cliente
                occupied_without_stay = self._get_occupied_rooms(request.check_in, request.check_out, exclude_stay=stay.id)
                
                if stay.room.id not in occupied_without_stay:
                    # ¡Solución encontrada!
                    original_price = self._calculate_room_price_for_room(stay.room, request)
                    
                    # Verificar presupuesto
                    if request.max_budget and original_price > request.max_budget:
                        continue
                    
                    solution = BookingSolution(
                        solution_type=SolutionType.UPGRADE_REALLOCATION,
                        priority=SolutionPriority.GOOD,
                        title=f"⬆️ Liberar {stay.room.name} (Upgrade a {stay.client.full_name})",
                        description=f"Mover a '{stay.client.full_name}' de {stay.room.name} a {king_room.name} (upgrade gratis)",
                        rooms=[{
                            'room_id': stay.room.id,
                            'room_name': stay.room.name,
                            'tier': stay.room.tier,
                            'check_in': request.check_in,
                            'check_out': request.check_out,
                            'nights': (request.check_out - request.check_in).days
                        }],
                        estimated_price=original_price,
                        upgrade_benefit="Cliente actual recibe upgrade gratis",
                        reallocation_details={
                            'current_guest': stay.client.full_name,
                            'current_room': stay.room.name,
                            'new_room': king_room.name,
                            'stay_id': stay.id
                        },
                        confidence_score=0.75,
                        additional_info={
                            'requires_guest_approval': True,
                            'goodwill_upgrade': True
                        }
                    )
                    
                    solutions.append(solution)
        
        return solutions
    
    def _get_occupied_rooms(self, check_in: date, check_out: date, exclude_stay: int = None) -> List[int]:
        """Obtiene IDs de habitaciones ocupadas en el período, opcionalmente excluyendo una estancia"""
        query = Stay.query.filter(
            Stay.status.in_(['Activa', 'Pendiente de Cierre']),
            Stay.check_in_date < check_out,
            db.or_(
                Stay.check_out_date.is_(None),
                Stay.check_out_date > check_in
            )
        )
        
        if exclude_stay:
            query = query.filter(Stay.id != exclude_stay)
        
        overlapping_stays = query.all()
        return [stay.room_id for stay in overlapping_stays if stay.room_id]
    
    def _calculate_room_price(self, room: Room, request: BookingRequest) -> float:
        """Calcula el precio estimado para una habitación"""
        nights = (request.check_out - request.check_in).days
        base_price = self.pricing_base.get(room.tier, 3000)
        
        # Aplicar modificadores estacionales, descuentos, etc.
        return base_price * nights
    
    def _calculate_room_price_partial(self, room: Room, check_in: date, check_out: date) -> float:
        """Calcula precio para un período parcial"""
        nights = (check_out - check_in).days
        base_price = self.pricing_base.get(room.tier, 3000)
        return base_price * nights
    
    def _calculate_room_price_for_room(self, room: Room, request: BookingRequest) -> float:
        """Calcula precio específico para una habitación"""
        return self._calculate_room_price(room, request)
    
    def _rank_solutions(self, solutions: List[BookingSolution]) -> List[BookingSolution]:
        """Ordena soluciones por prioridad y calidad"""
        priority_weights = {
            SolutionPriority.EXCELLENT: 4,
            SolutionPriority.GOOD: 3,
            SolutionPriority.ACCEPTABLE: 2,
            SolutionPriority.LAST_RESORT: 1
        }
        
        def solution_score(solution):
            priority_score = priority_weights.get(solution.priority, 1)
            confidence_score = solution.confidence_score
            
            # Bonus por upgrade
            upgrade_bonus = 0.1 if solution.upgrade_benefit else 0
            
            return (priority_score * 2) + confidence_score + upgrade_bonus
        
        return sorted(solutions, key=solution_score, reverse=True)


# === FUNCIONES DE UTILIDAD ===

def get_availability_summary(start_date: date, days: int = 30) -> Dict:
    """Obtiene resumen de disponibilidad para un período"""
    rooms = Room.query.all()
    summary = {
        'total_rooms': len(rooms),
        'queen_rooms': len([r for r in rooms if r.tier == 'Queen']),
        'king_rooms': len([r for r in rooms if r.tier == 'King']),
        'daily_availability': {}
    }
    
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        next_date = current_date + timedelta(days=1)
        
        engine = YieldManagementEngine()
        occupied = engine._get_occupied_rooms(current_date, next_date)
        available = len(rooms) - len(occupied)
        
        summary['daily_availability'][current_date.isoformat()] = {
            'available': available,
            'occupied': len(occupied),
            'occupancy_rate': (len(occupied) / len(rooms)) * 100 if rooms else 0
        }
    
    return summary