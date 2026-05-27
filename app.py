import sqlite3
import os
import datetime
import json 
import webview 
import gc
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['DATABASES_FOLDER'] = 'datos'

# ==========================================
# CONFIGURACIÓN DE USUARIOS (FLASK-LOGIN)
# ==========================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Si intentan entrar sin permiso, van al login

# Modelo de Usuario para Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role, group_id): # Agregamos group_id
        self.id = id
        self.username = username
        self.role = role
        self.group_id = group_id

# Función para conectar SOLO a la base de usuarios
def get_users_db():
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar tabla de usuarios si no existe
def init_users_db():
    conn = get_users_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_by TEXT -- Nombre del profe que lo creó
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            group_id INTEGER, -- <--- NUEVO CAMPO
            FOREIGN KEY(group_id) REFERENCES groups(id)
        )
    ''')
    try:
        conn.execute("INSERT INTO groups (name, created_by) VALUES ('General', 'Sistema')")
    except: pass
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_users_db() # Ejecutar al inicio

@login_manager.user_loader
def load_user(user_id):
    # 1. CASO ESPECIAL: EL DIOS (ID 0)
    # Si el ID es 0, reconstruimos al usuario desarrollador manualmente
    if str(user_id) == '0':
        return User(0, "Desarrollador", "dev", None)

    # 2. CASO NORMAL: Buscar en Base de Datos
    conn = get_users_db()
    try:
        user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    except:
        return None
    finally:
        conn.close()
        
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['role'], user_data['group_id'])
    
    return None

@app.route('/reset_password/<int:user_id>')
@login_required
def reset_password(user_id):
    # Solo el DEV puede hacer esto (Poder absoluto)
    if current_user.role != 'dev':
        flash('Acceso denegado. Solo para Dios.', 'error')
        return redirect(url_for('gestor_usuarios'))
    
    conn = get_users_db()
    try:
        user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
        if user:
            # La contraseña maestra será siempre "1234"
            new_pass_hash = generate_password_hash(os.environ.get('RESET_DEFAULT_PASS', 'Cambiar1234!'))
            
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_pass_hash, user_id))
            conn.commit()
            flash(f'¡Contraseña de {user["username"]} restablecida a "1234"!', 'success')
        else:
            flash('Usuario no encontrado.', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('gestor_usuarios'))


@app.route('/activacion')
def activacion():
    # Mostramos el HW ID para que el usuario te lo dicte
    hw_id = "LICENCIA-DESACTIVADA-LOCAL"
    return render_template('activacion.html', hw_id=hw_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('lobby'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

       
        DEV_USER = os.environ.get('DEV_USER')
        DEV_PASS = os.environ.get('DEV_PASS_HASH')
        # CORRECCIÓN 1: Usamos check_password_hash para que funcione tu contraseña normal
        if username == DEV_USER and check_password_hash(DEV_PASS, password):
            
            # CORRECCIÓN 2: Agregamos ', None' al final para cumplir con los 4 datos (id, user, role, group_id)
            user = User(0, "Desarrollador", "dev", None) 
            
            login_user(user)
            flash('⚡ MODO DIOS ACTIVADO: Bienvenido Creador.', 'success')
            return redirect(url_for('lobby'))
        
       
        # 2. LOGIN NORMAL (Base de Datos)
        conn = get_users_db()
        user_data = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'], user_data['role'], user_data['group_id'])
            login_user(user)
            return redirect(url_for('lobby'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            
    return render_template('login.html')

# En app.py

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('lobby'))
    
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        # 1. Recibimos el NOMBRE del grupo, no el ID
        group_name = request.form['group_name'].strip()
        
        if not username or not password or not group_name:
            flash('Faltan datos.', 'error')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        
        conn = get_users_db()
        try:
            # 2. LÓGICA "BUSCAR O CREAR" GRUPO
            # Normalizamos el nombre (mayúsculas) para evitar duplicados como "3ba" y "3BA"
            group_name_norm = group_name.upper()
            
            # Buscamos si ya existe
            grupo = conn.execute('SELECT id FROM groups WHERE name = ?', (group_name_norm,)).fetchone()
            
            if grupo:
                # Si existe, usamos su ID
                group_id = grupo['id']
            else:
                # Si NO existe, lo creamos ahora mismo
                cur = conn.execute('INSERT INTO groups (name, created_by) VALUES (?, ?)', 
                                   (group_name_norm, 'Auto-Registro'))
                group_id = cur.lastrowid # Recuperamos el ID del nuevo grupo
            
            # 3. CREAR AL USUARIO CON ESE GROUP_ID
            conn.execute('INSERT INTO users (username, password_hash, role, group_id) VALUES (?, ?, ?, ?)', 
                         (username, hashed_pw, 'user', group_id))
            
            conn.commit()
            flash(f'¡Cuenta creada! Te has unido al grupo "{group_name_norm}".', 'success')
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError:
            flash(f'El usuario "{username}" ya existe. Elige otro.', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        finally:
            conn.close()

    return render_template('register.html')
@app.route('/logout')
@login_required
def logout():
    # Limpiamos sesión de la empresa actual también
    session.pop('db_path', None)
    session.pop('empresa_nombre', None)
    logout_user()
    flash('Sesión cerrada.', 'success')
    return redirect(url_for('login'))

@app.route('/setup_admin', methods=['GET', 'POST'])
def setup_admin():
    conn = get_users_db()
    
    try:
        # 1. VERIFICAR SI YA HAY USUARIOS (Lógica existente)
        count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        if count > 0:
            return redirect(url_for('login'))
        
        # 2. PROCESAR FORMULARIO
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            role_request = request.form['role_request'] # 'admin' o 'user'
            codigo_ingresado = request.form.get('codigo_maestro', '')

            hashed_pw = generate_password_hash(password)
            
            # --- LÓGICA DE VALIDACIÓN DE ROL ---
            role_final = 'user' # Por defecto todos son alumnos
            
            # CÓDIGO MAESTRO DE TU EMPRESA DE SOFTWARE
            # Este es el código que tú le das a los profesores cuando compran la licencia "Teacher".
            MASTER_TOKEN = os.environ.get('MASTER_TOKEN')

            if role_request == 'admin':
                if codigo_ingresado == MASTER_TOKEN:
                    role_final = 'admin'
                else:
                    flash('⛔ Código de Centro incorrecto. Se ha creado una cuenta de ALUMNO.', 'warning')
                    role_final = 'user'
            
            # Insertamos el usuario con el rol decidido
            conn.execute('''
                INSERT INTO users (username, password_hash, role, group_id) 
                VALUES (?, ?, ?, ?)
            ''', (username, hashed_pw, role_final, 1))
            
            conn.commit()
            
            if role_final == 'admin':
                flash('¡Cuenta de PROFESOR creada con éxito!', 'success')
            else:
                flash('¡Cuenta de ALUMNO creada con éxito!', 'success')
                
            return redirect(url_for('login'))
            
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()
            
    return render_template('setup.html')
# --- ESQUEMA SQL PARA NUEVAS EMPRESAS ---

SCHEMA_SQL = """
/* ==========================================================================
   ESTRUCTURA DE TABLAS (SISTEMA CONTABLE)
   ========================================================================== */

CREATE TABLE IF NOT EXISTS cuentas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL,         -- 'Activo', 'Pasivo', 'Patrimonio', 'Ganancia', 'Pérdida'
    recibe_saldo BOOLEAN DEFAULT 1, -- 1=Imputable (Hija), 0=Agrupadora (Padre)
    descripcion TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS asientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    leyenda TEXT NOT NULL,
    descripcion TEXT,
    currency TEXT DEFAULT 'UYU',
    exchange_rate REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    rut TEXT,
    tipo TEXT NOT NULL, -- 'CLIENTE' o 'PROVEEDOR'
    telefono TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_asiento INTEGER NOT NULL,
    id_cuenta INTEGER NOT NULL,
    debe REAL DEFAULT 0,
    haber REAL DEFAULT 0,
    debe_org REAL DEFAULT 0,
    haber_org REAL DEFAULT 0,
    conciliado BOOLEAN DEFAULT 0, 
    id_conciliacion INTEGER,
    id_entidad INTEGER,         
    fecha_vencimiento TEXT,
    FOREIGN KEY(id_asiento) REFERENCES asientos(id),
    FOREIGN KEY(id_cuenta) REFERENCES cuentas(id)
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    stock_actual REAL DEFAULT 0,
    costo_promedio REAL DEFAULT 0,  
    precio_venta REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS movimientos_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    id_producto INTEGER NOT NULL,
    concepto TEXT NOT NULL, 
    tipo_movimiento TEXT NOT NULL, 
    cantidad REAL NOT NULL,
    costo_unitario REAL DEFAULT 0, 
    id_asiento INTEGER, 
    FOREIGN KEY(id_producto) REFERENCES productos(id)
);

CREATE TABLE IF NOT EXISTS tasas_iva (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    valor REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS conciliaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cuenta INTEGER NOT NULL,
    fecha_corte TEXT NOT NULL,
    saldo_banco REAL DEFAULT 0,
    estado TEXT DEFAULT 'ABIERTA'
);

CREATE TABLE IF NOT EXISTS items_extracto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_conciliacion INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    concepto TEXT NOT NULL,
    debe REAL DEFAULT 0,
    haber REAL DEFAULT 0,
    conciliado BOOLEAN DEFAULT 0,
    id_mov_sistema INTEGER,
    FOREIGN KEY(id_conciliacion) REFERENCES conciliaciones(id)
);

/* NUEVAS TABLAS FASE 3: PLANTILLAS */
CREATE TABLE IF NOT EXISTS plantillas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS plantillas_detalle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_plantilla INTEGER NOT NULL,
    id_cuenta INTEGER NOT NULL,
    lado TEXT NOT NULL,
    FOREIGN KEY(id_plantilla) REFERENCES plantillas(id) ON DELETE CASCADE,
    FOREIGN KEY(id_cuenta) REFERENCES cuentas(id)
);

CREATE TABLE IF NOT EXISTS comprobantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo TEXT DEFAULT 'interno' -- 'fiscal_compra', 'fiscal_venta', 'interno', etc.
);

/* ==========================================================================
   PLAN DE CUENTAS BASE (NORMATIVA URUGUAY DEC. 103/91 + NIIF PYMES)
   Estructura Jerárquica: Clase.Capítulo.Rubro.Cuenta
   ========================================================================== */

/* --------------------------------------------------------------------------
   1. ACTIVO
   -------------------------------------------------------------------------- */

/* 1.1.1.xx -> DISPONIBILIDADES (Caja y Bancos) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('1.1.1.01', 'Caja M/N', 'Activo', 'Dinero en efectivo en moneda nacional disponible en la empresa.'),
('1.1.1.02', 'Caja M/E', 'Activo', 'Dinero en efectivo en moneda extranjera (ej. dólares) disponible en caja.'),
('1.1.1.03', 'Banco Cuenta Corriente M/N', 'Activo', 'Saldos a favor en cuentas bancarias en moneda nacional de disponibilidad inmediata.'),
('1.1.1.04', 'Banco Cuenta Corriente M/E', 'Activo', 'Saldos a favor en cuentas bancarias en moneda extranjera de disponibilidad inmediata.'),
('1.1.1.05', 'Fondo Fijo', 'Activo', 'Monto fijo asignado para cubrir gastos menores diarios en efectivo, sujeto a rendición.');

/* 1.1.2.xx -> CRÉDITOS POR VENTAS (Deudores Comerciales) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('1.1.2.01', 'Deudores por Ventas', 'Activo', 'Derechos de cobro contra clientes por ventas a crédito en cuenta corriente.'),
('1.1.2.02', 'Documentos a Cobrar', 'Activo', 'Derechos de cobro respaldados por documentos formales firmados (vales o conformes).'),
('1.1.2.03', 'Deudores Morosos', 'Activo', 'Clientes con atrasos significativos en sus pagos, fuera de los plazos normales acordados.'),
('1.1.2.04', 'Cheques Diferidos a Cobrar', 'Activo', 'Cheques de pago diferido recibidos de terceros que aún están pendientes de vencimiento.'),
('1.1.2.99', 'Previsión p/Deudores Incobrables', 'Activo', 'Cuenta regularizadora. Estima el riesgo de incobrabilidad de los créditos según análisis de la cartera.'); /* Regularizadora */

/* 1.1.3.xx -> CRÉDITOS DIVERSOS (Fiscales y Otros) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('1.1.3.01', 'IVA Compras', 'Activo', 'Crédito fiscal a favor de la empresa por el IVA pagado en compras y servicios.'),
('1.1.3.02', 'Anticipos a Proveedores', 'Activo', 'Pagos entregados por adelantado a proveedores a cuenta de futuras compras.'),
('1.1.3.03', 'Anticipo de IRPF/IRAE', 'Activo', 'Pagos a cuenta y retenciones sufridas a favor de la empresa ante la DGI.');

/* 1.1.4.xx -> BIENES DE CAMBIO (Inventarios - NIIF Sec. 13) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('1.1.4.01', 'Mercaderías de Reventa', 'Activo', 'Stock físico disponible en depósitos locales. Artículos listos para entrega al cliente.'),
('1.1.4.02', 'Importaciones en Trámite', 'Activo', 'Acumulador de costos (FOB/CIF, fletes, seguros, aduana) de mercadería no nacionalizada.'), /* Acumulador de costos de importación */
('1.1.4.99', 'Previsión por Desvalorización de Stock', 'Activo', 'Cuenta regularizadora. Ajuste para reflejar pérdidas de valor u obsolescencia del inventario.');

/* 1.2.1.xx -> ACTIVO NO CORRIENTE (Bienes de Uso - Propiedad, Planta y Equipo) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('1.2.1.01', 'Muebles y Útiles', 'Activo', 'Mobiliario y equipamiento general de oficina destinado a la operativa de la empresa.'),
('1.2.1.02', 'Equipos de Computación', 'Activo', 'Hardware, computadoras, impresoras y servidores utilizados de forma permanente.'),
('1.2.1.03', 'Rodados', 'Activo', 'Vehículos o camiones propiedad de la empresa utilizados para logística o administración.'),
('1.2.1.04', 'Inmuebles', 'Activo', 'Locales, terrenos o edificios que son propiedad de la entidad comercial.'),
('1.2.1.99', 'Amortizaciones Acumuladas', 'Activo', 'Cuenta regularizadora global que acumula la pérdida de valor por desgaste de los bienes de uso.'); /* Regularizadora Global */

/* --------------------------------------------------------------------------
   2. PASIVO
   -------------------------------------------------------------------------- */

/* 2.1.1.xx -> DEUDAS COMERCIALES (Proveedores) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('2.1.1.01', 'Acreedores por Compras (Proveedores)', 'Pasivo', 'Obligaciones de pago con proveedores por la compra de mercaderías o insumos a crédito.'),
('2.1.1.02', 'Documentos a Pagar', 'Pasivo', 'Deudas comerciales documentadas y respaldadas mediante la firma de vales o conformes.'),
('2.1.1.03', 'Cheques Diferidos a Pagar', 'Pasivo', 'Cheques de pago diferido emitidos por la empresa pendientes de cobro por parte de terceros.');

/* 2.1.2.xx -> DEUDAS FINANCIERAS (Bancos) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('2.1.2.01', 'Vales Bancarios a Pagar', 'Pasivo', 'Obligaciones de corto plazo contraídas con instituciones financieras respaldadas por vales.'),
('2.1.2.02', 'Préstamos Bancarios Corrientes', 'Pasivo', 'Porción del capital de préstamos bancarios a vencer dentro de los próximos 12 meses.');

/* 2.1.3.xx -> DEUDAS SOCIALES Y FISCALES (El corazón de la liquidación) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('2.1.3.01', 'BPS a Pagar', 'Pasivo', 'Centraliza obligaciones con seguridad social (aportes personales retenidos y patronales).'), /* Aportes Personales + Patronales */
('2.1.3.02', 'BSE a Pagar', 'Pasivo', 'Deuda mensual por el seguro obligatorio de accidentes de trabajo.'), /* Seguro de Accidentes */
('2.1.3.03', 'Sueldos a Pagar', 'Pasivo', 'Remuneraciones líquidas pendientes de pago a los empleados.'), /* Líquido a pagar al empleado */
('2.1.3.04', 'IRPF a Pagar', 'Pasivo', 'Impuesto de retención mensual que grava la renta del trabajador. Deuda directa con DGI.'), /* Retenciones IRPF Cat II */
('2.1.3.05', 'Provisión para Aguinaldo', 'Pasivo', 'Beneficio acumulado por tiempo trabajado. Provisión de la cuota parte del sueldo anual complementario.'), /* Pasivo Contingente */
('2.1.3.06', 'Provisión para Salario Vacacional', 'Pasivo', 'Beneficio vinculado al goce de la licencia. Provisión proporcional para pago de vacaciones.'),
('2.1.3.07', 'IVA Ventas', 'Pasivo', 'Débito fiscal. Obligación de pago a DGI por el IVA facturado a clientes en comprobantes.'), /* Débito Fiscal */
('2.1.3.08', 'DGI a Pagar', 'Pasivo', 'Saldo neto a pagar a la Dirección General Impositiva resultante de la liquidación de impuestos.'); /* Saldo final de IVA/IRAE */

/* --------------------------------------------------------------------------
   3. PATRIMONIO
   -------------------------------------------------------------------------- */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('3.1.1.01', 'Capital Social', 'Patrimonio', 'Aportes formalmente integrados por los dueños o accionistas de la empresa.'),
('3.1.1.02', 'Ajuste al Capital', 'Patrimonio', 'Ajustes contables para el mantenimiento del capital o revaluaciones.'),
('3.1.2.01', 'Resultados Acumulados', 'Patrimonio', 'Ganancias o pérdidas de ejercicios económicos anteriores que no han sido distribuidas.'),
('3.1.3.01', 'Resultado del Ejercicio', 'Patrimonio', 'Pérdida o ganancia neta obtenida exclusivamente en el ejercicio económico actual.');

/* --------------------------------------------------------------------------
   4. INGRESOS (GANANCIAS)
   -------------------------------------------------------------------------- */

/* 4.1.1.xx -> INGRESOS OPERATIVOS */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('4.1.1.01', 'Ventas de Mercaderías (Plaza)', 'Ganancia', 'Ingresos operativos derivados de la venta de bienes en el mercado interno.'),
('4.1.1.02', 'Ventas de Servicios', 'Ganancia', 'Ingresos operativos generados por la prestación de servicios a terceros.'),
('4.1.1.03', 'Exportaciones', 'Ganancia', 'Ingresos por ventas de bienes o servicios al mercado internacional.');

/* 4.1.2.xx -> INGRESOS FINANCIEROS Y VARIOS */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('4.1.2.01', 'Diferencia de Cambio Ganada', 'Ganancia', 'Ingreso financiero originado por fluctuaciones favorables en la cotización de la moneda extranjera.'),
('4.1.2.02', 'Descuentos Obtenidos', 'Ganancia', 'Ingresos por rebajas o descuentos financieros logrados por pronto pago a proveedores.'),
('4.1.2.03', 'Intereses Ganados', 'Ganancia', 'Rendimientos financieros a favor de la empresa por mora de clientes o colocaciones bancarias.');

/* --------------------------------------------------------------------------
   5. EGRESOS (PÉRDIDAS)
   -------------------------------------------------------------------------- */

/* 5.1.1.xx -> COSTOS OPERATIVOS */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('5.1.1.01', 'Costo de Ventas (CMV)', 'Pérdida', 'Costo directo de adquisición o producción de la mercadería que ha sido vendida.');

/* 5.1.2.xx -> GASTOS DE PERSONAL (Desglose Profesional) */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('5.1.2.01', 'Sueldos y Jornales', 'Pérdida', 'Remuneración nominal bruta por tiempo trabajado. Gasto del ejercicio.'), /* Nominal */
('5.1.2.02', 'Aportes Patronales (Leyes Sociales)', 'Pérdida', 'Costo de seguridad social a cargo del empleador (ej. jubilación, FONASA, FRL).'), /* Gasto Empresa */
('5.1.2.03', 'Seguros de Accidentes (BSE)', 'Pérdida', 'Prima mensual por cobertura de accidentes pagada al BSE. Gasto operativo obligatorio.'), /* Gasto Empresa */
('5.1.2.04', 'Aguinaldos', 'Pérdida', 'Provisión mensual (1/12 del nominal) del sueldo anual complementario. Gasto devengado.'), /* Gasto devengado mensual */
('5.1.2.05', 'Salario Vacacional', 'Pérdida', 'Gasto devengado mensual proporcional para el futuro pago de licencias al personal.'); /* Gasto devengado mensual */

/* 5.1.3.xx -> GASTOS DE ADMINISTRACIÓN Y VENTAS */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('5.1.3.01', 'Gastos Generales', 'Pérdida', 'Gastos menores de administración y ventas que no justifican una cuenta específica.'),
('5.1.3.02', 'Alquileres Cedidos', 'Pérdida', 'Gastos por arrendamiento de locales, oficinas o depósitos comerciales.'),
('5.1.3.03', 'UTE / OSE / ANTEL', 'Pérdida', 'Gastos por consumos de energía eléctrica, agua, telefonía e internet.'),
('5.1.3.04', 'Honorarios Profesionales', 'Pérdida', 'Gastos por servicios prestados por profesionales independientes (contadores, abogados, etc).'),
('5.1.3.05', 'Papelería y Útiles', 'Pérdida', 'Gastos en insumos de oficina, resmas, tinta y papelería general.'),
('5.1.3.06', 'Publicidad y Propaganda', 'Pérdida', 'Inversiones en marketing, redes sociales, diseño o publicidad tradicional.'),
('5.1.3.07', 'Descuentos Concedidos', 'Pérdida', 'Gasto por rebajas o descuentos financieros otorgados a clientes por pronto pago.');

/* 5.1.4.xx -> GASTOS FINANCIEROS */
INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES 
('5.1.4.01', 'Diferencia de Cambio Perdida', 'Pérdida', 'Gasto financiero originado por fluctuaciones desfavorables en el tipo de cambio.'),
('5.1.4.02', 'Gastos Bancarios y Comisiones', 'Pérdida', 'Cargos cobrados por instituciones financieras por mantenimiento de cuentas o transferencias.'),
('5.1.4.03', 'Intereses Perdidos', 'Pérdida', 'Gastos financieros incurridos por préstamos bancarios, sobregiros o financiación de proveedores.');

/* ==========================================================================
   DATOS BASE: COMPROBANTES
   ========================================================================== */
INSERT INTO comprobantes (nombre, tipo) VALUES 
('Factura Contado', 'fiscal_venta'),
('Factura Crédito', 'fiscal_venta'),
('Nota de Crédito', 'fiscal_venta'),
('Recibo de Cobro', 'interno'),
('Recibo de Pago', 'interno'),
('Boleta de Depósito', 'interno'),
('Comprobante Interno', 'interno'),
/* Nuevos Comprobantes de Sueldos */
('X Aporte Obrero', 'interno'),
('X Aporte Patronal', 'interno'),
('X Aporte Ficto Patronal', 'interno');

/* ==========================================================================
   DATOS BASE: TASAS DE IVA (Uruguay)
   ========================================================================== */
INSERT INTO tasas_iva (nombre, valor) VALUES 
('IVA Básico (22%)', 0.22),
('IVA Mínimo (10%)', 0.10),
('Exento (0%)', 0.00);

"""

@app.template_filter('formato_kardex')
def formato_kardex(valor):
    if valor is None or valor == '': return ""
    try:
        val = float(valor)
        if val == 0: return "-"
        
        # Formato básico
        if val.is_integer(): texto = "{:.0f}".format(abs(val))
        else: texto = "{:.2f}".format(abs(val)).rstrip('0').rstrip('.')
        
        # Paréntesis para negativos (Devoluciones)
        if val < 0: return f"({texto})"
        return texto
    except: return valor

# --- FILTRO CONTABLE (Tu versión mejorada) ---
@app.template_filter('formato_contable')
def formato_contable(valor):
    if valor is None: return ""
    try:
        val = float(valor)
        abs_val = abs(val)
        if abs_val.is_integer(): texto = "{:.0f}".format(abs_val)
        else: texto = "{:.2f}".format(abs_val).rstrip('0').rstrip('.')
        texto = texto.replace('.', ',')
        if val < 0: return f"({texto})"
        return texto
    except ValueError: return valor

def migrar_db_multimoneda(conn):
    """Actualiza la estructura de la BD para soportar multimoneda en tablas 'asientos' y 'movimientos'."""
    try:
        # 1. Revisar tabla ASIENTOS
        cursor = conn.execute("PRAGMA table_info(asientos)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'currency' not in columnas:
            print("Migrando tabla asientos a multimoneda...")
            conn.execute("ALTER TABLE asientos ADD COLUMN currency TEXT DEFAULT 'UYU'")
            conn.execute("ALTER TABLE asientos ADD COLUMN exchange_rate REAL DEFAULT 1.0")
        
        # 2. Revisar tabla MOVIMIENTOS
        cursor = conn.execute("PRAGMA table_info(movimientos)")
        columnas_lineas = [col[1] for col in cursor.fetchall()]
        
        if 'debe_org' not in columnas_lineas:
            print("Migrando tabla movimientos a multimoneda...")
            conn.execute("ALTER TABLE movimientos ADD COLUMN debe_org REAL DEFAULT 0")
            conn.execute("ALTER TABLE movimientos ADD COLUMN haber_org REAL DEFAULT 0")
            conn.execute("UPDATE movimientos SET debe_org = debe, haber_org = haber")

        # Definimos las cuentas que SÍ O SÍ deben estar
        cuentas_requeridas = [
            ('4.1.02', 'Diferencia de Cambio Ganada', 'Ganancia'),
            ('5.1.03', 'Diferencia de Cambio Perdida', 'Pérdida'),
            ('3.3.01', 'Resultado del Ejercicio', 'Patrimonio'),
            ('3.3.02', 'Resultados de Ejercicios Anteriores', 'Patrimonio')
        ]

        for codigo, nombre, tipo in cuentas_requeridas:
            # Preguntamos: ¿Existe ya una cuenta con este código?
            existe = conn.execute('SELECT id FROM cuentas WHERE codigo = ?', (codigo,)).fetchone()
            
            if not existe:
                print(f"Inyectando cuenta faltante: {nombre}")
                conn.execute('INSERT INTO cuentas (codigo, nombre, tipo) VALUES (?, ?, ?)', 
                             (codigo, nombre, tipo))    
            
        conn.commit()
        # 3. Revisar tabla CUENTAS para agregar descripciones
        cursor = conn.execute("PRAGMA table_info(cuentas)")
        columnas_cuentas = [col[1] for col in cursor.fetchall()]
        
        if 'descripcion' not in columnas_cuentas:
            print("Migrando tabla cuentas para agregar descripciones...")
            conn.execute("ALTER TABLE cuentas ADD COLUMN descripcion TEXT DEFAULT 'Sin descripción asignada.'")
    except Exception as e:
        print(f"Error en migración: {e}")

# --- NUEVA FUNCIÓN DE CONEXIÓN (La clave del sistema Multi-Empresa) ---
def get_db_connection():
    # Intenta leer qué empresa eligió el usuario
    db_name = session.get('db_path')
    if not db_name:
        return None # No hay empresa seleccionada
    
    db_path = os.path.join(app.config['DATABASES_FOLDER'], db_name)

    if not os.path.exists(db_path):
        return None
    
   
    conn = sqlite3.connect(db_path, timeout=20)
    conn.row_factory = sqlite3.Row
    migrar_db_multimoneda(conn)
    return conn

# --- MOTOR DE CÁLCULO DE KARDEX (FIFO, LIFO, PMP) ---
def calcular_kardex(movimientos, metodo='PMP'):
    filas = []
    # Inventario: Lista de lotes [(cantidad, costo_unitario), ...]
    inventario = [] 
    
    saldo_cnt = 0
    saldo_total = 0

    for m in movimientos:
        fecha = m['fecha']
        concepto = m['concepto']
        tipo = m['tipo_movimiento']
        cant = m['cantidad']
        costo_u_mov = m['costo_unitario'] if m['costo_unitario'] else 0
        
        # Estructura de la fila para la tabla visual (11 columnas)
        fila = {
            'id': m['id'],
            'fecha': fecha,
            'concepto': concepto,
            'ent_cant': None, 'ent_cu': None, 'ent_ct': None,
            'sal_cant': None, 'sal_cu': None, 'sal_ct': None,
            'saldo_cant': 0, 'saldo_cu': 0, 'saldo_ct': 0
        }

        # --- LOGICA DE ENTRADAS (Compras / Devoluciones de Venta) ---
        if tipo == 'ENTRADA':
            # Si es devolución (cantidad negativa visualmente, pero suma al stock)
            # Asumimos que en la DB se guarda positivo y el concepto dice "Devolución"
            
            ct_mov = cant * costo_u_mov
            
            fila['ent_cant'] = cant
            fila['ent_cu'] = costo_u_mov
            fila['ent_ct'] = ct_mov

            # Actualizar Saldo General
            saldo_cnt += cant
            saldo_total += ct_mov
            
            # Actualizar Inventario según método
            if metodo == 'PMP':
                # En PMP no guardamos lotes, solo acumulamos
                pass 
            else:
                # FIFO/LIFO: Guardamos el lote
                inventario.append({'c': cant, 'p': costo_u_mov})

        # --- LOGICA DE SALIDAS (Ventas / Devoluciones de Compra) ---
        elif tipo == 'SALIDA':
            costo_salida_total = 0
            cant_pendiente = cant
            
            if metodo == 'PMP':
                # Costo Promedio = Saldo Total / Saldo Cantidad (ANTES de la salida)
                cpp = saldo_total / saldo_cnt if saldo_cnt > 0 else 0
                costo_salida_total = cant * cpp
                fila['sal_cu'] = cpp # El costo de salida es el promedio actual
                
            elif metodo in ['FIFO', 'LIFO']:
                # Consumir lotes
                costo_salida_acumulado = 0
                
                while cant_pendiente > 0 and inventario:
                    # Seleccionar lote según método
                    idx = 0 if metodo == 'FIFO' else -1
                    lote = inventario[idx]
                    
                    if lote['c'] > cant_pendiente:
                        # El lote alcanza y sobra
                        costo_salida_acumulado += cant_pendiente * lote['p']
                        lote['c'] -= cant_pendiente # Reducimos el lote
                        cant_pendiente = 0
                    else:
                        # El lote se acaba, pasamos al siguiente
                        costo_salida_acumulado += lote['c'] * lote['p']
                        cant_pendiente -= lote['c']
                        inventario.pop(idx) # Eliminamos lote agotado
                
                costo_salida_total = costo_salida_acumulado
                # Calculamos el Costo Unitario Promedio de esta salida específica para mostrarlo
                fila['sal_cu'] = costo_salida_total / cant if cant > 0 else 0

            fila['sal_cant'] = cant
            fila['sal_ct'] = costo_salida_total
            
            # Actualizar Saldos
            saldo_cnt -= cant
            saldo_total -= costo_salida_total

        # --- LLENAR COLUMNAS DE SALDO ---
        fila['saldo_cant'] = saldo_cnt
        fila['saldo_ct'] = saldo_total
        
        # Costo Unitario del Saldo (Siempre PMP para visualización)
        fila['saldo_cu'] = saldo_total / saldo_cnt if saldo_cnt > 0 else 0
        
        filas.append(fila)

    return filas
# =======================================================
#  RUTAS DE GESTIÓN (LOBBY Y CREACIÓN DE EMPRESAS)
# =======================================================

# En app.py

@app.route('/')
@login_required
def lobby():
    if session.get('db_path'):
        filepath = os.path.join(app.config['DATABASES_FOLDER'], session.get('db_path'))
        
        if os.path.exists(filepath):
            return redirect(url_for('dashboard'))
        else:
            session.pop('db_path', None)
            session.pop('empresa_nombre', None)

    # Variables de control
    es_dev = (current_user.role == 'dev')
    es_admin = (current_user.role == 'admin')
    mi_grupo = current_user.group_id if current_user.group_id else 0
    mi_user = "".join([c for c in current_user.username if c.isalnum()]).lower()

    # --- NUEVO: MAPA DE NOMBRES REALES ---
    # Traemos los nombres bonitos ("Alumno A") para no mostrar los feos ("alumnoa")
    conn_users = get_users_db()
    all_users = conn_users.execute('SELECT username FROM users').fetchall()
    conn_users.close()
    
    user_map = {}
    for u in all_users:
        # Replicamos la misma lógica de limpieza para poder cruzar los datos
        safe_key = "".join([c for c in u['username'] if c.isalnum()]).lower()
        user_map[safe_key] = u['username'] # Guardamos: "alumnoa" -> "Alumno A"
    # -------------------------------------

    archivos = [f for f in os.listdir(app.config['DATABASES_FOLDER']) if f.endswith('.db')]
    empresas = []

    for f in archivos:
        parts = f.replace('.db', '').split('_')
        
        if len(parts) < 3: continue 

        archivo_grupo = parts[0]
        archivo_user = parts[1] # Aquí viene "alumnoa"
        archivo_nombre = "_".join(parts[2:])
        
        mostrar = False
        
        if es_dev:
            mostrar = True
        elif es_admin:
            if archivo_grupo == f"g{mi_grupo}":
                mostrar = True
        else:
            if archivo_grupo == f"g{mi_grupo}" and archivo_user == mi_user:
                mostrar = True
        
        if mostrar:
            # --- CORRECCIÓN: Usamos el mapa para recuperar el nombre real ---
            nombre_propietario = user_map.get(archivo_user.lower(), archivo_user)
            # Si encuentra "alumnoa", pone "Alumno A". Si no, deja "alumnoa".

            empresas.append({
                'archivo': f,
                'nombre': archivo_nombre.replace('_', ' ').title(),
                'owner': nombre_propietario, # ¡Aquí va el nombre arreglado!
                'es_mio': (archivo_user == mi_user)
            })

    return render_template('lobby.html', empresas=empresas)

# En app.py

@app.route('/crear_empresa', methods=['POST'])
@login_required
def crear_empresa():
    nombre = request.form.get('nombre_empresa').strip()
    if not nombre:
        flash('El nombre no puede estar vacío', 'error')
        return redirect(url_for('lobby'))
    
    # Sanitización del nombre
    safe_name = "".join([c for c in nombre if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_').lower()
    
    # Prefijos de propiedad
    grupo_id = current_user.group_id if current_user.group_id else 0
    safe_user = "".join([c for c in current_user.username if c.isalnum()]).lower()
    
    filename = f"g{grupo_id}_{safe_user}_{safe_name}.db"
    filepath = os.path.join(app.config['DATABASES_FOLDER'], filename)
    
    if os.path.exists(filepath):
        flash('Ya existe una empresa con ese nombre en tu grupo.', 'error')
    else:
        conn = None  # Inicializamos la variable fuera
        try:
            conn = sqlite3.connect(filepath)
            conn.executescript(SCHEMA_SQL)

            try:
                  # Función auxiliar para buscar el ID de la cuenta por su código (Más seguro que por nombre)
                  def get_id(cod):
                      res = conn.execute("SELECT id FROM cuentas WHERE codigo = ?", (cod,)).fetchone()
                      return res[0] if res else None

                  # 1. Plantilla: Liquidación de IVA
                  conn.execute("INSERT INTO plantillas (nombre, descripcion) VALUES ('Liquidación de IVA', 'Cierre mensual de IVA')")
                  id_iva = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                  if get_id('2.1.3.07') and get_id('1.1.3.01'):
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'DEBE')", (id_iva, get_id('2.1.3.07'))) # IVA Ventas
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'HABER')", (id_iva, get_id('1.1.3.01'))) # IVA Compras

                  # 2. Plantilla: Liquidación de Sueldos
                  conn.execute("INSERT INTO plantillas (nombre, descripcion) VALUES ('Liquidación de Sueldos', 'Liquidación mensual de haberes y leyes sociales')")
                  id_sueldos = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                  if get_id('5.1.2.01') and get_id('2.1.3.01') and get_id('2.1.3.03'):
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'DEBE')", (id_sueldos, get_id('5.1.2.01'))) # Sueldos y Jornales
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'DEBE')", (id_sueldos, get_id('5.1.2.02'))) # Aportes Patronales (Opcional llenarlo o dejarlo en 0)
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'HABER')", (id_sueldos, get_id('2.1.3.01'))) # BPS a Pagar
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'HABER')", (id_sueldos, get_id('2.1.3.03'))) # Sueldos a Pagar

                  # 3. Plantilla: Compra de Mercadería a Crédito
                  conn.execute("INSERT INTO plantillas (nombre, descripcion) VALUES ('Compra de Mercadería (Crédito)', 'Ingreso de stock con factura a pagar')")
                  id_compra = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                  if get_id('1.1.4.01') and get_id('1.1.3.01') and get_id('2.1.1.01'):
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'DEBE')", (id_compra, get_id('1.1.4.01'))) # Mercaderías
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'DEBE')", (id_compra, get_id('1.1.3.01'))) # IVA Compras
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'HABER')", (id_compra, get_id('2.1.1.01'))) # Acreedores por Compras

                  # 4. Plantilla: Pago de Sueldos
                  conn.execute("INSERT INTO plantillas (nombre, descripcion) VALUES ('Pago de Sueldos (Efectivo)', 'Abono de los sueldos líquidos al personal')")
                  id_pago = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                  if get_id('2.1.3.03') and get_id('1.1.1.01'):
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'DEBE')", (id_pago, get_id('2.1.3.03'))) # Sueldos a Pagar
                      conn.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, 'HABER')", (id_pago, get_id('1.1.1.01'))) # Caja M/N

            except Exception as e:
                  print(f"Error inyectando plantillas predefinidas: {e}")
            
            conn.commit()
            # Si llega aquí, todo salió bien
            conn.close() 
            flash(f'Empresa "{nombre}" creada exitosamente.', 'success')
        except Exception as e:
            # Si hubo error (ej: sintaxis), mostramos mensaje
            flash(f'Error al crear empresa: {str(e)}', 'error')
        finally:
            # BLOQUE DE SEGURIDAD: Esto se ejecuta SIEMPRE, haya error o no.
            if conn:
                conn.close()
            
            # Si falló la creación (el archivo existe pero está vacío o roto), lo borramos para no dejar basura
            # (Solo si hubo excepción y el archivo se creó mal)
            if 'Error' in str(e) if 'e' in locals() else False:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except:
                    pass # Si no se puede borrar automático, no pasa nada

    return redirect(url_for('lobby'))

@app.route('/api/borrar_plantilla/<int:id_plantilla>', methods=['POST'])
@login_required
def borrar_plantilla(id_plantilla):
    conn = get_db_connection()
    if not conn: return jsonify({'status': 'error', 'msg': 'Error de BD'})
    try:
        # Borramos primero el detalle (las cuentas adentro) y luego la plantilla general
        conn.execute('DELETE FROM plantillas_detalle WHERE id_plantilla = ?', (id_plantilla,))
        conn.execute('DELETE FROM plantillas WHERE id = ?', (id_plantilla,))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        conn.close()

@app.route('/seleccionar_empresa/<archivo>')
def seleccionar_empresa(archivo):
    filepath = os.path.join(app.config['DATABASES_FOLDER'], archivo)
    
    if os.path.exists(filepath):
        session['db_path'] = archivo
        
        # --- CORRECCIÓN VISUAL ---
        # El archivo se llama algo como: "g1_alumnoa_mi_empresa.db"
        # Queremos mostrar solo: "Mi Empresa"
        
        nombre_limpio = archivo.replace('.db', '') # quitamos la extensión
        partes = nombre_limpio.split('_') # separamos por guion bajo
        
        # Si el archivo tiene la estructura estándar (grupo_usuario_nombre...)
        if len(partes) >= 3:
            # Ignoramos las 2 primeras partes (grupo y usuario) y unimos el resto
            nombre_a_mostrar = " ".join(partes[2:]).title()
        else:
            # Si es un archivo viejo o raro, lo mostramos tal cual pero limpio
            nombre_a_mostrar = nombre_limpio.replace('_', ' ').title()
            
        session['empresa_nombre'] = nombre_a_mostrar
        # -------------------------
        
        return redirect(url_for('dashboard'))
    else:
        flash('La empresa seleccionada no existe', 'error')
        return redirect(url_for('lobby'))

@app.route('/borrar_empresa/<archivo>')
def borrar_empresa(archivo):
    filepath = os.path.join(app.config['DATABASES_FOLDER'], archivo)
    gc.collect()
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            if session.get('db_path') == archivo:
                session.pop('db_path', None)
                session.pop('empresa_nombre', None)
            flash('Empresa eliminada', 'success')
        except Exception as e:
            flash(f'Error al eliminar: {str(e)}', 'error')
    return redirect(url_for('lobby'))

@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.pop('db_path', None)
    session.pop('empresa_nombre', None)
    return redirect(url_for('lobby'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # 1. DISPONIBILIDADES (Caja y Bancos)
    # ANTES: LIKE '1.1.%' (Esto agarraba Mercaderías y Créditos también ❌)
    # AHORA: LIKE '1.1.1.%' (Solo el rubro Disponibilidades ✅)
    sql_disp = "SELECT id FROM cuentas WHERE codigo LIKE '1.1.1%'"
    cuentas_disp = conn.execute(sql_disp).fetchall()
    
    total_disponibilidades = 0
    for c in cuentas_disp:
        res = conn.execute("SELECT SUM(debe) as d, SUM(haber) as h FROM movimientos WHERE id_cuenta = ?", (c['id'],)).fetchone()
        d = res['d'] if res['d'] else 0
        h = res['h'] if res['h'] else 0
        total_disponibilidades += (d - h) # Activo: Debe - Haber

    # 2. TOTAL DEUDAS (Pasivo)
    # Esto sigue siendo válido por "Tipo", pero podemos refinarlo si quisieras solo Pasivo Corriente.
    # Por ahora, dejemos TOTAL PASIVO para ser conservadores.
    sql_pasivo = "SELECT id FROM cuentas WHERE tipo = 'Pasivo'"
    cuentas_pasivo = conn.execute(sql_pasivo).fetchall()
    
    total_deudas = 0
    for c in cuentas_pasivo:
        res = conn.execute("SELECT SUM(debe) as d, SUM(haber) as h FROM movimientos WHERE id_cuenta = ?", (c['id'],)).fetchone()
        d = res['d'] if res['d'] else 0
        h = res['h'] if res['h'] else 0
        total_deudas += (h - d) # Pasivo: Haber - Debe

    # 3. LIQUIDEZ NETA (Solvencia inmediata)
    liquidez_neta = total_disponibilidades - total_deudas

    # 4. VENTAS Y GASTOS DEL MES (KPIs Operativos)
    hoy = datetime.date.today()
    mes_actual = hoy.strftime('%Y-%m') 
    
    # Ventas (Ganancia)
    res_ventas = conn.execute("SELECT SUM(m.haber) as total FROM movimientos m JOIN cuentas c ON m.id_cuenta = c.id JOIN asientos a ON m.id_asiento = a.id WHERE c.tipo = 'Ganancia' AND strftime('%Y-%m', a.fecha) = ?", (mes_actual,)).fetchone()
    total_ventas = res_ventas['total'] if res_ventas['total'] else 0

    # Gastos (Pérdida)
    res_gastos = conn.execute("SELECT SUM(m.debe) as total FROM movimientos m JOIN cuentas c ON m.id_cuenta = c.id JOIN asientos a ON m.id_asiento = a.id WHERE c.tipo = 'Pérdida' AND strftime('%Y-%m', a.fecha) = ?", (mes_actual,)).fetchone()
    total_gastos = res_gastos['total'] if res_gastos['total'] else 0

    # 5. RESULTADO DIFERENCIA DE CAMBIO (NUEVOS CÓDIGOS)
    # ANTES: 4.1.02 y 5.1.03
    # AHORA: 4.1.2.01 y 5.1.4.01 (Según tu nuevo Schema)
    
    # Ganancia por DC (4.1.2.01)
    res_dc_gan = conn.execute("SELECT SUM(m.haber) - SUM(m.debe) as t FROM movimientos m JOIN cuentas c ON m.id_cuenta = c.id WHERE c.codigo = '4.1.2.01'").fetchone()
    total_dc_gan = res_dc_gan['t'] if res_dc_gan['t'] else 0
    
    # Pérdida por DC (5.1.4.01)
    res_dc_per = conn.execute("SELECT SUM(m.debe) - SUM(m.haber) as t FROM movimientos m JOIN cuentas c ON m.id_cuenta = c.id WHERE c.codigo = '5.1.4.01'").fetchone()
    total_dc_per = res_dc_per['t'] if res_dc_per['t'] else 0

    dif_cambio = total_dc_gan - total_dc_per

    conn.close()
    
    return render_template('dashboard.html', 
                           empresa=session.get('empresa_nombre'),
                           disp=total_disponibilidades,
                           liquidez_neta=liquidez_neta,
                           ventas=total_ventas,
                           gastos=total_gastos,
                           dif_cambio=dif_cambio)

# =======================================================
#  TUS RUTAS CONTABLES ORIGINALES (CONECTADAS AL SISTEMA)
# =======================================================
@app.route('/kardex/<int:id_producto>', methods=['GET', 'POST'])
@login_required
def ver_kardex(id_producto):
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # Obtener Producto
    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (id_producto,)).fetchone()
    
    # Obtener Método seleccionado (Por defecto PMP)
    metodo = request.args.get('metodo', 'PMP') # PMP, FIFO, LIFO
    
    # Obtener Movimientos Crudos de la DB
    movimientos_db = conn.execute('SELECT * FROM movimientos_stock WHERE id_producto = ? ORDER BY fecha ASC, id ASC', (id_producto,)).fetchall()
    
    # PROCESAR CON EL MOTOR
    filas_kardex = calcular_kardex(movimientos_db, metodo)
    
    conn.close()
    return render_template('kardex.html', producto=producto, filas=filas_kardex, metodo_actual=metodo)

@app.route('/borrar_movimiento/<int:id_movimiento>')
def borrar_movimiento(id_movimiento):
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    id_producto = 0
    try:
        # 1. Obtener datos del movimiento antes de borrar (para saber qué producto es)
        mov = conn.execute('SELECT * FROM movimientos_stock WHERE id = ?', (id_movimiento,)).fetchone()
        if not mov:
            flash('El movimiento no existe.', 'error')
            return redirect(url_for('gestor_productos'))
            
        id_producto = mov['id_producto']
        tipo = mov['tipo_movimiento']
        cantidad = mov['cantidad']
        
        # 2. Revertir el impacto en el stock "rápido" (Tabla productos)
        if tipo == 'ENTRADA':
            # Si borro una entrada (compra), RESTO esas unidades del stock actual
            conn.execute('UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?', (cantidad, id_producto))
        else:
            # Si borro una salida (venta), SUMO esas unidades (vuelven al estante)
            conn.execute('UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?', (cantidad, id_producto))
            
        # 3. Borrar el movimiento definitivamente
        conn.execute('DELETE FROM movimientos_stock WHERE id = ?', (id_movimiento,))
        conn.commit()
        flash('Movimiento eliminado y stock recalculado.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error al borrar: {str(e)}', 'error')
    finally:
        conn.close()
        
    # Volver al Kardex del producto (si lo encontramos)
    if id_producto:
        return redirect(url_for('ver_kardex', id_producto=id_producto))
    else:
        return redirect(url_for('gestor_productos'))
    
@app.route('/agregar_movimiento_stock', methods=['POST'])
def agregar_movimiento_stock():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    id_producto = request.form['id_producto']
    fecha = request.form['fecha']
    concepto = request.form['concepto']
    tipo = request.form['tipo'] # ENTRADA o SALIDA
    cantidad = float(request.form['cantidad'])
    
    # --- CORRECCIÓN DEL ERROR ---
    # Obtenemos el valor crudo. Si es cadena vacía (''), usamos 0.0
    costo_input = request.form.get('costo', '')
    if costo_input == '':
        costo = 0.0
    else:
        try:
            costo = float(costo_input)
        except ValueError:
            costo = 0.0
    # ----------------------------
    
    try:
        conn.execute('''
            INSERT INTO movimientos_stock (fecha, id_producto, concepto, tipo_movimiento, cantidad, costo_unitario)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fecha, id_producto, concepto, tipo, cantidad, costo))
        
        # Actualizar stock "rápido" en tabla productos
        if tipo == 'ENTRADA':
            conn.execute('UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?', (cantidad, id_producto))
        else:
            conn.execute('UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?', (cantidad, id_producto))
            
        conn.commit()
        flash('Movimiento registrado.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('ver_kardex', id_producto=id_producto))


@app.route('/diario', methods=('GET', 'POST'))
@login_required
def diario():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))

    asegurar_tasas_iva(conn)
    
    # --- LÓGICA DE PERIODO DE TRABAJO ---
    hoy = datetime.date.today()
    
    # Si el usuario cambia el periodo desde la barra superior
    if request.args.get('mes') and request.args.get('anio'):
        session['trabajo_mes'] = int(request.args.get('mes'))
        session['trabajo_anio'] = int(request.args.get('anio'))
        # Limpiamos filtros de edición puntuales si cambiamos de mes
        return redirect(url_for('diario'))

    # Recuperar de sesión o usar actual por defecto
    mes_trabajo = session.get('trabajo_mes', hoy.month)
    anio_trabajo = session.get('trabajo_anio', hoy.year)
    
    # Nombres de meses para la vista
    nombres_meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    # ------------------------------------

    # Cargar datos auxiliares
    # ... (Tu código de carga de cuentas, productos, tasas_iva e IDs defecto sigue igual) ...
    id_costo_db = 0; id_merca_db = 0 # (Simplificado para el ejemplo, mantén tu lógica de búsqueda de IDs)
    try:
        row_costo = conn.execute("SELECT id FROM cuentas WHERE codigo LIKE '5.1.1.01%'").fetchone()
        row_merca = conn.execute("SELECT id FROM cuentas WHERE codigo LIKE '1.1.4.01%'").fetchone()
        if row_costo: id_costo_db = row_costo['id']
        if row_merca: id_merca_db = row_merca['id']
    except: pass
    
    cuentas = conn.execute('SELECT id, codigo, nombre FROM cuentas ORDER BY codigo').fetchall()
    productos = conn.execute('SELECT * FROM productos ORDER BY nombre').fetchall()
    tasas_db = conn.execute('SELECT * FROM tasas_iva ORDER BY valor DESC').fetchall()
    tasas_iva = [{'id': t['id'], 'nombre': t['nombre'], 'valor': t['valor']} for t in tasas_db]

    entidades_db = conn.execute('SELECT * FROM entidades ORDER BY nombre').fetchall()
    entidades_json = [{'id': e['id'], 'nombre': e['nombre'], 'tipo': e['tipo']} for e in entidades_db]

    # --- NUEVO FASE 3: Traer Plantillas ---
    plantillas_db = conn.execute('SELECT id, nombre FROM plantillas ORDER BY nombre').fetchall()
    plantillas_json = [{'id': p['id'], 'nombre': p['nombre']} for p in plantillas_db]
   

    # --- LÓGICA DE RECUPERACIÓN DE COMPROBANTES (NUEVO) ---
    # 1. Analizamos el historial de leyendas para "aprender" qué usaste antes
    # (Buscamos el formato "Tipo - Detalle" y robamos la parte izquierda)
    rows_historial = conn.execute("SELECT DISTINCT leyenda FROM asientos").fetchall()
    tipos_detectados = set()
    
    for row in rows_historial:
        texto = row['leyenda']
        if ' - ' in texto:
            parte_tipo = texto.split(' - ')[0].strip()
            if len(parte_tipo) > 2: # Filtro básico de seguridad
                tipos_detectados.add(parte_tipo)

    # 2. Definimos los Obligatorios (Aquí agregamos tu Boleta de Depósito)
    tipos_default = {
        "Boleta (Contado)", 
        "Factura (Crédito)", 
        "Boleta de Depósito Bancario",
        "Nota de Debito Bancaria",
        "Nota de Credito Bancaria",
        "Comprobante interno",
        "Inicio de actividades",
        "Recibo de sueldo",   
        "Recibo (Cobro/Pago)", 
        "Nota de Crédito", 
        "Nota de Débito",
        "Ticket",
        "e-Factura"
    }

    # 3. Fusionamos y Ordenamos
    lista_comprobantes = sorted(list(tipos_default.union(tipos_detectados)))
    if request.method == 'POST':
        if request.is_json:
            payload       = request.get_json(silent=True) or {}
            asientos_json = payload.get('asientos', [])
            moneda        = payload.get('moneda', 'UYU')
            try:
                cotizacion = float(payload.get('cotizacion', 1.0) or 1.0)
                if cotizacion <= 0:
                    cotizacion = 1.0
            except (TypeError, ValueError):
                cotizacion = 1.0
 
            # ── FASE 1: Validar TODOS sin insertar nada ──────────────
            asientos_preparados = []
 
            for idx, asiento_data in enumerate(asientos_json, start=1):
                try:
                    dia_input  = int(asiento_data.get('dia') or 0)
                    fecha_obj  = datetime.date(anio_trabajo, mes_trabajo, dia_input)
                    fecha_final = fecha_obj.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    return jsonify({
                        'status': 'error',
                        'msg': f'Asiento #{idx}: Fecha inválida (día={asiento_data.get("dia")!r}).'
                    }), 400
 
                comprobante   = str(asiento_data.get('comprobante') or '').strip()
                leyenda       = str(asiento_data.get('leyenda')     or '').strip()
                leyenda_final = f"{comprobante} - {leyenda}" if comprobante else leyenda
 
                movimientos_raw = asiento_data.get('movimientos') or []
                movimientos     = []
                total_debe      = 0.0
                total_haber     = 0.0
 
                for mov in movimientos_raw:
                    cta_id     = str(mov.get('cuenta_id')     or '').strip()
                    cta_nombre = str(mov.get('cuenta_nombre') or '').strip()
                    d_input    = abs(float(mov.get('debe',  0) or 0))
                    h_input    = abs(float(mov.get('haber', 0) or 0))
 
                    if not cta_id and not cta_nombre:
                        continue
 
                    total_debe  += d_input
                    total_haber += h_input
                    movimientos.append({
                        'cta_id':      cta_id,
                        'cta_nombre':  cta_nombre,
                        'd_input':     d_input,
                        'h_input':     h_input,
                        'entidad_id':  str(mov.get('entidad_id')  or '').strip() or None,
                        'vencimiento': str(mov.get('vencimiento') or '').strip() or None,
                    })
 
                if not movimientos:
                    return jsonify({
                        'status': 'error',
                        'msg': f'Asiento #{idx} ({comprobante or "sin comprobante"}): No tiene movimientos.'
                    }), 400
 
                if abs(total_debe - total_haber) > 0.01:
                    dif = round(abs(total_debe - total_haber), 2)
                    return jsonify({
                        'status': 'error',
                        'msg': f'Asiento #{idx} ({comprobante}): No cuadra (Diferencia: {dif}).'
                    }), 400
 
                asientos_preparados.append({
                    'fecha':       fecha_final,
                    'leyenda':     leyenda_final,
                    'movimientos': movimientos,
                })
 
            if not asientos_preparados:
                return jsonify({'status': 'error', 'msg': 'No hay asientos para registrar.'}), 400
 
            # ── FASE 2: Insertar TODO en una sola transacción ────────
            cursor = conn.cursor()
            try:
                monto_venta_detectado = 0.0
                palabras_prohibidas   = [
                    'deudor', 'cobrar', 'cliente', 'anticipo',
                    'costo', 'iva', 'pagar', 'cheque'
                ]
 
                for asiento in asientos_preparados:
                    cursor.execute(
                        'INSERT INTO asientos (fecha, leyenda, descripcion, currency, exchange_rate) VALUES (?, ?, ?, ?, ?)',
                        (asiento['fecha'], asiento['leyenda'], asiento['leyenda'], moneda, cotizacion)
                    )
                    asiento_id = cursor.lastrowid
 
                    for mov in asiento['movimientos']:
                        row_cuenta = None
                        cta_id     = mov['cta_id']
                        cta_nombre = mov['cta_nombre']
 
                        if cta_id and cta_id not in ('0', ''):
                            row_cuenta = conn.execute(
                                'SELECT id, nombre FROM cuentas WHERE id = ?', (cta_id,)
                            ).fetchone()
 
                        if row_cuenta is None and cta_nombre:
                            row_cuenta = conn.execute(
                                'SELECT id, nombre FROM cuentas WHERE LOWER(nombre) = ?',
                                (cta_nombre.lower(),)
                            ).fetchone()
 
                        if row_cuenta is None:
                            raise ValueError(f"La cuenta '{cta_nombre or cta_id}' no existe en la base de datos.")
 
                        d_pesos = round(mov['d_input'] * cotizacion, 2)
                        h_pesos = round(mov['h_input'] * cotizacion, 2)
 
                        cursor.execute(
                            '''INSERT INTO movimientos
                               (id_asiento, id_cuenta, debe, haber, debe_org, haber_org, id_entidad, fecha_vencimiento)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                            (asiento_id, row_cuenta['id'],
                             d_pesos, h_pesos,
                             mov['d_input'], mov['h_input'],
                             mov['entidad_id'], mov['vencimiento'])
                        )
 
                        # Detección de ventas para trigger stock
                        nom_cta = row_cuenta['nombre'].lower()
                        es_falso_positivo = any(p in nom_cta for p in palabras_prohibidas)
                        if 'ventas' in nom_cta and not es_falso_positivo and h_pesos > 0:
                            monto_venta_detectado += h_pesos
 
                conn.commit()
 
                n   = len(asientos_preparados)
                msg = f'{n} asiento{"s" if n > 1 else ""} registrado{"s" if n > 1 else ""} exitosamente.'
 
                if monto_venta_detectado > 0:
                    session['trigger_stock'] = {
                        'fecha':       asientos_preparados[0]['fecha'],
                        'monto_venta': monto_venta_detectado,
                    }
                    return jsonify({
                        'status': 'trigger_stock',
                        'msg': msg + ' Venta detectada: ¿Descargar stock?'
                    })
 
                return jsonify({'status': 'success', 'msg': msg})
 
            except ValueError as e:
                conn.rollback()
                return jsonify({'status': 'error', 'msg': str(e)}), 400
            except Exception as e:
                conn.rollback()
                return jsonify({'status': 'error', 'msg': f'Error interno: {str(e)}'}), 500
   
        # ==========================================
        # ZONA A: LÓGICA DE STOCK (TU CÓDIGO)
        # ==========================================
        # 1. ¿Es el Asiento AUTOMÁTICO de Costo (Viene del Modal de Stock)?
        if 'producto_id_stock' in request.form:
            try:
                prod_id = request.form['producto_id_stock']
                cantidad = float(request.form['cantidad_stock'])
                fecha_asiento = request.form.get('fecha_preserved', hoy.strftime('%Y-%m-%d'))
                
                # A. Calcular el Costo según el método (FIFO/PMP) usando el motor
                movs_previos = conn.execute('SELECT * FROM movimientos_stock WHERE id_producto = ? ORDER BY fecha ASC, id ASC', (prod_id,)).fetchall()
                kardex = calcular_kardex(movs_previos, metodo='PMP') # Por defecto PMP, podrías hacerlo configurable
                
                # Simulamos la salida para obtener el costo
                costo_total_calculado = 0
                
                # Lógica simplificada: Usamos la función auxiliar del motor si existiera, 
                # o calculamos rápido el último costo unitario del saldo (PMP actual)
                if kardex:
                    ultimo_saldo = kardex[-1]
                    costo_unitario = ultimo_saldo['saldo_cu']
                    costo_total_calculado = round(cantidad * costo_unitario, 2)
                else:
                    flash('Error: No hay stock para calcular el costo.', 'error')
                    return redirect(url_for('diario'))

                # B. Registrar en KARDEX (Salida)
                conn.execute('''
                    INSERT INTO movimientos_stock (fecha, id_producto, concepto, tipo_movimiento, cantidad, costo_unitario)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (fecha_asiento, prod_id, 'Venta (Auto)', 'SALIDA', cantidad, 0)) # Costo unit 0 porque es salida (se calcula)
                
                # Actualizar Stock Físico
                conn.execute('UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?', (cantidad, prod_id))

                # C. Registrar ASIENTO CONTABLE (Costo a Mercaderías)
                # Buscamos IDs de las cuentas (Asumiendo que existen por el Schema base)
                id_costo = conn.execute("SELECT id FROM cuentas WHERE codigo LIKE '5.1.1.01%'").fetchone()['id']
                id_merca = conn.execute("SELECT id FROM cuentas WHERE codigo LIKE '1.1.4.01%'").fetchone()['id']
                
                cursor = conn.cursor()
                cursor.execute('INSERT INTO asientos (fecha, leyenda, descripcion) VALUES (?, ?, ?)', 
                               (fecha_asiento, 'CMV - Venta Automática', 'Generado por Stock'))
                asiento_id = cursor.lastrowid

                cursor.execute('''
                    INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (asiento_id, id_costo_db, costo_total_calculado, 0, costo_total_calculado, 0))
                
                # Costo (Debe)
                cursor.execute('INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber) VALUES (?, ?, ?, ?)',
                               (asiento_id, id_costo, costo_total_calculado, 0))
                # Mercadería (Haber)
                cursor.execute('INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber) VALUES (?, ?, ?, ?)',
                               (asiento_id, id_merca, 0, costo_total_calculado))
                
                conn.commit()
                flash(f'¡Stock descontado y Asiento de Costo (${costo_total_calculado}) generado!', 'success')
                return redirect(url_for('diario'))

            except Exception as e:
                conn.rollback()
                flash(f'Error al procesar stock: {str(e)}', 'error')
                return redirect(url_for('diario'))


        else:
            try:
                # 1. CONSTRUCCIÓN DE FECHA (NUEVO)
                # Ya no leemos 'fecha' completa del form, leemos solo 'dia'
                dia_input = int(request.form['dia'])
                
                try:
                    # Construimos la fecha real usando el Año y Mes de la sesión
                    fecha_obj = datetime.date(anio_trabajo, mes_trabajo, dia_input)
                    fecha_final = fecha_obj.strftime('%Y-%m-%d')
                except ValueError:
                    flash('Fecha inválida (ej: 30 de Febrero).', 'error')
                    return redirect(url_for('diario'))
                
                # 2. Recibir Datos Generales
                leyenda_base = request.form.get('leyenda', '')
                tipo_compro = request.form.get('tipo_comprobante', '')
                leyenda_final = f"{tipo_compro} - {leyenda_base}" if tipo_compro else leyenda_base
                
                # 3. Recibir Datos Multimoneda
                moneda = request.form.get('moneda', 'UYU')
                try:
                    cotizacion = float(request.form.get('cotizacion', 1))
                    if cotizacion <= 0: cotizacion = 1.0
                except:
                    cotizacion = 1.0

               # 4. Recibir las Listas de Cuentas
                cuentas_ids = request.form.getlist('cuenta_id[]')
                cuentas_nombres = request.form.getlist('cuenta_nombre[]')
                debes = request.form.getlist('debe[]')
                habers = request.form.getlist('haber[]')

                entidades_ids = request.form.getlist('entidad_id[]')
                vencimientos = request.form.getlist('vencimiento[]')

                # 5. Sumar Inputs (NUEVO: Usamos abs() para forzar positivos)
                t_debe_input = sum([abs(float(d)) for d in debes if d])
                t_haber_input = sum([abs(float(h)) for h in habers if h])
                
                # 6. Validar Cuadre
                if abs(t_debe_input - t_haber_input) > 0.01:
                    flash(f'El asiento no cuadra (Dif: {round(t_debe_input - t_haber_input, 2)}).', 'error')
                else:
                    cursor = conn.cursor()
                    
                    # A. Insertar Encabezado (USANDO fecha_final)
                    cursor.execute('''
                        INSERT INTO asientos (fecha, leyenda, descripcion, currency, exchange_rate) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (fecha_final, leyenda_final, leyenda_final, moneda, cotizacion))
                    asiento_id = cursor.lastrowid

                    monto_venta_detectado = 0
                    
                    # B. Insertar Movimientos
                    for i in range(len(cuentas_ids)):
                        if not cuentas_ids[i]: continue
                        
                        # NUEVO: Usamos abs() para blindar cada línea individualmente
                        d_input = abs(float(debes[i])) if debes[i] else 0
                        h_input = abs(float(habers[i])) if habers[i] else 0
                        
                        # Conversión a Pesos (Funcional)
                        d_pesos = round(d_input * cotizacion, 2)
                        h_pesos = round(h_input * cotizacion, 2)
                        cta_id_form = cuentas_ids[i]
                        cta_nombre_form = cuentas_nombres[i].strip() if  i < len(cuentas_nombres) else ""

                        # 2. Rescate de ID (Si viene 0 o vacío)
                        row_cuenta = None
                        if cta_id_form and cta_id_form != "0" and cta_id_form != "":
                            row_cuenta = conn.execute('SELECT id, nombre FROM cuentas WHERE id=?', (cta_id_form,)).fetchone()
                        
                        # Salvavidas: Buscar por nombre si no hay ID
                        if row_cuenta is None and cta_nombre_form:
                             row_cuenta = conn.execute('SELECT id, nombre FROM cuentas WHERE LOWER(nombre) = ?', (cta_nombre_form.lower(),)).fetchone()
                             if row_cuenta:
                                 cuentas_ids[i] = row_cuenta['id'] # Corregimos el ID para la próxima (o para referencia)

                        # 3. Si encontramos la cuenta, analizamos si es Venta
                        if row_cuenta:
                            nom_cta = row_cuenta['nombre'].lower()
                            
                            # Lista Negra (Anti-Falso Positivo)
                            palabras_prohibidas = ['deudor', 'cobrar', 'cliente', 'anticipo', 'costo', 'iva', 'pagar', 'cheque']
                            es_falso_positivo = any(p in nom_cta for p in palabras_prohibidas)

                            # Condición Final: Dice "ventas", no es prohibida y es Ganancia (Haber)
                            if "ventas" in nom_cta and not es_falso_positivo and h_pesos > 0:
                                monto_venta_detectado += h_pesos
                        
                        # --- FIN BLOQUE ---
                        
                        entidad_val = entidades_ids[i] if i < len(entidades_ids) and entidades_ids[i].strip() != "" else None
                        vencimiento_val = vencimientos[i] if i < len(vencimientos) and vencimientos[i].strip() != "" else None
                        
                        cursor.execute('''
                            INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org, id_entidad, fecha_vencimiento) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (asiento_id, cuentas_ids[i], d_pesos, h_pesos, d_input, h_input, entidad_val, vencimiento_val))
                        
                       
                       
                        # Detectar Venta
                        # 1. Obtenemos el ID y el Nombre que vienen del formulario
                        cta_id_form = cuentas_ids[i]
                        cta_nombre_form = cuentas_nombres[i].strip() if i < len(cuentas_nombres) else "" # Asegúrate de recibir cuentas_nombres[] desde el form
                         # 2. Intentamos buscar por ID primero
                        row_cuenta = None
                        if cta_id_form and cta_id_form != "0" and cta_id_form != "":
                            row_cuenta = conn.execute('SELECT id, nombre FROM cuentas WHERE id=?', (cta_id_form,)).fetchone()
                                            # 3. SALVAVIDAS: Si no encontró por ID (porque era 0), buscamos por NOMBRE EXACTO
                        if row_cuenta is None and cta_nombre_form:
                            # Buscamos la cuenta que se llame igual (ej: "IVA Ventas")
                            row_cuenta = conn.execute('SELECT id, nombre FROM cuentas WHERE nombre LIKE ?', (cta_nombre_form,)).fetchone()
                            
                            # Si la encontramos, actualizamos el ID para que el asiento se guarde bien
                            if row_cuenta:
                                cuentas_ids[i] = row_cuenta['id'] # ¡Corregimos el ID al vuelo!
                                            # 4. AHORA SÍ: Si sigue siendo None, es un error real (cuenta no existe)
                        if row_cuenta is None:
                            flash(f"Error: La cuenta '{cta_nombre_form}' no existe en la base de datos.", "error")
                            return redirect(url_for('diario')) # O manejar el error como prefieras
                                            # 5. Todo en orden, seguimos con la lógica de detección de ventas
                        nom_cta = row_cuenta['nombre'].lower()
                       # --- CÓDIGO NUEVO EN APP.PY (Blindado contra Falsos Positivos) ---

                        # 1. Lista Negra (Palabras que ANULAN la venta)
                        palabras_prohibidas = ['deudor', 'cobrar', 'cliente', 'anticipo', 'costo', 'iva', 'pagar', 'cheque']
                        
                        # 2. Verificamos si la cuenta tiene alguna palabra prohibida
                        es_falso_positivo = any(palabra in nom_cta for palabra in palabras_prohibidas)
                        
                        # 3. Condición Final:
                        # - Debe decir "ventas"
                        # - NO debe tener palabras prohibidas
                        # - Debe tener monto en el Haber (Ganancia)
                        if "ventas" in nom_cta and not es_falso_positivo and h_pesos > 0: 
                            monto_venta_detectado += h_pesos
                    
                    conn.commit()

                    if monto_venta_detectado > 0:
                        flash('Venta registrada. ¿Deseas descargar el stock automáticamente?', 'info')
                        return render_template('diario.html', 
                                               cuentas=cuentas, 
                                               productos=productos, 
                                               # IMPORTANTE: Usamos la lista filtrada también aquí
                                               asientos=get_asientos_list(conn, mes_trabajo, anio_trabajo), 
                                               trigger_stock=True, 
                                               fecha_preservada=fecha_final, # Usamos la fecha construida
                                               monto_venta=monto_venta_detectado, 
                                               tasas_iva=tasas_iva,
                                               id_costo_defecto=id_costo_db,
                                               id_merca_defecto=id_merca_db,
                                               mes_actual=mes_trabajo, anio_actual=anio_trabajo, nombres_meses=nombres_meses,
                                               comprobantes=lista_comprobantes,
                                               entidades=entidades_json,
                                               plantillas=plantillas_json)

                    flash(f'Asiento registrado el {fecha_final}.', 'success')
                    return redirect(url_for('diario'))

            except Exception as e:
                conn.rollback()
                flash(f'Error: {str(e)}', 'error')
    # GET: Mostrar página normal
    trigger_stock_session = session.pop('trigger_stock', None)
 
    return render_template('diario.html',
                           cuentas=cuentas,
                           productos=productos,
                           asientos=get_asientos_list(conn, mes_trabajo, anio_trabajo),
                           tasas_iva=tasas_iva,
                           id_costo_defecto=id_costo_db,
                           id_merca_defecto=id_merca_db,
                           mes_actual=mes_trabajo,
                           anio_actual=anio_trabajo,
                           nombres_meses=nombres_meses,
                           comprobantes=lista_comprobantes,
                           entidades=entidades_json,
                           plantillas=plantillas_json,
                           trigger_stock=bool(trigger_stock_session),
                           fecha_preservada=(trigger_stock_session or {}).get('fecha', hoy.strftime('%Y-%m-%d')),
                           monto_venta=(trigger_stock_session or {}).get('monto_venta', 0))
  
def get_asientos_list(conn, mes, anio):
    # Formateamos mes a 2 dígitos (ej: '01', '10')
    str_mes = f"{mes:02d}"
    str_anio = str(anio)
    
    # Filtramos por año y mes usando strftime de SQLite
    asientos_db = conn.execute('''
        SELECT * FROM asientos 
        WHERE strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
        ORDER BY fecha ASC, id ASC
    ''', (str_anio, str_mes)).fetchall()
    
    lista = []
    meses = {'01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril', '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto', '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'}

    for a in asientos_db:
        # ... (El resto de la lógica de esta función se mantiene igual, procesando movs) ...
        # Solo copia el interior del bucle for existente en tu código original
        anio_row, mes_row, dia_row = a['fecha'].split('-')
        nombre_mes = meses.get(mes_row, mes_row)
        grupo_mes = f"{nombre_mes} {anio_row}"

        movs = conn.execute('''
            SELECT m.debe, m.haber, m.debe_org, m.haber_org, c.nombre 
            FROM movimientos m JOIN cuentas c ON m.id_cuenta = c.id 
            WHERE m.id_asiento = ?
        ''', (a['id'],)).fetchall()
        
        moneda_label = ""
        if 'currency' in a.keys() and a['currency'] == 'USD':
            moneda_label = f" (U$S {a['exchange_rate']})"

        lista.append({
            'id': a['id'], 
            'fecha': a['fecha'], 
            'grupo_mes': grupo_mes, 
            'leyenda': a['leyenda'] + moneda_label, 
            'movs_debe': [m for m in movs if m['debe']>0], 
            'movs_haber': [m for m in movs if m['haber']>0],
            'es_usd': (a['currency'] == 'USD') if 'currency' in a.keys() else False
        })
    return lista
@app.route('/cuentas_corrientes', methods=['GET', 'POST'])
@login_required
def cuentas_corrientes():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))

    # Si el usuario envió el formulario para crear una nueva entidad
    if request.method == 'POST':
        nombre = request.form['nombre']
        rut = request.form.get('rut', '')
        tipo = request.form['tipo'] # 'CLIENTE' o 'PROVEEDOR'
        telefono = request.form.get('telefono', '')
        
        conn.execute('INSERT INTO entidades (nombre, rut, tipo, telefono) VALUES (?, ?, ?, ?)',
                     (nombre, rut, tipo, telefono))
        conn.commit()
        flash('Entidad creada correctamente.', 'success')
        return redirect(url_for('cuentas_corrientes'))

    # Para cargar la pantalla, buscamos todas las entidades y calculamos su saldo vivo
    query = """
        SELECT e.id, e.nombre, e.rut, e.tipo, e.telefono,
               COALESCE(SUM(CASE WHEN e.tipo = 'CLIENTE' THEN m.debe - m.haber ELSE m.haber - m.debe END), 0) as saldo_total
        FROM entidades e
        LEFT JOIN movimientos m ON e.id = m.id_entidad
        GROUP BY e.id, e.nombre, e.rut, e.tipo, e.telefono
        ORDER BY e.tipo, e.nombre
    """
    entidades = conn.execute(query).fetchall()
    cuentas = conn.execute("SELECT id, nombre FROM cuentas ORDER BY nombre").fetchall()
    conn.close()

    return render_template('cuentas_corrientes.html', entidades=entidades, cuentas=cuentas)
@app.route('/liquidar_deuda', methods=['POST'])
@login_required
def liquidar_deuda():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))

    try:
        id_entidad = request.form['id_entidad']
        tipo = request.form['tipo_entidad'] # 'CLIENTE' o 'PROVEEDOR'
        monto = float(request.form['monto_pago'])
        id_cuenta_dinero = request.form['cuenta_dinero'] # Ej: Caja o Banco
        id_cuenta_deuda = request.form['cuenta_deuda']   # Ej: Deudores por Ventas
        fecha = request.form.get('fecha_pago', datetime.date.today().strftime('%Y-%m-%d'))
        
        cursor = conn.cursor()
        
        # 0. Buscar el nombre de la entidad para el comprobante
        cursor.execute("SELECT nombre FROM entidades WHERE id = ?", (id_entidad,))
        entidad_bd = cursor.fetchone()
        nombre_entidad = entidad_bd['nombre'] if entidad_bd else "Entidad"

        # 1. Crear el Asiento (Con el comprobante correcto)
        leyenda = f"Recibo (Cobro a {nombre_entidad})" if tipo == 'CLIENTE' else f"Recibo (Pago a {nombre_entidad})"
        cursor.execute("INSERT INTO asientos (fecha, leyenda, currency, exchange_rate) VALUES (?, ?, 'UYU', 1.0)", (fecha, leyenda))
        id_asiento = cursor.lastrowid

        # 2. Armar los Movimientos (Partida Doble)
        if tipo == 'CLIENTE':
            # Entra plata (Debe), Baja la deuda (Haber)
            cursor.execute("INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org) VALUES (?, ?, ?, 0, ?, 0)", (id_asiento, id_cuenta_dinero, monto, monto))
            cursor.execute("INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org, id_entidad) VALUES (?, ?, 0, ?, 0, ?, ?)", (id_asiento, id_cuenta_deuda, monto, monto, id_entidad))
        else:
            # Baja la deuda (Debe), Sale plata (Haber)
            cursor.execute("INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org, id_entidad) VALUES (?, ?, ?, 0, ?, 0, ?)", (id_asiento, id_cuenta_deuda, monto, monto, id_entidad))
            cursor.execute("INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org) VALUES (?, ?, 0, ?, 0, ?)", (id_asiento, id_cuenta_dinero, monto, monto))

        conn.commit()
        flash('Operación registrada en el Libro Diario exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al registrar el pago: {e}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('cuentas_corrientes'))
@app.route('/mayor')
@login_required
def mayor():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    cuentas = conn.execute('SELECT * FROM cuentas ORDER BY codigo').fetchall()
    cuenta_id = request.args.get('cuenta_id')
    modo = request.args.get('modo', 'lista')
    
    cuenta_actual = None
    movimientos_detallados = []
    total_debe = 0; total_haber = 0; saldo_final = 0; es_cuenta_deudora = False
    
    if cuenta_id:
        cuenta_actual = conn.execute('SELECT * FROM cuentas WHERE id = ?', (cuenta_id,)).fetchone()
        if cuenta_actual:
            es_cuenta_deudora = cuenta_actual['tipo'] in ['Activo', 'Pérdida', 'Gastos']
            sql = '''SELECT m.debe, m.haber, m.debe_org, m.haber_org, 
                        a.fecha, a.leyenda, a.id as asiento_id,
                        a.currency, a.exchange_rate
                    FROM movimientos m 
                    JOIN asientos a ON m.id_asiento = a.id
                    WHERE m.id_cuenta = ? 
                    ORDER BY a.fecha ASC, a.id ASC'''
            rows = conn.execute(sql, (cuenta_id,)).fetchall()
            
            saldo_acumulado = 0
            for r in rows:
                debe = r['debe'] if r['debe'] else 0.0
                haber = r['haber'] if r['haber'] else 0.0

                # Recuperamos los valores originales (si son nulos, ponemos 0)
                debe_org = r['debe_org'] if r['debe_org'] else 0.0
                haber_org = r['haber_org'] if r['haber_org'] else 0.0

                total_debe += debe
                total_haber += haber
                if es_cuenta_deudora: saldo_acumulado += (debe - haber)
                else: saldo_acumulado += (haber - debe)
                
                movimientos_detallados.append({
                'fecha': r['fecha'], 
                'asiento_id': r['asiento_id'], 
                'leyenda': r['leyenda'], 
                'debe': debe, 
                'haber': haber, 
                'saldo': saldo_acumulado,
                # Datos multimoneda
                'currency': r['currency'],
                'exchange_rate': r['exchange_rate'],
                'debe_org': debe_org,
                'haber_org': haber_org
            })
        saldo_final = saldo_acumulado

    conn.close()
    return render_template('mayor.html', cuentas=cuentas, orden_tipos=['Activo', 'Pasivo', 'Patrimonio', 'Ganancia', 'Pérdida'],
                           cuenta_actual=cuenta_actual, movimientos=movimientos_detallados, cuenta_seleccionada_id=int(cuenta_id) if cuenta_id else None,
                           es_cuenta_deudora=es_cuenta_deudora, modo_vista=modo, total_debe=total_debe, total_haber=total_haber, saldo_final=saldo_final)

@app.route('/balances')
@login_required
def balances():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # 1. MAPA DE RUBROS (La inteligencia del reporte "Clase Mundial")
    # Define cómo se llaman los grupos basados en los primeros 5 caracteres del código (1.1.1)
    mapa_rubros = {
        # ACTIVO
        '1.1.1': 'Disponibilidades',
        '1.1.2': 'Créditos por Ventas',
        '1.1.3': 'Créditos Diversos',
        '1.1.4': 'Bienes de Cambio',
        '1.2.1': 'Bienes de Uso',
        # PASIVO
        '2.1.1': 'Deudas Comerciales',
        '2.1.2': 'Deudas Financieras',
        '2.1.3': 'Deudas Sociales y Fiscales',
        '2.2.1': 'Deudas a Largo Plazo',
        # PATRIMONIO
        '3.1.1': 'Capital Integrado',
        '3.1.2': 'Reservas',
        '3.1.3': 'Resultados Acumulados',
        '3.3.0': 'Resultados Acumulados', # Compatibilidad extra
        # RESULTADOS
        '4.1.1': 'Ingresos Operativos',
        '4.1.2': 'Ingresos Financieros',
        '5.1.1': 'Costos Operativos',
        '5.1.2': 'Gastos de Personal',
        '5.1.3': 'Gastos de Administración y Ventas',
        '5.1.4': 'Gastos Financieros'
    }

    # 2. OBTENER DATOS (Ahora pedimos el CÓDIGO y ordenamos por él)
    sql = '''
        SELECT c.codigo, c.nombre, c.tipo, 
               SUM(m.debe) as total_debe, SUM(m.haber) as total_haber 
        FROM cuentas c 
        LEFT JOIN movimientos m ON c.id = m.id_cuenta 
        GROUP BY c.id 
        ORDER BY c.codigo ASC
    '''
    datos = conn.execute(sql).fetchall()

    # Estructuras para agrupar: {'1.1.1': {'nombre': 'Disponibilidades', 'saldo': 0, 'cuentas': []}}
    # Usamos diccionarios auxiliares para agrupar al vuelo
    grupos_activos = {}
    grupos_pasivos = {}
    grupos_patrimonio = {}
    grupos_ganancias = {}
    grupos_perdidas = {}

    total_activo = 0; total_pasivo = 0; total_patrimonio = 0; total_ganancias = 0; total_perdidas = 0

    def agregar_al_grupo(diccionario_grupos, codigo, nombre_cuenta, saldo):
        if saldo == 0: return # No mostramos cuentas en cero
        
        # Detectar Rubro (1.1.1)
        prefijo = codigo[:5] if len(codigo) >= 5 else codigo
        nombre_rubro = mapa_rubros.get(prefijo, 'Otros Rubros')
        
        # Crear grupo si no existe
        if prefijo not in diccionario_grupos:
            diccionario_grupos[prefijo] = {'rubro': nombre_rubro, 'saldo_total': 0, 'cuentas': []}
        
        # Agregar cuenta
        diccionario_grupos[prefijo]['cuentas'].append({'nombre': nombre_cuenta, 'saldo': saldo})
        diccionario_grupos[prefijo]['saldo_total'] += saldo

    for fila in datos:
        debe = fila['total_debe'] if fila['total_debe'] else 0
        haber = fila['total_haber'] if fila['total_haber'] else 0
        tipo = fila['tipo']; nombre = fila['nombre']; codigo = fila['codigo']
        
        if tipo == 'Activo':
            saldo = debe - haber
            if saldo != 0: 
                agregar_al_grupo(grupos_activos, codigo, nombre, saldo)
                total_activo += saldo
        elif tipo == 'Pasivo':
            saldo = haber - debe
            if saldo != 0: 
                agregar_al_grupo(grupos_pasivos, codigo, nombre, saldo)
                total_pasivo += saldo
        elif tipo == 'Patrimonio':
            saldo = haber - debe
            # Excluir el resultado del ejercicio automático para no duplicar visualmente si se calcula abajo
            if "Resultado del Ejercicio" not in nombre and saldo != 0: 
                agregar_al_grupo(grupos_patrimonio, codigo, nombre, saldo)
                total_patrimonio += saldo
        elif tipo == 'Ganancia':
            saldo = haber - debe
            if saldo != 0: 
                agregar_al_grupo(grupos_ganancias, codigo, nombre, saldo)
                total_ganancias += saldo
        elif tipo == 'Pérdida':
            saldo = debe - haber
            if saldo != 0: 
                agregar_al_grupo(grupos_perdidas, codigo, nombre, saldo)
                total_perdidas += saldo

    resultado_ejercicio = round(total_ganancias - total_perdidas, 2)
    total_patrimonio_neto = total_patrimonio + resultado_ejercicio
    total_pasivo_mas_patrimonio = round(total_pasivo + total_patrimonio_neto, 2)
    total_activo = round(total_activo, 2)

    # --- LÓGICA DE DIFERENCIA DE CAMBIO (Tu código original intacto) ---
    sql_detalle = '''
        SELECT a.fecha, a.id as asiento_id, a.leyenda, a.currency, a.exchange_rate,
               c.codigo, c.nombre as cuenta_nombre, m.debe, m.haber
        FROM movimientos m
        JOIN asientos a ON m.id_asiento = a.id
        JOIN cuentas c ON m.id_cuenta = c.id
        WHERE c.codigo IN ('4.1.02', '5.1.03')
        ORDER BY a.fecha DESC, a.id DESC
    '''
    movimientos_dc = conn.execute(sql_detalle).fetchall()
    dc_ganancia_total = sum([m['haber'] - m['debe'] for m in movimientos_dc if m['codigo'] == '4.1.02'])
    dc_perdida_total = sum([m['debe'] - m['haber'] for m in movimientos_dc if m['codigo'] == '5.1.03'])
    dc_neto = dc_ganancia_total - dc_perdida_total

    conn.close()

    # Convertimos los diccionarios a listas ordenadas para la vista
    # (.values() nos da los objetos grupo, Python 3.7+ mantiene orden de inserción que viene del ORDER BY SQL)
    return render_template('balances.html', 
                           activos=list(grupos_activos.values()), total_activo=total_activo, 
                           pasivos=list(grupos_pasivos.values()), total_pasivo=total_pasivo, 
                           patrimonio=list(grupos_patrimonio.values()), total_patrimonio=total_patrimonio, 
                           ganancias=list(grupos_ganancias.values()), total_ganancias=total_ganancias, 
                           perdidas=list(grupos_perdidas.values()), total_perdidas=total_perdidas, 
                           resultado_ejercicio=resultado_ejercicio, 
                           total_pasivo_mas_patrimonio=total_pasivo_mas_patrimonio,
                           movimientos_dc=movimientos_dc,
                           dc_ganancia_total=dc_ganancia_total,
                           dc_perdida_total=dc_perdida_total,
                           dc_neto=dc_neto)

@app.route('/borrar_asiento/<int:id_asiento>', methods=['POST'])
def borrar_asiento(id_asiento):
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    try:
        conn.execute('DELETE FROM movimientos WHERE id_asiento = ?', (id_asiento,))
        conn.execute('DELETE FROM asientos WHERE id = ?', (id_asiento,))
        conn.commit()
        flash('Asiento eliminado correctamente.', 'success')
    except Exception as e:
        conn.rollback(); flash(f'Error: {str(e)}', 'error')
    finally: conn.close()
    return redirect(url_for('diario'))

@app.route('/borrar_seleccionados', methods=['POST'])
def borrar_seleccionados():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    ids = request.form.getlist('ids_a_borrar')
    if ids:
        try:
            placeholders = ', '.join('?' for _ in ids)
            conn.execute(f'DELETE FROM movimientos WHERE id_asiento IN ({placeholders})', ids)
            conn.execute(f'DELETE FROM asientos WHERE id IN ({placeholders})', ids)
            conn.commit()
            flash(f'Se eliminaron {len(ids)} asientos correctamente.', 'success')
        except Exception as e:
            conn.rollback(); flash(f'Error: {str(e)}', 'error')
    conn.close()
    return redirect(url_for('diario'))

# --- AGREGAR ESTO AL FINAL DE app.py (Antes del main) ---

# ==========================================
# GESTIÓN DEL PLAN DE CUENTAS (CRUD)
# ==========================================

@app.route('/cuentas')
@login_required
def gestor_cuentas():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # Obtenemos todas las cuentas ordenadas por código
    cuentas = conn.execute('SELECT * FROM cuentas ORDER BY codigo ASC').fetchall()
    conn.close()
    
    return render_template('cuentas.html', cuentas=cuentas)

@app.route('/guardar_cuenta', methods=['POST'])
def guardar_cuenta():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    id_cuenta = request.form.get('id_cuenta') # Si viene ID, es edición
    codigo = request.form.get('codigo').strip()
    nombre = request.form.get('nombre').strip()
    tipo = request.form.get('tipo')
    descripcion = request.form.get('descripcion', '').strip()
    
    try:
        if id_cuenta:
            conn.execute('UPDATE cuentas SET codigo = ?, nombre = ?, tipo = ?, descripcion = ? WHERE id = ?',
                         (codigo, nombre, tipo, descripcion, id_cuenta))
            flash(f'Cuenta "{nombre}" actualizada.', 'success')
        else:
            existe = conn.execute('SELECT id FROM cuentas WHERE codigo = ?', (codigo,)).fetchone()
            if existe:
                flash(f'Error: El código {codigo} ya existe.', 'error')
            else:
                conn.execute('INSERT INTO cuentas (codigo, nombre, tipo, descripcion) VALUES (?, ?, ?, ?)',
                             (codigo, nombre, tipo, descripcion))
                flash(f'Cuenta "{nombre}" creada.', 'success')
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f'Error al guardar: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('gestor_cuentas'))

@app.route('/borrar_cuenta/<int:id_cuenta>')
def borrar_cuenta(id_cuenta):
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    try:
        # VALIDACIÓN DE SEGURIDAD: No borrar si tiene movimientos
        movs = conn.execute('SELECT COUNT(*) as cant FROM movimientos WHERE id_cuenta = ?', (id_cuenta,)).fetchone()
        
        if movs['cant'] > 0:
            flash('⛔ No se puede eliminar: Esta cuenta tiene asientos contables registrados.', 'error')
        else:
            conn.execute('DELETE FROM cuentas WHERE id = ?', (id_cuenta,))
            conn.commit()
            flash('Cuenta eliminada correctamente.', 'success')
            
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('gestor_cuentas'))

# ==========================================
# MÓDULO DE STOCK / INVENTARIO
# ==========================================

@app.route('/productos')
@login_required
def gestor_productos():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # Listamos productos con su valoración actual
    productos = conn.execute('SELECT * FROM productos ORDER BY nombre').fetchall()
    
    # Calculamos el valor total del inventario
    valor_total_inventario = sum([p['stock_actual'] * p['costo_promedio'] for p in productos])
    
    conn.close()
    return render_template('productos.html', productos=productos, valor_total=valor_total_inventario)

@app.route('/guardar_producto', methods=['POST'])
def guardar_producto():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    id_prod = request.form.get('id_producto')
    codigo = request.form.get('codigo').strip()
    nombre = request.form.get('nombre').strip()
    precio_venta = request.form.get('precio_venta') or 0
    
    try:
        if id_prod:
            # Edición (Solo datos básicos, no tocamos stock ni costos aquí)
            conn.execute('UPDATE productos SET codigo=?, nombre=?, precio_venta=? WHERE id=?',
                         (codigo, nombre, precio_venta, id_prod))
            flash(f'Producto "{nombre}" actualizado.', 'success')
        else:
            # Creación
            conn.execute('INSERT INTO productos (codigo, nombre, stock_actual, costo_promedio, precio_venta) VALUES (?, ?, 0, 0, ?)',
                         (codigo, nombre, precio_venta))
            flash(f'Producto "{nombre}" creado.', 'success')
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('gestor_productos'))

# --- AGREGAR ESTAS NUEVAS FUNCIONES AL FINAL DE app.py ---

def asegurar_tasas_iva(conn):
    """Crea tasas por defecto si la tabla está vacía"""
    try:
        count = conn.execute('SELECT COUNT(*) as c FROM tasas_iva').fetchone()['c']
        if count == 0:
            conn.execute("INSERT INTO tasas_iva (nombre, valor) VALUES ('Básica', 22.0)")
            conn.execute("INSERT INTO tasas_iva (nombre, valor) VALUES ('Mínima', 10.0)")
            conn.execute("INSERT INTO tasas_iva (nombre, valor) VALUES ('Exenta', 0.0)")
            conn.commit()
    except: pass

@app.route('/guardar_tasa_iva', methods=['POST'])
def guardar_tasa_iva():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    try:
        conn.execute('INSERT INTO tasas_iva (nombre, valor) VALUES (?, ?)', 
                     (request.form.get('nombre'), request.form.get('valor')))
        conn.commit()
        flash('Tasa agregada.', 'success')
    except: conn.rollback()
    finally: conn.close()
    return redirect(url_for('diario'))

@app.route('/borrar_tasa_iva/<int:id_tasa>')
def borrar_tasa_iva(id_tasa):
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    conn.execute('DELETE FROM tasas_iva WHERE id = ?', (id_tasa,))
    conn.commit(); conn.close()
    flash('Tasa eliminada.', 'success')
    return redirect(url_for('diario'))

# ==========================================
# MÓDULO DE CONCILIACIÓN BANCARIA (FINAL)
# ==========================================

@app.route('/conciliacion', methods=['GET', 'POST'])
@login_required
def conciliacion():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # 1. Aseguramos tablas (Código existente...)
    try:
        conn.execute('SELECT fecha_corte FROM conciliaciones LIMIT 1')
    except:
        try:
            conn.execute('DROP TABLE IF EXISTS items_extracto')
            conn.execute('DROP TABLE IF EXISTS conciliaciones')
        except: pass
        
    conn.execute('''CREATE TABLE IF NOT EXISTS conciliaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cuenta INTEGER NOT NULL,
            fecha_corte TEXT NOT NULL,
            saldo_banco REAL DEFAULT 0,
            estado TEXT DEFAULT 'ABIERTA'
        )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS items_extracto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_conciliacion INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            concepto TEXT NOT NULL,
            debe REAL DEFAULT 0,
            haber REAL DEFAULT 0,
            conciliado BOOLEAN DEFAULT 0,
            id_mov_sistema INTEGER,
            FOREIGN KEY(id_conciliacion) REFERENCES conciliaciones(id)
        )''')

    # 2. Cargar Bancos
    bancos = conn.execute("SELECT * FROM cuentas WHERE codigo LIKE '1.1.1%' AND nombre LIKE '%Banco%' ORDER BY codigo").fetchall()
    
    # 3. Historial
    historial = conn.execute('''
        SELECT c.fecha_corte, c.saldo_banco, c.estado, cu.nombre as nombre_banco, cu.id as id_cuenta
        FROM conciliaciones c
        JOIN cuentas cu ON c.id_cuenta = cu.id
        ORDER BY c.fecha_corte DESC
    ''').fetchall()
    
    cuenta_id = request.args.get('cuenta_id')
    fecha_corte = request.args.get('fecha_corte')
    
    datos = {}
    
    if cuenta_id and fecha_corte:
        concil = conn.execute('SELECT * FROM conciliaciones WHERE id_cuenta = ? AND fecha_corte = ?', (cuenta_id, fecha_corte)).fetchone()
        
        cuenta_banco = conn.execute('SELECT nombre FROM cuentas WHERE id = ?', (cuenta_id,)).fetchone()
        datos['nombre_banco'] = cuenta_banco['nombre'] if cuenta_banco else "Banco"

        if not concil:
            datos['fase'] = 'carga'
        else:
            datos['fase'] = 'punteo'
            datos['info'] = concil
            datos['extracto'] = conn.execute('SELECT * FROM items_extracto WHERE id_conciliacion = ? ORDER BY fecha ASC', (concil['id'],)).fetchall()
            
            anio_mes = fecha_corte[:7]
            
            # --- CAMBIO 1: Traemos debe_org, haber_org y currency ---
            sql_sis = '''
                SELECT m.id, m.debe, m.haber, m.debe_org, m.haber_org, m.conciliado, 
                       a.fecha, a.leyenda, a.currency 
                FROM movimientos m 
                JOIN asientos a ON m.id_asiento = a.id
                WHERE m.id_cuenta = ? 
                  AND strftime('%Y-%m', a.fecha) = ? 
                  AND a.fecha <= ?
                ORDER BY a.fecha ASC, a.id ASC
            '''
            datos['sistema'] = conn.execute(sql_sis, (cuenta_id, anio_mes, fecha_corte)).fetchall()

            # --- CAMBIO 2: Calculamos el saldo usando los montos ORIGINALES (_org) ---
            # Esto asegura que si la cuenta es en USD, el saldo se muestre en USD
            sql_saldo = '''
                SELECT SUM(m.debe_org) as d, SUM(m.haber_org) as h 
                FROM movimientos m 
                JOIN asientos a ON m.id_asiento = a.id
                WHERE m.id_cuenta = ? AND a.fecha <= ?
            '''
            res = conn.execute(sql_saldo, (cuenta_id, fecha_corte)).fetchone()
            d = res['d'] if res['d'] else 0
            h = res['h'] if res['h'] else 0
            datos['saldo_sistema_calculado'] = round(d - h, 2)

    conn.close()
    return render_template('conciliacion.html', bancos=bancos, sel_cuenta=cuenta_id, sel_fecha=fecha_corte, datos=datos, historial=historial)

@app.route('/guardar_extracto', methods=['POST'])
def guardar_extracto():
    conn = get_db_connection()
    try:
        data = request.json
        cur = conn.cursor()
        
        # Guardamos fecha_corte exacta
        cur.execute('INSERT INTO conciliaciones (id_cuenta, fecha_corte, saldo_banco) VALUES (?, ?, ?)',
                    (data['cuenta_id'], data['fecha_corte'], data['saldo_final']))
        cid = cur.lastrowid
        
        for item in data['items']:
            cur.execute('''
                INSERT INTO items_extracto (id_conciliacion, fecha, concepto, debe, haber)
                VALUES (?, ?, ?, ?, ?)
            ''', (cid, item['fecha'], item['concepto'], item['debe'], item['haber']))
        
        conn.commit()
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        conn.close()

@app.route('/borrar_conciliacion')
def borrar_conciliacion():
    conn = get_db_connection()
    c_id = request.args.get('cuenta_id')
    f_corte = request.args.get('fecha_corte')
    
    try:
        # 1. Buscar la conciliación
        concil = conn.execute('SELECT id FROM conciliaciones WHERE id_cuenta = ? AND fecha_corte = ?', (c_id, f_corte)).fetchone()
        
        if concil:
            cid = concil['id']
            
            # 2. IMPORTANTE: "Liberar" los movimientos del sistema (destildarlos)
            # Buscamos qué movimientos del sistema estaban atados a esta conciliación implícitamente por fecha/cuenta
            # O simplemente reseteamos los de ese periodo para esa cuenta
            anio_mes = f_corte[:7] # '2026-01'
            conn.execute('''
                UPDATE movimientos 
                SET conciliado = 0 
                WHERE id_cuenta = ? 
                AND id_asiento IN (
                    SELECT id FROM asientos WHERE strftime('%Y-%m', fecha) = ? AND fecha <= ?
                )
            ''', (c_id, anio_mes, f_corte))

            # 3. Borrar los datos del extracto y la cabecera
            conn.execute('DELETE FROM items_extracto WHERE id_conciliacion = ?', (cid,))
            conn.execute('DELETE FROM conciliaciones WHERE id = ?', (cid,))
            
            conn.commit()
            flash('Conciliación reiniciada. Los movimientos del libro han sido liberados.', 'success')
            
    except Exception as e:
        conn.rollback()
        flash(f'Error al borrar: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('conciliacion', cuenta_id=c_id, fecha_corte=f_corte))

@app.route('/conciliar_par', methods=['POST'])
def conciliar_par():
    conn = get_db_connection()
    try:
        d = request.json
        if d.get('id_extracto'):
            conn.execute('UPDATE items_extracto SET conciliado = ? WHERE id = ?', (d['estado'], d['id_extracto']))
        if d.get('id_sistema'):
            conn.execute('UPDATE movimientos SET conciliado = ? WHERE id = ?', (d['estado'], d['id_sistema']))
        conn.commit()
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        conn.close()

# --- AGREGAR EN app.py ---

@app.route('/cerrar_conciliacion')
def cerrar_conciliacion():
    conn = get_db_connection()
    c_id = request.args.get('cuenta_id')
    f_corte = request.args.get('fecha_corte')
    
    try:
        # Actualizamos el estado a CERRADA
        conn.execute('''
            UPDATE conciliaciones 
            SET estado = 'CERRADA' 
            WHERE id_cuenta = ? AND fecha_corte = ?
        ''', (c_id, f_corte))
        conn.commit()
        flash('Conciliación finalizada y archivada exitosamente.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al cerrar: {str(e)}', 'error')
    finally:
        conn.close()
    
    # Redirigimos al menú principal de conciliación (Historial)
    return redirect(url_for('conciliacion'))

@app.route('/reabrir_conciliacion')
def reabrir_conciliacion():
    conn = get_db_connection()
    c_id = request.args.get('cuenta_id')
    f_corte = request.args.get('fecha_corte')
    
    try:
        # Volvemos el estado a ABIERTA
        conn.execute('''
            UPDATE conciliaciones 
            SET estado = 'ABIERTA' 
            WHERE id_cuenta = ? AND fecha_corte = ?
        ''', (c_id, f_corte))
        conn.commit()
        flash('Conciliación reabierta. Ya puedes editarla.', 'info')
    except Exception as e:
        conn.rollback()
        flash(f'Error al reabrir: {str(e)}', 'error')
    finally:
        conn.close()
    
    
    # Recargamos la página para ver los botones de nuevo
    return redirect(url_for('conciliacion', cuenta_id=c_id, fecha_corte=f_corte))

# ==========================================
# GESTIÓN DE USUARIOS (SOLO ADMIN)
# ==========================================

from functools import wraps
from flask import abort

# Decorador personalizado para proteger rutas de solo admin

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Permitimos si es 'admin' O SI ES 'dev'
        if not current_user.is_authenticated or (current_user.role != 'admin' and current_user.role != 'dev'):
            flash('⛔ Acceso denegado. Se requieren permisos de Administrador.', 'error')
            return redirect(url_for('lobby'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/usuarios')
@login_required
@admin_required
def gestor_usuarios():
    conn = get_users_db()
    
    if current_user.role == 'dev':
        # El Dios ve todo y el nombre del grupo
        sql = '''
            SELECT u.*, g.name as group_name 
            FROM users u 
            LEFT JOIN groups g ON u.group_id = g.id 
            ORDER BY u.username
        '''
        users = conn.execute(sql).fetchall()
    else:
        # El Admin solo ve a los de SU grupo
        sql = '''
            SELECT u.*, g.name as group_name 
            FROM users u 
            LEFT JOIN groups g ON u.group_id = g.id 
            WHERE u.group_id = ?
            ORDER BY u.username
        '''
        users = conn.execute(sql, (current_user.group_id,)).fetchall()
        
    conn.close()
    return render_template('usuarios.html', users=users)

@app.route('/crear_usuario', methods=['POST'])
@login_required
@admin_required
def crear_usuario():
    # 1. Obtener datos del formulario
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()
    role = request.form.get('role') # 'admin' o 'user'
    
    if not username or not password:
        flash('Faltan datos.', 'error')
        return redirect(url_for('gestor_usuarios'))

    hashed_pw = generate_password_hash(password)
    
    # --- AQUÍ VA EL BLOQUE QUE PREGUNTASTE ---
    # Lógica para asignar el grupo automáticamente:
    
    if current_user.role == 'admin':
        # Si soy un Profe (Admin), el alumno hereda MI grupo/clase
        group_id = current_user.group_id
    else:
        # Si soy el DEV (Dios), por defecto asigno al grupo 1 (o podría elegirlo)
        # Esto evita errores si creas usuarios desde el modo dios
        group_id = 1 

    conn = get_users_db()
    try:
        # Insertamos INCLUYENDO el group_id
        conn.execute('INSERT INTO users (username, password_hash, role, group_id) VALUES (?, ?, ?, ?)', 
                     (username, hashed_pw, role, group_id))
        conn.commit()
        flash(f'Usuario "{username}" creado correctamente en el grupo {group_id}.', 'success')
    except sqlite3.IntegrityError:
        flash(f'El usuario "{username}" ya existe.', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()
    # ------------------------------------------
        
    return redirect(url_for('gestor_usuarios'))

@app.route('/borrar_usuario/<int:user_id>')
@login_required
@admin_required
def borrar_usuario(user_id):
    # Evitar que el admin se borre a sí mismo
    if user_id == current_user.id:
        flash('No puedes eliminar tu propia cuenta mientras estás logueado.', 'error')
        return redirect(url_for('gestor_usuarios'))
    if user_id == 0:
        flash('⚠️ ¡Acción prohibida! No se puede eliminar al Sistema.', 'error')
        return redirect(url_for('gestor_usuarios'))

    conn = get_users_db()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('gestor_usuarios'))

@app.route('/cambiar_rol/<int:user_id>')
@login_required
@admin_required
def cambiar_rol(user_id):
    # Protecciones básicas
    if user_id == current_user.id:
        flash('No puedes cambiar tu propio rol.', 'error')
        return redirect(url_for('gestor_usuarios'))
    
    conn = get_users_db()
    try:
        # 1. Obtenemos el usuario actual
        user = conn.execute('SELECT role, username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            flash('Usuario no encontrado.', 'error')
            return redirect(url_for('gestor_usuarios'))
            
        # 2. Invertimos el rol (Toggle)
        nuevo_rol = 'user' if user['role'] == 'admin' else 'admin'
        
        # 3. Guardamos
        conn.execute('UPDATE users SET role = ? WHERE id = ?', (nuevo_rol, user_id))
        conn.commit()
        
        flash(f'Rol de {user["username"]} cambiado a {nuevo_rol.upper()}.', 'success')
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('gestor_usuarios'))
@app.route('/exportar_empresa/<archivo>')
@login_required
def exportar_empresa(archivo):
    # Verificamos que el archivo exista en la carpeta de datos
    filepath = os.path.join(app.config['DATABASES_FOLDER'], archivo)
    if os.path.exists(filepath):
        # Enviamos el archivo al usuario para que lo descargue
        return send_file(filepath, as_attachment=True, download_name=archivo)
    else:
        flash('El archivo no existe.', 'error')
        return redirect(url_for('lobby'))

# --- IMPORTAR EMPRESA (SUBIR .DB) ---
# En app.py, reemplaza la ruta '/importar_empresa' actual

@app.route('/importar_empresa', methods=['POST'])
@login_required
def importar_empresa():
    if 'archivo_db' not in request.files:
        flash('No seleccionaste ningún archivo', 'error')
        return redirect(url_for('lobby'))
    
    file = request.files['archivo_db']
    
    if file.filename == '':
        flash('Nombre de archivo vacío', 'error')
        return redirect(url_for('lobby'))

    if file and file.filename.endswith('.db'):
        # 1. Limpiamos el nombre original del archivo para evitar caracteres raros
        nombre_base = file.filename.replace('.db', '')
        safe_name = "".join([c for c in nombre_base if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_').lower()
        
        # 2. Le pegamos TU firma de propiedad (Grupo + Usuario)
        # Así aseguramos que aparezca en TU lista
        grupo_id = current_user.group_id if current_user.group_id else 0
        safe_user = "".join([c for c in current_user.username if c.isalnum()]).lower()
        
        # OJO: Si el archivo ya traía prefijos (ej: g1_juan_hola.db) los quitamos para no duplicar
        # Esto es simple: si empieza con gX_, asumimos que tiene formato viejo y lo tratamos como nombre bruto
        
        new_filename = f"g{grupo_id}_{safe_user}_{safe_name}.db"
        
        filepath = os.path.join(app.config['DATABASES_FOLDER'], new_filename)
        
        try:
            file.save(filepath)
            flash('Empresa importada exitosamente.', 'success')
        except Exception as e:
            flash(f'Error al guardar: {str(e)}', 'error')
            
    else:
        flash('Solo se permiten archivos .db', 'error')

    return redirect(url_for('lobby'))

@app.route('/imprimir_asiento/<int:id_asiento>')
@login_required
def imprimir_asiento(id_asiento):
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # 1. Obtener Cabecera
    asiento = conn.execute('SELECT * FROM asientos WHERE id = ?', (id_asiento,)).fetchone()
    
    if not asiento:
        conn.close()
        flash('El asiento solicitado no existe.', 'error')
        return redirect(url_for('diario'))
    
    # 2. Obtener Movimientos (Incluyendo columnas _org para multimoneda)
    sql_movs = '''
        SELECT m.debe, m.haber, m.debe_org, m.haber_org, 
               c.codigo, c.nombre
        FROM movimientos m 
        JOIN cuentas c ON m.id_cuenta = c.id
        WHERE m.id_asiento = ?
        ORDER BY m.debe DESC, m.haber DESC
    '''
    movs = conn.execute(sql_movs, (id_asiento,)).fetchall()
    
    # 3. Calcular Totales para el pie de página
    total_debe = sum([m['debe'] for m in movs])
    total_haber = sum([m['haber'] for m in movs])
    
    conn.close()
    
    return render_template('comprobante.html', 
                           asiento=asiento, 
                           movs=movs, 
                           empresa=session.get('empresa_nombre', 'Empresa'),
                           total_debe=total_debe, 
                           total_haber=total_haber)
@app.route('/cierre')
@login_required
def cierre_ejercicio():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # Filtros de Fecha (Por defecto: Año actual)
    hoy = datetime.date.today()
    f_inicio = request.args.get('fecha_inicio', f"{hoy.year}-01-01")
    f_fin = request.args.get('fecha_fin', f"{hoy.year}-12-31")
    
    # --- ETAPA 1: REFUNDICIÓN (Ganancias y Pérdidas) ---
    sql_res = '''
        SELECT c.id, c.codigo, c.nombre, c.tipo, 
               SUM(m.debe) as total_debe, SUM(m.haber) as total_haber
        FROM cuentas c
        LEFT JOIN movimientos m ON c.id = m.id_cuenta
        LEFT JOIN asientos a ON m.id_asiento = a.id
        WHERE c.tipo IN ('Ganancia', 'Pérdida')
          AND a.fecha BETWEEN ? AND ?
        GROUP BY c.id
        HAVING (total_debe - total_haber) <> 0
        ORDER BY c.codigo
    '''
    cuentas_res = conn.execute(sql_res, (f_inicio, f_fin)).fetchall()
    
    # Calcular Neto Previsto
    neto_refundicion = 0
    for c in cuentas_res:
        saldo = (c['total_haber'] or 0) - (c['total_debe'] or 0) # Acreedor - Deudor
        neto_refundicion += saldo

    # --- ETAPA 2: CIERRE PATRIMONIAL (Activo, Pasivo, Patrimonio) ---
    # Nota: Esto calcula los saldos AL MOMENTO DE CIERRE (incluyendo el resultado si ya se refundió)
    sql_pat = '''
        SELECT c.id, c.codigo, c.nombre, c.tipo, 
               SUM(m.debe) as total_debe, SUM(m.haber) as total_haber
        FROM cuentas c
        LEFT JOIN movimientos m ON c.id = m.id_cuenta
        LEFT JOIN asientos a ON m.id_asiento = a.id
        WHERE c.tipo IN ('Activo', 'Pasivo', 'Patrimonio')
          AND a.fecha <= ? -- Todo lo histórico hasta el cierre
        GROUP BY c.id
        HAVING (total_debe - total_haber) <> 0
        ORDER BY c.codigo
    '''
    cuentas_pat = conn.execute(sql_pat, (f_fin,)).fetchall()
    
    conn.close()
    
    return render_template('cierre.html', 
                           f_inicio=f_inicio, 
                           f_fin=f_fin,
                           cuentas_res=cuentas_res,
                           neto_refundicion=neto_refundicion,
                           cuentas_pat=cuentas_pat)


@app.route('/cierre/refundicion', methods=['POST'])
@login_required
def procesar_refundicion():
    conn = get_db_connection()
    try:
        f_inicio = request.form['fecha_inicio']
        f_fin = request.form['fecha_fin']
        
        # 1. Obtener saldos
        sql = '''
            SELECT c.id, SUM(m.debe) as d, SUM(m.haber) as h, 
                   SUM(m.debe_org) as do, SUM(m.haber_org) as ho
            FROM cuentas c
            JOIN movimientos m ON c.id = m.id_cuenta
            JOIN asientos a ON m.id_asiento = a.id
            WHERE c.tipo IN ('Ganancia', 'Pérdida') AND a.fecha BETWEEN ? AND ?
            GROUP BY c.id
        '''
        saldos = conn.execute(sql, (f_inicio, f_fin)).fetchall()
        
        if not saldos:
            flash('No hay saldos de resultados para refundir.', 'info')
            return redirect(url_for('cierre_ejercicio', fecha_inicio=f_inicio, fecha_fin=f_fin))

        # 2. Crear Asiento
        cur = conn.cursor()
        cur.execute("INSERT INTO asientos (fecha, leyenda, descripcion, tipo_comprobante) VALUES (?, ?, ?, 'C.I.')",
                    (f_fin, 'Por asiento de refundición de resultados', 'Cierre Etapa 1'))
        asiento_id = cur.lastrowid
        
        total_neto = 0
        
        for s in saldos:
            saldo = (s['h'] or 0) - (s['d'] or 0) # Saldo Acreedor
            saldo_org = (s['ho'] or 0) - (s['do'] or 0)
            
            if abs(saldo) < 0.01: continue
            
            # Para cancelar: Si es Acreedor (Positivo), Debito. Si es Deudor, Acredito.
            debe = saldo if saldo > 0 else 0
            haber = abs(saldo) if saldo < 0 else 0
            
            # Multimoneda simplificada: cerramos el org proporcionalmente
            debe_org = saldo_org if saldo > 0 else 0
            haber_org = abs(saldo_org) if saldo < 0 else 0
            
            cur.execute('''
                INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (asiento_id, s['id'], debe, haber, debe_org, haber_org))
            
            total_neto += saldo

        # 3. Registrar Resultado (3.3.01)
        cta_res = conn.execute("SELECT id FROM cuentas WHERE codigo = '3.3.01'").fetchone()
        
        if total_neto > 0: # Ganancia -> Haber Patrimonio
            cur.execute("INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org) VALUES (?, ?, 0, ?, 0, ?)",
                        (asiento_id, cta_res['id'], total_neto, total_neto))
        else: # Pérdida -> Debe Patrimonio
            cur.execute("INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org) VALUES (?, ?, ?, 0, ?, 0)",
                        (asiento_id, cta_res['id'], abs(total_neto), abs(total_neto)))
            
        conn.commit()
        flash('✅ Etapa 1: Refundición completada.', 'success')
        
    except Exception as e:
        conn.rollback(); flash(f'Error: {e}', 'error')
    finally: conn.close()
    
    return redirect(url_for('cierre_ejercicio', fecha_inicio=f_inicio, fecha_fin=f_fin))


