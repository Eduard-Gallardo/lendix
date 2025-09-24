from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.login import login_required
from utils.db import get_db_connection
from datetime import datetime, timedelta

prestamos_bp = Blueprint('prestamos', __name__, template_folder='templates')
reservas_bp = Blueprint('reservas', __name__, template_folder='templates')

# Vista combinada de préstamos y reservas con filtros
@prestamos_bp.route('/prestamos', methods=['GET'])
@login_required
def prestamos():
    conn = get_db_connection()
    
    # Obtener parámetros de filtro
    filtro_estado = request.args.get('estado', 'todos')
    filtro_dias = request.args.get('dias', '30')
    
    try:
        filtro_dias = int(filtro_dias)
    except ValueError:
        filtro_dias = 30
    
    # Construir consulta de préstamos con filtros - CORREGIDO
    prestamos_query = '''
        SELECT p.id, u.nombre AS usuario, c.implemento, p.fecha_prestamo, p.fecha_devolucion, 
               p.instructor, p.jornada, p.ambiente, c.id as id_implemento, p.nombre as nombre_prestatario
        FROM prestamos p
        JOIN usuarios u ON p.fk_usuario = u.id
        JOIN catalogo c ON p.fk_modelo = c.id
        WHERE p.fecha_prestamo >= date('now', ?)
    '''
    prestamos_params = [f'-{filtro_dias} days']
    
    # Si no es administrador, solo mostrar préstamos del usuario actual
    if session.get('rol') != 'admin':
        prestamos_query += ' AND p.fk_usuario = ?'
        prestamos_params.append(session.get('user_id'))
    
    if filtro_estado == 'activos':
        prestamos_query += ' AND p.fecha_devolucion IS NULL'
    elif filtro_estado == 'devueltos':
        prestamos_query += ' AND p.fecha_devolucion IS NOT NULL'
    
    prestamos_query += ' ORDER BY p.fecha_prestamo DESC'
    
    prestamos_items = conn.execute(prestamos_query, prestamos_params).fetchall()

    # Construir consulta de reservas con filtros
    reservas_query = '''
        SELECT r.id, u.nombre AS usuario, c.implemento, r.fecha_reserva, r.fecha_inicio, 
               r.fecha_fin, r.lugar, r.estado, c.id as id_implemento, r.nombre as nombre_solicitante, r.fk_usuario
        FROM reservas r
        JOIN usuarios u ON r.fk_usuario = u.id
        JOIN catalogo c ON r.fk_implemento = c.id
        WHERE r.fecha_reserva >= date('now', ?)
    '''
    reservas_params = [f'-{filtro_dias} days']
    
    # Si no es administrador, solo mostrar reservas del usuario actual
    if session.get('rol') != 'admin':
        reservas_query += ' AND r.fk_usuario = ?'
        reservas_params.append(session.get('user_id'))
    
    if filtro_estado == 'pendientes':
        reservas_query += " AND r.estado = 'pendiente'"
    elif filtro_estado == 'aprobadas':
        reservas_query += " AND r.estado = 'aprobada'"
    elif filtro_estado == 'canceladas':
        reservas_query += " AND r.estado = 'cancelada'"
    
    reservas_query += ' ORDER BY r.fecha_reserva DESC'
    
    reservas_items = conn.execute(reservas_query, reservas_params).fetchall()
    
    # Estadísticas
    stats = {
        'total_prestamos': len(prestamos_items),
        'prestamos_activos': len([p for p in prestamos_items if p['fecha_devolucion'] is None]),
        'total_reservas': len(reservas_items),
        'reservas_pendientes': len([r for r in reservas_items if r['estado'] == 'pendiente']),
    }
    
    conn.close()

    return render_template('views/prestamos_reservas.html',
                        prestamos=prestamos_items,
                        reservas=reservas_items,
                        stats=stats,
                        filtro_estado=filtro_estado,
                        filtro_dias=filtro_dias)

