#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

def test_login():
    session = requests.Session()
    
    # Obtener la página de login
    login_page = session.get('http://127.0.0.1:5004/login')
    print(f"Login page status: {login_page.status_code}")
    
    # Extraer el token CSRF
    soup = BeautifulSoup(login_page.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
    print(f"CSRF token: {csrf_token[:20]}...")
    
    # Hacer login
    login_data = {
        'username': 'elizabeth',
        'password': 'password123',
        'csrf_token': csrf_token,
        'submit': 'Iniciar Sesión'
    }
    
    response = session.post('http://127.0.0.1:5004/login', data=login_data)
    print(f"Login response status: {response.status_code}")
    print(f"Final URL: {response.url}")
    
    # Probar acceso al panel principal
    dashboard = session.get('http://127.0.0.1:5004/')
    print(f"Dashboard status: {dashboard.status_code}")
    
    if dashboard.status_code == 200:
        print("✅ ¡Login exitoso! Panel principal accesible")
        if 'Panel de Control Airbnb' in dashboard.text:
            print("✅ Template del panel de control cargado correctamente")
        else:
            print("❌ Panel de control no se cargó correctamente")
    else:
        print(f"❌ Error accediendo al panel: {dashboard.status_code}")

if __name__ == '__main__':
    try:
        test_login()
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")