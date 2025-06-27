#!/usr/bin/env python3
"""
Script para poblar la base de datos con datos de prueba
Genera clientes, productos, gastos, estancias y pagos ficticios
"""

import os
import sys
from datetime import datetime, timedelta
import random

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Room, Client, Stay, Payment, Expense, Supply

# Datos ficticios para República Dominicana
DOMINICAN_FIRST_NAMES = [
    'Ana', 'María', 'Carmen', 'Rosa', 'Juana', 'Isabel', 'Teresa', 'Francisca', 'Esperanza', 'Luz',
    'Carlos', 'José', 'Manuel', 'Francisco', 'Rafael', 'Antonio', 'Miguel', 'Pedro', 'Ramón', 'Luis'
]

DOMINICAN_LAST_NAMES = [
    'García', 'Rodríguez', 'Martínez', 'Hernández', 'González', 'Pérez', 'Sánchez', 'Ramírez', 
    'Cruz', 'Vargas', 'Castillo', 'Jiménez', 'Morales', 'Ortiz', 'Delgado', 'Castro', 'Ruiz'
]

DOMINICAN_COMPANIES = [
    'Supermercado Nacional', 'Ferretería Central', 'Distribuidora Caribeña', 'Comercial Antillana',
    'Suministros del Este', 'Importadora Dominicana', 'Grupo Empresarial', 'Distribuciones Modernas'
]

def create_test_users():
    """Crear usuarios de prueba si no existen"""
    users_data = [
        {'username': 'elizabeth', 'role': 'empleada'},
        {'username': 'alejandrina', 'role': 'socia'},
        {'username': 'propietario1', 'role': 'dueño'},
        {'username': 'propietario2', 'role': 'dueño'}
    ]
    
    created_users = []
    for user_data in users_data:
        user = User.query.filter_by(username=user_data['username']).first()
        if not user:
            user = User(username=user_data['username'], role=user_data['role'])
            user.set_password('password123')
            db.session.add(user)
            created_users.append(user)
            print(f"✅ Usuario creado: {user_data['username']} ({user_data['role']})")
        else:
            created_users.append(user)
            print(f"ℹ️  Usuario ya existe: {user_data['username']}")
    
    return created_users

def create_test_rooms():
    """Crear habitaciones de prueba si no existen"""
    rooms_data = [
        'Habitación 1', 'Habitación 2', 'Habitación 3', 
        'Suite Principal', 'Habitación Familiar'
    ]
    
    created_rooms = []
    for room_name in rooms_data:
        room = Room.query.filter_by(name=room_name).first()
        if not room:
            room = Room(name=room_name, status=random.choice(['Limpia', 'Ocupada', 'Mantenimiento']))
            db.session.add(room)
            created_rooms.append(room)
            print(f"✅ Habitación creada: {room_name}")
        else:
            created_rooms.append(room)
    
    return created_rooms

