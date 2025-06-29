from flask import Flask
from config import Config
from .extensions import db
from flask_login import LoginManager
from flask_migrate import Migrate

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # --- INICIALIZAMOS LAS EXTENSIONES ---
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    from . import models
    migrate = Migrate(app, db)

    # --- CONFIGURAMOS FLASK-LOGIN ---
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    # --- ¡NUEVO! REGISTRAMOS LOS COMANDOS CLI ---
    from . import commands
    app.cli.add_command(commands.seed_db_command)

    @app.route('/test')
    def test_page():
        return '<h1>¡La configuración funciona!</h1>'

    # --- CONTEXT PROCESSOR PARA PERMISOS ---
    @app.context_processor
    def inject_permissions():
        from app.decorators import check_permission
        return dict(check_permission=check_permission)

    # --- MIDDLEWARE DE PERMISOS Y AUDITORÍA ---
    from app.middleware import PermissionMiddleware
    PermissionMiddleware(app)

    # --- REGISTRAR FILTROS PERSONALIZADOS PARA TEMPLATES ---
    register_template_filters(app)
    
    # --- REGISTRAMOS LOS BLUEPRINTS V3.0 (AL FINAL) ---
    from app.routes import register_blueprints
    register_blueprints(app)

    return app

def register_template_filters(app):
    """Registra filtros personalizados para las plantillas"""
    from datetime import datetime, date, timedelta
    
    @app.template_filter('friendly_date')
    def friendly_date_filter(dt):
        """Convierte datetime a formato amigable: Hoy, Mañana, Ayer, etc."""
        if not dt:
            return "Sin fecha"
        
        # Convertir a date si es datetime
        if isinstance(dt, datetime):
            dt = dt.date()
        
        today = date.today()
        delta = (dt - today).days
        
        if delta == 0:
            return "Hoy"
        elif delta == 1:
            return "Mañana"
        elif delta == -1:
            return "Ayer"
        elif delta == 2:
            return "Pasado mañana"
        elif delta == -2:
            return "Anteayer"
        elif -7 <= delta < 0:
            return f"Hace {abs(delta)} días"
        elif 0 < delta <= 7:
            return f"En {delta} días"
        elif delta > 7:
            return dt.strftime('%d/%m/%Y')
        else:
            return dt.strftime('%d/%m/%Y')
    
    @app.template_filter('friendly_datetime')
    def friendly_datetime_filter(dt):
        """Convierte datetime completo a formato amigable con hora"""
        if not dt:
            return "Sin fecha"
        
        date_part = friendly_date_filter(dt)
        time_part = dt.strftime('%H:%M')
        
        if date_part in ['Hoy', 'Mañana', 'Ayer']:
            return f"{date_part} {time_part}"
        else:
            return f"{date_part} {time_part}"
    
    @app.template_global()
    def moment():
        """Función global para obtener momento actual"""
        return datetime.now()
