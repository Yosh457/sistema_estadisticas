# blueprints/admin.py
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from models import db, Usuario, Rol, Log, Dashboard, Grupo, UsuarioGlobal # Importamos la Global
from utils import registrar_log, admin_required

admin_bp = Blueprint('admin', __name__, template_folder='../templates', url_prefix='/admin')

@admin_bp.route('/panel')
@login_required
@admin_required
def panel():
    page = request.args.get('page', 1, type=int)
    busqueda = request.args.get('busqueda', '')
    rol_filtro = request.args.get('rol_filtro', '')
    estado_filtro = request.args.get('estado_filtro', '')

    # Hacemos Join con la identidad global para buscar por nombre
    query = Usuario.query.join(Usuario.identidad)

    if busqueda:
        query = query.filter(
            or_(
                UsuarioGlobal.nombre_completo.ilike(f'%{busqueda}%'),
                UsuarioGlobal.email.ilike(f'%{busqueda}%')
            )
        )
    
    if rol_filtro:
        query = query.filter(Usuario.rol_id == rol_filtro)

    if estado_filtro == 'activo':
        query = query.filter(Usuario.activo == True)
    elif estado_filtro == 'inactivo':
        query = query.filter(Usuario.activo == False)
    
    # Ordenamos por nombre global
    pagination = query.order_by(UsuarioGlobal.nombre_completo).paginate(page=page, per_page=10, error_out=False)
    
    roles_para_filtro = Rol.query.order_by(Rol.nombre).all()

    return render_template('admin_panel.html', 
                           pagination=pagination,
                           roles_para_filtro=roles_para_filtro,
                           busqueda=busqueda,
                           rol_filtro=rol_filtro,
                           estado_filtro=estado_filtro,
                           usuario=current_user)