def create_test_clients():
    """Crear 20 clientes ficticios"""
    print("\n🧑‍🤝‍🧑 Creando clientes ficticios...")
    
    clients = []
    for i in range(20):
        # Generar datos realistas dominicanos
        first_name = random.choice(DOMINICAN_FIRST_NAMES)
        last_name = random.choice(DOMINICAN_LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        
        # Teléfonos dominicanos realistas
        phone_prefixes = ['809', '829', '849']
        phone = f"{random.choice(phone_prefixes)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"
        
        # Email opcional (algunos clientes no tienen)
        email = f"{first_name.lower()}.{last_name.lower()}@gmail.com" if random.choice([True, False, False]) else None
        
        notes_options = [
            "Cliente frecuente, muy educado",
            "Prefiere habitación silenciosa", 
            "Viaja por trabajo",
            "Cliente de confianza",
            "Familia con niños pequeños",
            None, None  # Más probabilidad de no tener notas
        ]
        
        client = Client(
            full_name=full_name,
            phone_number=phone,
            email=email,
            notes=random.choice(notes_options)
        )
        
        clients.append(client)
        db.session.add(client)
        print(f"  👤 {full_name} - {phone}")
    
    return clients

def create_test_supplies():
    """Crear inventario con productos variados"""
    print("\n📦 Creando inventario de suministros...")
    
    supplies_data = [
        # Limpieza
        {'name': 'Detergente en Polvo', 'category': 'Limpieza', 'stock': 15, 'min_stock': 5, 'price': 85.00},
        {'name': 'Cloro Líquido', 'category': 'Limpieza', 'stock': 8, 'min_stock': 3, 'price': 45.00},
        {'name': 'Jabón Líquido', 'category': 'Limpieza', 'stock': 12, 'min_stock': 4, 'price': 120.00},
        {'name': 'Papel Higiénico (Paquete)', 'category': 'Limpieza', 'stock': 25, 'min_stock': 10, 'price': 180.00},
        {'name': 'Toallas de Papel', 'category': 'Limpieza', 'stock': 6, 'min_stock': 8, 'price': 65.00},  # Stock bajo
        {'name': 'Desinfectante', 'category': 'Limpieza', 'stock': 10, 'min_stock': 5, 'price': 95.00},
        
        # Amenidades
        {'name': 'Champú (Botella)', 'category': 'Amenidades', 'stock': 20, 'min_stock': 8, 'price': 150.00},
        {'name': 'Acondicionador', 'category': 'Amenidades', 'stock': 18, 'min_stock': 8, 'price': 165.00},
        {'name': 'Jabón de Baño', 'category': 'Amenidades', 'stock': 35, 'min_stock': 15, 'price': 25.00},
        {'name': 'Toallas de Baño', 'category': 'Amenidades', 'stock': 30, 'min_stock': 12, 'price': 450.00},
        {'name': 'Sábanas (Juego)', 'category': 'Amenidades', 'stock': 2, 'min_stock': 6, 'price': 890.00},  # Stock bajo
        
        # Cocina
        {'name': 'Café Molido (Libra)', 'category': 'Cocina', 'stock': 8, 'min_stock': 4, 'price': 185.00},
        {'name': 'Azúcar (Libra)', 'category': 'Cocina', 'stock': 12, 'min_stock': 5, 'price': 35.00},
        {'name': 'Aceite de Cocina', 'category': 'Cocina', 'stock': 6, 'min_stock': 3, 'price': 125.00},
        {'name': 'Sal (Libra)', 'category': 'Cocina', 'stock': 15, 'min_stock': 5, 'price': 15.00},
        
        # Mantenimiento
        {'name': 'Bombillos LED', 'category': 'Mantenimiento', 'stock': 1, 'min_stock': 5, 'price': 95.00},  # Stock bajo
        {'name': 'Pilas AA (Paquete)', 'category': 'Mantenimiento', 'stock': 8, 'min_stock': 4, 'price': 120.00},
        {'name': 'Cinta Adhesiva', 'category': 'Mantenimiento', 'stock': 5, 'min_stock': 3, 'price': 45.00},
        {'name': 'Destornilladores (Set)', 'category': 'Mantenimiento', 'stock': 2, 'min_stock': 1, 'price': 385.00},
        
        # Oficina
        {'name': 'Papel Bond (Resma)', 'category': 'Oficina', 'stock': 4, 'min_stock': 2, 'price': 245.00},
        {'name': 'Bolígrafos (Paquete)', 'category': 'Oficina', 'stock': 12, 'min_stock': 6, 'price': 85.00}
    ]
    
    supplies = []
    for supply_data in supplies_data:
        supply = Supply(
            name=supply_data['name'],
            category=supply_data['category'],
            current_stock=supply_data['stock'],
            minimum_stock=supply_data['min_stock'],
            unit_price=supply_data['price'],
            supplier=random.choice(DOMINICAN_COMPANIES) if random.choice([True, False]) else None,
            notes=f"Proveedor confiable - {random.choice(['Entrega rápida', 'Buenos precios', 'Calidad garantizada'])}" if random.choice([True, False]) else None
        )
        
        supplies.append(supply)
        db.session.add(supply)
        
        status = "🔴 STOCK BAJO" if supply.is_low_stock() else "✅ Stock OK"
        print(f"  📦 {supply_data['name']} - Stock: {supply_data['stock']} {status}")
    
    return supplies

def create_test_expenses(users):
    """Crear gastos variados pagados por diferentes personas"""
    print("\n💸 Creando gastos de prueba...")
    
    # Encontrar usuarios específicos
    elizabeth = next((u for u in users if u.username == 'elizabeth'), None)
    alejandrina = next((u for u in users if u.username == 'alejandrina'), None)
    propietario1 = next((u for u in users if u.username == 'propietario1'), None)
    propietario2 = next((u for u in users if u.username == 'propietario2'), None)
    
    expenses_data = [
        # Gastos de Elizabeth (empleada) - Afectan su cuadre de caja
        {'desc': 'Compra de detergente y cloro', 'amount': 245.50, 'category': 'Limpieza', 'paid_by': elizabeth, 'method': 'Efectivo'},
        {'desc': 'Reparación de grifo habitación 2', 'amount': 450.00, 'category': 'Mantenimiento', 'paid_by': elizabeth, 'method': 'Efectivo'},
        {'desc': 'Compra de papel higiénico', 'amount': 180.00, 'category': 'Limpieza', 'paid_by': elizabeth, 'method': 'Efectivo'},
        {'desc': 'Café y azúcar para huéspedes', 'amount': 320.00, 'category': 'Amenidades', 'paid_by': elizabeth, 'method': 'Efectivo'},
        {'desc': 'Bombillos para habitaciones', 'amount': 285.00, 'category': 'Mantenimiento', 'paid_by': elizabeth, 'method': 'Tarjeta'},
        {'desc': 'Productos de limpieza varios', 'amount': 520.75, 'category': 'Limpieza', 'paid_by': elizabeth, 'method': 'Efectivo'},
        
        # Gastos de Alejandrina (socia) - NO afectan cuadre de Elizabeth
        {'desc': 'Compra de toallas nuevas', 'amount': 1250.00, 'category': 'Amenidades', 'paid_by': alejandrina, 'method': 'Tarjeta'},
        {'desc': 'Pago de electricidad', 'amount': 3450.00, 'category': 'Servicios', 'paid_by': alejandrina, 'method': 'Transferencia'},
        {'desc': 'Internet y cable', 'amount': 2100.00, 'category': 'Servicios', 'paid_by': alejandrina, 'method': 'Tarjeta'},
        {'desc': 'Compra de sábanas de calidad', 'amount': 2890.00, 'category': 'Amenidades', 'paid_by': alejandrina, 'method': 'Tarjeta'},
        {'desc': 'Reparación aire acondicionado', 'amount': 1850.00, 'category': 'Mantenimiento', 'paid_by': alejandrina, 'method': 'Efectivo'},
        {'desc': 'Marketing digital y publicidad', 'amount': 5500.00, 'category': 'Marketing', 'paid_by': alejandrina, 'method': 'Transferencia'},
        {'desc': 'Compra de electrodomésticos', 'amount': 8750.00, 'category': 'Equipamiento', 'paid_by': alejandrina, 'method': 'Tarjeta'},
        
        # Gastos de propietarios - NO afectan cuadre de Elizabeth
        {'desc': 'Seguro de la propiedad', 'amount': 12500.00, 'category': 'Seguros', 'paid_by': propietario1, 'method': 'Transferencia'},
        {'desc': 'Impuestos municipales', 'amount': 8900.00, 'category': 'Impuestos', 'paid_by': propietario1, 'method': 'Transferencia'},
        {'desc': 'Renovación de licencias', 'amount': 2300.00, 'category': 'Legal', 'paid_by': propietario2, 'method': 'Tarjeta'},
        {'desc': 'Consultoría contable', 'amount': 4500.00, 'category': 'Profesional', 'paid_by': propietario2, 'method': 'Transferencia'},
        {'desc': 'Reparaciones mayores', 'amount': 15600.00, 'category': 'Mantenimiento', 'paid_by': propietario1, 'method': 'Transferencia'},
    ]
    
    expenses = []
    for i, expense_data in enumerate(expenses_data):
        # Fechas aleatorias en los últimos 2 meses
        days_ago = random.randint(1, 60)
        expense_date = datetime.now() - timedelta(days=days_ago)
        
        expense = Expense(
            description=expense_data['desc'],
            amount=expense_data['amount'],
            category=expense_data['category'],
            expense_date=expense_date,
            paid_by_user_id=expense_data['paid_by'].id if expense_data['paid_by'] else None,
            payment_method=expense_data['method']
        )
        
        expenses.append(expense)
        db.session.add(expense)
        
        paid_by_name = expense_data['paid_by'].username.title() if expense_data['paid_by'] else "N/A"
        affects_cash = "⚠️ AFECTA CAJA" if expense_data['paid_by'] == elizabeth else "✅ No afecta"
        print(f"  💸 DOP {expense_data['amount']:,.2f} - {expense_data['desc'][:40]}... ({paid_by_name}) {affects_cash}")
    
    return expenses

def create_test_stays_and_payments(clients, rooms):
    """Crear estancias y pagos de prueba"""
    print("\n🏨 Creando estancias y pagos...")
    
    booking_channels = ['Airbnb', 'Booking.com', 'Directo', 'Expedia', 'WhatsApp']
    payment_methods = ['Efectivo', 'Tarjeta', 'Transferencia']
    
    stays = []
    payments = []
    
    # Crear entre 25-35 estancias en los últimos 3 meses
    num_stays = random.randint(25, 35)
    
    for i in range(num_stays):
        client = random.choice(clients)
        room = random.choice(rooms)
        
        # Fechas aleatorias en los últimos 90 días
        days_ago = random.randint(1, 90)
        check_in = datetime.now() - timedelta(days=days_ago)
        
        # Estancias de 1-7 días
        stay_duration = random.randint(1, 7)
        check_out = check_in + timedelta(days=stay_duration)
        
        stay = Stay(
            client_id=client.id,
            room_id=room.id,
            check_in_date=check_in,
            check_out_date=check_out,
            booking_channel=random.choice(booking_channels)
        )
        
        stays.append(stay)
        db.session.add(stay)
        db.session.flush()  # Para obtener el ID
        
        # Crear 1-3 pagos por estancia
        num_payments = random.randint(1, 3)
        total_payment = 0
        
        # Precios por noche entre 1500-4500 DOP
        night_price = random.randint(1500, 4500)
        expected_total = night_price * stay_duration
        
        for j in range(num_payments):
            if j == num_payments - 1:  # Último pago
                payment_amount = expected_total - total_payment
            else:
                payment_amount = random.randint(500, expected_total // 2)
                total_payment += payment_amount
            
            # Fecha de pago cercana al check-in
            payment_date = check_in + timedelta(days=random.randint(0, 2))
            
            payment = Payment(
                stay_id=stay.id,
                amount=payment_amount,
                payment_date=payment_date,
                method=random.choice(payment_methods)
            )
            
            payments.append(payment)
            db.session.add(payment)
        
        print(f"  🏨 {client.full_name} - {room.name} ({stay_duration} noches) - DOP {expected_total:,.2f}")
    
    return stays, payments

def main():
    """Función principal para ejecutar la población de datos"""
    print("🚀 Iniciando población de datos de prueba...")
    print("=" * 50)
    
    # Crear la aplicación Flask
    app = create_app()
    
    with app.app_context():
        print("📊 Creando usuarios y habitaciones...")
        users = create_test_users()
        rooms = create_test_rooms()
        
        # Commit para tener IDs disponibles
        db.session.commit()
        
        # Crear datos de prueba
        clients = create_test_clients()
        supplies = create_test_supplies()
        expenses = create_test_expenses(users)
        stays, payments = create_test_stays_and_payments(clients, rooms)
        
        # Commit final
        try:
            db.session.commit()
            print("\n" + "=" * 50)
            print("✅ DATOS DE PRUEBA CREADOS EXITOSAMENTE!")
            print("=" * 50)
            print(f"👥 Clientes: {len(clients)}")
            print(f"🏨 Habitaciones: {len(rooms)}")
            print(f"📦 Suministros: {len(supplies)}")
            print(f"💸 Gastos: {len(expenses)}")
            print(f"🛏️  Estancias: {len(stays)}")
            print(f"💰 Pagos: {len(payments)}")
            print("\n🎯 Ahora puedes probar el sistema con datos realistas!")
            
            # Mostrar resumen de gastos por persona
            print("\n💸 RESUMEN DE GASTOS POR PERSONA:")
            elizabeth_total = sum(e.amount for e in expenses if e.paid_by and e.paid_by.username == 'elizabeth')
            alejandrina_total = sum(e.amount for e in expenses if e.paid_by and e.paid_by.username == 'alejandrina')
            propietarios_total = sum(e.amount for e in expenses if e.paid_by and e.paid_by.role == 'dueño')
            
            print(f"👩‍💼 Elizabeth (empleada): DOP {elizabeth_total:,.2f} - ⚠️ AFECTA su cuadre de caja")
            print(f"👩‍💼 Alejandrina (socia): DOP {alejandrina_total:,.2f} - ✅ NO afecta cuadre")
            print(f"👑 Propietarios: DOP {propietarios_total:,.2f} - ✅ NO afecta cuadre")
            print(f"📊 TOTAL GASTOS DEL NEGOCIO: DOP {elizabeth_total + alejandrina_total + propietarios_total:,.2f}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al crear datos: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)