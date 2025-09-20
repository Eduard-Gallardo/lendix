from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.login import login_required
from utils.db import get_db_connection
from flask import session
from datetime import datetime, timedelta

catalogo_bp = Blueprint('catalogo', __name__, template_folder='templates')

@catalogo_bp.route('/catalogo', methods=['GET', 'POST'])
@login_required
def catalogo():
    if request.method == 'POST':
        # 🔹 Solo admin puede agregar implementos
        if session.get('rol') != 'admin':
            flash('No tienes permiso para agregar implementos.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        implemento = request.form['implemento']
        descripcion = request.form['descripcion']
        disponibilidad = request.form['disponibilidad']
        categoria = request.form['categoria']
        imagen_url = request.form['imagen_url']
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO catalogo (implemento, descripcion, disponibilidad, categoria, imagen_url) VALUES (?, ?, ?, ?, ?)',
            (implemento, descripcion, disponibilidad, categoria, imagen_url))
        conn.commit()
        conn.close()
        
        flash('Implemento agregado al catálogo exitosamente.', 'success')
        return redirect(url_for('catalogo.catalogo'))
    
    conn = get_db_connection()
    catalogo_items = conn.execute('SELECT * FROM catalogo').fetchall()
    conn.close()
    
    return render_template('views/catalogo.html', catalogo=catalogo_items)


@catalogo_bp.route('/catalogo/filtrar', methods=['GET'])
@login_required
def filtrar_catalogo():
    filtro = request.args.get('filtro', '')
    categoria = request.args.get('categoria', '')

    conn = get_db_connection()

    query = "SELECT * FROM catalogo WHERE 1=1"
    params = []

    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)

    if filtro:
        query += " AND (implemento LIKE ? OR descripcion LIKE ?)"
        params.extend([f'%{filtro}%', f'%{filtro}%'])

    catalogo_items = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('views/catalogo.html',
                           catalogo=catalogo_items,
                           filtro=filtro,
                           categoria=categoria)


# Ruta para registrar préstamo
@catalogo_bp.route('/prestar/<int:id>', methods=['POST'])
@login_required
def prestar(id):
    conn = get_db_connection()
    try:
        # Verificar disponibilidad antes de prestar
        implemento = conn.execute('SELECT disponibilidad FROM catalogo WHERE id = ?', (id,)).fetchone()
        
        if not implemento:
            flash('El implemento no existe.', 'error')
            return redirect(url_for('catalogo.catalogo'))
            
        if implemento['disponibilidad'] <= 0:
            flash('Este implemento no está disponible para préstamo.', 'error')
            return redirect(url_for('catalogo.catalogo'))
        
        fk_usuario = session.get('user_id')
        fecha_prestamo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        nombre = request.form.get("nombre")
        instructor = request.form.get("instructor")
        jornada = request.form.get("jornada")
        ambiente = request.form.get("ambiente")

        # Validar campos obligatorios
        if not all([nombre, instructor, jornada, ambiente]):
            flash('Todos los campos del préstamo son obligatorios.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        conn.execute('''
            INSERT INTO prestamos (fk_usuario, fk_modelo, fecha_prestamo, nombre, instructor, jornada, ambiente)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (fk_usuario, id, fecha_prestamo, nombre, instructor, jornada, ambiente))

        # Restar 1 a la disponibilidad en lugar de establecer a 0
        nueva_disponibilidad = implemento['disponibilidad'] - 1
        conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', (nueva_disponibilidad, id))
        
        conn.commit()
        flash("Préstamo registrado con éxito", "success")
    except Exception as e:
        flash(f"Error en el préstamo: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))


# Ruta para registrar reserva
@catalogo_bp.route('/reservar/<int:id>', methods=['POST'])
@login_required
def reservar(id):
    conn = get_db_connection()
    try:
        # Verificar disponibilidad antes de reservar
        implemento = conn.execute('SELECT disponibilidad FROM catalogo WHERE id = ?', (id,)).fetchone()
        
        if not implemento:
            flash('El implemento no existe.', 'error')
            return redirect(url_for('catalogo.catalogo'))
            
        if implemento['disponibilidad'] <= 0:
            flash('Este implemento no está disponible para reserva.', 'error')
            return redirect(url_for('catalogo.catalogo'))
        
        fk_usuario = session.get('user_id')
        fecha_reserva = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        nombre = request.form.get("nombre")
        lugar = request.form.get("lugar")
        hora_inicio = request.form.get("hora_inicio")
        hora_fin = request.form.get("hora_fin")

        # Validar campos obligatorios
        if not all([nombre, lugar, hora_inicio, hora_fin]):
            flash('Todos los campos de la reserva son obligatorios.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Validar que la fecha de inicio sea anterior a la fecha de fin
        if hora_inicio >= hora_fin:
            flash('La fecha de inicio debe ser anterior a la fecha de fin.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        conn.execute('''
            INSERT INTO reservas (fk_usuario, fk_implemento, fecha_reserva, fecha_inicio, fecha_fin, nombre, lugar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (fk_usuario, id, fecha_reserva, hora_inicio, hora_fin, nombre, lugar))

        # Restar 1 a la disponibilidad para reservas
        nueva_disponibilidad = implemento['disponibilidad'] - 1
        conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', (nueva_disponibilidad, id))
        
        conn.commit()
        flash("Reserva registrada con éxito", "success")
    except Exception as e:
        flash(f"Error en la reserva: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))


# Nueva función para devolver implementos
@catalogo_bp.route('/devolver/<int:id>', methods=['POST'])
@login_required
def devolver(id):
    # Solo admin puede procesar devoluciones
    if session.get('rol') != 'admin':
        flash('No tienes permiso para procesar devoluciones.', 'error')
        return redirect(url_for('catalogo.catalogo'))
    
    conn = get_db_connection()
    try:
        # Obtener información del préstamo activo
        prestamo = conn.execute(
            'SELECT * FROM prestamos WHERE fk_modelo = ? AND fecha_devolucion IS NULL ORDER BY fecha_prestamo DESC LIMIT 1', 
            (id,)
        ).fetchone()
        
        if prestamo:
            fecha_devolucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Registrar la devolución
            conn.execute(
                'UPDATE prestamos SET fecha_devolucion = ? WHERE id = ?',
                (fecha_devolucion, prestamo['id'])
            )
            
            # Obtener la disponibilidad actual y sumar 1
            implemento = conn.execute('SELECT disponibilidad FROM catalogo WHERE id = ?', (id,)).fetchone()
            if implemento:
                nueva_disponibilidad = implemento['disponibilidad'] + 1
                conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', (nueva_disponibilidad, id))
            
            conn.commit()
            flash('Devolución registrada exitosamente.', 'success')
        else:
            flash('No se encontró un préstamo activo para este implemento.', 'error')
            
    except Exception as e:
        flash(f'Error al procesar la devolución: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('catalogo.catalogo'))


# Nueva función para cancelar reservas
@catalogo_bp.route('/cancelar_reserva/<int:id>', methods=['POST'])
@login_required
def cancelar_reserva(id):
    conn = get_db_connection()
    try:
        # Obtener información de la reserva
        reserva = conn.execute('SELECT * FROM reservas WHERE id = ?', (id,)).fetchone()
        
        if reserva:
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
    
    return redirect(url_for('catalogo.catalogo'))