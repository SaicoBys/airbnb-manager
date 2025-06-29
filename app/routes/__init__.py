"""
AIRBNB MANAGER V3.0 - INICIALIZACIÓN DE BLUEPRINTS
Registra todos los blueprints modulares de la aplicación
"""

def register_blueprints(app):
    """Registra todos los blueprints de la aplicación"""
    
    # Importar blueprints
    from app.routes import panel_routes, ajax_routes, auth_routes, supply_routes, intelligence_routes
    
    # Registrar blueprints principales
    app.register_blueprint(panel_routes.bp)  # Sin url_prefix para que sea la raíz
    app.register_blueprint(ajax_routes.bp)  # Ya tiene url_prefix='/ajax'
    app.register_blueprint(auth_routes.bp, url_prefix='/auth')
    app.register_blueprint(supply_routes.bp)  # Ya tiene url_prefix='/supply-packages'
    app.register_blueprint(intelligence_routes.bp)  # Ya tiene url_prefix='/intelligence'
    
    # Blueprint principal (mantener compatibilidad)
    # Este será eliminado gradualmente según se migran las rutas
    from app.routes.main_routes import bp as main_bp
    app.register_blueprint(main_bp)