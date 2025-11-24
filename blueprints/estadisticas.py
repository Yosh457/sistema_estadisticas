# blueprints/estadisticas.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import Dashboard, Grupo

estadisticas_bp = Blueprint('estadisticas', __name__, template_folder='../templates', url_prefix='/estadisticas')

# Ruta 1: Mostrar los Grupos (Tarjetas)
@estadisticas_bp.route('/')
@login_required
def seleccion_grupo():
    if current_user.rol.nombre not in ['Admin', 'Lector']:
        abort(403)
    
    grupos = Grupo.query.order_by(Grupo.orden).all()
    return render_template('estadisticas/seleccion_grupo.html', grupos=grupos)

# Ruta 2: Mostrar la Lista de Paneles de UN Grupo (ACORDEONES)
@estadisticas_bp.route('/grupo/<int:grupo_id>')
@login_required
def lista_por_grupo(grupo_id):
    if current_user.rol.nombre not in ['Admin', 'Lector']:
        abort(403)
        
    grupo = Grupo.query.get_or_404(grupo_id)
    dashboards = Dashboard.query.filter_by(grupo_id=grupo_id, activo=True).order_by(Dashboard.orden).all()
    
    return render_template('estadisticas/lista.html', dashboards=dashboards, grupo=grupo)

# Ruta 3: Ver el PowerBI en pantalla completa
@estadisticas_bp.route('/ver/<int:id>')
@login_required
def ver_dashboard(id):
    if current_user.rol.nombre not in ['Admin', 'Lector']:
        abort(403)

    dashboard = Dashboard.query.get_or_404(id)
    if not dashboard.activo:
        abort(404)

    return render_template('estadisticas/ver.html', dashboard=dashboard)