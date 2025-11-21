from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.security import generate_password_hash
from datetime import datetime
from models import db, Usuario, Rol, Log
from utils import registrar_log

admin_bp = Blueprint('admin', __name__, template_folder='../templates', url_prefix='/admin')

@admin_bp.route('/panel')
@login_required
def panel():
    # Paginación
    page = request.args.get('page', 1, type=int)
    
    # Filtros que vienen de la URL (GET)
    busqueda = request.args.get('busqueda', '')
    rol_filtro = request.args.get('rol_filtro', '')
    estado_filtro = request.args.get('estado_filtro', '')

    # Query base
    query = Usuario.query

    # 1. Filtro de Búsqueda (Nombre o Email)
    if busqueda:
        query = query.filter(
            or_(
                Usuario.nombre_completo.ilike(f'%{busqueda}%'),
                Usuario.email.ilike(f'%{busqueda}%')
            )
        )
    
    # 2. Filtro de Rol
    if rol_filtro:
        query = query.filter(Usuario.rol_id == rol_filtro)

    # 3. Filtro de Estado
    if estado_filtro == 'activo':
        query = query.filter(Usuario.activo == True)
    elif estado_filtro == 'inactivo':
        query = query.filter(Usuario.activo == False)
    
    # Ordenar y paginar
    pagination = query.order_by(Usuario.id).paginate(page=page, per_page=10, error_out=False)
    
    # Obtener roles para llenar el select del filtro
    roles_para_filtro = Rol.query.order_by(Rol.nombre).all()

    return render_template('admin_panel.html', 
                           pagination=pagination,
                           roles_para_filtro=roles_para_filtro,
                           busqueda=busqueda,
                           rol_filtro=rol_filtro,
                           estado_filtro=estado_filtro,
                           usuario=current_user)

# --- RUTAS PANEL DE ADMIN ---

@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    if request.method == 'POST':
        nombre = request.form.get('nombre_completo')
        email = request.form.get('email')
        password = request.form.get('password')
        rol_id = request.form.get('rol_id')
        
        # Checkbox devuelve '1' si está marcado, o nada si no
        forzar_cambio = request.form.get('forzar_cambio_clave') == '1'

        # 1. Validaciones
        if Usuario.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'danger')
            return redirect(url_for('admin.crear_usuario'))

        # 2. Crear Usuario
        nuevo_usuario = Usuario(
            nombre_completo=nombre,
            email=email,
            rol_id=rol_id,
            cambio_clave_requerido=forzar_cambio,
            activo=True
        )
        nuevo_usuario.set_password(password)
        
        db.session.add(nuevo_usuario)
        db.session.commit()

        # 3. Registrar Log
        registrar_log(
            accion="Creación de Usuario",
            detalles=f"Creó al usuario {nombre} ({email})"
        )

        flash('Usuario creado con éxito.', 'success')
        return redirect(url_for('admin.panel'))

    # GET: Mostrar formulario
    roles = Rol.query.order_by(Rol.nombre).all()
    return render_template('crear_usuario.html', roles=roles)

@admin_bp.route('/ver_logs')
@login_required
def ver_logs():
    flash('Funcionalidad en construcción', 'info')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    usuario_a_editar = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        # 1. Recoger datos del formulario
        usuario_a_editar.nombre_completo = request.form.get('nombre_completo')
        usuario_a_editar.email = request.form.get('email')
        usuario_a_editar.rol_id = request.form.get('rol_id')
        
        # Checkbox: si está marcado es True, si no, False
        forzar_cambio = request.form.get('forzar_cambio_clave') == '1'
        usuario_a_editar.cambio_clave_requerido = forzar_cambio

        # 2. Lógica de Contraseña (Solo si escribieron algo)
        password = request.form.get('password')
        if password and password.strip(): # Si hay texto y no son solo espacios
            usuario_a_editar.set_password(password)
            flash('Contraseña actualizada.', 'info')
        
        # 3. Guardar cambios
        try:
            db.session.commit()
            
            # 4. Registrar Log
            registrar_log(
                accion="Edición de Usuario", 
                detalles=f"Editó los datos del usuario {usuario_a_editar.nombre_completo} (ID: {usuario_a_editar.id})"
            )
            
            flash('Usuario actualizado con éxito.', 'success')
            return redirect(url_for('admin.panel'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar: El correo podría estar duplicado.', 'danger')

    # GET: Cargar formulario con datos actuales
    roles = Rol.query.order_by(Rol.nombre).all()
    return render_template('editar_usuario.html', 
                           usuario=usuario_a_editar,
                           roles=roles)

@admin_bp.route('/toggle_activo/<int:id>', methods=['POST'])
@login_required
def toggle_activo(id):
    # Lógica rápida para que pruebes el botón de activar/desactivar
    usuario = Usuario.query.get_or_404(id)
    # Evitar que el admin se desactive a sí mismo
    if usuario.id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.panel'))
        
    usuario.activo = not usuario.activo
    db.session.commit()
    
    estado = "activado" if usuario.activo else "desactivado"

    registrar_log(
        accion="Cambio de Estado",
        detalles=f"Usuario {usuario.nombre_completo} fue {estado}."
    )
    
    flash(f'Usuario {usuario.nombre_completo} {estado}.', 'success')
    return redirect(url_for('admin.panel'))