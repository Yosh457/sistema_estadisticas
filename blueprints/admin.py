import os
import io
from openpyxl import Workbook
from openpyxl.styles import Font
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, Usuario, Rol, Log, Dashboard, Grupo
from utils import registrar_log, admin_required

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

# --- GESTIÓN DE USUARIOS ---
@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    # Obtenemos listas para los permisos
    todos_grupos = Grupo.query.order_by(Grupo.orden).all()
    todos_dashboards = Dashboard.query.order_by(Dashboard.grupo_id, Dashboard.orden).all()
    roles = Rol.query.order_by(Rol.nombre).all()

    # POST: Procesar formulario
    if request.method == 'POST':
        nombre = request.form.get('nombre_completo')
        email = request.form.get('email')
        password = request.form.get('password')
        rol_id = request.form.get('rol_id')
        
        # Checkbox devuelve '1' si está marcado, o nada si no
        forzar_cambio = request.form.get('forzar_cambio_clave') == '1'

        # 1. VALIDACIÓN: Correo Duplicado
        if Usuario.query.filter_by(email=email).first():
            flash('Error: El correo electrónico ya está registrado en el sistema.', 'danger')
            # Guardamos lo que el usuario escribió para devolverlo
            datos_previos = {
                'nombre_completo': nombre,
                'email': email,
                'rol_id': int(rol_id) if rol_id else None,
                'permisos_grupos': [int(x) for x in request.form.getlist('permisos_grupos')], # Lista de IDs
                'permisos_dashboards': [int(x) for x in request.form.getlist('permisos_dashboards')]
            }
            
            return render_template('crear_usuario.html', 
                                   roles=roles, 
                                   grupos=todos_grupos, 
                                   dashboards=todos_dashboards,
                                   datos_previos=datos_previos)

        # 2. Crear Usuario
        nuevo_usuario = Usuario(
            nombre_completo=nombre,
            email=email,
            rol_id=rol_id,
            cambio_clave_requerido=forzar_cambio,
            activo=True
        )
        nuevo_usuario.set_password(password)
        
        # 3. ASIGNAR PERMISOS (Solo si es rol Lector, aunque el admin ve todo por defecto en el código)
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

            registrar_log("Creación de Usuario", f"Creó al usuario {nombre} ({email}) con permisos asignados.")
            flash('Usuario creado con éxito.', 'success')
            return redirect(url_for('admin.panel'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear usuario: {str(e)}', 'danger')

    return render_template('crear_usuario.html', roles=roles, grupos=todos_grupos, dashboards=todos_dashboards)

@admin_bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    usuario_a_editar = Usuario.query.get_or_404(id)

    # Listas para permisos y roles
    todos_grupos = Grupo.query.order_by(Grupo.orden).all()
    todos_dashboards = Dashboard.query.order_by(Dashboard.grupo_id, Dashboard.orden).all()
    roles = Rol.query.order_by(Rol.nombre).all()

    if request.method == 'POST':
        email_nuevo = request.form.get('email')
        
        # 1. VALIDACIÓN: Correo Duplicado (Verificar si existe Y si no es el mismo usuario)
        usuario_existente = Usuario.query.filter_by(email=email_nuevo).first()
        if usuario_existente and usuario_existente.id != id:
            flash('Error: Ese correo electrónico ya pertenece a otro usuario.', 'danger')
            return render_template('editar_usuario.html', usuario=usuario_a_editar, roles=roles, grupos=todos_grupos, dashboards=todos_dashboards)

        # 2. Actualizar Datos Básicos
        usuario_a_editar.nombre_completo = request.form.get('nombre_completo')
        usuario_a_editar.email = email_nuevo
        usuario_a_editar.rol_id = request.form.get('rol_id')
        usuario_a_editar.cambio_clave_requerido = request.form.get('forzar_cambio_clave') == '1'

        # 3. Actualizar Contraseña (Si aplica)
        password = request.form.get('password')
        if password and password.strip():
            usuario_a_editar.set_password(password)
            flash('Contraseña actualizada.', 'info')

        # 4. ACTUALIZAR PERMISOS
        # Limpiamos todo primero
        usuario_a_editar.grupos_permitidos = []
        usuario_a_editar.dashboards_permitidos = []

        # Obtenemos lo nuevo del form
        grupos_ids = request.form.getlist('permisos_grupos')
        dashboards_ids = request.form.getlist('permisos_dashboards')

        for gid in grupos_ids:
            grupo = Grupo.query.get(int(gid))
            if grupo: usuario_a_editar.grupos_permitidos.append(grupo)
        
        for did in dashboards_ids:
            dash = Dashboard.query.get(int(did))
            if dash: usuario_a_editar.dashboards_permitidos.append(dash)

        try:
            db.session.commit()
            registrar_log("Edición de Usuario", f"Editó datos y permisos de {usuario_a_editar.nombre_completo}")
            flash('Usuario actualizado con éxito.', 'success')
            return redirect(url_for('admin.panel'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar en base de datos: {str(e)}', 'danger')

    return render_template('editar_usuario.html', usuario=usuario_a_editar, roles=roles, grupos=todos_grupos, dashboards=todos_dashboards)

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
    todos_los_usuarios = Usuario.query.all()
    todos_los_usuarios.sort(key=lambda u: u.nombre_completo)
    
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
    
    estado = "activado" if dashboard.activo else "desactivado"
    registrar_log("Cambio Estado Dashboard", f"El dashboard '{dashboard.titulo}' fue {estado}.")
    
    flash(f'Dashboard "{dashboard.titulo}" {estado}.', 'success')
    return redirect(url_for('admin.admin_dashboards'))

@admin_bp.route('/exportar_logs_xlsx')
@login_required
@admin_required
def exportar_logs_xlsx():
    # 1. Obtenemos todos los logs ordenados por fecha (más reciente primero)
    logs = Log.query.order_by(Log.timestamp.desc()).all()

    # 2. Creamos un libro de Excel en memoria
    wb = Workbook()
    ws = wb.active
    ws.title = "Logs"

    # 3. Definimos los encabezados de la hoja
    headers = ['ID', 'Fecha y Hora', 'Usuario', 'Acción', 'Detalles']
    ws.append(headers)

    # 4. Aplicamos estilo en negrita a la fila de encabezados
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # 5. Escribimos los datos de cada log en la hoja
    for log in logs:
        ws.append([
            log.id,
            log.timestamp.strftime('%d-%m-%Y %H:%M:%S'),
            log.usuario_nombre,
            log.accion,
            log.detalles
        ])

    # 6. Ajustamos automáticamente el ancho de las columnas
    for column_cells in ws.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter

        for cell in column_cells:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))

        ws.column_dimensions[column_letter].width = max_length + 2

    # 7. Guardamos el archivo Excel en un buffer en memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # 8. Preparamos la respuesta HTTP para descargar el archivo XLSX
    response = make_response(output.getvalue())
    response.headers[
        'Content-Disposition'
    ] = 'attachment; filename=reporte_logs.xlsx'
    response.headers[
        'Content-Type'
    ] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    # 9. Retornamos el archivo para su descarga
    return response