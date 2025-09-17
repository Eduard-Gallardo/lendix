
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, session  # Agregar session
import sqlite3
import os
from utils.db import get_db_connection
from werkzeug.utils import secure_filename
from routes.login import login_required  # Agregar este import

# Configuración del Blueprint
admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Configuración
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Crear directorio de uploads si no existe
def ensure_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

# AGREGAR ESTA FUNCIÓN DE VERIFICACIÓN DE ADMIN
def is_admin():
    return session.get('user_email') == 'Eduard@gmail.com'

# Rutas del Blueprint
@admin_bp.route('/admin') 
@admin_bp.route('/admin/')
@login_required  # AGREGAR DECORADOR DE LOGIN
def admin():
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Obtener estadísticas
    total_implementos = conn.execute('SELECT COUNT(*) as count FROM catalogo').fetchone()['count']
    total_usuarios = conn.execute('SELECT COUNT(*) as count FROM usuarios').fetchone()['count']
    total_reservas = conn.execute('SELECT COUNT(*) as count FROM reservas').fetchone()['count']
    implementos = conn.execute('SELECT * FROM catalogo ORDER BY id DESC LIMIT 5').fetchall()
    
    conn.close()
    
    return render_template('admin/panel_administrador.html', 
                    total_implementos=total_implementos,
                    total_usuarios=total_usuarios,
                    total_reservas=total_reservas,
                    implementos=implementos)

@admin_bp.route('/admin/catalogo')
def ver_catalogo():
    conn = get_db_connection()
    implementos = conn.execute('SELECT * FROM catalogo ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/panel_administrador.html', implementos=implementos)

@admin_bp.route('/admin/catalogo/agregar', methods=['GET', 'POST'])
def agregar_implemento():
    if request.method == 'POST':
        # Obtener datos del formulario
        implemento = request.form.get('implemento')
        descripcion = request.form.get('descripcion')
        disponibilidad = request.form.get('disponibilidad')
        categoria = request.form.get('categoria')
        
        # Validar campos obligatorios
        if not all([implemento, descripcion, disponibilidad, categoria]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('admin/agregar_implemento.html')
        
        # Manejar la carga de la imagen
        imagen_url = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                ensure_upload_folder()
                filename = secure_filename(file.filename)
                # Crear nombre único para evitar colisiones
                unique_filename = f"{os.urandom(8).hex()}_{filename}"
                file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                imagen_url = unique_filename
        
        # Guardar en la base de datos
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO catalogo (implemento, descripcion, disponibilidad, categoria, imagen_url) VALUES (?, ?, ?, ?, ?)',
                (implemento, descripcion, disponibilidad, categoria, imagen_url)
            )
            conn.commit()
            flash('Implemento agregado correctamente', 'success')
        except sqlite3.Error as e:
            flash(f'Error al guardar en la base de datos: {str(e)}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('admin.ver_catalogo'))
    
    return render_template('admin/agregar_implemento.html')

@admin_bp.route('/admin/catalogo/editar/<int:id>', methods=['GET', 'POST'])
def editar_implemento(id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        implemento = request.form.get('implemento')
        descripcion = request.form.get('descripcion')
        disponibilidad = request.form.get('disponibilidad')
        categoria = request.form.get('categoria')
        
        # Validar campos obligatorios
        if not all([implemento, descripcion, disponibilidad, categoria]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('admin.editar_implemento', id=id))
        
        # Si se sube una nueva imagen
        imagen_url = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                ensure_upload_folder()
                filename = secure_filename(file.filename)
                unique_filename = f"{os.urandom(8).hex()}_{filename}"
                file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                imagen_url = unique_filename
        
        # Actualizar en la base de datos
        try:
            if imagen_url:
                conn.execute(
                    'UPDATE catalogo SET implemento = ?, descripcion = ?, disponibilidad = ?, categoria = ?, imagen_url = ? WHERE id = ?',
                    (implemento, descripcion, disponibilidad, categoria, imagen_url, id)
                )
            else:
                conn.execute(
                    'UPDATE catalogo SET implemento = ?, descripcion = ?, disponibilidad = ?, categoria = ? WHERE id = ?',
                    (implemento, descripcion, disponibilidad, categoria, id)
                )
            conn.commit()
            flash('Implemento actualizado correctamente', 'success')
        except sqlite3.Error as e:
            flash(f'Error al actualizar: {str(e)}', 'error')
        
        conn.close()
        return redirect(url_for('admin.ver_catalogo'))
    
    # GET request - mostrar formulario con datos actuales
    implemento = conn.execute('SELECT * FROM catalogo WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if implemento is None:
        flash('Implemento no encontrado', 'error')
        return redirect(url_for('admin.ver_catalogo'))
    
    return render_template('admin/editar_implemento.html', implemento=implemento)

@admin_bp.route('/admin/catalogo/eliminar/<int:id>', methods=['POST'])
def eliminar_implemento(id):
    conn = get_db_connection()
    
    try:
        # Obtener información de la imagen para eliminarla del sistema de archivos
        implemento = conn.execute('SELECT imagen_url FROM catalogo WHERE id = ?', (id,)).fetchone()
        
        if implemento and implemento['imagen_url']:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, implemento['imagen_url']))
            except OSError:
                pass  # Si el archivo no existe, continuar
        
        conn.execute('DELETE FROM catalogo WHERE id = ?', (id,))
        conn.commit()
        flash('Implemento eliminado correctamente', 'success')
    except sqlite3.Error as e:
        flash(f'Error al eliminar: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin.ver_catalogo'))

