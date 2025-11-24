from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import pytz
import secrets

# Importamos modelos y utilidades
from models import db, Usuario
from utils import registrar_log, enviar_correo_reseteo

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

# --- Lógica de Redirección ---
def obtener_ruta_redireccion(usuario):
    """Define a dónde va el usuario según su Rol."""
    if not usuario.rol:
        return url_for('auth.login')
    
    nombre_rol = usuario.rol.nombre
    
    if nombre_rol == "Admin":
        return url_for('admin.panel')
    elif nombre_rol == "Lector":
        # CORRECCIÓN: Ahora los lectores van a la selección de grupos
        return url_for('estadisticas.seleccion_grupo')
    else:
        return url_for('estadisticas.seleccion_grupo')

# --- RUTAS DE LOGIN/LOGOUT ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, lo mandamos a su panel
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Buscamos el usuario
        usuario = Usuario.query.filter_by(email=email).first()

        # Verificaciones
        if usuario:
            if not usuario.activo:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return redirect(url_for('auth.login'))
        
        if usuario and usuario.check_password(password):
            login_user(usuario)

            # Log
            registrar_log("Inicio de Sesión", f"Usuario {usuario.nombre_completo} inició sesión.")

            # Verificar si requiere cambio de clave INMEDIATAMENTE
            if usuario.cambio_clave_requerido:
                return redirect(url_for('auth.cambiar_clave'))
            
            flash(f'Bienvenido, {usuario.nombre_completo}', 'success')
            
            return redirect(obtener_ruta_redireccion(usuario))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    registrar_log("Cierre de Sesión", f"Usuario {current_user.nombre_completo} cerró sesión.")
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))

# --- RUTAS DE GESTIÓN DE CLAVE ---
@auth_bp.route('/cambiar_clave', methods=['GET', 'POST'])
@login_required
def cambiar_clave():
    # Solo permitimos entrar aquí si el flag está activo
    if not current_user.cambio_clave_requerido:
        return redirect(obtener_ruta_redireccion(current_user))
        
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')
        
        # Cambiamos la clave
        current_user.set_password(nueva_password)
        current_user.cambio_clave_requerido = False # Quitamos el bloqueo
        db.session.commit()
        
        registrar_log("Cambio de Clave", "El usuario actualizó su contraseña obligatoria.")
        
        flash('Contraseña actualizada. ¡Gracias!', 'success')
        return redirect(obtener_ruta_redireccion(current_user))
        
    return render_template('cambiar_clave.html')

@auth_bp.route('/solicitar-reseteo', methods=['GET', 'POST'])
def solicitar_reseteo():
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    if request.method == 'POST':
        email = request.form.get('email')
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario:
            # Generar Token
            token = secrets.token_hex(16)
            
            # Hora Chile para expiración (1 hora)
            chile_tz = pytz.timezone('America/Santiago')
            ahora_chile = datetime.now(chile_tz).replace(tzinfo=None)
            expiracion = ahora_chile + timedelta(hours=1)
            
            usuario.reset_token = token
            usuario.reset_token_expiracion = expiracion
            db.session.commit()
            
            # Enviar correo
            enviar_correo_reseteo(usuario, token)
            
            # Mensaje genérico por seguridad (aunque el usuario no exista, a veces se dice enviado)
            # Pero aquí seremos explícitos como en tu código anterior
            flash(f'Se ha enviado un enlace a {email}. Revisa tu bandeja.', 'success')
        else:
            flash(f'El correo {email} no está registrado en el sistema.', 'danger')
            
        return redirect(url_for('auth.login'))
        
    return render_template('solicitar_reseteo.html')

@auth_bp.route('/resetear-clave/<token>', methods=['GET', 'POST'])
def resetear_clave(token):
    if current_user.is_authenticated:
        return redirect(obtener_ruta_redireccion(current_user))

    usuario = Usuario.query.filter_by(reset_token=token).first()
    
    # Validar Token y Expiración
    chile_tz = pytz.timezone('America/Santiago')
    ahora_chile = datetime.now(chile_tz).replace(tzinfo=None)
    
    if not usuario or not usuario.reset_token_expiracion or usuario.reset_token_expiracion < ahora_chile:
        flash('El enlace es inválido o ha expirado. Solicita uno nuevo.', 'danger')
        return redirect(url_for('auth.solicitar_reseteo'))
        
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')
        usuario.set_password(nueva_password)
        
        # Limpiar token
        usuario.reset_token = None
        usuario.reset_token_expiracion = None
        db.session.commit()
        
        registrar_log("Recuperación Clave", f"El usuario {usuario.nombre_completo} reseteó su clave vía correo.")
        
        flash('Tu contraseña ha sido restablecida. Inicia sesión.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('resetear_clave.html')