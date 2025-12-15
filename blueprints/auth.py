# blueprints/auth.py (Estadísticas)
import secrets
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, Usuario, UsuarioGlobal 
from utils import registrar_log, enviar_correo_reseteo, es_password_segura

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

def obtener_ruta_redireccion(usuario):
    if not usuario.rol: return url_for('auth.login')
    return url_for('admin.panel') if usuario.rol.nombre == "Admin" else url_for('estadisticas.seleccion_grupo')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        identidad_global = UsuarioGlobal.query.filter_by(email=email).first()

        if identidad_global and identidad_global.check_password(password):
            usuario_local = Usuario.query.filter_by(usuario_global_id=identidad_global.id).first()
            
            if usuario_local and usuario_local.activo and identidad_global.activo:
                login_user(usuario_local)
                registrar_log("Inicio de Sesión", f"Usuario {usuario_local.nombre_completo} inició sesión.")
                
                if identidad_global.cambio_clave_requerido:
                    flash('Por seguridad, debes cambiar tu contraseña ahora.', 'warning')
                    return redirect(url_for('auth.cambiar_clave'))
                
                flash(f'Bienvenido, {usuario_local.nombre_completo}', 'success')
                return redirect(obtener_ruta_redireccion(usuario_local))
            else:
                flash('No tienes permisos para acceder a Estadísticas.', 'warning')
        else:
            flash('Credenciales incorrectas.', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    registrar_log("Cierre de Sesión", f"Usuario {current_user.nombre_completo} cerró sesión.")
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))

# --- GESTIÓN DE CLAVES (GLOBAL) ---

@auth_bp.route('/cambiar_clave', methods=['GET', 'POST'])
@login_required
def cambiar_clave():
    if request.method == 'POST':
        password_nueva = request.form.get('nueva_password')
        password_confirmar = request.form.get('confirmar_password')

        if password_nueva != password_confirmar:
            flash('Las nuevas contraseñas no coinciden.', 'warning')
            return render_template('cambiar_clave.html')

        if not es_password_segura(password_nueva):
            flash('La contraseña no es segura.', 'warning')
            return render_template('cambiar_clave.html')

        try:
            usuario_global = current_user.identidad
            usuario_global.password_hash = generate_password_hash(password_nueva)
            usuario_global.cambio_clave_requerido = False
            db.session.commit()
            
            registrar_log("Cambio de Clave", f"Usuario {current_user.nombre_completo} cambió su clave.")
            logout_user() # Forzamos re-login
            flash('Contraseña actualizada. Inicia sesión nuevamente.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar.', 'danger')

    return render_template('cambiar_clave.html')

@auth_bp.route('/solicitar-reseteo', methods=['GET', 'POST'])
def solicitar_reseteo():
    if request.method == 'POST':
        email = request.form.get('email')
        usuario_global = UsuarioGlobal.query.filter_by(email=email).first()
        
        if usuario_global:
            token = secrets.token_hex(16)
            usuario_global.reset_token = token
            usuario_global.reset_token_expiracion = datetime.now() + timedelta(hours=1) # Ojo con la TZ si es critica
            db.session.commit()
            enviar_correo_reseteo(usuario_global, token)
            flash(f'Se ha enviado un enlace a {email}.', 'success')
        else:
            flash(f'El correo {email} no se encuentra registrado.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('solicitar_reseteo.html')

@auth_bp.route('/resetear-clave/<token>', methods=['GET', 'POST'])
def resetear_clave(token):
    usuario_global = UsuarioGlobal.query.filter_by(reset_token=token).first()
    if not usuario_global or not usuario_global.reset_token_expiracion or usuario_global.reset_token_expiracion < datetime.now():
        flash('Enlace inválido o expirado.', 'danger')
        return redirect(url_for('auth.solicitar_reseteo'))
        
    if request.method == 'POST':
        nueva = request.form.get('nueva_password')
        if not es_password_segura(nueva):
            flash('Contraseña insegura.', 'danger')
            return render_template('resetear_clave.html', token=token)
            
        usuario_global.password_hash = generate_password_hash(nueva)
        usuario_global.reset_token = None
        usuario_global.cambio_clave_requerido = False
        db.session.commit()
        flash('Contraseña restablecida. Inicia sesión.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('resetear_clave.html', token=token)