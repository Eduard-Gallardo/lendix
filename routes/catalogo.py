from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.login import login_required
from utils.db import get_db_connection
from utils.permisos import verificar_permiso_prestamo, es_instructor, es_aprendiz
from datetime import datetime

catalogo_bp = Blueprint('catalogo', __name__, template_folder='templates')

# Vista principal del catálogo
@catalogo_bp.route('/catalogo', methods=['GET', 'POST'])
@login_required
def catalogo():
    if request.method == 'POST':
        # Solo admin puede agregar implementos
        if session.get('rol') != 'admin':
            flash('No tienes permiso para agregar implementos.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        implemento = request.form.get('implemento')
        descripcion = request.form.get('descripcion')
        disponibilidad = request.form.get('disponibilidad')
        categoria = request.form.get('categoria')
        imagen_url = request.form.get('imagen_url')

        # Validar campos obligatorios
        if not all([implemento, descripcion, disponibilidad, categoria]):
            flash('Todos los campos obligatorios deben ser completados.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        try:
            disponibilidad = int(disponibilidad)
            if disponibilidad < 0:
                flash('La disponibilidad no puede ser negativa.', 'error')
                return redirect(url_for('catalogo.catalogo'))
        except ValueError:
            flash('La disponibilidad debe ser un número entero.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        conn = get_db_connection()
        try:
            conn.execute(
                '''INSERT INTO catalogo (implemento, descripcion, disponibilidad, categoria, imagen_url)
                   VALUES (?, ?, ?, ?, ?)''',
                (implemento, descripcion, disponibilidad, categoria, imagen_url)
            )
            conn.commit()
            flash('Implemento agregado al catálogo exitosamente.', 'success')
        except Exception as e:
            flash(f'Error al agregar implemento: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('catalogo.catalogo'))

    conn = get_db_connection()
    catalogo_items = conn.execute('SELECT * FROM catalogo ORDER BY implemento').fetchall()
    conn.close()
    return render_template('views/catalogo.html', catalogo=catalogo_items)

# Filtrar catálogo
@catalogo_bp.route('/catalogo/filtrar', methods=['GET'])
@login_required
def filtrar_catalogo():
    filtro = request.args.get('filtro', '')
    categoria = request.args.get('categoria', '')
    disponibilidad = request.args.get('disponibilidad', '')

    conn = get_db_connection()
    query = "SELECT * FROM catalogo WHERE 1=1"
    params = []

    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)

    if disponibilidad == 'disponible':
        query += " AND disponibilidad > 0"
    elif disponibilidad == 'agotado':
        query += " AND disponibilidad = 0"

    if filtro:
        query += " AND (implemento LIKE ? OR descripcion LIKE ?)"
        params.extend([f'%{filtro}%', f'%{filtro}%'])

    query += " ORDER BY implemento"
    catalogo_items = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('views/catalogo.html',
                           catalogo=catalogo_items,
                           filtro=filtro,
                           categoria=categoria,
                           disponibilidad=disponibilidad)

# Registrar préstamo - CORREGIDO Y FUNCIONAL
@catalogo_bp.route('/prestar/<int:id>', methods=['POST'])
@login_required
def prestar(id):
    conn = get_db_connection()
    try:
        # Verificar que el implemento existe y tiene disponibilidad
        implemento = conn.execute(
            'SELECT id, implemento, disponibilidad FROM catalogo WHERE id = ?', (id,)
        ).fetchone()

        if not implemento:
            flash('El implemento no existe.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        if implemento['disponibilidad'] <= 0:
            flash('Este implemento no está disponible para préstamo.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        fk_usuario = session.get('user_id')
        fecha_prestamo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Obtener datos del formulario - CORREGIDO: usar 'nombre' directamente
        nombre_prestatario = request.form.get("nombre")
        instructor = request.form.get("instructor")
        jornada = request.form.get("jornada")
        ambiente = request.form.get("ambiente")

        # Validar campos obligatorios
        if not all([nombre_prestatario, instructor, jornada, ambiente]):
            flash('Todos los campos del préstamo son obligatorios.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # VERIFICAR PERMISOS DE PRÉSTAMO
        user_id = session.get('user_id')
        tiene_permiso, mensaje_permiso = verificar_permiso_prestamo(user_id, ambiente)
        
        if not tiene_permiso:
            flash(f'No puedes solicitar préstamos en este ambiente: {mensaje_permiso}', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Registrar el préstamo en la base de datos - CORREGIDO: campo 'nombre'
        conn.execute('''
            INSERT INTO prestamos (fk_usuario, fk_modelo, fecha_prestamo, fecha_devolucion, 
                                nombre, instructor, jornada, ambiente)
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?)
        ''', (fk_usuario, id, fecha_prestamo, nombre_prestatario, instructor, jornada, ambiente))

        # Actualizar la disponibilidad del implemento
        nueva_disponibilidad = implemento['disponibilidad'] - 1
        conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', 
                    (nueva_disponibilidad, id))

        conn.commit()
        flash(f"Préstamo de '{implemento['implemento']}' registrado con éxito", "success")
        
    except Exception as e:
        flash(f"Error en el préstamo: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

#  Registrar reserva - FUNCIONAL
@catalogo_bp.route('/reservar/<int:id>', methods=['POST'])
@login_required
def reservar(id):
    conn = get_db_connection()
    try:
        # Verificar que el implemento existe y tiene disponibilidad
        implemento = conn.execute(
            'SELECT id, implemento, disponibilidad FROM catalogo WHERE id = ?', (id,)
        ).fetchone()

        if not implemento:
            flash('El implemento no existe.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        if implemento['disponibilidad'] <= 0:
            flash('Este implemento no está disponible para reserva.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        fk_usuario = session.get('user_id')
        fecha_reserva = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Obtener datos del formulario
        nombre = request.form.get("nombre")
        lugar = request.form.get("lugar")
        fecha_inicio = request.form.get("hora_inicio")
        fecha_fin = request.form.get("hora_fin")

        # Validar campos obligatorios
        if not all([nombre, lugar, fecha_inicio, fecha_fin]):
            flash('Todos los campos de la reserva son obligatorios.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # VERIFICAR PERMISOS DE RESERVA (usar el lugar como ambiente)
        user_id = session.get('user_id')
        tiene_permiso, mensaje_permiso = verificar_permiso_prestamo(user_id, lugar)
        
        if not tiene_permiso:
            flash(f'No puedes solicitar reservas en este ambiente: {mensaje_permiso}', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Validar que la fecha de inicio sea anterior a la fecha de fin
        if fecha_inicio >= fecha_fin:
            flash('La fecha de inicio debe ser anterior a la fecha de fin.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Registrar la reserva en la base de datos
        conn.execute('''
            INSERT INTO reservas (fk_usuario, fk_implemento, fecha_reserva, fecha_inicio, 
                                fecha_fin, nombre, lugar, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pendiente')
        ''', (fk_usuario, id, fecha_reserva, fecha_inicio, fecha_fin, nombre, lugar))

        # Actualizar la disponibilidad del implemento
        nueva_disponibilidad = implemento['disponibilidad'] - 1
        conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', 
                    (nueva_disponibilidad, id))

        conn.commit()
        flash(f"Reserva de '{implemento['implemento']}' registrada con éxito", "success")
        
    except Exception as e:
        flash(f"Error en la reserva: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# Devolver implemento (solo admin) - FUNCIONAL
@catalogo_bp.route('/devolver/<int:id>', methods=['POST'])
@login_required
def devolver(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para procesar devoluciones.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    conn = get_db_connection()
    try:
        # Buscar el préstamo activo más reciente para este implemento
        prestamo = conn.execute(
            '''SELECT * FROM prestamos 
               WHERE fk_modelo = ? AND fecha_devolucion IS NULL 
               ORDER BY fecha_prestamo DESC LIMIT 1''',
            (id,)
        ).fetchone()

        if not prestamo:
            flash('No se encontró un préstamo activo para este implemento.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Registrar la devolución
        fecha_devolucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            'UPDATE prestamos SET fecha_devolucion = ? WHERE id = ?',
            (fecha_devolucion, prestamo['id'])
        )

        # Actualizar la disponibilidad del implemento
        implemento = conn.execute(
            'SELECT disponibilidad FROM catalogo WHERE id = ?', (id,)
        ).fetchone()
        
        if implemento:
            nueva_disponibilidad = implemento['disponibilidad'] + 1
            conn.execute(
                'UPDATE catalogo SET disponibilidad = ? WHERE id = ?',
                (nueva_disponibilidad, id)
            )

        conn.commit()
        flash('Devolución registrada exitosamente.', 'success')

    except Exception as e:
        flash(f'Error al procesar la devolución: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# Cancelar reserva desde el catálogo - FUNCIONAL
@catalogo_bp.route('/cancelar_reserva_catalogo/<int:id>', methods=['POST'])
@login_required
def cancelar_reserva_catalogo(id):
    conn = get_db_connection()
    try:
        # Obtener información de la reserva
        reserva = conn.execute(
            'SELECT * FROM reservas WHERE id = ?', (id,)
        ).fetchone()
        
        if not reserva:
            flash('No se encontró la reserva.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Verificar permisos (usuario dueño o admin)
        if session.get('user_id') != reserva['fk_usuario'] and session.get('rol') != 'admin':
            flash('No tienes permiso para cancelar esta reserva.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Verificar que la reserva no esté ya cancelada
        if reserva['estado'] == 'cancelada':
            flash('Esta reserva ya fue cancelada.', 'warning')
            return redirect(url_for('catalogo.catalogo'))

        # Marcar la reserva como cancelada
        conn.execute(
            'UPDATE reservas SET estado = "cancelada" WHERE id = ?', 
            (id,)
        )

        # Restaurar la disponibilidad del implemento (solo si estaba aprobada)
        if reserva['estado'] == 'aprobada':
            implemento = conn.execute(
                'SELECT disponibilidad FROM catalogo WHERE id = ?', 
                (reserva['fk_implemento'],)
            ).fetchone()
            
            if implemento:
                nueva_disponibilidad = implemento['disponibilidad'] + 1
                conn.execute(
                    'UPDATE catalogo SET disponibilidad = ? WHERE id = ?', 
                    (nueva_disponibilidad, reserva['fk_implemento'])
                )

        conn.commit()
        flash('Reserva cancelada exitosamente.', 'success')
            
    except Exception as e:
        flash(f'Error al cancelar la reserva: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('catalogo.catalogo'))

# 📌 Editar implemento (solo admin) - NUEVA FUNCIÓN
@catalogo_bp.route('/editar_implemento/<int:id>', methods=['POST'])
@login_required
def editar_implemento(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para editar implementos.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    implemento = request.form.get('implemento')
    descripcion = request.form.get('descripcion')
    disponibilidad = request.form.get('disponibilidad')
    categoria = request.form.get('categoria')
    imagen_url = request.form.get('imagen_url')

    # Validar campos obligatorios
    if not all([implemento, descripcion, disponibilidad, categoria]):
        flash('Todos los campos obligatorios deben ser completados.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    try:
        disponibilidad = int(disponibilidad)
        if disponibilidad < 0:
            flash('La disponibilidad no puede ser negativa.', 'error')
            return redirect(url_for('catalogo.catalogo'))
    except ValueError:
        flash('La disponibilidad debe ser un número entero.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    conn = get_db_connection()
    try:
        conn.execute(
            '''UPDATE catalogo 
               SET implemento = ?, descripcion = ?, disponibilidad = ?, 
                   categoria = ?, imagen_url = ?
               WHERE id = ?''',
            (implemento, descripcion, disponibilidad, categoria, imagen_url, id)
        )
        conn.commit()
        flash('Implemento actualizado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar implemento: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# 📌 Eliminar implemento (solo admin) - NUEVA FUNCIÓN
@catalogo_bp.route('/eliminar_implemento/<int:id>', methods=['POST'])
@login_required
def eliminar_implemento(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para eliminar implementos.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    conn = get_db_connection()
    try:
        # Verificar si hay préstamos activos
        prestamos_activos = conn.execute(
            'SELECT COUNT(*) as count FROM prestamos WHERE fk_modelo = ? AND fecha_devolucion IS NULL',
            (id,)
        ).fetchone()

        # Verificar si hay reservas activas
        reservas_activas = conn.execute(
            "SELECT COUNT(*) as count FROM reservas WHERE fk_implemento = ? AND estado = 'aprobada'",
            (id,)
        ).fetchone()

        if prestamos_activos['count'] > 0 or reservas_activas['count'] > 0:
            flash('No se puede eliminar el implemento porque tiene préstamos o reservas activas.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        conn.execute('DELETE FROM catalogo WHERE id = ?', (id,))
        conn.commit()
        flash('Implemento eliminado exitosamente.', 'success')
        
    except Exception as e:
        flash(f'Error al eliminar implemento: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))