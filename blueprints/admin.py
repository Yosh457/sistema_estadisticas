from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_
from models import db, Usuario, Rol

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

# --- RUTAS PLACEHOLDER (Para que los botones no den error) ---

@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    flash('Funcionalidad en construcción', 'info')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/ver_logs')
@login_required
def ver_logs():
    flash('Funcionalidad en construcción', 'info')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    flash(f'Editar usuario {id} en construcción', 'info')
    return redirect(url_for('admin.panel'))

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
    flash(f'Usuario {usuario.nombre_completo} {estado}.', 'success')
    return redirect(url_for('admin.panel'))