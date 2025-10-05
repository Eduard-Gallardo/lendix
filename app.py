from flask import Flask, render_template, url_for, redirect, session
from flask_session import Session
from routes.admin import admin_bp
from routes.login import login_bp
from routes.registro import registro_bp
from routes.prestamos import prestamos_bp
from routes.catalogo import catalogo_bp
from utils.db import init_db, crear_admin_inicial, migrar_base_datos

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-in-production'

# Configuración de la sesión
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

# Inicializar Flask-Session
Session(app)

# Inicializar base de datos al arrancar
with app.app_context():
    try:
        init_db()
        migrar_base_datos()  # Migrar estructura existente
        crear_admin_inicial()
        print("Base de datos inicializada y migrada correctamente")
    except Exception as e:
        print(f"Error al inicializar base de datos: {e}")

@app.route('/')
def index():
    return render_template('views/index.html')

@app.context_processor
def inject_user():
    """Inyecta información del usuario en todos los templates"""
    return dict(
        current_user={
            'id': session.get('user_id'),
            'nombre': session.get('user_nombre'),
            'email': session.get('user_email'),
            'rol': session.get('rol'),
            'is_authenticated': 'user_id' in session
        }
    )

# Registrar blueprints
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(login_bp)
app.register_blueprint(registro_bp, url_prefix='/registro')
app.register_blueprint(prestamos_bp, url_prefix='/prestamos')
app.register_blueprint(catalogo_bp, url_prefix='/catalogo')

# Manejadores de errores
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403

# Filtros de template personalizados
@app.template_filter('format_date')
def format_date(date_string):
    """Formatea una fecha para mostrarla de forma legible"""
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        return date_obj.strftime("%d/%m/%Y %H:%M")
    except:
        return date_string

@app.template_filter('format_date_short')
def format_date_short(date_string):
    """Formatea una fecha de forma corta"""
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        return date_obj.strftime("%d/%m/%Y")
    except:
        return date_string

@app.template_filter('time_ago')
def time_ago(date_string):
    """Calcula cuánto tiempo ha pasado desde una fecha"""
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - date_obj
        
        if delta.days > 365:
            years = delta.days // 365
            return f"hace {years} año{'s' if years > 1 else ''}"
        elif delta.days > 30:
            months = delta.days // 30
            return f"hace {months} mes{'es' if months > 1 else ''}"
        elif delta.days > 0:
            return f"hace {delta.days} día{'s' if delta.days > 1 else ''}"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"hace {hours} hora{'s' if hours > 1 else ''}"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"hace {minutes} minuto{'s' if minutes > 1 else ''}"
        else:
            return "hace un momento"
    except:
        return date_string

# Comando CLI para inicializar la base de datos manualmente
@app.cli.command()
def initdb():
    """Inicializa la base de datos"""
    init_db()
    crear_admin_inicial()
    print("Base de datos inicializada")

@app.cli.command()
def migratedb():
    """Migra la base de datos existente para corregir inconsistencias"""
    migrar_base_datos()
    print("Migración de base de datos completada")

@app.cli.command()
def resetdb():
    """Resetea completamente la base de datos (PELIGRO: borra todos los datos)"""
    import os
    db_path = 'models/database.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Base de datos eliminada")
    init_db()
    crear_admin_inicial()
    print("Base de datos recreada")
