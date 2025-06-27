import os

class Config:
    """
    Clase de configuración para la aplicación Flask.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil-de-adivinar'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- ¡NUEVA VARIABLE! ---
    # Tasa de cambio para la conversión. Puedes actualizar este valor cuando lo necesites.
    TASA_CAMBIO_DOP_USD = 58.50
