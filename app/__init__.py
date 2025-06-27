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

    # --- REGISTRAMOS LOS BLUEPRINTS ---
    from . import routes
    app.register_blueprint(routes.bp)
    
    # --- CONFIGURAMOS FLASK-LOGIN ---
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

    return app
