from app import create_app

# Creamos una instancia de nuestra aplicación llamando a la factory.
app = create_app()

if __name__ == '__main__':
    # Usamos app.run() para iniciar el servidor de desarrollo de Flask.
    # El host '0.0.0.0' hace que el servidor sea accesible desde otros
    # dispositivos en la misma red, no solo desde localhost.
    # El modo debug está activado para facilitar el desarrollo.
    app.run(host='0.0.0.0', port=5004, debug=True)
