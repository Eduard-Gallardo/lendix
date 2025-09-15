from flask import Flask, render_template, url_for, redirect, session
from routes.admin import admin_bp
from routes.login import login_bp
from routes.registro import registro_bp
from routes.prestamos import prestamos_bp
from routes.catalogo import catalogo_bp

app = Flask(__name__)
app.secret_key = 'super'

# Configuración de la sesión
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

@app.route('/')
def index():
    return render_template('views/index.html')
@app.context_processor
def inject_user():
    return dict(
        current_user={
            'id': session.get('user_id'),
            'nombre': session.get('user_nombre'),
            'email': session.get('user_email'),
            'is_authenticated': 'user_id' in session
        }
    )

app.register_blueprint(admin_bp, url_prefix='/admin')

app.register_blueprint(login_bp, url_prefix='/login')

app.register_blueprint(registro_bp, url_prefix='/registro')

app.register_blueprint(prestamos_bp, url_prefix='/prestamos')

app.register_blueprint(catalogo_bp, url_prefix='/catalogo')
