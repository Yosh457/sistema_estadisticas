# 📊 Sistema de Paneles de Estadísticas - Salud MAHO

Sistema web desarrollado para la **Unidad de TICs del Departamento de Salud de la Municipalidad de Alto Hospicio**. Permite la centralización, visualización y gestión segura de paneles de datos (PowerBI) para la toma de decisiones.

## 🚀 Características Principales

* **Visualización Centralizada:** Integración de iframes de PowerBI organizados por Áreas (Rayen, Per Cápita, Call Center, etc.).
* **Gestión de Accesos (RBAC):**
    * **Administrador:** Acceso total, gestión de usuarios, paneles y auditoría.
    * **Lector:** Acceso limitado solo a los grupos y paneles asignados explícitamente.
* **Seguridad:**
    * Protección contra ataques CSRF.
    * Manejo seguro de sesiones y contraseñas (Hash).
    * Forzado de cambio de contraseña en primer inicio.
* **Auditoría Completa:**
    * Registro de logs (Logins, Ediciones, Vistas).
    * **Exportación a Excel (.xlsx):** Reportes nativos con formato profesional.
* **Experiencia de Usuario (UX):**
    * Buscador Global de Paneles.
    * Navegación por migas de pan (Breadcrumbs).
    * Interfaz moderna con TailwindCSS.

## 🛠️ Tecnologías Utilizadas

* **Backend:** Python 3, Flask.
* **Base de Datos:** MySQL (SQLAlchemy ORM).
* **Frontend:** HTML5, Jinja2, TailwindCSS (CDN), JavaScript.
* **Librerías Clave:** `Flask-Login`, `OpenPyXL` (Excel), `Werkzeug`.

## 📂 Estructura del Proyecto

El proyecto sigue una arquitectura modular basada en **Blueprints**:

```text
sistema_estadisticas/
├── blueprints/          # Lógica de rutas (Admin, Auth, Estadísticas)
├── static/              # Imágenes, CSS y JS (Tailwind config, logos)
├── templates/           # Vistas HTML (Jinja2)
├── utils/               # Helpers, Decoradores y Utilidades
├── app.py               # Punto de entrada de la aplicación
├── models.py            # Modelos de Base de Datos
└── requirements.txt     # Dependencias
```
## 🌿 Gestión de Ramas y Despliegue
Este repositorio maneja dos flujos de trabajo distintos:

1. **Rama `main`** (Desarrollo Local / Standalone)
* **Autenticación:** Local (Tabla usuarios interna).

* **Uso:** Para desarrollo, pruebas de nuevas funcionalidades y uso offline.

* **Base de Datos:** Esquema local estadisticas_db.

2. **Rama `produccion-global`** (Despliegue)
* **Autenticación:** Centralizada (Identidad Global).

* **Arquitectura:** Valida credenciales contra una BD externa (mahosalu_usuarios_global) y autoriza permisos localmente.

* **Uso:** Versión productiva desplegada en el Hosting/CPanel.

## ⚙️ Instalación Local

1. Clonar el repositorio:

```bash
git clone https://github.com/Yosh457/sistema_estadisticas.git
cd sistema_estadisticas
```
2. Crear entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```
3. Instalar dependencias:

```bash
pip install -r requirements.txt
```
4. Configurar variables de entorno (.env):

```env
SECRET_KEY=tu_clave_secreta
MYSQL_PASSWORD=tu_password_mysql
EMAIL_USUARIO=tu_correo@gmail.com
EMAIL_CONTRASENA=tu_contraseña_aplicacion
```
5. Ejecutar:

```bash
python app.py
```
---
Desarrollado por **Josting Silva**  
Analista Programador – Unidad de TICs  
Departamento de Salud, Municipalidad de Alto Hospicio