# --- VINCULAR USUARIO (Antes Crear) ---
@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_usuario():
    # Listas para permisos
    todos_grupos = Grupo.query.order_by(Grupo.orden).all()
    todos_dashboards = Dashboard.query.order_by(Dashboard.grupo_id, Dashboard.orden).all()
    roles = Rol.query.order_by(Rol.nombre).all()

    if request.method == 'POST':
        usuario_global_id = request.form.get('usuario_global_id')
        rol_id = request.form.get('rol_id')
        
        if not usuario_global_id or not rol_id:
            flash('Debes seleccionar un funcionario y un rol.', 'danger')
            return redirect(url_for('admin.crear_usuario'))

        # Validar si ya existe localmente
        if Usuario.query.filter_by(usuario_global_id=usuario_global_id).first():
            flash('Este funcionario ya tiene acceso al sistema.', 'warning')
            return redirect(url_for('admin.crear_usuario'))

        # Crear Usuario Local
        nuevo_usuario = Usuario(
            usuario_global_id=usuario_global_id,
            rol_id=rol_id,
            activo=True
        )
        
        # ASIGNAR PERMISOS DE DASHBOARDS (Si aplica)
        grupos_ids = request.form.getlist('permisos_grupos')
        dashboards_ids = request.form.getlist('permisos_dashboards')

        for gid in grupos_ids:
            grupo = Grupo.query.get(int(gid))
            if grupo: nuevo_usuario.grupos_permitidos.append(grupo)
        
        for did in dashboards_ids:
            dash = Dashboard.query.get(int(did))
            if dash: nuevo_usuario.dashboards_permitidos.append(dash)
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()

            # Obtener nombre para log
            usr_glob = UsuarioGlobal.query.get(usuario_global_id)
            nombre_log = usr_glob.nombre_completo if usr_glob else "ID " + str(usuario_global_id)

            registrar_log("Vinculación Usuario", f"Otorgó acceso a {nombre_log} con permisos específicos.")
            flash('Funcionario vinculado con éxito.', 'success')
            return redirect(url_for('admin.panel'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al vincular: {str(e)}', 'danger')

    # BUSCAR USUARIOS GLOBALES DISPONIBLES (Que no estén ya en local)
    ids_locales = db.session.query(Usuario.usuario_global_id).all()
    ids_locales_lista = [id[0] for id in ids_locales]

    if ids_locales_lista:
        usuarios_disponibles = UsuarioGlobal.query.filter(
            UsuarioGlobal.id.notin_(ids_locales_lista),
            UsuarioGlobal.activo == True
        ).order_by(UsuarioGlobal.nombre_completo).all()
    else:
        usuarios_disponibles = UsuarioGlobal.query.filter_by(activo=True).order_by(UsuarioGlobal.nombre_completo).all()

    return render_template('crear_usuario.html', 
                           roles=roles, 
                           grupos=todos_grupos, 
                           dashboards=todos_dashboards,
                           usuarios_disponibles=usuarios_disponibles)

@admin_bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    usuario_local = Usuario.query.get_or_404(id)

    todos_grupos = Grupo.query.order_by(Grupo.orden).all()
    todos_dashboards = Dashboard.query.order_by(Dashboard.grupo_id, Dashboard.orden).all()
    roles = Rol.query.order_by(Rol.nombre).all()

    if request.method == 'POST':
        # Solo editamos Rol y Permisos
        usuario_local.rol_id = request.form.get('rol_id')
        
        # Actualizar Permisos (Borrar y volver a agregar)
        usuario_local.grupos_permitidos = []
        usuario_local.dashboards_permitidos = []

        grupos_ids = request.form.getlist('permisos_grupos')
        dashboards_ids = request.form.getlist('permisos_dashboards')

        for gid in grupos_ids:
            grupo = Grupo.query.get(int(gid))
            if grupo: usuario_local.grupos_permitidos.append(grupo)
        
        for did in dashboards_ids:
            dash = Dashboard.query.get(int(did))
            if dash: usuario_local.dashboards_permitidos.append(dash)

        try:
            db.session.commit()
            registrar_log("Edición Permisos", f"Actualizó permisos de {usuario_local.nombre_completo}")
            flash('Permisos actualizados con éxito.', 'success')
            return redirect(url_for('admin.panel'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')

    return render_template('editar_usuario.html', 
                           usuario=usuario_local, 
                           roles=roles, 
                           grupos=todos_grupos, 
                           dashboards=todos_dashboards)

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

@admin_bp.route('/ver_logs')
@login_required
def ver_logs():
    page = request.args.get('page', 1, type=int)
    
    # Capturamos los filtros de la URL
    usuario_filtro_id = request.args.get('usuario_id', '')
    accion_filtro = request.args.get('accion', '')

    # Ordenamos por fecha descendente (lo más nuevo primero)
    query = Log.query.order_by(Log.timestamp.desc())

    # Aplicamos filtros si existen
    if usuario_filtro_id:
        query = query.filter(Log.usuario_id == usuario_filtro_id)
    if accion_filtro:
        query = query.filter(Log.accion == accion_filtro)
        
    # Paginación
    pagination = query.paginate(page=page, per_page=15, error_out=False)
    
    # Datos para los selectores (Dropdowns)
    todos_los_usuarios = Usuario.query.order_by(Usuario.nombre_completo).all()
    
    # Lista manual de las acciones que hemos programado en este sistema
    acciones_posibles = [
        "Inicio de Sesión",
        "Cierre de Sesión",
        "Creación de Usuario",
        "Edición de Usuario",
        "Cambio de Estado" # (Activar/Desactivar)
    ]
    
    # Pasamos los filtros actuales para mantener seleccionada la opción en el HTML
    filtros_actuales = {
        'usuario_id': usuario_filtro_id,
        'accion': accion_filtro
    }

    return render_template('ver_logs.html',
                        pagination=pagination,
                        todos_los_usuarios=todos_los_usuarios,
                        acciones_posibles=acciones_posibles,
                        filtros=filtros_actuales)

# --- GESTIÓN DE DASHBOARDS ---

@admin_bp.route('/dashboards')
@login_required
@admin_required
def admin_dashboards():
    dashboards = Dashboard.query.order_by(Dashboard.grupo_id, Dashboard.orden).all()
    return render_template('admin_dashboards.html', dashboards=dashboards)

@admin_bp.route('/crear_dashboard', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_dashboard():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        url_iframe = request.form.get('url_iframe')
        grupo_id = request.form.get('grupo_id')
        orden = request.form.get('orden')
        
        # Manejo de Imagen
        imagen_filename = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Guardamos en static
                file.save(os.path.join(current_app.root_path, 'static', filename))
                imagen_filename = filename

        nuevo_dash = Dashboard(
            titulo=titulo,
            descripcion=descripcion,
            url_iframe=url_iframe,
            grupo_id=grupo_id,
            orden=orden,
            imagen_preview=imagen_filename,
            activo=True
        )
        
        db.session.add(nuevo_dash)
        db.session.commit()
        
        registrar_log("Creación Dashboard", f"Creó el dashboard '{titulo}'")
        flash('Dashboard creado con éxito.', 'success')
        return redirect(url_for('admin.admin_dashboards'))

    grupos = Grupo.query.order_by(Grupo.orden).all()
    return render_template('crear_editar_dashboard.html', grupos=grupos, dashboard=None)

@admin_bp.route('/editar_dashboard/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_dashboard(id):
    dashboard = Dashboard.query.get_or_404(id)
    
    if request.method == 'POST':
        dashboard.titulo = request.form.get('titulo')
        dashboard.descripcion = request.form.get('descripcion')
        dashboard.url_iframe = request.form.get('url_iframe')
        dashboard.grupo_id = request.form.get('grupo_id')
        dashboard.orden = request.form.get('orden')
        
        # Manejo de Imagen (Solo si se sube una nueva)
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.root_path, 'static', filename))
                dashboard.imagen_preview = filename

        db.session.commit()
        registrar_log("Edición Dashboard", f"Editó el dashboard '{dashboard.titulo}'")
        flash('Dashboard actualizado.', 'success')
        return redirect(url_for('admin.admin_dashboards'))

    grupos = Grupo.query.order_by(Grupo.orden).all()
    return render_template('crear_editar_dashboard.html', grupos=grupos, dashboard=dashboard)

@admin_bp.route('/toggle_dashboard/<int:id>', methods=['POST'])
@login_required
@admin_required
def toggle_dashboard(id):
    dashboard = Dashboard.query.get_or_404(id)
    dashboard.activo = not dashboard.activo
    db.session.commit()
    flash(f'Dashboard "{dashboard.titulo}" {"activado" if dashboard.activo else "desactivado"}.', 'info')
    return redirect(url_for('admin.admin_dashboards'))