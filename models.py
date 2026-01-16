# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

db = SQLAlchemy()

# --- TABLAS INTERMEDIAS ---
usuario_grupos = db.Table('usuario_grupos',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('grupo_id', db.Integer, db.ForeignKey('grupos.id'), primary_key=True)
)

usuario_dashboards = db.Table('usuario_dashboards',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('dashboard_id', db.Integer, db.ForeignKey('dashboards.id'), primary_key=True)
)

def obtener_hora_chile():
    chile_tz = pytz.timezone('America/Santiago')
    return datetime.now(chile_tz).replace(tzinfo=None)

# --- MODELO GLOBAL (Referencia) ---
class UsuarioGlobal(db.Model):
    # Ajusta 'mahosalu_usuarios_global' si en tu local se llama diferente
    __tablename__ = 'usuarios_global'
    __table_args__ = {'schema': 'mahosalu_usuarios_global'} 

    id = db.Column(db.Integer, primary_key=True)
    rut = db.Column(db.String(12))
    nombre_completo = db.Column(db.String(255))
    email = db.Column(db.String(255))
    password_hash = db.Column(db.String(255))
    activo = db.Column(db.Boolean)
    cambio_clave_requerido = db.Column(db.Boolean)
    reset_token = db.Column(db.String(32))
    reset_token_expiracion = db.Column(db.DateTime)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- MODELO LOCAL ---
class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol')

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=obtener_hora_chile)
    
    # Vínculo con la Global
    usuario_global_id = db.Column(db.Integer, nullable=False, unique=True)
    
    # Relación "Virtual" con UsuarioGlobal
    identidad = db.relationship('UsuarioGlobal', 
                                primaryjoin='Usuario.usuario_global_id == UsuarioGlobal.id',
                                foreign_keys='Usuario.usuario_global_id',
                                uselist=False, viewonly=True)

    # Relación con Rol Local
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    rol = db.relationship('Rol', back_populates='usuarios')

    # Acceso a grupos permitidos (Local)
    grupos_permitidos = db.relationship('Grupo', secondary=usuario_grupos, lazy='subquery',
        backref=db.backref('usuarios_con_acceso', lazy=True))
    
    # Acceso a dashboards permitidos (Local)
    dashboards_permitidos = db.relationship('Dashboard', secondary=usuario_dashboards, lazy='subquery',
        backref=db.backref('usuarios_con_acceso', lazy=True))

    # PROXIES: Para no romper los templates existentes
    @property
    def nombre_completo(self):
        return self.identidad.nombre_completo if self.identidad else "Usuario Desconocido"
    
    @property
    def email(self):
        return self.identidad.email if self.identidad else ""
    
    @property
    def cambio_clave_requerido(self):
        return self.identidad.cambio_clave_requerido if self.identidad else False

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=obtener_hora_chile) 
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nombre = db.Column(db.String(255))
    accion = db.Column(db.String(255), nullable=False)
    detalles = db.Column(db.Text)
    
    usuario = db.relationship('Usuario', backref=db.backref('logs', lazy=True))

# --- MODELOS DE DASHBOARDS ---

class Grupo(db.Model):
    __tablename__ = 'grupos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    imagen = db.Column(db.String(255)) 
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    
    # Relación para acceder a los dashboards de este grupo
    dashboards = db.relationship('Dashboard', back_populates='grupo')

class Dashboard(db.Model):
    __tablename__ = 'dashboards'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    url_iframe = db.Column(db.Text, nullable=False)
    imagen_preview = db.Column(db.String(255)) 
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id'), nullable=True)
    grupo = db.relationship('Grupo', back_populates='dashboards')