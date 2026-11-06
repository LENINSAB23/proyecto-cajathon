from functools import wraps
from urllib.parse import urlsplit
from flask import Blueprint, abort, current_app, render_template, request, redirect, url_for, session, flash
from httpx import HTTPError
from supabase import AuthError
from werkzeug.security import check_password_hash
from database.db import get_supabase, query_db, execute_db
from config import Config

auth_bp = Blueprint('auth', __name__)

ROLE_HOME_ENDPOINTS = {
    'Administrador': 'dashboard.index',
    'Analista de créditos': 'dashboard.index',
    'Personal de cobranza': 'morosidad.index'
}

def role_home_url(user_role):
    endpoint = ROLE_HOME_ENDPOINTS.get(user_role)
    if not endpoint:
        abort(403)
    return url_for(endpoint)

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
            if user_role != 'Administrador' and user_role not in roles:
                if user_role not in ROLE_HOME_ENDPOINTS:
                    abort(403)
                flash(f'Acceso denegado: El rol "{user_role}" no tiene permisos para esta acción.', 'danger')
                return redirect(role_home_url(user_role))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def authenticate_user(email, password):
    if Config.USE_SUPABASE_AUTH:
        try:
            response = get_supabase().auth.sign_in_with_password({
                "email": email,
                "password": password
            })
        except AuthError as error:
            if getattr(error, "status", None) in (400, 401):
                return None
            raise

        auth_user = response.user
        if not auth_user or not auth_user.email:
            return None

        user = query_db(
            "SELECT * FROM usuarios WHERE id = ? AND activo = TRUE",
            (str(auth_user.id),),
            one=True
        )
        if user and user['email'].strip().lower() == auth_user.email.strip().lower():
            return user
        return None

    user = query_db(
        "SELECT * FROM usuarios WHERE email = ? AND activo = TRUE",
        (email,),
        one=True
    )
    if user and user.get('password_hash') and check_password_hash(user['password_hash'], password):
        return user
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(role_home_url(session.get('user_role')))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        try:
            user = authenticate_user(email, password)
        except (HTTPError, AuthError):
            current_app.logger.exception("No se pudo validar la cuenta de inicio de sesión")
            flash('No se pudo validar el acceso en este momento. Inténtelo nuevamente.', 'danger')
            return render_template('login.html')

        if user:
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['nombre']
            session['user_email'] = user['email']
            session['user_role'] = user['rol']
            session['user_cargo'] = user['cargo']
            session['user_agencia'] = user['agencia']
            session['user_avatar'] = user.get('avatar_url')

            execute_db("UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
            flash(f'¡Bienvenido a CAJA INTELIGENTE, {user["nombre"]}!', 'success')
            next_url = request.args.get('next', '')
            target = urlsplit(next_url)
            if (
                target.path.startswith('/')
                and not target.path.startswith('//')
                and not target.netloc
                and not target.scheme
                and '\\' not in target.path
            ):
                return redirect(target.path + (f"?{target.query}" if target.query else ""))
            return redirect(role_home_url(user['rol']))
        else:
            flash('Correo electrónico o contraseña incorrectos.', 'danger')

    return render_template('login.html')

@auth_bp.route('/demo-login/<role>')
def demo_login(role):
    """Acceso rápido con un clic para evaluadores del proyecto según el rol deseado."""
    if not Config.DEMO_LOGIN_ENABLED:
        abort(404)

    role_map = {
        'admin': 'admin@creditrisk.pe',
        'analista': 'analista@creditrisk.pe',
        'cobranzas': 'cobranzas@creditrisk.pe'
    }
    email = role_map.get(role.lower())
    if not email:
        abort(404)
    user = query_db("SELECT * FROM usuarios WHERE email = ?", (email,), one=True)
    if user:
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['nombre']
        session['user_email'] = user['email']
        session['user_role'] = user['rol']
        session['user_cargo'] = user['cargo']
        session['user_agencia'] = user['agencia']
        session['user_avatar'] = user.get('avatar_url')
        flash(f'Sesión iniciada como: {user["rol"]} ({user["nombre"]})', 'info')
        return redirect(role_home_url(user['rol']))
    abort(404)

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Ha cerrado sesión correctamente. ¡Hasta pronto!', 'info')
    return redirect(url_for('auth.login'))
