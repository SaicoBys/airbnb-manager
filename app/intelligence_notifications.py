"""
AIRBNB MANAGER V3.0 - SISTEMA DE NOTIFICACIONES INTELIGENTES
Sistema proactivo de alertas y sugerencias basado en análisis de datos
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import json

from app.extensions import db
from app.models import Room, Stay, Client, Supply, Payment, Expense, SupplyUsage
from app.intelligence import BookingPatternAnalyzer, AvailabilityEngine


class NotificationType(Enum):
    """Tipos de notificaciones del sistema"""
    BUSINESS_OPPORTUNITY = "business_opportunity"
    OPERATIONAL_ALERT = "operational_alert"
    REVENUE_OPTIMIZATION = "revenue_optimization"
    INVENTORY_WARNING = "inventory_warning"
    CLIENT_INSIGHT = "client_insight"
    MARKET_TREND = "market_trend"
    PERFORMANCE_ALERT = "performance_alert"


class NotificationPriority(Enum):
    """Prioridades de notificaciones"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class IntelligentNotification:
    """Estructura de una notificación inteligente"""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    action_text: Optional[str] = None
    action_url: Optional[str] = None
    data: Dict = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    auto_dismiss: bool = False


class IntelligentNotificationEngine:
    """Motor principal de notificaciones inteligentes"""
    
    def __init__(self):
        self.analyzers = {
            'revenue': RevenueAnalyzer(),
            'occupancy': OccupancyAnalyzer(),
            'inventory': InventoryAnalyzer(),
            'client': ClientBehaviorAnalyzer(),
            'operations': OperationalAnalyzer()
        }
    
    def generate_notifications(self) -> List[IntelligentNotification]:
        """
        Genera todas las notificaciones inteligentes disponibles
        """
        all_notifications = []
        
        # Ejecutar todos los analizadores
        for analyzer_name, analyzer in self.analyzers.items():
            try:
                notifications = analyzer.analyze()
                all_notifications.extend(notifications)
            except Exception as e:
                # Log error pero continuar con otros analizadores
                print(f"Error en analyzer {analyzer_name}: {str(e)}")
        
        # Ordenar por prioridad y relevancia
        all_notifications.sort(key=lambda n: (
            self._priority_weight(n.priority),
            n.created_at or datetime.now()
        ), reverse=True)
        
        # Limitar a las 20 más importantes
        return all_notifications[:20]
    
    def _priority_weight(self, priority: NotificationPriority) -> int:
        """Asigna peso numérico a las prioridades"""
        weights = {
            NotificationPriority.CRITICAL: 5,
            NotificationPriority.HIGH: 4,
            NotificationPriority.MEDIUM: 3,
            NotificationPriority.LOW: 2,
            NotificationPriority.INFO: 1
        }
        return weights.get(priority, 1)


