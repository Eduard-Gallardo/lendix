from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.login import login_required
from utils.db import get_db_connection

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
