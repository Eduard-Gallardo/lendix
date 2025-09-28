from flask import Flask, render_template, url_for, redirect, session
from routes.admin import admin_bp
from routes.login import login_bp
from routes.registro import registro_bp
from routes.prestamos import prestamos_bp, reservas_bp
from routes.catalogo import catalogo_bp
from routes.instructor import instructor_bp  # Nuevo blueprint para instructores
from utils.db import init_db, seed_sample_data

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_in_production'

# Configuración de la sesión
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora


@app.route('/')
def index():
    return render_template('views/index.html')

@app.context_processor
def inject_user():
    """Inyectar información del usuario en todas las plantillas"""
    return dict(
        current_user={
            'id': session.get('user_id'),
            'nombre': session.get('user_nombre'),
            'email': session.get('user_email'),
            'rol': session.get('rol'),
            'is_authenticated': 'user_id' in session,
            'is_admin': session.get('rol') == 'admin',
            'is_instructor': session.get('rol') in ['instructor', 'admin'],
            'is_aprendiz': session.get('rol') == 'aprendiz',
            'is_externo': session.get('rol') == 'externo'
        },
        session=session  # Para acceder a session en las plantillas
    )

# Registrar blueprints
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(login_bp, url_prefix='/login')
app.register_blueprint(registro_bp, url_prefix='/registro')
app.register_blueprint(prestamos_bp, url_prefix='/prestamos')
app.register_blueprint(reservas_bp, url_prefix='/reservas')
app.register_blueprint(catalogo_bp, url_prefix='/catalogo')
app.register_blueprint(instructor_bp, url_prefix='/instructor')

# Manejo de errores
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403
