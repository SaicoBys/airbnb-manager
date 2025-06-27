from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user

def role_required(*allowed_roles):
    """
    Decorador que requiere que el usuario tenga uno de los roles especificados.
    
    Usage:
        @role_required('dueño')
        @role_required('dueño', 'socia')
        @role_required('dueño', 'socia', 'empleada')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debes iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('main.login'))
            
            if current_user.role not in allowed_roles:
                flash('No tienes permisos para acceder a esta funcionalidad.', 'danger')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def owner_required(f):
    """Decorador que requiere que el usuario sea dueño."""
    return role_required('dueño')(f)

def management_required(f):
    """Decorador que requiere que el usuario sea dueño o socia."""
    return role_required('dueño', 'socia')(f)

def permission_required(permission_method):
    """
    Decorador que verifica un método específico de permisos del usuario.
    
    Usage:
        @permission_required('can_manage_finances')
        @permission_required('can_view_reports')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debes iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('main.login'))
            
            if not hasattr(current_user, permission_method):
                flash('Error de configuración de permisos.', 'danger')
                return redirect(url_for('main.index'))
            
            if not getattr(current_user, permission_method)():
                flash('No tienes permisos para realizar esta acción.', 'danger')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_permission(permission_method):
    """
    Función auxiliar para verificar permisos en plantillas o lógica de rutas.
    
    Returns:
        bool: True si el usuario tiene el permiso, False en caso contrario.
    """
    if not current_user.is_authenticated:
        return False
    
    if not hasattr(current_user, permission_method):
        return False
    
    return getattr(current_user, permission_method)()

def log_user_action(action, details=None, category='INFO'):
    """
    Función para registrar acciones del usuario usando el sistema de auditoría.
    
    Args:
        action (str): Descripción de la acción realizada
        details (str, optional): Detalles adicionales de la acción
        category (str): Categoría del log (INFO, WARNING, CRITICAL)
    """
    from app.middleware import AuditLog
    AuditLog.log_user_action(action, details, category)