class RevenueAnalyzer:
    """Analizador de oportunidades de ingresos"""
    
    def analyze(self) -> List[IntelligentNotification]:
        notifications = []
        
        # Análisis de tendencias de ingresos
        notifications.extend(self._analyze_revenue_trends())
        
        # Oportunidades de precios
        notifications.extend(self._analyze_pricing_opportunities())
        
        # Habitaciones subutilizadas
        notifications.extend(self._analyze_underutilized_rooms())
        
        return notifications
    
    def _analyze_revenue_trends(self) -> List[IntelligentNotification]:
        """Analiza tendencias de ingresos"""
        notifications = []
        
        # Comparar ingresos del mes actual vs mes anterior
        current_month = datetime.now().replace(day=1)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        
        current_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.payment_date >= current_month
        ).scalar() or 0
        
        last_month_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.payment_date >= last_month,
            Payment.payment_date < current_month
        ).scalar() or 0
        
        if last_month_revenue > 0:
            change_percent = ((current_revenue - last_month_revenue) / last_month_revenue) * 100
            
            if change_percent < -15:  # Caída significativa
                notifications.append(IntelligentNotification(
                    id="revenue_decline",
                    type=NotificationType.REVENUE_OPTIMIZATION,
                    priority=NotificationPriority.HIGH,
                    title="📉 Caída en Ingresos Detectada",
                    message=f"Los ingresos han caído {abs(change_percent):.1f}% comparado con el mes anterior. Considera estrategias de marketing o ajustes de precios.",
                    action_text="Ver Análisis Detallado",
                    action_url="/intelligence/analyze_patterns",
                    data={'change_percent': change_percent, 'current_revenue': current_revenue}
                ))
            elif change_percent > 20:  # Crecimiento significativo
                notifications.append(IntelligentNotification(
                    id="revenue_growth",
                    type=NotificationType.BUSINESS_OPPORTUNITY,
                    priority=NotificationPriority.MEDIUM,
                    title="📈 Excelente Crecimiento de Ingresos",
                    message=f"¡Los ingresos han aumentado {change_percent:.1f}%! Considera aumentar precios o expandir capacidad.",
                    action_text="Optimizar Precios",
                    action_url="/intelligence/optimize_pricing",
                    data={'change_percent': change_percent}
                ))
        
        return notifications
    
    def _analyze_pricing_opportunities(self) -> List[IntelligentNotification]:
        """Identifica oportunidades de optimización de precios"""
        notifications = []
        
        # Buscar habitaciones con alta demanda pero precios bajos
        analyzer = BookingPatternAnalyzer()
        tier_demand = analyzer.get_room_tier_demand()
        
        for tier, data in tier_demand.items():
            if data['bookings'] > 15 and data['avg_payment'] < 3000:  # Alta demanda, precio bajo
                notifications.append(IntelligentNotification(
                    id=f"pricing_opportunity_{tier}",
                    type=NotificationType.REVENUE_OPTIMIZATION,
                    priority=NotificationPriority.MEDIUM,
                    title=f"💰 Oportunidad de Precio - {tier}",
                    message=f"Las habitaciones {tier} tienen alta demanda ({data['bookings']} reservas) pero precio promedio bajo. Considera aumentar precios.",
                    action_text="Ver Sugerencias de Precio",
                    data={'tier': tier, 'bookings': data['bookings'], 'avg_payment': data['avg_payment']}
                ))
        
        return notifications
    
    def _analyze_underutilized_rooms(self) -> List[IntelligentNotification]:
        """Identifica habitaciones subutilizadas"""
        notifications = []
        
        # Habitaciones con baja ocupación en los últimos 30 días
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        room_utilization = db.session.query(
            Room.id,
            Room.name,
            Room.tier,
            db.func.count(Stay.id).label('bookings')
        ).outerjoin(Stay, db.and_(
            Stay.room_id == Room.id,
            Stay.check_in_date >= thirty_days_ago
        )).group_by(Room.id).all()
        
        for room_data in room_utilization:
            if room_data.bookings < 3:  # Menos de 3 reservas en 30 días
                notifications.append(IntelligentNotification(
                    id=f"underutilized_room_{room_data.id}",
                    type=NotificationType.BUSINESS_OPPORTUNITY,
                    priority=NotificationPriority.LOW,
                    title=f"🏨 {room_data.name} Subutilizada",
                    message=f"Solo {room_data.bookings} reservas en 30 días. Considera promociones especiales o reducir precio temporalmente.",
                    action_text="Crear Promoción",
                    data={'room_id': room_data.id, 'bookings': room_data.bookings}
                ))
        
        return notifications


