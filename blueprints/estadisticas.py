# blueprints/estadisticas.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import Dashboard, Grupo

estadisticas_bp = Blueprint('estadisticas', __name__, template_folder='../templates', url_prefix='/estadisticas')

# Ruta 1: Mostrar los Grupos (Tarjetas)
@estadisticas_bp.route('/')
@login_required
def seleccion_grupo():
    if current_user.rol.nombre == 'Admin':
        # El admin ve todos los grupos
        grupos = Grupo.query.order_by(Grupo.orden).all()
    elif current_user.rol.nombre == 'Lector':
        # El lector ve SOLO los grupos asignados
        grupos = current_user.grupos_permitidos
        # Ordenamos manualmente porque la relación many-to-many no siempre respeta el orden
        grupos.sort(key=lambda x: x.orden)
    else:
        abort(403)
    
    return render_template('estadisticas/seleccion_grupo.html', grupos=grupos)

# Ruta 2: Mostrar la Lista de Paneles de UN Grupo (ACORDEONES)
@estadisticas_bp.route('/grupo/<int:grupo_id>')
@login_required
def lista_por_grupo(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    
    # Validar permiso de Grupo (Si no es admin y no tiene el grupo, fuera)
    if current_user.rol.nombre != 'Admin' and grupo not in current_user.grupos_permitidos:
        abort(403)

    # Filtrar Dashboards
    if current_user.rol.nombre == 'Admin':
        dashboards = Dashboard.query.filter_by(grupo_id=grupo_id, activo=True).order_by(Dashboard.orden).all()
    else:
        # Filtramos los dashboards del grupo que TAMBIÉN estén en la lista de permitidos del usuario
        # Usamos un conjunto (set) para intersección rápida o una lista por comprensión
        dashboards_grupo = Dashboard.query.filter_by(grupo_id=grupo_id, activo=True).order_by(Dashboard.orden).all()
        dashboards = [d for d in dashboards_grupo if d in current_user.dashboards_permitidos]
    
    return render_template('estadisticas/lista.html', dashboards=dashboards, grupo=grupo)

# Ruta 3: Ver el PowerBI en pantalla completa
@estadisticas_bp.route('/ver/<int:id>')
@login_required
def ver_dashboard(id):
    dashboard = Dashboard.query.get_or_404(id)
    if not dashboard.activo:
        abort(404)

    # Validar permiso de Dashboard
    if current_user.rol.nombre != 'Admin' and dashboard not in current_user.dashboards_permitidos:
        abort(403)

    return render_template('estadisticas/ver.html', dashboard=dashboard)