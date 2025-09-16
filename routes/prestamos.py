from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.login import login_required
from utils.db import get_db_connection

prestamos_bp = Blueprint('prestamos', __name__, template_folder='templates')

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
    conn.close()
    
    return render_template('views/prestamos.html', prestamos=prestamos_items)