class OccupancyAnalyzer:
    """Analizador de patrones de ocupación"""
    
    def analyze(self) -> List[IntelligentNotification]:
        notifications = []
        
        # Análisis de ocupación actual
        notifications.extend(self._analyze_current_occupancy())
        
        # Predicciones de ocupación
        notifications.extend(self._predict_occupancy_trends())
        
        return notifications
    
    def _analyze_current_occupancy(self) -> List[IntelligentNotification]:
        """Analiza la ocupación actual"""
        notifications = []
        
        total_rooms = Room.query.count()
        occupied_rooms = Stay.query.filter(Stay.status == 'Activa').count()
        occupancy_rate = (occupied_rooms / total_rooms) * 100 if total_rooms > 0 else 0
        
        if occupancy_rate > 85:
            notifications.append(IntelligentNotification(
                id="high_occupancy",
                type=NotificationType.BUSINESS_OPPORTUNITY,
                priority=NotificationPriority.HIGH,
                title="🔥 Alta Ocupación - Oportunidad de Revenue",
                message=f"Ocupación al {occupancy_rate:.1f}%. Considera aumentar precios para maximizar ingresos.",
                action_text="Ajustar Precios",
                data={'occupancy_rate': occupancy_rate}
            ))
        elif occupancy_rate < 30:
            notifications.append(IntelligentNotification(
                id="low_occupancy",
                type=NotificationType.OPERATIONAL_ALERT,
                priority=NotificationPriority.MEDIUM,
                title="📉 Baja Ocupación - Acción Requerida",
                message=f"Ocupación solo al {occupancy_rate:.1f}%. Implementa promociones o estrategias de marketing.",
                action_text="Ver Estrategias",
                data={'occupancy_rate': occupancy_rate}
            ))
        
        return notifications
    
    def _predict_occupancy_trends(self) -> List[IntelligentNotification]:
        """Predice tendencias de ocupación"""
        notifications = []
        
        # Verificar próximas llegadas y salidas
        today = date.today()
        next_week = today + timedelta(days=7)
        
        upcoming_checkouts = Stay.query.filter(
            Stay.status == 'Activa',
            db.func.date(Stay.check_out_date) >= today,
            db.func.date(Stay.check_out_date) <= next_week
        ).count()
        
        upcoming_checkins = Stay.query.filter(
            Stay.status == 'Activa',
            db.func.date(Stay.check_in_date) >= today,
            db.func.date(Stay.check_in_date) <= next_week
        ).count()
        
        net_change = upcoming_checkins - upcoming_checkouts
        
        if net_change < -5:
            notifications.append(IntelligentNotification(
                id="occupancy_drop_predicted",
                type=NotificationType.BUSINESS_OPPORTUNITY,
                priority=NotificationPriority.MEDIUM,
                title="📅 Caída de Ocupación Prevista",
                message=f"Se prevé una disminución neta de {abs(net_change)} habitaciones la próxima semana. Tiempo ideal para promociones de último momento.",
                action_text="Crear Ofertas",
                data={'net_change': net_change, 'checkouts': upcoming_checkouts, 'checkins': upcoming_checkins}
            ))
        
        return notifications


class InventoryAnalyzer:
    """Analizador de inventario y suministros"""
    
    def analyze(self) -> List[IntelligentNotification]:
        notifications = []
        
        # Alertas de stock bajo
        notifications.extend(self._analyze_low_stock())
        
        # Análisis de uso excesivo
        notifications.extend(self._analyze_excessive_usage())
        
        # Sugerencias de reorden
        notifications.extend(self._suggest_reorder_points())
        
        return notifications
    
    def _analyze_low_stock(self) -> List[IntelligentNotification]:
        """Analiza alertas de stock bajo"""
        notifications = []
        
        low_stock_supplies = Supply.query.filter(
            Supply.current_stock <= Supply.minimum_stock
        ).all()
        
        critical_supplies = [s for s in low_stock_supplies if s.current_stock == 0]
        warning_supplies = [s for s in low_stock_supplies if s.current_stock > 0]
        
        if critical_supplies:
            notifications.append(IntelligentNotification(
                id="critical_stock_out",
                type=NotificationType.INVENTORY_WARNING,
                priority=NotificationPriority.CRITICAL,
                title="🚨 Suministros Agotados",
                message=f"{len(critical_supplies)} suministros están completamente agotados. Esto puede afectar las operaciones.",
                action_text="Ver Lista Crítica",
                action_url="/supplies",
                data={'critical_supplies': [s.name for s in critical_supplies]}
            ))
        
        if warning_supplies:
            notifications.append(IntelligentNotification(
                id="low_stock_warning",
                type=NotificationType.INVENTORY_WARNING,
                priority=NotificationPriority.HIGH,
                title="⚠️ Stock Bajo Detectado",
                message=f"{len(warning_supplies)} suministros están por debajo del nivel mínimo.",
                action_text="Gestionar Inventario",
                action_url="/supplies",
                data={'warning_supplies': [s.name for s in warning_supplies]}
            ))
        
        return notifications
    
    def _analyze_excessive_usage(self) -> List[IntelligentNotification]:
        """Detecta uso excesivo de suministros"""
        notifications = []
        
        # Buscar usos que excedan significativamente lo esperado
        recent_usages = SupplyUsage.query.filter(
            SupplyUsage.usage_date >= datetime.now() - timedelta(days=7),
            SupplyUsage.quantity_expected.isnot(None)
        ).all()
        
        excessive_usages = []
        for usage in recent_usages:
            if usage.quantity_used > usage.quantity_expected * 1.5:  # 50% más de lo esperado
                excessive_usages.append(usage)
        
        if excessive_usages:
            # Agrupar por suministro
            supply_groups = {}
            for usage in excessive_usages:
                supply_name = usage.supply.name
                if supply_name not in supply_groups:
                    supply_groups[supply_name] = []
                supply_groups[supply_name].append(usage)
            
            for supply_name, usages in supply_groups.items():
                if len(usages) >= 2:  # Patrón repetitivo
                    notifications.append(IntelligentNotification(
                        id=f"excessive_usage_{supply_name}",
                        type=NotificationType.OPERATIONAL_ALERT,
                        priority=NotificationPriority.MEDIUM,
                        title=f"📊 Uso Excesivo: {supply_name}",
                        message=f"Se detectó uso consistentemente alto de {supply_name}. Revisar procesos o ajustar paquetes.",
                        action_text="Revisar Detalles",
                        data={'supply_name': supply_name, 'incidents': len(usages)}
                    ))
        
        return notifications
    
    def _suggest_reorder_points(self) -> List[IntelligentNotification]:
        """Sugiere puntos de reorden basados en patrones de uso"""
        notifications = []
        
        # Analizar velocidad de consumo
        supplies_with_usage = db.session.query(
            Supply,
            db.func.sum(SupplyUsage.quantity_used).label('total_used'),
            db.func.count(SupplyUsage.id).label('usage_count')
        ).join(SupplyUsage).filter(
            SupplyUsage.usage_date >= datetime.now() - timedelta(days=30)
        ).group_by(Supply.id).all()
        
        for supply, total_used, usage_count in supplies_with_usage:
            if usage_count > 5:  # Suficientes datos
                monthly_consumption = total_used
                daily_consumption = monthly_consumption / 30
                days_until_stockout = supply.current_stock / daily_consumption if daily_consumption > 0 else float('inf')
                
                if days_until_stockout < 7:  # Menos de una semana
                    notifications.append(IntelligentNotification(
                        id=f"reorder_suggestion_{supply.id}",
                        type=NotificationType.INVENTORY_WARNING,
                        priority=NotificationPriority.HIGH,
                        title=f"🔄 Reordenar: {supply.name}",
                        message=f"Al ritmo actual de consumo, se agotará en {days_until_stockout:.1f} días.",
                        action_text="Actualizar Stock",
                        action_url=f"/update_stock/{supply.id}",
                        data={'days_until_stockout': days_until_stockout, 'daily_consumption': daily_consumption}
                    ))
        
        return notifications


