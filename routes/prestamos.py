from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.login import login_required
from utils.db import get_db_connection

prestamos_bp = Blueprint('prestamos', __name__, template_folder='templates')
reservas_bp = Blueprint('reservas', __name__, template_folder='templates') 

@prestamos_bp.route('/prestamos', methods=['GET', 'POST'])
@login_required
def prestamos():
    conn = get_db_connection()
    prestamos_items = conn.execute('''
        SELECT p.id, u.nombre AS usuario, c.implemento, p.fecha_prestamo, p.fecha_devolucion, p.instructor, p.jornada, p.ambiente
        FROM prestamos p
        JOIN usuarios u ON p.fk_usuario = u.id
        JOIN catalogo c ON p.fk_modelo = c.id
        ORDER BY p.fecha_prestamo DESC
    ''').fetchall()
    reservas_items = conn.execute('''
        SELECT r.id, u.nombre AS usuario, c.implemento, r.fecha_reserva, r.fecha_inicio, r.fecha_fin, r.lugar, r.estado
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
        SELECT r.id, u.nombre AS usuario, c.implemento, r.fecha_reserva, r.fecha_inicio, r.fecha_fin, r.lugar, r.estado
        FROM reservas r
        JOIN usuarios u ON r.fk_usuario = u.id
        JOIN catalogo c ON r.fk_implemento = c.id
        ORDER BY r.fecha_reserva DESC
    ''').fetchall()
    conn.close()
    
    return render_template('views/reservas.html', reservas=reservas_items)