# Gestión de usuarios
@admin_bp.route('/admin/usuarios')
def gestion_usuarios():
    conn = get_db_connection()
    usuarios = conn.execute('SELECT * FROM usuarios ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/gestion_usuarios.html', usuarios=usuarios)

# Gestión de reservas
@admin_bp.route('/admin/reservas')
def gestion_reservas():
    conn = get_db_connection()
    reservas = conn.execute('''
        SELECT r.*, u.nombre as usuario_nombre, c.implemento 
        FROM reservas r 
        JOIN usuarios u ON r.fk_usuario = u.id 
        JOIN catalogo c ON r.fk_implemento = c.id 
        ORDER BY r.fecha_reserva DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/gestion_reservas.html', reservas=reservas)

# API endpoint para obtener todos los implementos (útil para AJAX)
@admin_bp.route('/api/admin/catalogo')
def api_catalogo():
    conn = get_db_connection()
    implementos = conn.execute('SELECT * FROM catalogo ORDER BY id DESC').fetchall()
    conn.close()
    
    # Convertir resultados a lista de diccionarios
    result = []
    for row in implementos:
        result.append(dict(row))
    
    return jsonify(result)

# API endpoint para obtener un implemento específico
@admin_bp.route('/api/admin/catalogo/<int:id>')
def api_implemento(id):
    conn = get_db_connection()
    implemento = conn.execute('SELECT * FROM catalogo WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if implemento is None:
        return jsonify({'error': 'Implemento no encontrado'}), 404
    
    return jsonify(dict(implemento))

# API endpoint para obtener estadísticas
@admin_bp.route('/api/admin/estadisticas')
def api_estadisticas():
    conn = get_db_connection()
    
    total_implementos = conn.execute('SELECT COUNT(*) as count FROM catalogo').fetchone()['count']
    total_usuarios = conn.execute('SELECT COUNT(*) as count FROM usuarios').fetchone()['count']
    total_reservas = conn.execute('SELECT COUNT(*) as count FROM reservas').fetchone()['count']
    reservas_activas = conn.execute('SELECT COUNT(*) as count FROM reservas WHERE estado = "activa"').fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'total_implementos': total_implementos,
        'total_usuarios': total_usuarios,
        'total_reservas': total_reservas,
        'reservas_activas': reservas_activas
    })