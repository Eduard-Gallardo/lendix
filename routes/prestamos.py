from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.login import login_required
from utils.db import get_db_connection

prestamos_bp = Blueprint('prestamos', __name__)

@prestamos_bp.route('/prestamos', methods=['GET', 'POST'])
@login_required
def prestamos():
    if request.method == 'POST':
        implemento = request.form['implemento']
        descripcion = request.form['descripcion']
        disponibilidad = request.form['disponibilidad']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO catalogo (implemento, descripcion, disponibilidad) VALUES (?, ?, ?)',
                     (implemento, descripcion, disponibilidad))
        conn.commit()
        conn.close()
        
        flash('Implemento agregado al catálogo exitosamente.', 'success')
        return redirect(url_for('prestamos.prestamos'))
    
    conn = get_db_connection()
    catalogo_items = conn.execute('SELECT * FROM catalogo').fetchall()
    conn.close()
    
    return render_template('prestamos.html', catalogo=catalogo_items)