# Procesar devolución de préstamo (CORREGIDO)
@prestamos_bp.route('/devolver_prestamo/<int:id>', methods=['POST'])
@login_required
def devolver_prestamo(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para procesar devoluciones.', 'error')
        return redirect(url_for('prestamos.prestamos'))

    conn = get_db_connection()
    try:
        # CONSULTA CORREGIDA - Incluye todos los campos necesarios
        prestamo = conn.execute('''
            SELECT p.*, c.implemento, u.nombre as usuario_nombre 
            FROM prestamos p 
            JOIN catalogo c ON p.fk_modelo = c.id 
            JOIN usuarios u ON p.fk_usuario = u.id
            WHERE p.id = ?
        ''', (id,)).fetchone()

        if not prestamo:
            flash('No se encontró el préstamo.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        if prestamo['fecha_devolucion'] is not None:
            flash('Este préstamo ya fue devuelto.', 'warning')
            return redirect(url_for('prestamos.prestamos'))

        fecha_devolucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            'UPDATE prestamos SET fecha_devolucion = ? WHERE id = ?',
            (fecha_devolucion, id)
        )

        # Actualizar disponibilidad del implemento
        implemento = conn.execute(
            'SELECT disponibilidad FROM catalogo WHERE id = ?',
            (prestamo['fk_modelo'],)
        ).fetchone()

        if implemento:
            nueva_disponibilidad = implemento['disponibilidad'] + 1
            conn.execute(
                'UPDATE catalogo SET disponibilidad = ? WHERE id = ?',
                (nueva_disponibilidad, prestamo['fk_modelo'])
            )

        conn.commit()
        flash(f'Devolución de "{prestamo["implemento"]}" registrada exitosamente.', 'success')

    except Exception as e:
        flash(f'Error al procesar la devolución: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('prestamos.prestamos'))


# Cancelar reserva (mejorado)
@reservas_bp.route('/cancelar_reserva/<int:id>', methods=['POST'])
@login_required
def cancelar_reserva(id):
    conn = get_db_connection()
    try:
        reserva = conn.execute('''
            SELECT r.*, c.implemento 
            FROM reservas r 
            JOIN catalogo c ON r.fk_implemento = c.id 
            WHERE r.id = ?
        ''', (id,)).fetchone()

        if not reserva:
            flash('No se encontró la reserva.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        # Verificar permisos: usuario dueño o admin
        if session.get('user_id') != reserva['fk_usuario'] and session.get('rol') != 'admin':
            flash('No tienes permiso para cancelar esta reserva.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        if reserva['estado'] == 'cancelada':
            flash('Esta reserva ya fue cancelada.', 'warning')
            return redirect(url_for('prestamos.prestamos'))

        # Verificar si la reserva ya empezó
        fecha_inicio = datetime.strptime(reserva['fecha_inicio'], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > fecha_inicio and session.get('rol') != 'admin':
            flash('No puedes cancelar una reserva que ya ha comenzado.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        conn.execute('UPDATE reservas SET estado = "cancelada" WHERE id = ?', (id,))

        # Solo restaurar disponibilidad si la reserva estaba aprobada
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
        flash(f'Reserva de "{reserva["implemento"]}" cancelada exitosamente.', 'success')

    except Exception as e:
        flash(f'Error al cancelar la reserva: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('prestamos.prestamos'))

# Aprobar reserva (solo admin) - Mejorado
@reservas_bp.route('/aprobar_reserva/<int:id>', methods=['POST'])
@login_required
def aprobar_reserva(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para aprobar reservas.', 'error')
        return redirect(url_for('reservas.reservas'))

    conn = get_db_connection()
    try:
        reserva = conn.execute('''
            SELECT r.*, c.implemento, c.disponibilidad 
            FROM reservas r 
            JOIN catalogo c ON r.fk_implemento = c.id 
            WHERE r.id = ?
        ''', (id,)).fetchone()

        if not reserva:
            flash('No se encontró la reserva.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        if reserva['estado'] != 'pendiente':
            flash('Solo se pueden aprobar reservas pendientes.', 'warning')
            return redirect(url_for('prestamos.prestamos'))

        # Verificar disponibilidad
        if reserva['disponibilidad'] <= 0:
            flash('No hay disponibilidad para aprobar esta reserva.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        # Verificar conflictos de fechas con otras reservas aprobadas
        reservas_conflicto = conn.execute('''
            SELECT id FROM reservas 
            WHERE fk_implemento = ? 
            AND estado = 'aprobada'
            AND (
                (fecha_inicio BETWEEN ? AND ?) OR
                (fecha_fin BETWEEN ? AND ?) OR
                (? BETWEEN fecha_inicio AND fecha_fin) OR
                (? BETWEEN fecha_inicio AND fecha_fin)
            )
            AND id != ?
        ''', (reserva['fk_implemento'], 
            reserva['fecha_inicio'], reserva['fecha_fin'],
            reserva['fecha_inicio'], reserva['fecha_fin'],
            reserva['fecha_inicio'], reserva['fecha_fin'],
            id)).fetchall()

        if reservas_conflicto:
            flash('Existe un conflicto de horario con otra reserva aprobada.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        # Aprobar reserva y actualizar disponibilidad
        conn.execute('UPDATE reservas SET estado = "aprobada" WHERE id = ?', (id,))
        
        nueva_disponibilidad = reserva['disponibilidad'] - 1
        conn.execute(
            'UPDATE catalogo SET disponibilidad = ? WHERE id = ?',
            (nueva_disponibilidad, reserva['fk_implemento'])
        )

        conn.commit()
        flash(f'Reserva de "{reserva["implemento"]}" aprobada exitosamente.', 'success')

    except Exception as e:
        flash(f'Error al aprobar la reserva: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('prestamos.prestamos'))

# Rechazar reserva (solo admin) - Nueva función
@reservas_bp.route('/rechazar_reserva/<int:id>', methods=['POST'])
@login_required
def rechazar_reserva(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para rechazar reservas.', 'error')
        return redirect(url_for('reservas.reservas'))

    conn = get_db_connection()
    try:
        reserva = conn.execute('''
            SELECT r.*, c.implemento 
            FROM reservas r 
            JOIN catalogo c ON r.fk_implemento = c.id 
            WHERE r.id = ?
        ''', (id,)).fetchone()

        if not reserva:
            flash('No se encontró la reserva.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        if reserva['estado'] != 'pendiente':
            flash('Solo se pueden rechazar reservas pendientes.', 'warning')
            return redirect(url_for('prestamos.prestamos'))

        conn.execute('UPDATE reservas SET estado = "rechazada" WHERE id = ?', (id,))
        conn.commit()
        
        flash(f'Reserva de "{reserva["implemento"]}" rechazada.', 'info')

    except Exception as e:
        flash(f'Error al rechazar la reserva: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('prestamos.prestamos'))

# Exportar datos (nueva función)
@prestamos_bp.route('/exportar_prestamos', methods=['GET'])
@login_required
def exportar_prestamos():
    if session.get('rol') != 'admin':
        flash('No tienes permiso para exportar datos.', 'error')
        return redirect(url_for('prestamos.prestamos'))
    
    formato = request.args.get('formato', 'csv')
    conn = get_db_connection()
    
    prestamos = conn.execute('''
        SELECT p.*, u.nombre as usuario, c.implemento
        FROM prestamos p
        JOIN usuarios u ON p.fk_usuario = u.id
        JOIN catalogo c ON p.fk_modelo = c.id
        ORDER BY p.fecha_prestamo DESC
    ''').fetchall()
    
    conn.close()
    
    # Aquí puedes implementar la lógica de exportación a CSV o Excel
    # Por ahora solo redirigimos
    flash('Función de exportación en desarrollo.', 'info')
    return redirect(url_for('prestamos.prestamos'))