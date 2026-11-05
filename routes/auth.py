from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from database.db import query_db, execute_db

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicie sesión para acceder a este módulo.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Por favor inicie sesión para continuar.', 'warning')
                return redirect(url_for('auth.login'))
            user_role = session.get('user_role')
            if user_role not in roles and 'Administrador' not in roles and user_role != 'Administrador':
                flash(f'Acceso denegado: El rol "{user_role}" no tiene permisos para esta acción.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = query_db("SELECT * FROM usuarios WHERE email = ? AND activo = 1", (email,), one=True)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['nombre']
            session['user_email'] = user['email']
            session['user_role'] = user['rol']
            session['user_cargo'] = user['cargo']
            session['user_agencia'] = user['agencia']
            session['user_avatar'] = user.get('avatar_url')

            execute_db("UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
            flash(f'¡Bienvenido a Caja Inteligente, {user["nombre"]}!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard.index'))
        else:
            flash('Correo electrónico o contraseña incorrectos.', 'danger')

    return render_template('login.html')

@auth_bp.route('/demo-login/<role>')
def demo_login(role):
    """Acceso rápido con un clic para evaluadores del proyecto según el rol deseado."""
    role_map = {
        'admin': 'admin@cajainteligente.pe',
        'analista': 'analista@cajainteligente.pe',
        'cobranzas': 'cobranzas@cajainteligente.pe'
    }
    email = role_map.get(role.lower(), 'admin@cajainteligente.pe')
    user = query_db("SELECT * FROM usuarios WHERE email = ?", (email,), one=True)
    if user:
        session['user_id'] = user['id']
        session['user_name'] = user['nombre']
        session['user_email'] = user['email']
        session['user_role'] = user['rol']
        session['user_cargo'] = user['cargo']
        session['user_agencia'] = user['agencia']
        session['user_avatar'] = user.get('avatar_url')
        flash(f'Sesión iniciada en Modo Demostración como: {user["rol"]} ({user["nombre"]})', 'info')
    return redirect(url_for('dashboard.index'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Ha cerrado sesión correctamente. ¡Hasta pronto!', 'info')
    return redirect(url_for('auth.login'))
