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
        implemento = request.form['implemento']
        descripcion = request.form['descripcion']
        disponibilidad = request.form['disponibilidad']
        categoria = request.form['categoria']
        imagen_url = request.form['imagen_url']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO catalogo (implemento, descripcion, disponibilidad, categoria, imagen_url) VALUES (?, ?, ?, ?, ?)',
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
    
    conn = get_db_connection()
    if filtro:
        catalogo_items = conn.execute('SELECT * FROM catalogo WHERE implemento LIKE ? OR descripcion LIKE ?',
                                    (f'%{filtro}%', f'%{filtro}%')).fetchall()
    else:
        catalogo_items = conn.execute('SELECT * FROM catalogo').fetchall()
    conn.close()
    
    return render_template('views/catalogo.html', catalogo=catalogo_items, filtro=filtro)


# Ruta para registrar préstamo
@catalogo_bp.route('/prestar/<int:id>', methods=['POST'])
def prestar(id):
    conn = get_db_connection()
    try:
        fk_usuario = session.get('user_id')
        fecha_prestamo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fecha_devolucion = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

        nombre = request.form.get("nombre")
        instructor = request.form.get("instructor")
        jornada = request.form.get("jornada")
        ambiente = request.form.get("ambiente")

        conn.execute('''
            INSERT INTO prestamos (fk_usuario, fk_modelo, fecha_prestamo, fecha_devolucion, nombre, instructor, jornada, ambiente)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fk_usuario, id, fecha_prestamo, fecha_devolucion, nombre, instructor, jornada, ambiente))

        conn.execute('UPDATE catalogo SET disponibilidad = 0 WHERE id = ?', (id,))
        conn.commit()
        flash("Préstamo registrado con éxito", "success")
    except Exception as e:
        flash(f"Error en el préstamo: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))


# Ruta para registrar reserva
@catalogo_bp.route('/reservar/<int:id>', methods=['POST'])
def reservar(id):
    conn = get_db_connection()
    try:
        fk_usuario = session.get('user_id')
        fecha_reserva = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        nombre = request.form.get("nombre")
        lugar = request.form.get("lugar")
        hora_inicio = request.form.get("hora_inicio")
        hora_fin = request.form.get("hora_fin")

        conn.execute('''
            INSERT INTO reservas (fk_usuario, fk_implemento, fecha_reserva, fecha_inicio, fecha_fin, nombre, lugar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (fk_usuario, id, fecha_reserva, hora_inicio, hora_fin, nombre, lugar))

        conn.commit()
        flash("Reserva registrada con éxito", "success")
    except Exception as e:
        flash(f"Error en la reserva: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

