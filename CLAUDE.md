# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Run the application:**
```bash
python run.py
```
The application runs on http://localhost:5001 with debug mode enabled.

**Database operations:**
```bash
# Initialize database migrations
flask db init

# Create migration
flask db migrate -m "description"

# Apply migrations
flask db upgrade

# Seed database with test data
flask seed-db
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

## Architecture Overview

This is a Flask-based Airbnb property management system with Spanish language interface.

**Core Structure:**
- **Flask Application Factory Pattern**: `app/__init__.py` creates the app using `create_app()` factory
- **Blueprint-based Routes**: All routes defined in `app/routes.py` using Flask Blueprint
- **SQLAlchemy ORM**: Database models in `app/models.py` with relationships
- **Flask-WTF Forms**: Form definitions in `app/forms.py` with validation
- **Flask-Login Authentication**: User authentication with role-based access
- **Flask-Migrate**: Database versioning and migrations

**Key Models and Relationships:**
- **User**: Authentication with roles (`dueño`, `socia`) and password hashing
- **Client**: Guest information with stays relationship
- **Room**: Property rooms with status tracking and stays
- **Stay**: Core booking entity linking clients to rooms with booking channels
- **Payment**: Revenue tracking linked to stays
- **Expense**: Cost tracking with categories
- **Task**: User task management

**Data Flow:**
1. Stays connect Clients to Rooms with check-in/out dates and booking channels (Airbnb, Booking.com, Directo)
2. Payments are linked to specific stays for revenue tracking
3. Expenses are independent cost tracking with categories
4. Reports aggregate payments and expenses with DOP/USD conversion

**Configuration:**
- `config.py`: Contains database URI, secret key, and exchange rate (`TASA_CAMBIO_DOP_USD`)
- SQLite database stored in `instance/app.db`
- Environment variables supported for production deployment

**Templates:**
- Spanish language interface
- Bootstrap-based responsive design
- Jinja2 templates in `app/templates/`
- Base template with navigation in `base.html`

**CLI Commands:**
- Custom `flask seed-db` command in `app/commands.py` for development data
- Creates test users (jacob/alejandrina), rooms, clients, stays, payments, and expenses

**Key Business Logic:**
- Currency conversion between DOP and USD using configurable exchange rate
- Monthly reporting with profit calculations
- Room status management (Limpia, Ocupada, Mantenimiento)
- Multi-channel booking tracking (Airbnb, Booking.com, Direct)
- User role-based access control

**Development Notes:**
- Spanish language used throughout (comments, UI text, model names)
- Test data includes realistic Airbnb scenario with multiple rooms and booking channels
- Flask debug mode enabled for development server
- Instance folder contains SQLite database for development