@app.route('/cierre/patrimonial', methods=['POST'])
@login_required
def procesar_cierre_patrimonial():
    conn = get_db_connection()
    try:
        f_fin = request.form['fecha_fin']
        
        # 1. Obtener saldos finales de Activo, Pasivo y Patrimonio
        sql = '''
            SELECT c.id, SUM(m.debe) as d, SUM(m.haber) as h, 
                   SUM(m.debe_org) as do, SUM(m.haber_org) as ho
            FROM cuentas c
            JOIN movimientos m ON c.id = m.id_cuenta
            JOIN asientos a ON m.id_asiento = a.id
            WHERE c.tipo IN ('Activo', 'Pasivo', 'Patrimonio') AND a.fecha <= ?
            GROUP BY c.id
        '''
        saldos = conn.execute(sql, (f_fin,)).fetchall()
        
        cur = conn.cursor()
        cur.execute("INSERT INTO asientos (fecha, leyenda, descripcion, tipo_comprobante) VALUES (?, ?, ?, 'C.I.')",
                    (f_fin, 'Por asiento de cierre patrimonial', 'Cierre Etapa 2'))
        asiento_id = cur.lastrowid
        
        for s in saldos:
            saldo = (s['d'] or 0) - (s['h'] or 0) # Saldo Deudor (Activos positivos)
            saldo_org = (s['do'] or 0) - (s['ho'] or 0)
            
            if abs(saldo) < 0.01: continue
            
            # Para cancelar: Si es Deudor (Activo), Acredito. Si es Acreedor (Pasivo), Debito.
            debe = abs(saldo) if saldo < 0 else 0
            haber = saldo if saldo > 0 else 0
            
            debe_org = abs(saldo_org) if saldo < 0 else 0
            haber_org = saldo_org if saldo > 0 else 0
            
            cur.execute('''
                INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (asiento_id, s['id'], debe, haber, debe_org, haber_org))
            
        conn.commit()
        flash('✅ Etapa 2: Cierre Patrimonial completado. El libro diario ha quedado en CERO.', 'success')

    except Exception as e:
        conn.rollback(); flash(f'Error: {e}', 'error')
    finally: conn.close()
    
    return redirect(url_for('cierre_ejercicio', fecha_fin=f_fin))


@app.route('/cierre/apertura', methods=['POST'])
@login_required
def procesar_apertura():
    conn = get_db_connection()
    try:
        f_fin = request.form['fecha_fin']
       
        fecha_apertura = request.form['fecha_apertura']

        # Buscamos el asiento de CIERRE PATRIMONIAL (Etapa 2) recién hecho para invertirlo
        # Truco: Buscamos el último asiento de Cierre Patrimonial en esa fecha
        asiento_cierre = conn.execute('''
            SELECT id FROM asientos 
            WHERE fecha = ? AND leyenda = 'Por asiento de cierre patrimonial' 
            ORDER BY id DESC LIMIT 1
        ''', (f_fin,)).fetchone()
        
        if not asiento_cierre:
            flash('Error: No se encontró el Asiento de Cierre Patrimonial para invertir.', 'error')
            return redirect(url_for('cierre_ejercicio', fecha_fin=f_fin))
        
       # IDs Cuentas Especiales
        try:
            cta_res_ej = conn.execute("SELECT id FROM cuentas WHERE codigo='3.3.01'").fetchone()['id']
        except:
            flash('Error crítico: Falta la cuenta 3.3.01', 'error'); return redirect(url_for('cierre_ejercicio'))

        cta_res_ant_row = conn.execute("SELECT id FROM cuentas WHERE codigo='3.3.02'").fetchone()
        
        if not cta_res_ant_row:
            cur = conn.cursor()
            cur.execute("INSERT INTO cuentas (codigo, nombre, tipo) VALUES ('3.3.02', 'Resultados de Ejercicios Anteriores', 'Patrimonio')")
            cta_res_ant = cur.lastrowid
        else:
            cta_res_ant = cta_res_ant_row['id']
        # Traemos los movimientos del cierre para invertirlos
        movs = conn.execute('SELECT * FROM movimientos WHERE id_asiento = ?', (asiento_cierre['id'],)).fetchall()
        
        cur = conn.cursor()
        cur.execute("INSERT INTO asientos (fecha, leyenda, descripcion, tipo_comprobante) VALUES (?, ?, ?, 'C.I.')",
                    (fecha_apertura, 'Por asiento de apertura de ejercicio', 'Etapa 3'))
        asiento_new_id = cur.lastrowid
        
        for m in movs:
            # INVERSIÓN: Lo que estaba en Debe va a Haber, y viceversa
            nuevo_debe = m['haber']
            nuevo_haber = m['debe']
            nuevo_debe_org = m['haber_org']
            nuevo_haber_org = m['debe_org']
            
            # CAMBIO DE CUENTA: Si es 3.3.01 (Resultado del Ejercicio) -> 3.3.02 (Resultados Acumulados)
            cuenta_id = m['id_cuenta']
            if cuenta_id == cta_res_ej:
                cuenta_id = cta_res_ant
            
            cur.execute('''
                INSERT INTO movimientos (id_asiento, id_cuenta, debe, haber, debe_org, haber_org)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (asiento_new_id, cuenta_id, nuevo_debe, nuevo_haber, nuevo_debe_org, nuevo_haber_org))
            
        conn.commit()
        flash(f'✅ Etapa 3: Apertura generada con fecha {fecha_apertura}. Resultados trasladados a Ejercicios Anteriores.', 'success')

    except Exception as e:
        conn.rollback(); flash(f'Error: {e}', 'error')
    finally: conn.close()
    
    # Redirigimos manteniendo el filtro de fecha fin para que el usuario no pierda contexto
    return redirect(url_for('cierre_ejercicio', fecha_fin=f_fin))

