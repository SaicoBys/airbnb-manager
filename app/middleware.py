from flask import request, session, g
from flask_login import current_user
from datetime import datetime
import logging

class PermissionMiddleware:
    """Middleware para registrar acciones y verificar permisos automáticamente."""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa el middleware con la aplicación Flask."""
        # Configurar logging para acciones de usuarios
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('user_actions')
        
        # Registrar el middleware
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Se ejecuta antes de cada request."""
        # Guardar información de la request para logging
        g.start_time = datetime.utcnow()
        g.user_ip = request.remote_addr
        g.user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # Log de accesos a rutas sensibles
        if self._is_sensitive_route():
            self._log_sensitive_access()
    
    def after_request(self, response):
        """Se ejecuta después de cada request."""
        # Calcular tiempo de respuesta
        if hasattr(g, 'start_time'):
            response_time = (datetime.utcnow() - g.start_time).total_seconds()
            
            # Log de acciones que modifican datos
            if request.method in ['POST', 'PUT', 'DELETE'] and response.status_code < 400:
                self._log_data_modification(response_time)
        
        return response
    
    def _is_sensitive_route(self):
        """Determina si la ruta actual es sensible."""
        sensitive_routes = [
            '/reports',
            '/monthly_report',
            '/delete_supply',
            '/add_payment',
            '/add_expense'
        ]
        
        return any(route in request.path for route in sensitive_routes)
    
    def _log_sensitive_access(self):
        """Registra acceso a rutas sensibles."""
        if current_user.is_authenticated:
            self.logger.info(
                f"SENSITIVE_ACCESS - User: {current_user.username} "
                f"({current_user.role}) accessed {request.path} "
                f"from IP: {g.user_ip}"
            )
    
    def _log_data_modification(self, response_time):
        """Registra modificaciones de datos."""
        if current_user.is_authenticated and request.method in ['POST', 'PUT', 'DELETE']:
            action = self._get_action_description()
            self.logger.info(
                f"DATA_MODIFICATION - User: {current_user.username} "
                f"({current_user.role}) performed: {action} "
                f"on {request.path} - Response time: {response_time:.3f}s"
            )
    
    def _get_action_description(self):
        """Obtiene una descripción de la acción basada en la ruta y método."""
        path = request.path
        method = request.method
        
        action_map = {
            '/add_supply': 'Added supply',
            '/edit_supply': 'Edited supply',
            '/update_stock': 'Updated stock',
            '/delete_supply': 'Deleted supply',
            '/add_client': 'Added client',
            '/add_expense': 'Added expense',
            '/add_stay': 'Added stay',
            '/add_payment': 'Added payment',
        }
        
        for route, description in action_map.items():
            if route in path:
                return description
        
        return f"{method} request to {path}"

class AuditLog:
    """Clase para manejar logging de auditoría más detallado."""
    
    @staticmethod
    def log_user_action(action, details=None, category='INFO'):
        """
        Registra una acción específica del usuario con detalles.
        
        Args:
            action (str): Descripción de la acción
            details (str): Detalles adicionales
            category (str): Categoría del log (INFO, WARNING, CRITICAL)
        """
        logger = logging.getLogger('audit')
        
        if current_user.is_authenticated:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'user': current_user.username,
                'role': current_user.role,
                'action': action,
                'details': details,
                'ip': request.remote_addr if request else 'Unknown',
                'user_agent': request.headers.get('User-Agent', 'Unknown') if request else 'Unknown'
            }
            
            log_message = (
                f"AUDIT - {log_entry['user']} ({log_entry['role']}) "
                f"performed: {log_entry['action']}"
            )
            
            if details:
                log_message += f" - Details: {details}"
            
            if category == 'WARNING':
                logger.warning(log_message)
            elif category == 'CRITICAL':
                logger.critical(log_message)
            else:
                logger.info(log_message)