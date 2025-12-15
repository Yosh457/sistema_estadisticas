# utils/helpers.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from flask import url_for
from flask_login import current_user
from models import db, Log

import re

def es_password_segura(password):
    """Valida que la contraseña cumpla con los requisitos de seguridad."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password): 
        return False
    if not re.search(r"[0-9]", password): 
        return False
    return True

def registrar_log(accion, detalles):
    """Registra una acción en la base de datos."""
    if current_user.is_authenticated:
        try:
            nuevo_log = Log(
                usuario_id=current_user.id,
                usuario_nombre=current_user.nombre_completo,
                accion=accion,
                detalles=detalles
            )
            db.session.add(nuevo_log)
            db.session.commit()
        except Exception as e:
            # Si falla el log, no queremos que se caiga toda la app, 
            # pero imprimimos el error en consola.
            print(f"Error al registrar log: {e}")
            db.session.rollback()

def enviar_correo_reseteo(usuario, token):
    """
    Envía el correo con el link de recuperación.
    NOTA: En la arquitectura global, esto eventualmente se moverá al Portal TICs,
    pero lo mantenemos aquí por compatibilidad temporal o notificaciones futuras.
    """
    remitente = os.getenv("EMAIL_USUARIO")
    contrasena = os.getenv("EMAIL_CONTRASENA")
    
    if not remitente or not contrasena:
        print("ERROR: Credenciales de correo faltantes en .env")
        return

    msg = MIMEMultipart()
    msg['Subject'] = 'Restablecimiento de Contraseña - Sistema Estadísticas'
    msg['From'] = formataddr(('Sistema Estadísticas', remitente))
    msg['To'] = usuario.email

    # Generamos el link apuntando a la ruta de auth
    url_reseteo = url_for('auth.resetear_clave', token=token, _external=True)

    cuerpo_html = f"""
    <div style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #2563eb;">Recuperación de Contraseña</h2>
        <p>Hola <strong>{usuario.nombre_completo}</strong>,</p>
        <p>Hemos recibido una solicitud para restablecer tu contraseña en el Sistema de Estadísticas.</p>
        <p style="margin: 20px 0;">
            <a href="{url_reseteo}" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                Restablecer mi contraseña
            </a>
        </p>
        <p>Si no solicitaste esto, puedes ignorar este correo. El enlace expirará en 1 hora.</p>
        <hr style="border: 0; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #888;">Unidad de TICs - Departamento de Salud</p>
    </div>
    """
    msg.attach(MIMEText(cuerpo_html, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(remitente, contrasena)
            server.send_message(msg)
            print(f"Correo enviado a {usuario.email}")
    except Exception as e:
        print(f"Error enviando correo: {e}")