# --- EN app.py ---

@app.route('/balance_8')
@login_required
def balance_8():
    conn = get_db_connection()
    if not conn: return redirect(url_for('lobby'))
    
    # 1. Obtener Cuentas con sus Sumas del Periodo (Debe y Haber)
    # Filtramos para que solo traiga cuentas que tuvieron movimiento o tienen saldo
    sql = '''
        SELECT c.codigo, c.nombre, c.tipo, 
               SUM(m.debe) as sum_debe, SUM(m.haber) as sum_haber
        FROM cuentas c
        JOIN movimientos m ON c.id = m.id_cuenta
        GROUP BY c.id
        ORDER BY c.codigo ASC
    '''
    rows = conn.execute(sql).fetchall()
    
    lineas = []
    
    # Acumuladores Verticales
    t_sum_debe = 0; t_sum_haber = 0
    t_sal_deudor = 0; t_sal_acreedor = 0
    t_inv_activo = 0; t_inv_pasivo = 0
    t_res_perdida = 0; t_res_ganancia = 0
    
    for r in rows:
        debe = r['sum_debe'] if r['sum_debe'] else 0
        haber = r['sum_haber'] if r['sum_haber'] else 0
        
        # Si la cuenta está en cero absoluto, la saltamos para limpiar la vista
        if debe == 0 and haber == 0: continue
        
        # A. SALDOS
        saldo_deudor = 0
        saldo_acreedor = 0
        if debe > haber:
            saldo_deudor = debe - haber
        else:
            saldo_acreedor = haber - debe
            
        # B. DISTRIBUCIÓN (INVENTARIO vs RESULTADOS)
        inv_activo = 0; inv_pasivo = 0
        res_perdida = 0; res_ganancia = 0
        
        tipo = r['tipo']
        
        # Lógica de distribución según el Tipo de Cuenta
        if tipo == 'Activo':
            inv_activo = saldo_deudor # Los activos tienen saldo deudor
        elif tipo in ['Pasivo', 'Patrimonio']:
            inv_pasivo = saldo_acreedor # Pas/PN tienen saldo acreedor
        elif tipo in ['Pérdida', 'Gastos']:
            res_perdida = saldo_deudor
        elif tipo == 'Ganancia':
            res_ganancia = saldo_acreedor
            
        # Construir línea
        lineas.append({
            'codigo': r['codigo'],
            'nombre': r['nombre'],
            'sum_debe': debe,
            'sum_haber': haber,
            'sal_deudor': saldo_deudor,
            'sal_acreedor': saldo_acreedor,
            'inv_activo': inv_activo,
            'inv_pasivo': inv_pasivo,
            'res_perdida': res_perdida,
            'res_ganancia': res_ganancia
        })
        
        # Sumar a totales verticales
        t_sum_debe += debe
        t_sum_haber += haber
        t_sal_deudor += saldo_deudor
        t_sal_acreedor += saldo_acreedor
        t_inv_activo += inv_activo
        t_inv_pasivo += inv_pasivo
        t_res_perdida += res_perdida
        t_res_ganancia += res_ganancia

    # 3. CÁLCULO DEL RESULTADO DEL EJERCICIO (El ajuste)
    resultado = t_res_ganancia - t_res_perdida
    
    ajuste_row = {
        'nombre': 'RESULTADO DEL EJERCICIO',
        'inv_activo': 0, 'inv_pasivo': 0,
        'res_perdida': 0, 'res_ganancia': 0
    }
    
    if resultado > 0: 
        # GANANCIA
        # 1. Se agrega en Pérdidas para igualar la columna de Resultados
        ajuste_row['res_perdida'] = resultado 
        # 2. Se agrega en Pasivo+PN para igualar la columna de Inventario (Aumenta Patrimonio)
        ajuste_row['inv_pasivo'] = resultado 
    else:
        # PÉRDIDA
        # 1. Se agrega en Ganancias para igualar Resultados
        ajuste_row['res_ganancia'] = abs(resultado)
        # 2. Se agrega en Activo para igualar Inventario (O restando Pasivo, pero en hoja de 8 col se suele poner en el lado opuesto para cuadrar sumas iguales)
        ajuste_row['inv_activo'] = abs(resultado)

    # 4. TOTALES FINALES (Totales Verticales + Ajuste)
    finales = {
        'sum_debe': t_sum_debe,
        'sum_haber': t_sum_haber,
        'sal_deudor': t_sal_deudor,
        'sal_acreedor': t_sal_acreedor,
        # Sumamos el ajuste para que visualmente cuadren abajo
        'inv_activo': t_inv_activo + ajuste_row['inv_activo'],
        'inv_pasivo': t_inv_pasivo + ajuste_row['inv_pasivo'],
        'res_perdida': t_res_perdida + ajuste_row['res_perdida'],
        'res_ganancia': t_res_ganancia + ajuste_row['res_ganancia']
    }
    
    totales_parciales = {
        'inv_activo': t_inv_activo, 'inv_pasivo': t_inv_pasivo,
        'res_perdida': t_res_perdida, 'res_ganancia': t_res_ganancia
    }

    conn.close()
    
    return render_template('balance_8.html', 
                           lineas=lineas, 
                           parciales=totales_parciales,
                           ajuste=ajuste_row,
                           finales=finales,
                           empresa=session.get('empresa_nombre'))

