from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.login import login_required
from utils.db import get_db_connection
from flask import session

prestamos_bp = Blueprint('prestamos', __name__, template_folder='templates')
reservas_bp = Blueprint('reservas', __name__, template_folder='templates') 

@prestamos_bp.route('/prestamos', methods=['GET', 'POST'])
@login_required
def prestamos():
    conn = get_db_connection()
    prestamos_items = conn.execute('''
        SELECT p.id, u.nombre AS usuario, c.implemento, p.fecha_prestamo, p.fecha_devolucion, 
               p.instructor, p.jornada, p.ambiente, c.id as id_implemento
        FROM prestamos p
        JOIN usuarios u ON p.fk_usuario = u.id
        JOIN catalogo c ON p.fk_modelo = c.id
        ORDER BY p.fecha_prestamo DESC
    ''').fetchall()
    
    reservas_items = conn.execute('''
        SELECT r.id, u.nombre AS usuario, c.implemento, r.fecha_reserva, r.fecha_inicio, 
               r.fecha_fin, r.lugar, r.estado, c.id as id_implemento
        FROM reservas r
        JOIN usuarios u ON r.fk_usuario = u.id
        JOIN catalogo c ON r.fk_implemento = c.id
        ORDER BY r.fecha_reserva DESC
    ''').fetchall()
    conn.close()

    return render_template('views/prestamos_reservas.html', prestamos=prestamos_items, reservas=reservas_items)


@reservas_bp.route('/reservas', methods=['GET', 'POST'])
@login_required
def reservas():
    conn = get_db_connection()
    reservas_items = conn.execute('''
        SELECT r.id, u.nombre AS usuario, c.implemento, r.fecha_reserva, r.fecha_inicio, 
               r.fecha_fin, r.lugar, r.estado, c.id as id_implemento
        FROM reservas r
        JOIN usuarios u ON r.fk_usuario = u.id
        JOIN catalogo c ON r.fk_implemento = c.id
        ORDER BY r.fecha_reserva DESC
    ''').fetchall()
    conn.close()
    
    return render_template('views/reservas.html', reservas=reservas_items)


# Ruta para procesar devoluciones de préstamos
@prestamos_bp.route('/devolver_prestamo/<int:id>', methods=['POST'])
@login_required
def devolver_prestamo(id):
    # Solo admin puede procesar devoluciones
    if session.get('rol') != 'admin':
        flash('No tienes permiso para procesar devoluciones.', 'error')
        return redirect(url_for('prestamos.prestamos'))
    
    conn = get_db_connection()
    try:
        # Obtener información del préstamo
        prestamo = conn.execute('SELECT * FROM prestamos WHERE id = ?', (id,)).fetchone()
        
        if prestamo:
            fecha_devolucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Registrar la devolución
            conn.execute(
                'UPDATE prestamos SET fecha_devolucion = ? WHERE id = ?',
                (fecha_devolucion, id)
            )
            
            # Obtener la disponibilidad actual y sumar 1
            implemento = conn.execute('SELECT disponibilidad FROM catalogo WHERE id = ?', (prestamo['fk_modelo'],)).fetchone()
            if implemento:
                nueva_disponibilidad = implemento['disponibilidad'] + 1
                conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', 
                           (nueva_disponibilidad, prestamo['fk_modelo']))
            
            conn.commit()
            flash('Devolución registrada exitosamente.', 'success')
        else:
            flash('No se encontró el préstamo.', 'error')
            
    except Exception as e:
        flash(f'Error al procesar la devolución: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('prestamos.prestamos'))


# Ruta para cancelar reservas
@reservas_bp.route('/cancelar_reserva/<int:id>', methods=['POST'])
@login_required
def cancelar_reserva(id):
    conn = get_db_connection()
    try:
        # Obtener información de la reserva
        reserva = conn.execute('SELECT * FROM reservas WHERE id = ?', (id,)).fetchone()
        
        if reserva:
            # Solo el usuario que creó la reserva o un admin puede cancelarla
            if session.get('user_id') != reserva['fk_usuario'] and session.get('rol') != 'admin':
                flash('No tienes permiso para cancelar esta reserva.', 'error')
                return redirect(url_for('reservas.reservas'))
            
            # Marcar la reserva como cancelada
            conn.execute('UPDATE reservas SET estado = "cancelada" WHERE id = ?', (id,))
            
            # Sumar 1 a la disponibilidad del implemento
            implemento = conn.execute('SELECT disponibilidad FROM catalogo WHERE id = ?', (reserva['fk_implemento'],)).fetchone()
            if implemento:
                nueva_disponibilidad = implemento['disponibilidad'] + 1
                conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', 
                           (nueva_disponibilidad, reserva['fk_implemento']))
            
            conn.commit()
            flash('Reserva cancelada exitosamente.', 'success')
        else:
            flash('No se encontró la reserva.', 'error')
            
    except Exception as e:
        flash(f'Error al cancelar la reserva: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('reservas.reservas'))


# Ruta para aprobar reservas (solo admin)
@reservas_bp.route('/aprobar_reserva/<int:id>', methods=['POST'])
@login_required
def aprobar_reserva(id):
    # Solo admin puede aprobar reservas
    if session.get('rol') != 'admin':
        flash('No tienes permiso para aprobar reservas.', 'error')
        return redirect(url_for('reservas.reservas'))
    
    conn = get_db_connection()
    try:
        # Obtener información de la reserva
        reserva = conn.execute('SELECT * FROM reservas WHERE id = ?', (id,)).fetchone()
        
        if reserva:
            # Verificar disponibilidad antes de aprobar
            implemento = conn.execute('SELECT disponibilidad FROM catalogo WHERE id = ?', (reserva['fk_implemento'],)).fetchone()
            
            if implemento and implemento['disponibilidad'] > 0:
                # Aprobar la reserva
                conn.execute('UPDATE reservas SET estado = "aprobada" WHERE id = ?', (id,))
                
                # Restar 1 a la disponibilidad del implemento
                nueva_disponibilidad = implemento['disponibilidad'] - 1
                conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', 
                           (nueva_disponibilidad, reserva['fk_implemento']))
                
                conn.commit()
                flash('Reserva aprobada exitosamente.', 'success')
            else:
                flash('No hay disponibilidad para aprobar esta reserva.', 'error')
        else:
            flash('No se encontró la reserva.', 'error')
            
    except Exception as e:
        flash(f'Error al aprobar la reserva: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('reservas.reservas'))