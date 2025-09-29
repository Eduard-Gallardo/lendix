
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, session  # Agregar session
import sqlite3
import os
from utils.db import get_db_connection
from werkzeug.utils import secure_filename
from routes.login import login_required  # Agregar este import
from datetime import datetime, timedelta
from utils.permisos import (
    es_instructor, es_aprendiz, verificar_permiso_prestamo, 
    crear_permiso_ambiente, asignar_aprendiz_a_instructor,
    obtener_aprendices_del_instructor, obtener_permisos_instructor,
    obtener_ambientes_disponibles
)

# Configuración del Blueprint
admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Configuración de subida de imagenes
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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
@login_required
def ver_catalogo():
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    conn = get_db_connection()
    implementos = conn.execute('SELECT * FROM catalogo ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/panel_administrador.html', implementos=implementos)

@admin_bp.route('/admin/catalogo/agregar', methods=['GET', 'POST'])
@login_required
def agregar_implemento():
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
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
@login_required
def editar_implemento(id):
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
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
@login_required
def eliminar_implemento(id):
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
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
@login_required
def gestion_usuarios():
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    conn = get_db_connection()
    usuarios = conn.execute('SELECT * FROM usuarios ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/gestion_usuarios.html', usuarios=usuarios)

# Gestión de reservas
@admin_bp.route('/admin/reservas')
@login_required
def gestion_reservas():
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
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

# 📌 Nueva ruta para gestión de devoluciones de préstamos
@admin_bp.route('/devolucion_prestamos')
@login_required
def devolucion_prestamos():
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))


    conn = get_db_connection()
    
    try:
        # Obtener préstamos activos (sin fecha_devolucion)
        prestamos_activos = conn.execute('''
            SELECT p.*, u.nombre as usuario_nombre, c.implemento,
                   julianday('now') - julianday(p.fecha_prestamo) as dias_transcurridos
            FROM prestamos p
            JOIN usuarios u ON p.fk_usuario = u.id
            JOIN catalogo c ON p.fk_modelo = c.id
            WHERE p.fecha_devolucion IS NULL
            ORDER BY p.fecha_prestamo DESC
        ''').fetchall()
        
        # Convertir días transcurridos a entero
        prestamos_con_dias = []
        for prestamo in prestamos_activos:
            prestamo_dict = dict(prestamo)
            prestamo_dict['dias_transcurridos'] = int(prestamo['dias_transcurridos']) if prestamo['dias_transcurridos'] else 0
            prestamos_con_dias.append(prestamo_dict)
        
        # Estadísticas
        total_prestamos = len(prestamos_con_dias)
        
        # Contar implementos únicos prestados
        implementos_unicos = len(set(p['fk_modelo'] for p in prestamos_con_dias))
        
        # Préstamos de hoy
        hoy = datetime.now().strftime("%Y-%m-%d")
        prestamos_hoy = conn.execute('''
            SELECT COUNT(*) as count FROM prestamos 
            WHERE fecha_prestamo LIKE ? AND fecha_devolucion IS NULL
        ''', (f'{hoy}%',)).fetchone()['count']
        
    except Exception as e:
        flash(f'Error al cargar préstamos: {str(e)}', 'error')
        prestamos_con_dias = []
        total_prestamos = 0
        implementos_unicos = 0
        prestamos_hoy = 0
    finally:
        conn.close()
    
    return render_template('admin/dvprestamos.html',
                         prestamos_activos=prestamos_con_dias,
                         total_prestamos=total_prestamos,
                         total_implementos=implementos_unicos,
                         prestamos_hoy=prestamos_hoy)

# 📌 Nueva ruta para procesar devolución desde el panel admin
@admin_bp.route('/devolver_prestamo_admin/<int:id>', methods=['POST'])
@login_required
def devolver_prestamo_admin(id):
    # VERIFICAR SI ES ADMIN
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        # Obtener información completa del préstamo
        prestamo = conn.execute('''
            SELECT p.*, c.implemento, c.disponibilidad, u.nombre as usuario_nombre
            FROM prestamos p
            JOIN catalogo c ON p.fk_modelo = c.id
            JOIN usuarios u ON p.fk_usuario = u.id
            WHERE p.id = ?
        ''', (id,)).fetchone()
        
        if not prestamo:
            flash('No se encontró el préstamo.', 'error')
            return redirect(url_for('admin.devolucion_prestamos'))
        
        if prestamo['fecha_devolucion'] is not None:
            flash('Este préstamo ya fue devuelto anteriormente.', 'warning')
            return redirect(url_for('admin.devolucion_prestamos'))
        
        # Registrar la devolución
        fecha_devolucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            'UPDATE prestamos SET fecha_devolucion = ? WHERE id = ?',
            (fecha_devolucion, id)
        )
        
        # Actualizar disponibilidad del implemento
        nueva_disponibilidad = prestamo['disponibilidad'] + 1
        conn.execute(
            'UPDATE catalogo SET disponibilidad = ? WHERE id = ?',
            (nueva_disponibilidad, prestamo['fk_modelo'])
        )
        
        conn.commit()
        
        flash(f'Devolución registrada exitosamente: {prestamo["implemento"]} devuelto por {prestamo["nombre"]}', 'success')
        
    except Exception as e:
        flash(f'Error al procesar la devolución: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin.devolucion_prestamos'))

