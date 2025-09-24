from utils.db import get_db_connection
from flask import Blueprint, render_template, request, redirect, url_for, session

bp = Blueprint('perfil', __name__, template_folder='templates')

@bp.route('/perfil')
def perfil():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    conn.close()

    if user is None:
        return redirect(url_for('login.login'))

    return render_template('views/perfil.html', user=user)