# ==========================================
# API DE PLANTILLAS (FASE 3)
# ==========================================
@app.route('/api/guardar_plantilla', methods=['POST'])
@login_required
def guardar_plantilla():
    conn = get_db_connection()
    if not conn: return jsonify({'status': 'error', 'msg': 'Error de base de datos'})
    
    datos = request.json
    nombre_plantilla = datos.get('nombre')
    cuentas = datos.get('cuentas') # Recibe lista de cuentas y lados
    
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO plantillas (nombre) VALUES (?)", (nombre_plantilla,))
        id_plantilla = cursor.lastrowid
        
        for c in cuentas:
            cursor.execute("INSERT INTO plantillas_detalle (id_plantilla, id_cuenta, lado) VALUES (?, ?, ?)", 
                           (id_plantilla, c['id'], c['lado']))
        
        conn.commit()
        return jsonify({'status': 'success', 'id': id_plantilla, 'nombre': nombre_plantilla})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        conn.close()

@app.route('/api/obtener_plantilla/<int:id_plantilla>')
@login_required
def obtener_plantilla(id_plantilla):
    conn = get_db_connection()
    if not conn: return jsonify([])
    
    detalle = conn.execute('''
        SELECT pd.id_cuenta, c.nombre, pd.lado 
        FROM plantillas_detalle pd
        JOIN cuentas c ON pd.id_cuenta = c.id
        WHERE pd.id_plantilla = ?
    ''', (id_plantilla,)).fetchall()
    
    conn.close()
    return jsonify([dict(d) for d in detalle])

if __name__ == '__main__':
     window = webview.create_window('Konta', app, width=1280, height=800)
     webview.start(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true', user_agent='pywebview-app')