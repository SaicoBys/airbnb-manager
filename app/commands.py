import click
from flask.cli import with_appcontext
from datetime import datetime, timedelta

from .extensions import db
from .models import User, Room, Client, Stay, Payment, Expense, Task, Supply

@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """
    Limpia la base de datos y la puebla con datos de prueba.
    """
    # 1. Limpiamos todas las tablas para un inicio fresco
    click.echo("Limpiando datos antiguos...")
    Payment.query.delete()
    Stay.query.delete()
    Expense.query.delete()
    Task.query.delete()
    Client.query.delete()
    Room.query.delete()
    User.query.delete()
    Supply.query.delete()
    db.session.commit()
    click.echo("Tablas limpiadas.")

    # 2. Creamos los Usuarios
    click.echo("Creando usuarios...")
    jacob = User(username='jacob', role='dueño')
    jacob.set_password('clave123')
    alejandrina = User(username='alejandrina', role='socia')
    alejandrina.set_password('clave123')
    elizabeth = User(username='elizabeth', role='empleada')
    elizabeth.set_password('clave123')
    db.session.add_all([jacob, alejandrina, elizabeth])
    db.session.commit()
    click.echo("Usuarios creados.")

    # 3. Creamos las Habitaciones
    click.echo("Creando habitaciones...")
    room1 = Room(name='Habitación 1 - Vista al Jardín')
    room2 = Room(name='Suite 2 - Balcón Privado')
    room3 = Room(name='Habitación 3 - Económica')
    db.session.add_all([room1, room2, room3])
    db.session.commit()
    click.echo("Habitaciones creadas.")

    # 4. Creamos los Clientes
    click.echo("Creando clientes...")
    client1 = Client(full_name='Juan Pérez', phone_number='809-111-1111')
    client2 = Client(full_name='Ana García', phone_number='809-222-2222', email='ana.garcia@email.com')
    client3 = Client(full_name='Carlos Rodriguez', phone_number='809-333-3333')
    db.session.add_all([client1, client2, client3])
    db.session.commit()
    click.echo("Clientes creados.")

    # 5. Creamos Estancias y sus Pagos asociados
    click.echo("Creando estancias y pagos...")
    stay1 = Stay(client=client1, room=room2, check_in_date=datetime.utcnow() - timedelta(days=10), check_out_date=datetime.utcnow() - timedelta(days=5), booking_channel='Airbnb')
    db.session.add(stay1)
    db.session.commit()
    payment1 = Payment(amount=5500.00, stay=stay1, method='Tarjeta')
    db.session.add(payment1)

    stay2 = Stay(client=client2, room=room1, check_in_date=datetime.utcnow() - timedelta(days=3), booking_channel='Directo')
    db.session.add(stay2)
    db.session.commit()
    payment2 = Payment(amount=2500.00, stay=stay2, method='Efectivo')
    db.session.add(payment2)

    stay3 = Stay(client=client1, room=room3, check_in_date=datetime.utcnow() - timedelta(days=20), check_out_date=datetime.utcnow() - timedelta(days=18), booking_channel='Booking.com')
    db.session.add(stay3)
    db.session.commit()
    payment3 = Payment(amount=1800.00, stay=stay3, method='Efectivo')
    db.session.add(payment3)
    click.echo("Estancias y pagos creados.")

    # 6. Creamos Gastos de prueba
    click.echo("Creando gastos...")
    expense1 = Expense(description='Compra de productos de limpieza', amount=1250.50, category='Suministros', expense_date=datetime.utcnow() - timedelta(days=8))
    expense2 = Expense(description='Pago factura de internet', amount=2500.00, category='Servicios', expense_date=datetime.utcnow() - timedelta(days=2))
    expense3 = Expense(description='Reparación de ducha Hab. 1', amount=800.00, category='Mantenimiento', expense_date=datetime.utcnow() - timedelta(days=15))
    db.session.add_all([expense1, expense2, expense3])
    click.echo("Gastos creados.")

    # 7. Creamos Suministros de prueba
    click.echo("Creando suministros...")
    
    # Productos de limpieza
    supply1 = Supply(name='Detergente líquido', category='Limpieza', current_stock=15, minimum_stock=10, unit_price=120.00, supplier='Supermarket Central')
    supply2 = Supply(name='Papel higiénico', category='Baño', current_stock=8, minimum_stock=20, unit_price=45.00, supplier='Distribuidora López')  # Stock bajo
    supply3 = Supply(name='Desinfectante multiusos', category='Limpieza', current_stock=0, minimum_stock=5, unit_price=89.50, supplier='Supermarket Central')  # Agotado
    
    # Amenities
    supply4 = Supply(name='Champú pequeño', category='Amenities', current_stock=25, minimum_stock=15, unit_price=35.00, supplier='Hotel Supplies RD')
    supply5 = Supply(name='Toallas de baño', category='Ropa de Cama', current_stock=12, minimum_stock=8, unit_price=450.00, supplier='Textiles Morales')
    supply6 = Supply(name='Sábanas matrimoniales', category='Ropa de Cama', current_stock=3, minimum_stock=6, unit_price=850.00, supplier='Textiles Morales')  # Stock bajo
    
    # Cocina
    supply7 = Supply(name='Filtros de agua', category='Cocina', current_stock=18, minimum_stock=10, unit_price=25.00, supplier='Ferretería González')
    supply8 = Supply(name='Bolsas de basura grandes', category='Limpieza', current_stock=1, minimum_stock=10, unit_price=75.00, supplier='Distribuidora López')  # Stock bajo
    
    # Mantenimiento  
    supply9 = Supply(name='Bombillos LED', category='Mantenimiento', current_stock=22, minimum_stock=12, unit_price=180.00, supplier='Ferretería González')
    supply10 = Supply(name='Pilas AA', category='Mantenimiento', current_stock=0, minimum_stock=8, unit_price=45.00, supplier='Ferretería González')  # Agotado
    
    db.session.add_all([supply1, supply2, supply3, supply4, supply5, supply6, supply7, supply8, supply9, supply10])
    click.echo("Suministros creados (algunos con stock bajo para testing).")

    # 8. Guardamos todos los cambios finales
    db.session.commit()
    click.echo("¡Base de datos poblada con datos de prueba!")