# ===== GESTIÓN DE PERMISOS DE AMBIENTES =====

@admin_bp.route('/gestion_permisos')
@login_required
def gestion_permisos():
    """Vista principal para gestionar permisos de ambientes"""
    # VERIFICAR SI ES ADMIN O INSTRUCTOR
    if not is_admin() and not es_instructor(session.get('user_id')):
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    user_id = session.get('user_id')
    
    # Obtener permisos del instructor
    permisos = obtener_permisos_instructor(user_id)
    
    # Obtener aprendices asignados
    aprendices = obtener_aprendices_del_instructor(user_id)
    
    # Obtener ambientes disponibles
    ambientes_disponibles = obtener_ambientes_disponibles()
    
    return render_template('admin/gestion_permisos.html',
                         permisos=permisos,
                         aprendices=aprendices,
                         ambientes_disponibles=ambientes_disponibles)

@admin_bp.route('/configurar_permiso_ambiente', methods=['POST'])
@login_required
def configurar_permiso_ambiente():
    """Configura el permiso de un ambiente para un instructor"""
    if not is_admin() and not es_instructor(session.get('user_id')):
        flash('No tienes permisos para realizar esta acción', 'error')
        return redirect(url_for('admin.gestion_permisos'))
    
    instructor_id = session.get('user_id')
    ambiente = request.form.get('ambiente')
    habilitado = request.form.get('habilitado') == 'on'
    
    if not ambiente:
        flash('Debe seleccionar un ambiente', 'error')
        return redirect(url_for('admin.gestion_permisos'))
    
    if crear_permiso_ambiente(instructor_id, ambiente, habilitado):
        estado = "habilitado" if habilitado else "deshabilitado"
        flash(f'Permiso para el ambiente "{ambiente}" {estado} correctamente', 'success')
    else:
        flash('Error al configurar el permiso', 'error')
    
    return redirect(url_for('admin.gestion_permisos'))

@admin_bp.route('/asignar_aprendiz', methods=['POST'])
@login_required
def asignar_aprendiz():
    """Asigna un aprendiz a un instructor en un ambiente específico"""
    if not is_admin() and not es_instructor(session.get('user_id')):
        flash('No tienes permisos para realizar esta acción', 'error')
        return redirect(url_for('admin.gestion_permisos'))
    
    instructor_id = session.get('user_id')
    aprendiz_id = request.form.get('aprendiz_id')
    ambiente = request.form.get('ambiente')
    
    if not all([aprendiz_id, ambiente]):
        flash('Debe seleccionar un aprendiz y un ambiente', 'error')
        return redirect(url_for('admin.gestion_permisos'))
    
    # Verificar que el usuario seleccionado es realmente un aprendiz
    if not es_aprendiz(aprendiz_id):
        flash('El usuario seleccionado no es un aprendiz', 'error')
        return redirect(url_for('admin.gestion_permisos'))
    
    if asignar_aprendiz_a_instructor(instructor_id, aprendiz_id, ambiente):
        # Obtener nombre del aprendiz
        conn = get_db_connection()
        aprendiz = conn.execute('SELECT nombre FROM usuarios WHERE id = ?', (aprendiz_id,)).fetchone()
        conn.close()
        
        flash(f'Aprendiz "{aprendiz["nombre"]}" asignado al ambiente "{ambiente}" correctamente', 'success')
    else:
        flash('Error al asignar el aprendiz', 'error')
    
    return redirect(url_for('admin.gestion_permisos'))

@admin_bp.route('/obtener_aprendices_disponibles')
@login_required
def obtener_aprendices_disponibles():
    """API endpoint para obtener aprendices disponibles para asignar"""
    if not is_admin() and not es_instructor(session.get('user_id')):
        return jsonify({'error': 'Sin permisos'}), 403
    
    conn = get_db_connection()
    aprendices = conn.execute('''
        SELECT id, nombre, email 
        FROM usuarios 
        WHERE tipo_usuario = 'aprendiz' AND activo = 1
        ORDER BY nombre
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(aprendiz) for aprendiz in aprendices])

@admin_bp.route('/verificar_permiso_prestamo/<ambiente>')
@login_required
def verificar_permiso_prestamo_api(ambiente):
    """API endpoint para verificar si un usuario puede solicitar préstamos en un ambiente"""
    user_id = session.get('user_id')
    tiene_permiso, mensaje = verificar_permiso_prestamo(user_id, ambiente)
    
    return jsonify({
        'tiene_permiso': tiene_permiso,
        'mensaje': mensaje
    })