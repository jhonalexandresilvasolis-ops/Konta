# Konta 

Esta es una Aplicación demo de escritorio para contabilidad general, construida con **Python + Flask** y empaquetada como app nativa usando **pywebview**. Pensada para pequeñas y medianas empresas bajo normativa uruguaya.

---

##  Funcionalidades

- **Libro Diario** — registro de asientos contables con partida doble
- **Libro Mayor** — seguimiento por cuenta individual
- **Cuentas Corrientes** — gestión de clientes y proveedores
- **Libro de Inventario** — control de stock con costo promedio ponderado, fifo y lifo
- **Balances** — Estado de Resultados y Situación Patrimonial
- **Conciliación Bancaria** — comparación entre la registracion del bancario y registros del sistema
- **Cierre Contable** — ciclo completo: refundición de resultados → cierre patrimonial → apertura
- **Multi-empresa** — cada empresa tiene su propia base de datos SQLite independiente
- **Sistema de usuarios y roles** — Alumno / Profesor (Admin) / Desarrollador
- **Plan de cuentas base** — precargado con cuentas según normativa uruguaya

---

##  Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3, Flask |
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript |
| Base de datos | SQLite (una por empresa + una de usuarios) |
| Desktop | pywebview (ventana nativa) |
| Autenticación | Flask-Login + Werkzeug |

---

##  Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/konta.git
cd konta
```

### 2. Crear y activar entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copiá el archivo de ejemplo y completá los valores:

```bash
cp .env.example .env
```

Editá `.env` con tus propios valores (ver sección siguiente).

### 5. Ejecutar la aplicación

```bash
python app.py
```

Se abrirá una ventana de escritorio con la aplicación.

> **Modo desarrollo (navegador):** descomentá `app.run(debug=True, port=5000)` al final de `app.py` y comentá las líneas de pywebview.

---

## ⚙️ Variables de entorno (`.env`)

Creá un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# Clave secreta de Flask (generala con: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=

# Credenciales del usuario desarrollador
DEV_USER=dev_master
DEV_PASS_HASH=          # Hash generado con werkzeug.security.generate_password_hash()

# Token para registro de cuentas de Profesor/Admin
MASTER_TOKEN=

# Contraseña por defecto al resetear un usuario
RESET_DEFAULT_PASS=
```

Para generar el `DEV_PASS_HASH` en la terminal:

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash("tu_contraseña"))
```

---

## 📁 Estructura del proyecto

```
konta/
├── app.py                  # Backend principal (Flask)
├── setup_db.py             # Script para inicializar la base de datos
├── requirements.txt
├── .env                    # Variables de entorno (NO se sube al repo)
├── .env.example            # Plantilla de variables de entorno
├── .gitignore
├── templates/              # Plantillas HTML (Jinja2)
│   ├── base.html
│   ├── balances.html
│   ├── cierre.html
│   └── ...
├── static/
│   ├── css/
│   └── js/
└── datos/                  # Bases de datos de empresas (NO se suben al repo)
```

---

## 👤 Roles de usuario

| Rol | Descripción |
|-----|-------------|
| `user` | Alumno — acceso de lectura y registro de operaciones |
| `admin` | Profesor — gestión de usuarios y grupos |
| `dev` | Desarrollador — acceso total al sistema |

El primer usuario del sistema se registra en `/setup_admin`. Para crear una cuenta de `admin` se requiere el `MASTER_TOKEN` definido en `.env`.

---