class ClientBehaviorAnalyzer:
    """Analizador de comportamiento de clientes"""
    
    def analyze(self) -> List[IntelligentNotification]:
        notifications = []
        
        # VIPs que no han visitado recientemente
        notifications.extend(self._analyze_vip_retention())
        
        # Oportunidades de upselling
        notifications.extend(self._analyze_upselling_opportunities())
        
        return notifications
    
    def _analyze_vip_retention(self) -> List[IntelligentNotification]:
        """Analiza retención de clientes VIP"""
        notifications = []
        
        # Definir VIPs como clientes con más de 50,000 en gasto total
        vip_clients = Client.query.all()
        vip_clients = [c for c in vip_clients if c.total_spent() > 50000]
        
        three_months_ago = datetime.now() - timedelta(days=90)
        
        inactive_vips = []
        for client in vip_clients:
            last_visit = client.last_visit()
            if last_visit and last_visit < three_months_ago.date():
                inactive_vips.append(client)
        
        if inactive_vips:
            notifications.append(IntelligentNotification(
                id="vip_retention_alert",
                type=NotificationType.CLIENT_INSIGHT,
                priority=NotificationPriority.HIGH,
                title="👑 Clientes VIP Inactivos",
                message=f"{len(inactive_vips)} clientes VIP no han visitado en 3+ meses. Considera campañas de reactivación.",
                action_text="Ver Lista VIP",
                data={'inactive_vips': [{'name': c.full_name, 'total_spent': c.total_spent()} for c in inactive_vips]}
            ))
        
        return notifications
    
    def _analyze_upselling_opportunities(self) -> List[IntelligentNotification]:
        """Identifica oportunidades de upselling"""
        notifications = []
        
        # Clientes que siempre eligen habitaciones económicas pero gastan mucho
        economic_clients = db.session.query(Client).join(Stay).join(Room).filter(
            Room.tier == 'Económica'
        ).group_by(Client.id).having(
            db.func.count(Stay.id) >= 3  # Al menos 3 estancias
        ).all()
        
        high_spending_economic = []
        for client in economic_clients:
            avg_per_stay = client.total_spent() / client.visit_count()
            if avg_per_stay > 4000:  # Gasto alto para tier económico
                high_spending_economic.append(client)
        
        if high_spending_economic:
            notifications.append(IntelligentNotification(
                id="upselling_opportunity",
                type=NotificationType.BUSINESS_OPPORTUNITY,
                priority=NotificationPriority.MEDIUM,
                title="⬆️ Oportunidad de Upselling",
                message=f"{len(high_spending_economic)} clientes de tier económico con alto gasto. Considera ofrecer upgrades.",
                action_text="Ver Candidatos",
                data={'candidates': [c.full_name for c in high_spending_economic]}
            ))
        
        return notifications


