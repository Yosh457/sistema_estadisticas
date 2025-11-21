from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Usuario

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, lo mandamos a su panel
    if current_user.is_authenticated:
        return redirect(url_for('admin.panel'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Buscamos el usuario
        usuario = Usuario.query.filter_by(email=email).first()

        # Verificamos usuario y contraseña
        if usuario and usuario.check_password(password):
            if not usuario.activo:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return redirect(url_for('auth.login'))
            
            login_user(usuario)
            flash(f'Bienvenido, {usuario.nombre_completo}', 'success')
            
            # Aquí definiremos a dónde va cada rol más adelante. 
            # Por ahora, todos al panel de admin.
            return redirect(url_for('admin.panel'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))