class OperationalAnalyzer:
    """Analizador de eficiencia operacional"""
    
    def analyze(self) -> List[IntelligentNotification]:
        notifications = []
        
        # Habitaciones que tardan mucho en limpiarse
        notifications.extend(self._analyze_cleaning_efficiency())
        
        # Patrones de check-in/check-out
        notifications.extend(self._analyze_checkin_patterns())
        
        return notifications
    
    def _analyze_cleaning_efficiency(self) -> List[IntelligentNotification]:
        """Analiza eficiencia de limpieza"""
        notifications = []
        
        # Habitaciones en estado "Por Limpiar" por más de 24 horas
        yesterday = datetime.now() - timedelta(days=1)
        
        # Esta lógica sería más compleja en un sistema real con logs de estado
        rooms_needing_cleaning = Room.query.filter(Room.status == 'Por Limpiar').count()
        
        if rooms_needing_cleaning > 2:
            notifications.append(IntelligentNotification(
                id="cleaning_backlog",
                type=NotificationType.OPERATIONAL_ALERT,
                priority=NotificationPriority.MEDIUM,
                title="🧹 Retraso en Limpieza",
                message=f"{rooms_needing_cleaning} habitaciones pendientes de limpieza. Revisa la capacidad del equipo.",
                action_text="Ver Estado Habitaciones",
                data={'rooms_count': rooms_needing_cleaning}
            ))
        
        return notifications
    
    def _analyze_checkin_patterns(self) -> List[IntelligentNotification]:
        """Analiza patrones de check-in/check-out"""
        notifications = []
        
        # Analizar estancias que se extienden frecuentemente
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        extended_stays = Stay.query.filter(
            Stay.check_in_date >= week_ago,
            Stay.check_out_date > Stay.check_in_date + timedelta(days=7)  # Estancias largas
        ).count()
        
        total_recent_stays = Stay.query.filter(Stay.check_in_date >= week_ago).count()
        
        if total_recent_stays > 0:
            extended_rate = (extended_stays / total_recent_stays) * 100
            
            if extended_rate > 30:  # Más del 30% son estancias largas
                notifications.append(IntelligentNotification(
                    id="long_stay_pattern",
                    type=NotificationType.BUSINESS_OPPORTUNITY,
                    priority=NotificationPriority.LOW,
                    title="📅 Patrón de Estancias Largas",
                    message=f"{extended_rate:.1f}% de las reservas recientes son estancias largas. Considera descuentos por semana/mes.",
                    action_text="Crear Promoción",
                    data={'extended_rate': extended_rate}
                ))
        
        return notifications


# === UTILIDADES PARA INTEGRACIÓN CON EL FRONTEND ===

def get_notifications_for_dashboard() -> Dict:
    """
    Obtiene notificaciones formateadas para el dashboard
    """
    engine = IntelligentNotificationEngine()
    notifications = engine.generate_notifications()
    
    # Categorizar por tipo
    categorized = {
        'critical': [],
        'business_opportunities': [],
        'operational_alerts': [],
        'insights': []
    }
    
    for notification in notifications:
        if notification.priority == NotificationPriority.CRITICAL:
            categorized['critical'].append(notification)
        elif notification.type in [NotificationType.BUSINESS_OPPORTUNITY, NotificationType.REVENUE_OPTIMIZATION]:
            categorized['business_opportunities'].append(notification)
        elif notification.type == NotificationType.OPERATIONAL_ALERT:
            categorized['operational_alerts'].append(notification)
        else:
            categorized['insights'].append(notification)
    
    return {
        'notifications': categorized,
        'total_count': len(notifications),
        'critical_count': len(categorized['critical']),
        'opportunities_count': len(categorized['business_opportunities'])
    }