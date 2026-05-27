/* diario_extras.js */

document.addEventListener('DOMContentLoaded', function () {
    // Inicializar estado de la moneda al cargar
    if (typeof toggleCotizacion === 'function') {
        toggleCotizacion();
    }
});

// ==========================================
// 1. LÓGICA DE MONEDA Y COTIZACIÓN
// ==========================================

function toggleCotizacion() {
    const monedaInput = document.getElementById('moneda');
    const cotizacionVisual = document.getElementById('cotizacion_visual');

    if (!monedaInput || !cotizacionVisual) return;

    const moneda = monedaInput.value.toUpperCase();

    if (moneda === 'UYU' || moneda === '') {
        cotizacionVisual.value = "1.00";
        cotizacionVisual.readOnly = true;
        cotizacionVisual.style.color = "#aaa";
        cotizacionVisual.style.backgroundColor = "#f8f9fa";
    } else {
        cotizacionVisual.readOnly = false;
        cotizacionVisual.style.color = "#000";
        cotizacionVisual.style.backgroundColor = "#fff";
        if (cotizacionVisual.value === "1.00") {
            cotizacionVisual.value = "";
        }
        cotizacionVisual.placeholder = "Ej: 42.5";
    }
}

function prepararEnvio(event) {
    event.preventDefault();
 
    // Sincronizar moneda global
    const monedaVal  = (document.getElementById('moneda')             || {}).value || 'UYU';
    const cotizacion = parseFloat((document.getElementById('cotizacion_visual') || {}).value) || 1.0;
    const hiddenMon  = document.getElementById('hidden_moneda');
    const hiddenCot  = document.getElementById('hidden_cotizacion');
    if (hiddenMon) hiddenMon.value = monedaVal;
    if (hiddenCot) hiddenCot.value = cotizacion;
 
    // Validar todos los bloques
    if (typeof auditoriaFinal === 'function') {
        if (!auditoriaFinal(event)) return false;
    }
 
    // Construir payload JSON
    const bloques  = document.querySelectorAll('.bloque-asiento-dinamico');
    const asientos = [];
 
    bloques.forEach(bloque => {
        const dia         = parseInt((bloque.querySelector('.input-dia-asiento')  || {}).value || '0', 10);
        const comprobante = ((bloque.querySelector('.input-comprobante') || {}).value || '').trim();
        const leyenda     = ((bloque.querySelector('.input-leyenda')     || {}).value || '').trim();
 
        const movimientos = [];
        bloque.querySelectorAll('.bloque-input-container .fila-movimiento').forEach(fila => {
            const cuenta_id    = ((fila.querySelector('.hidden-id-cuenta')   || {}).value || '').trim();
            const cuenta_nombre= ((fila.querySelector('.input-cuenta')       || {}).value || '').trim();
            const debe         = parseFloat((fila.querySelector('.input-debe')  || {}).value) || 0;
            const haber        = parseFloat((fila.querySelector('.input-haber') || {}).value) || 0;
            const entidad_id   = ((fila.querySelector('.hidden-entidad-id')   || {}).value || '').trim();
            const vencimiento  = ((fila.querySelector('.hidden-vencimiento')  || {}).value || '').trim();
 
            if (cuenta_nombre || (cuenta_id && cuenta_id !== '0')) {
                movimientos.push({ cuenta_id, cuenta_nombre, debe, haber, entidad_id, vencimiento });
            }
        });
 
        asientos.push({ dia, comprobante, leyenda, movimientos });
    });
 
    const payload = { moneda: monedaVal, cotizacion, asientos };
 
    // Deshabilitar botón
    const btn = document.getElementById('btn-guardar');
    if (btn) { btn.disabled = true; btn.innerHTML = '⏳ Guardando...'; }
 
    const resetBtn = () => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '✅ REGISTRAR ASIENTOS <small style="font-weight:normal;opacity:0.8;">(Alt+Enter)</small>';
        }
    };
 
    fetch('/diario', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload)
    })
    .then(r => {
        if (!r.ok) return r.json().then(d => { throw new Error(d.msg || `Error HTTP ${r.status}`); });
        return r.json();
    })
    .then(data => {
        resetBtn();
        if (data.status === 'success' || data.status === 'trigger_stock') {
            Swal.fire({
                toast: true, position: 'top-end', icon: 'success',
                title: data.msg || 'Asientos registrados',
                showConfirmButton: false, timer: 2500
            }).then(() => {
                window.location.href = window.location.pathname + window.location.search;
            });
        } else {
            Swal.fire({ icon: 'error', title: 'Error', text: data.msg || 'Error desconocido.', confirmButtonColor: '#2c3e50' });
        }
    })
    .catch(err => {
        resetBtn();
        Swal.fire({ icon: 'error', title: 'Error de conexión', text: err.message || 'No se pudo contactar al servidor.', confirmButtonColor: '#2c3e50' });
    });
 
    return false;
}
 

// ==========================================
// 2. LÓGICA DEL MODAL DE COSTO DE VENTAS
// ==========================================

function cerrarModalFusion() {
    const modal = document.getElementById('modalFusion');
    if (modal) modal.style.display = 'none';
}

function switchTab(tabId) {
    // 1. Ocultar todos los contenidos
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    // 2. Desactivar todos los botones
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

    // 3. Mostrar el contenido deseado
    const target = document.getElementById(tabId);
    if (target) target.classList.add('active');

    // 4. Activar el botón correspondiente
    const botones = document.querySelectorAll('.tab-btn');
    botones.forEach(btn => {
        // Busamos si el onclick contiene el nombre del tab
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)) {
            btn.classList.add('active');
        }
    });
}

function syncManualCost() {
    const costo = document.getElementById('input-manual-costo').value;
    const haberOculto = document.getElementById('input-manual-haber-oculto');
    if (haberOculto) haberOculto.value = costo;

    // --- PARCHE PARA EL ERROR 400 (Falta de fecha) ---
    // Atrapamos el formulario de la pestaña Manual
    const formManual = document.querySelector('#tab-manual form');

    // Verificamos si ya creamos el input del día oculto
    let inputDia = formManual.querySelector('input[name="dia"]');
    if (!inputDia) {
        inputDia = document.createElement('input');
        inputDia.type = 'hidden';
        inputDia.name = 'dia';
        formManual.appendChild(inputDia);
    }

     const diaPrincipal = document.querySelector('.input-dia-asiento');
    inputDia.value = (diaPrincipal && diaPrincipal.value) ? diaPrincipal.value : "1";

    return true;
}
/* EN DIARIO_EXTRAS.JS - Reemplazo TOTAL de aplicarCalculo */
function aplicarCalculo() {
    const resultadoEl = document.getElementById('calc-resultado');
    const monto = parseFloat(resultadoEl ? resultadoEl.innerText : 0);
    if (!monto || monto <= 0) { alert("Calcula un monto válido primero"); return; }
 
    const mainContainer = document.getElementById('main-container');
    const idCosto = mainContainer ? (mainContainer.getAttribute('data-id-costo') || "0") : "0";
    const idMerca = mainContainer ? (mainContainer.getAttribute('data-id-merca') || "0") : "0";
 
    const obtenerNombreCuenta = (idBuscado, nombreDefault) => {
        const opciones = document.querySelectorAll('#cuentas-list option');
        for (let opt of opciones) {
            if (opt.getAttribute('data-id') === idBuscado) return opt.value;
        }
        return nombreDefault;
    };
 
    const nombreCosto = obtenerNombreCuenta(idCosto, "Costo de Ventas (CMV)");
    const nombreMerca = obtenerNombreCuenta(idMerca, "Mercaderías de Reventa");
 
    const modal = document.getElementById('modalFusion');
    if (modal) modal.style.display = 'none';
 
    // Scope al bloque activo
    const bloque    = _getBloqueActivo();
    const container = bloque
        ? bloque.querySelector('.bloque-input-container')
        : document.querySelector('.bloque-input-container');
    if (!container) return;
 
    const filas = Array.from(container.querySelectorAll('.fila-movimiento'));
 
    const esFila_Vacia = (fila) => {
        const nombre = fila.querySelector('.input-cuenta');
        const debe   = fila.querySelector('.input-debe');
        const haber  = fila.querySelector('.input-haber');
        return (
            (!nombre || nombre.value.trim() === '') &&
            (!debe  || !debe.value  || parseFloat(debe.value)  === 0) &&
            (!haber || !haber.value || parseFloat(haber.value) === 0)
        );
    };
 
    let filaReutilizable = null;
    filas.forEach(fila => {
        if (!esFila_Vacia(fila)) return;
        if (container.querySelectorAll('.fila-movimiento').length <= 1) {
            filaReutilizable = fila;
        } else {
            fila.remove();
        }
    });
 
    if (!filaReutilizable) filaReutilizable = window.agregarLinea(container);
 
    const rellenarFila = (fila, id, nombre, debe, haber) => {
        const inpNombre = fila.querySelector('.input-cuenta');
        const inpId     = fila.querySelector('.hidden-id-cuenta');
        const inpDebe   = fila.querySelector('.input-debe');
        const inpHaber  = fila.querySelector('.input-haber');
        if (inpNombre) { inpNombre.value = nombre; inpNombre.setAttribute('name', 'cuenta_nombre[]'); }
        if (inpId)     inpId.value = id;
        if (inpDebe)   { inpDebe.readOnly = false;  inpDebe.style.backgroundColor = 'transparent';  inpDebe.value = ''; }
        if (inpHaber)  { inpHaber.readOnly = false; inpHaber.style.backgroundColor = 'transparent'; inpHaber.value = ''; }
        if (debe  > 0 && inpDebe)  { inpDebe.value  = debe.toFixed(2);  detectarLado(inpDebe); }
        if (haber > 0 && inpHaber) { inpHaber.value = haber.toFixed(2); detectarLado(inpHaber); }
    };
 
    rellenarFila(filaReutilizable, idCosto, nombreCosto, monto, 0);
 
    const filaMerca = window.agregarLinea(container);
    rellenarFila(filaMerca, idMerca, nombreMerca, 0, monto);
 
    const form = document.getElementById('form-diario');
    if (!form) return;
 
    const inputDia = bloque
        ? bloque.querySelector('.input-dia-asiento')
        : document.querySelector('.input-dia-asiento');
    const inputFechaPreservada = document.querySelector('input[name="fecha_preserved"]');
    if (inputDia && !inputDia.value && inputFechaPreservada && inputFechaPreservada.value) {
        const partes = inputFechaPreservada.value.split('-');
        if (partes.length === 3) inputDia.value = parseInt(partes[2], 10);
    }
 
    const inputCompro = bloque
        ? bloque.querySelector('.input-comprobante')
        : document.querySelector('.input-comprobante');
    if (inputCompro && !inputCompro.value) inputCompro.value = "Comprobante Interno";
 
    if (form.checkValidity()) {
        const btnG = document.querySelector('.btn-guardar');
        if (btnG) btnG.innerText = "Guardando...";
        setTimeout(() => form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true })), 100);
    } else {
        form.reportValidity();
    }
}
 


function detectarEscrituraManual() {
    const leyenda = document.getElementById('input-leyenda-dinamica');
    if (leyenda) leyenda.value = "Costo de Ventas (Ajuste Manual)";
}

/* EN DIARIO_EXTRAS.JS */

function calcularMargen() {
    const metodo = document.getElementById('calc-metodo').value;
    // Permitimos decimales en el porcentaje
    const porcentaje = parseFloat(document.getElementById('calc-porcentaje').value) || 0;

    // Obtenemos el precio de venta (sin IVA) desde el atributo del modal
    const modal = document.getElementById('modalFusion');
    const ventaTotal = parseFloat(modal.getAttribute('data-monto-venta')) || 0;

    let costoCalculado = 0;

    if (ventaTotal > 0 && porcentaje >= 0) {

        switch (metodo) {

            // CASO A: El Costo es el X% directo del Precio
            // Ejemplo: Vendo a 100, Costo es 70% -> Costo = 70.
            case 'costo_sobre_venta':
                costoCalculado = ventaTotal * (porcentaje / 100);
                break;

            // CASO B: La Utilidad es el X% del Precio (Lo que me sobra es costo)
            // Ejemplo: Vendo a 100, quiero ganar 30% -> Costo = 70.
            case 'utilidad_sobre_venta':
                costoCalculado = ventaTotal * (1 - (porcentaje / 100));
                break;

            // CASO C: Utilidad sobre Costo (Markup clásico)
            // Fórmula: PV = Costo * (1 + %)  ->  Costo = PV / (1 + %)
            // Ejemplo: Costo 100 + 50% ganancia = Venta 150.
            // Inverso: 150 / 1.5 = 100.
            case 'utilidad_sobre_costo':
                costoCalculado = ventaTotal / (1 + (porcentaje / 100));
                break;

            // CASO D: TU NUEVA FÓRMULA (Costo sobre Utilidad)
            // Lógica: Utilidad = 100%, Costo = X%. Precio = 100% + X%.
            // Regla de 3: Costo = (Precio * X) / (100 + X)
            case 'costo_sobre_utilidad':
                // (ventaTotal * porcentaje) / (100 + porcentaje)
                costoCalculado = (ventaTotal * porcentaje) / (100 + porcentaje);
                break;
        }

        // Mostramos el resultado formateado
        document.getElementById('calc-resultado').innerText = costoCalculado.toFixed(2);
    } else {
        document.getElementById('calc-resultado').innerText = "0.00";
    }
}

// ============================================================================
// DETECCIÓN DE DEVOLUCIONES — VERSIÓN CORREGIDA
// ============================================================================
// PROBLEMAS DE LA VERSIÓN ANTERIOR (los tres que convivían):
//
//   1. ID incorrecto del checkbox:
//      Buscaba 'check-iva-auto' → no existe en el HTML.
//      El real es 'check-iva' (diario.html línea 69).
//      Como retornaba null, el guard no bloqueaba, pero era un bug latente.
//
//   2. El evento "change" nunca disparaba en el flujo normal:
//      "change" en input[type=number] solo se dispara al hacer blur
//      Y SOLO si el valor cambió desde el último blur.
//      En tu sistema, al presionar Enter se crea nueva línea y el focus
//      salta automáticamente → el blur de input-debe puede no generar
//      "change" si el browser ya registró ese valor en un blur anterior
//      (ej: si detectarLado hace blur/focus programático).
//      Resultado: el modal sencillamente nunca se abría.
//
//   3. La fila inicial no recibía el listener:
//      El forEach inicial buscaba .fila-movimiento pero esa fila viene
//      del HTML estático de Jinja. Si por timing o por la forma en que
//      se monta el DOM la línea del forEach se ejecuta antes de que esa
//      fila exista, quedaba sin conectar. El Observer solo cubría filas
//      NUEVAS (agregarLinea), no la primera.
//
// SOLUCIÓN APLICADA:
//   • Reemplazar "change" por un DEBOUNCE sobre "input".
//     "input" se dispara con CADA keystroke, así que siempre funciona.
//     El debounce de 600ms garantiza que el modal solo aparezca cuando
//     el usuario pausa de escribir (no interrumpido por cada tecla).
//     Es el mismo patrón que usa un buscador al escribir.
//
//   • Usar delegación en #input-container (como en la versión original
//     que sí funcionaba) en lugar de conectar listeners fila por fila.
//     Esto elimina el problema de timing de la fila inicial Y de las
//     filas nuevas de un golpe, sin necesidad de MutationObserver.
//
//   • Corregir el ID del checkbox a 'check-iva'.
// ============================================================================

(function () {

    // ──────────────────────────────────────────────────────────────────────
    // ESTADO INTERNO
    // ──────────────────────────────────────────────────────────────────────
    var _filaDevActiva = null;   // Fila que está mostrando el modal actualmente
    var _timerDebounce = null;   // Referencia al setTimeout del debounce

    // ──────────────────────────────────────────────────────────────────────
    // DEBOUNCE: el núcleo del "esperar a que termine de escribir"
    //
    // Cómo funciona:
    //   Cada vez que el usuario escribe un carácter, se cancela cualquier
    //   timer anterior y se crea uno nuevo de 600ms.
    //   Solo cuando pasan 600ms SIN que llegue otro "input", el callback
    //   se ejecuta. Si el usuario sigue escribiendo, el timer se reinicia.
    //
    // Por qué 600ms y no más/menos:
    //   < 400ms → se siente interrumpido para una pausa natural entre
    //             dígitos (ej: escribir "1000" con una pausa breve).
    //   600ms   → tiempo natural de "dejé de escribir, estoy leyendo".
    //   > 1000ms → se siente que el sistema no responde.
    // ──────────────────────────────────────────────────────────────────────
    var DEBOUNCE_MS = 1000;

    function _debounceDeteccion(fila) {
        if (_timerDebounce) {
            clearTimeout(_timerDebounce);
            _timerDebounce = null;
        }
        _timerDebounce = setTimeout(function () {
            _timerDebounce = null;
            _analizarPosibleDevolucion(fila);
        }, DEBOUNCE_MS);
    }

    // ──────────────────────────────────────────────────────────────────────
    // LISTENER PRINCIPAL — delegado en #input-container
    //
    // Por qué delegación y no listeners individuales:
    //   Las filas se crean dinámicamente con agregarLinea(). Con
    //   delegación, UN solo listener en el contenedor captura eventos
    //   de cualquier hijo presente o futuro. No importa cuántas filas
    //   se agreguen ni si la primera fila ya estaba en el DOM al cargar.
    //   Sin MutationObserver, sin forEach inicial, sin timing issues.
    // ──────────────────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        var container = document.getElementById('bloques-container') 
        if (!container) return;

         container.addEventListener('input', function (e) {
            var target = e.target;

            // Solo nos interesa .input-debe
            if (!target.classList.contains('input-debe')) return;

            // Obtener la fila padre
            var fila = target.closest('.fila-movimiento');
            if (!fila) return;

            // Si el campo tiene valor > 0, iniciar/reiniciar debounce.
            // Si se borró el valor, cancelar cualquier timer pendiente.
            var valor = parseFloat(target.value);
            if (valor && valor > 0) {
                _debounceDeteccion(fila);
            } else {
                // Borró el valor → cancelar timer si estaba corriendo
                if (_timerDebounce) {
                    clearTimeout(_timerDebounce);
                    _timerDebounce = null;
                }
            }
        });

        // Conectar eventos del modal (una sola vez, al cargar)
        _configurarModal();
    });

    // ──────────────────────────────────────────────────────────────────────
    // ANÁLISIS: ¿es devolución?
    // ──────────────────────────────────────────────────────────────────────
    function _analizarPosibleDevolucion(fila) {
        var inpDebe = fila.querySelector('.input-debe');
        var monto = parseFloat(inpDebe ? inpDebe.value : 0);
        if (!monto || monto <= 0) return;

        // Guard: checkbox global "IVA Automático"
        // ID correcto según diario.html línea 69: 'check-iva'
        var chkIva = document.getElementById('check-iva');
        if (chkIva && !chkIva.checked) return;

        // Guard: la cuenta debe ser de tipo "Ventas"
        var inpCuenta = fila.querySelector('.input-cuenta');
        var nombreCuenta = inpCuenta ? inpCuenta.value : '';
        if (!nombreCuenta) return;

        // Usamos la función global existente en diario.js (línea ~1271)
        if (typeof esVentaDeResultado !== 'function') return;
        if (!esVentaDeResultado(nombreCuenta)) return;

        // Guard: si el modal ya está abierto para esta misma fila, no abrir otra vez
        if (_filaDevActiva === fila) return;

        // ✓ Todo pasó → abrir modal
        _abrirModalIVADev(fila, monto);
    }

    // ──────────────────────────────────────────────────────────────────────
    // GESTIÓN DEL MODAL
    // ──────────────────────────────────────────────────────────────────────
    function _poblarTasas() {
        var select = document.getElementById('modal-iva-dev-tasa');
        if (!select) return;
        select.innerHTML = '';

        var mainContainer = document.getElementById('main-container');
        var tasas = [];
        try {
            tasas = JSON.parse(mainContainer.getAttribute('data-tasas-iva') || '[]');
        } catch (e) { /* fallback abajo */ }

        if (tasas.length > 0) {
            tasas.forEach(function (t) {
                var opt = document.createElement('option');
                opt.value = t.valor;
                opt.textContent = t.nombre + ' (' + t.valor + '%)';
                select.appendChild(opt);
            });
        } else {
            // Fallback si no hay tasas configuradas
            [{ valor: '22', nombre: 'Básica' },
            { valor: '10', nombre: 'Mínima' },
            { valor: '0', nombre: 'Exento' }].forEach(function (t) {
                var opt = document.createElement('option');
                opt.value = t.valor;
                opt.textContent = t.nombre + ' (' + t.valor + '%)';
                select.appendChild(opt);
            });
        }
    }

    function _abrirModalIVADev(fila, montoBase) {
        _filaDevActiva = fila;

        // Poblar tasas frescas (refleja configuración actual)
        _poblarTasas();

        // Mostrar contexto
        var inpCuenta = fila.querySelector('.input-cuenta');
        var elCuenta = document.getElementById('modal-iva-dev-cuenta');
        var elMonto = document.getElementById('modal-iva-dev-monto');
        if (elCuenta) elCuenta.textContent = inpCuenta ? inpCuenta.value : '—';
        if (elMonto) elMonto.textContent = '$' + montoBase.toFixed(2);

        // Preview inicial
        _actualizarPreviewIVADev(montoBase);

        // Mostrar
        var modal = document.getElementById('modal-iva-devoluciones');
        if (modal) modal.style.display = 'flex';
    }

    function _cerrarModalIVADev() {
        var modal = document.getElementById('modal-iva-devoluciones');
        if (modal) modal.style.display = 'none';
        _filaDevActiva = null;
    }

    function _actualizarPreviewIVADev(montoBase) {
        var select = document.getElementById('modal-iva-dev-tasa');
        var tasa = parseFloat(select ? select.value : 0) || 0;
        var iva = montoBase * (tasa / 100);
        var total = montoBase + iva;

        var fmt = function (n) { return '$' + n.toFixed(2); };

        var elBase = document.getElementById('modal-iva-dev-preview-base');
        var elIVA = document.getElementById('modal-iva-dev-preview-iva');
        var elTotal = document.getElementById('modal-iva-dev-preview-total');

        if (elBase) elBase.textContent = fmt(montoBase);
        if (elIVA) elIVA.textContent = fmt(iva);
        if (elTotal) elTotal.textContent = fmt(total);
    }

    // ──────────────────────────────────────────────────────────────────────
    // CONFIRMACIÓN: escribir el IVA en la fila correspondiente
    // ──────────────────────────────────────────────────────────────────────
    function _confirmarIVADevoluciones() {
        if (!_filaDevActiva) return;

        var inpDebeBase = _filaDevActiva.querySelector('.input-debe');
        var montoBase = parseFloat(inpDebeBase ? inpDebeBase.value : 0) || 0;
        var select = document.getElementById('modal-iva-dev-tasa');
        var tasa = parseFloat(select ? select.value : 0) || 0;
        var montoIVA = montoBase * (tasa / 100);

        // Si es Exento (tasa 0), no hay IVA que registrar
        if (montoIVA <= 0) {
            _cerrarModalIVADev();
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    toast: true, position: 'top-end', icon: 'info',
                    title: 'Tasa Exento: no se genera IVA.',
                    showConfirmButton: false, timer: 2500
                });
            }
            return;
        }

        // Buscar fila existente de "IVA Ventas" en todo el container
        var filaIVA = _buscarFilaIVAVentas(_filaDevActiva)

        // Si no existe, crear una nueva y moverla justo debajo de la fila activa
        if (!filaIVA && typeof window.agregarLinea === 'function') {
            filaIVA = window.agregarLinea(_filaDevActiva);
            if (filaIVA) {
                // Insertar justo debajo de la fila de Ventas (más lógico visualmente)
                _filaDevActiva.parentNode.insertBefore(filaIVA, _filaDevActiva.nextSibling);
            }
        }

        if (filaIVA) {
            var inpNom = filaIVA.querySelector('.input-cuenta');
            var inpDebe = filaIVA.querySelector('.input-debe');
            var inpHaber = filaIVA.querySelector('.input-haber');

            // Nombre de la cuenta
            if (inpNom) {
                inpNom.value = 'IVA Ventas';
                if (typeof buscarId === 'function') buscarId(inpNom);
            }

            // Escribir monto en DEBE
            if (inpDebe) {
                inpDebe.readOnly = false;
                inpDebe.style.backgroundColor = 'transparent';
                inpDebe.value = montoIVA.toFixed(2);
                // detectarLado bloquea el HABER y aplica estilo visual
                if (typeof detectarLado === 'function') detectarLado(inpDebe);
            }

            // Asegurar HABER limpio
            if (inpHaber) {
                inpHaber.value = '';
            }
        }

        _cerrarModalIVADev();

        if (typeof Swal !== 'undefined') {
            Swal.fire({
                toast: true, position: 'top-end', icon: 'success',
                title: 'IVA Devolución registrado: $' + montoIVA.toFixed(2),
                showConfirmButton: false, timer: 2500
            });
        }
    }

    // Busca una fila con "IVA" y "Ventas" en el nombre (case-insensitive, sin tildes)
     function _buscarFilaIVAVentas(filaRef) {
        var bloque = filaRef ? filaRef.closest('.bloque-asiento-dinamico') : null;
        var inputContainer = bloque
            ? bloque.querySelector('.bloque-input-container')
            : document.querySelector('.bloque-input-container');
        var filas = inputContainer ? inputContainer.querySelectorAll('.fila-movimiento') : [];
 
        for (var i = 0; i < filas.length; i++) {
            var inp = filas[i].querySelector('.input-cuenta');
            if (!inp || !inp.value) continue;
            var nombre = inp.value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
            if (nombre.indexOf('iva') !== -1 && nombre.indexOf('ventas') !== -1) return filas[i];
        }
        return null;
    }

    // ──────────────────────────────────────────────────────────────────────
    // WIRING DEL MODAL (botones, select, overlay)
    // ──────────────────────────────────────────────────────────────────────
    function _configurarModal() {
        var btnCerrar = document.getElementById('modal-iva-dev-cerrar');
        var btnCancelar = document.getElementById('modal-iva-dev-cancelar');
        var btnConfirmar = document.getElementById('modal-iva-dev-confirmar');
        var selectTasa = document.getElementById('modal-iva-dev-tasa');
        var overlay = document.getElementById('modal-iva-devoluciones');

        if (btnCerrar) btnCerrar.addEventListener('click', _cerrarModalIVADev);
        if (btnCancelar) btnCancelar.addEventListener('click', _cerrarModalIVADev);
        if (btnConfirmar) btnConfirmar.addEventListener('click', _confirmarIVADevoluciones);

        if (selectTasa) {
            selectTasa.addEventListener('change', function () {
                if (!_filaDevActiva) return;
                var inp = _filaDevActiva.querySelector('.input-debe');
                var base = parseFloat(inp ? inp.value : 0) || 0;
                _actualizarPreviewIVADev(base);
            });
        }

        // Click en el overlay (fuera del contenido) → cerrar
        if (overlay) {
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) _cerrarModalIVADev();
            });
        }
    }

})();
// ==========================================
// ASISTENTE DE CUENTAS CORRIENTES (FASE 1)
// ==========================================
let filaActivaEntidad = null;

function detectarCuentaCorriente(inputCuenta) {
    if (!inputCuenta || !inputCuenta.value) return;

    // Si ya le preguntamos en esta fila, no lo volvemos a molestar
    if (inputCuenta.dataset.entidadPreguntada === "true") return;

    const val = inputCuenta.value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();

    // 1. REGLA DE EXCLUSIÓN: Las previsiones son globales, no piden cliente.
    if (val.includes('prevision')) return;

    // 2. PALABRAS GATILLO (Atrapa Deudores, Morosos, Proveedores, Acreedores, etc)
    const palabrasGatillo = ['deudor', 'proveedor', 'acreedor', 'documentos a', 'cliente'];
    const esCorriente = palabrasGatillo.some(p => val.includes(p));

    if (esCorriente) {
        filaActivaEntidad = inputCuenta.closest('.fila-movimiento');

        // Marcamos que ya se le preguntó para no hacer un bucle infinito
        inputCuenta.dataset.entidadPreguntada = "true";

        // Obtener entidades desde el HTML
        const container = document.getElementById('main-container');
        let entidades = [];
        try { entidades = JSON.parse(container.getAttribute('data-entidades') || '[]'); } catch (e) { }

        // Llenar el select
        const select = document.getElementById('modal-entidad-select');
        select.innerHTML = '<option value="" disabled selected>-- Selecciona Entidad --</option>';

        if (entidades.length === 0) {
            select.innerHTML += '<option value="">(No hay entidades creadas aún)</option>';
        } else {
            entidades.forEach(e => {
                select.innerHTML += `<option value="${e.id}">${e.nombre} (${e.tipo})</option>`;
            });
        }

        // Poner fecha de vencimiento a 30 días por defecto
        const hoy = new Date();
        hoy.setDate(hoy.getDate() + 30);
        document.getElementById('modal-entidad-vencimiento').value = hoy.toISOString().split('T')[0];

        // Mostrar modal
        document.getElementById('modal-entidades').style.display = 'flex';
    }
}

function confirmarEntidad() {
    if (!filaActivaEntidad) return;

    const idEntidad = document.getElementById('modal-entidad-select').value;
    const fechaVen = document.getElementById('modal-entidad-vencimiento').value;

    if (idEntidad) {
        filaActivaEntidad.querySelector('.hidden-entidad-id').value = idEntidad;
        filaActivaEntidad.querySelector('.hidden-vencimiento').value = fechaVen;

        Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: 'Entidad vinculada', showConfirmButton: false, timer: 2000 });
    }

    document.getElementById('modal-entidades').style.display = 'none';
    filaActivaEntidad.querySelector('.input-debe').focus();
}
async function guardarComoPlantilla() {
    // Scope al bloque activo
    const bloque = _getBloqueActivo();
    const filas  = bloque
        ? bloque.querySelectorAll('.bloque-input-container .fila-movimiento')
        : document.querySelectorAll('.bloque-input-container .fila-movimiento');
 
    let cuentas = [];
 
    filas.forEach(fila => {
        const inputId    = fila.querySelector('input[name="cuenta_id[]"]');
        const inputDebe  = fila.querySelector('input[name="debe[]"]');
        const inputHaber = fila.querySelector('input[name="haber[]"]');
 
        if (!inputId || !inputDebe || !inputHaber) return;
 
        const idCuenta = inputId.value;
        const debe  = parseFloat(inputDebe.value)  || 0;
        const haber = parseFloat(inputHaber.value) || 0;
 
        if (idCuenta && idCuenta !== "0" && idCuenta !== "") {
            let lado = 'DEBE';
            if (haber > 0) lado = 'HABER';
            cuentas.push({ id: idCuenta, lado: lado });
        }
    });
 
    if (cuentas.length === 0) {
        Swal.fire('Atención', 'No hay cuentas válidas seleccionadas para guardar.', 'warning');
        return;
    }
 
    const { value: nombrePlantilla } = await Swal.fire({
        title: 'Guardar Estructura',
        text: 'Se guardarán las cuentas y su ubicación (Debe/Haber), pero no los importes.',
        input: 'text',
        inputPlaceholder: 'Ej: Liquidación de Sueldos',
        showCancelButton: true,
        confirmButtonColor: '#f39c12',
        cancelButtonColor: '#7f8c8d',
        confirmButtonText: '💾 Guardar Plantilla',
        cancelButtonText: 'Cancelar',
        inputValidator: (value) => {
            if (!value) return '¡Necesitas escribir un nombre!'
        }
    });
 
    if (!nombrePlantilla) return;
 
    try {
        const response = await fetch('/api/guardar_plantilla', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre: nombrePlantilla, cuentas: cuentas })
        });
 
        const data = await response.json();
 
        if (data.status === 'success') {
            Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: 'Plantilla guardada', showConfirmButton: false, timer: 2000 });
 
            const select = document.getElementById('selector-plantillas');
            const option = document.createElement('option');
            option.value = data.id;
            option.text  = data.nombre;
            select.appendChild(option);
        } else {
            Swal.fire('Error', data.msg, 'error');
        }
    } catch (error) {
        Swal.fire('Error', 'Hubo un problema de conexión.', 'error');
    }
}
 
async function cargarPlantilla() {
    const select      = document.getElementById('selector-plantillas');
    const idPlantilla = select.value;
    if (!idPlantilla) return;
 
    try {
        const response = await fetch(`/api/obtener_plantilla/${idPlantilla}`);
        const data = await response.json();
 
        if (Array.isArray(data) && data.length > 0) {
            // Scope al bloque activo
            const bloque       = _getBloqueActivo();
            const container    = bloque
                ? bloque.querySelector('.bloque-input-container')
                : document.querySelector('.bloque-input-container');
            const filasActuales = Array.from(container.querySelectorAll('.fila-movimiento'));
 
            const filaBase = filasActuales[0];
            filasActuales.slice(1).forEach(f => f.remove());
 
            data.forEach((cuenta, index) => {
                let fila = index === 0 ? filaBase : window.agregarLinea(container);
 
                const inpNombre = fila.querySelector('.input-cuenta');
                const inpId     = fila.querySelector('.hidden-id-cuenta');
                const inpDebe   = fila.querySelector('.input-debe');
                const inpHaber  = fila.querySelector('.input-haber');
 
                if (inpNombre) { inpNombre.value = cuenta.nombre; inpNombre.setAttribute('name', 'cuenta_nombre[]'); }
                if (inpId)     inpId.value = cuenta.id_cuenta;
 
                if (inpDebe)  { inpDebe.readOnly  = false; inpDebe.style.backgroundColor  = 'transparent'; inpDebe.value  = ''; }
                if (inpHaber) { inpHaber.readOnly = false; inpHaber.style.backgroundColor = 'transparent'; inpHaber.value = ''; }
 
                if (cuenta.lado === 'DEBE' && inpHaber) {
                    inpHaber.readOnly = true;
                    inpHaber.style.backgroundColor = '#f8f9fa';
                } else if (cuenta.lado === 'HABER' && inpDebe) {
                    inpDebe.readOnly = true;
                    inpDebe.style.backgroundColor = '#f8f9fa';
                }
            });
 
            select.value = "";
            const primerInputLibre = filaBase.parentNode.querySelector('.input-debe:not([readonly]), .input-haber:not([readonly])');
            if (primerInputLibre) primerInputLibre.focus();
            Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: 'Plantilla cargada', showConfirmButton: false, timer: 2000 });
 
        } else if (Array.isArray(data) && data.length === 0) {
            Swal.fire('Atención', 'Esta plantilla no tiene cuentas guardadas.', 'warning');
        } else {
            Swal.fire('Error', 'Formato de datos irreconocible.', 'error');
        }
    } catch (error) {
        console.error("Error cargando plantilla:", error);
        Swal.fire('Error', 'Hubo un problema de conexión al cargar la plantilla.', 'error');
    }
}

async function eliminarPlantilla() {
    const selectOriginal = document.getElementById('selector-plantillas');

    // 1. Extraemos las plantillas que existen en tu menú desplegable
    const opciones = {};
    let hayPlantillas = false;

    Array.from(selectOriginal.options).forEach(opt => {
        if (opt.value) { // Ignoramos la opción por defecto ("-- Cargar Plantilla --")
            opciones[opt.value] = opt.text;
            hayPlantillas = true;
        }
    });

    if (!hayPlantillas) {
        Swal.fire('Atención', 'No hay plantillas guardadas para eliminar.', 'info');
        return;
    }

    // 2. Mostramos un popup con su propio menú desplegable solo para borrar
    const { value: idPlantilla } = await Swal.fire({
        title: '🗑️ Eliminar Plantilla',
        text: 'Selecciona la plantilla que deseas borrar permanentemente:',
        input: 'select',
        inputOptions: opciones,
        inputPlaceholder: '-- Elige una plantilla --',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sí, borrar',
        cancelButtonText: 'Cancelar',
        inputValidator: (value) => {
            if (!value) return 'Debes seleccionar una plantilla para eliminar';
        }
    });

    // 3. Si el usuario eligió una y le dio a confirmar, la borramos en Python
    if (idPlantilla) {
        try {
            const response = await fetch(`/api/borrar_plantilla/${idPlantilla}`, { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                // Removemos la opción del select principal de tu pantalla
                const optionToRemove = selectOriginal.querySelector(`option[value="${idPlantilla}"]`);
                if (optionToRemove) optionToRemove.remove();

                Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: 'Plantilla eliminada', showConfirmButton: false, timer: 2000 });
            } else {
                Swal.fire('Error', data.msg, 'error');
            }
        } catch (error) {
            Swal.fire('Error', 'Problema de conexión.', 'error');
        }
    }
}
function agregarLinea(contextEl) {
    // Determinar en qué bloque-input-container operar
    let container = null;
 
    if (contextEl) {
        const bloque = contextEl.closest
            ? (contextEl.closest('.bloque-asiento-dinamico') || contextEl.closest('.bloque-input-container'))
            : null;
        if (bloque) {
            container = bloque.classList.contains('bloque-input-container')
                ? bloque
                : bloque.querySelector('.bloque-input-container');
        }
    }
 
    // Fallback: primer bloque disponible
    if (!container) container = document.querySelector('.bloque-input-container');
    if (!container) return null;
 
    const div = document.createElement('div');
    div.className = 'fila-movimiento';
 
    div.innerHTML = `
        <div>
            <input type="number" step="0.01" name="debe[]"
                   class="input-papel input-monto input-debe"
                   placeholder="0.00" onkeyup="detectarLado(this)">
        </div>
        <div style="grid-column: 2 / 4; display: flex;">
            <input type="text" name="cuenta_nombre[]"
                   class="input-papel input-cuenta input-smart"
                   placeholder="Escribe la cuenta..."
                   onchange="buscarId(this)" oninput="buscarId(this)"
                   onblur="setTimeout(() => detectarCuentaCorriente(this), 200)"
                   autocomplete="off">
            <input type="hidden" name="cuenta_id[]"   class="hidden-id-cuenta"  value="0">
            <input type="hidden" name="entidad_id[]"  class="hidden-entidad-id" value="">
            <input type="hidden" name="vencimiento[]" class="hidden-vencimiento" value="">
        </div>
        <div>
            <input type="number" step="0.01" name="haber[]"
                   class="input-papel input-monto text-right input-haber"
                   placeholder="0.00" onkeyup="detectarLado(this)">
        </div>
        <div>
            <button type="button" class="btn-eliminar-fila"
                    onclick="eliminarLinea(this)" tabindex="-1"
                    title="Eliminar renglón">×</button>
        </div>
    `;
 
    container.appendChild(div);
 
    const nuevoInput = div.querySelector('.input-cuenta');
 
    if (typeof setupAutocomplete === 'function' && window._opcionesCuentas && window._opcionesCuentas.length) {
        setupAutocomplete(nuevoInput, window._opcionesCuentas);
    }
 
    nuevoInput.addEventListener('input', function () {
        if (typeof detectarVentaAutomatica === 'function') detectarVentaAutomatica(this);
    });
 
    return div;
}
 function eliminarLinea(btn) {
    // Scope al bloque-input-container correcto
    const container = btn.closest('.bloque-input-container');
    if (!container) return;
 
    const filas = container.querySelectorAll('.fila-movimiento');
 
    if (filas.length <= 1) {
        const row = filas[0];
        row.querySelectorAll('input').forEach(input => {
            input.value = '';
            input.readOnly = false;
            input.style.backgroundColor = 'transparent';
            if (input.classList.contains('input-cuenta')) {
                input.style.textAlign = 'left';
                input.style.fontStyle = 'normal';
                input.style.color = '#333';
            }
        });
        const primDebe = row.querySelector('.input-debe');
        if (primDebe) primDebe.focus();
        return;
    }
 
    btn.closest('.fila-movimiento').remove();
}
 
 
// ────────────────────────────────────────────────────────────
// [3] BUSCA la función autocompletarVenta() COMPLETA y reemplázala.
//     (aprox. línea 576)
// ────────────────────────────────────────────────────────────
function autocompletarVenta(roworigen, neto, iva) {
    const inputHaberOrigen = roworigen.querySelector('.input-haber');
    const inputDebeOrigen  = roworigen.querySelector('.input-debe');
 
    if (inputDebeOrigen) inputDebeOrigen.value = "";
    if (inputHaberOrigen) {
        inputHaberOrigen.value = neto.toFixed(2);
        if (typeof detectarLado === 'function') detectarLado(inputHaberOrigen);
    }
 
    // Agregar la fila de IVA dentro del mismo bloque
    agregarLinea(roworigen);
 
    const container = roworigen.closest('.bloque-input-container');
    const filas = container ? container.querySelectorAll('.fila-movimiento') : [];
    const filaIVA = filas[filas.length - 1];
 
    if (filaIVA) {
        const inpNombre = filaIVA.querySelector('.input-cuenta');
        const inpId     = filaIVA.querySelector('.hidden-id-cuenta');
        const inpHaber  = filaIVA.querySelector('.input-haber');
 
        if (inpNombre) inpNombre.value = "IVA Ventas";
        if (inpId)     inpId.value = "0";
        if (inpHaber)  {
            inpHaber.value = iva.toFixed(2);
            if (typeof detectarLado === 'function') detectarLado(inpHaber);
        }
    }
}
// ────────────────────────────────────────────────────────────
// Helper: devuelve el bloque .bloque-asiento-dinamico activo
// ────────────────────────────────────────────────────────────
function _getBloqueActivo() {
    const active = document.activeElement;
    if (active) {
        const bloque = active.closest('.bloque-asiento-dinamico');
        if (bloque) return bloque;
    }
    const todos = document.querySelectorAll('.bloque-asiento-dinamico');
    return todos.length > 0 ? todos[todos.length - 1] : null;
}
 
// ────────────────────────────────────────────────────────────
// Agregar un nuevo bloque de asiento al lote (máx. 6)
// ────────────────────────────────────────────────────────────
let _contadorAsientos = 1;
 
function agregarAsiento() {
    const MAX_ASIENTOS = 6;
    const todos = document.querySelectorAll('.bloque-asiento-dinamico');
 
    if (todos.length >= MAX_ASIENTOS) {
        Swal.fire({
            toast: true, position: 'top-end', icon: 'warning',
            title: `Máximo ${MAX_ASIENTOS} asientos por envío`,
            showConfirmButton: false, timer: 2500
        });
        return;
    }
 
    _contadorAsientos++;
    const idx = _contadorAsientos;
 
    const template = document.getElementById('asiento-1');
    if (!template) return;
 
    const nuevo = template.cloneNode(true);
 
    nuevo.id = `asiento-${idx}`;
    nuevo.dataset.asientoIdx = String(idx);
 
    const tituloEl = nuevo.querySelector('.bloque-numero');
    if (tituloEl) tituloEl.textContent = `Asiento #${idx}`;
 
    // Agregar botón eliminar
    const header = nuevo.querySelector('.bloque-asiento-header');
    if (header) {
        const btnElim = document.createElement('button');
        btnElim.type      = 'button';
        btnElim.className = 'btn-eliminar-bloque';
        btnElim.title     = 'Eliminar este asiento del lote';
        btnElim.innerHTML = '✕ Eliminar asiento';
        btnElim.onclick   = function () { eliminarAsiento(this); };
        header.appendChild(btnElim);
    }
 
    // Quitar autofocus y el id único del comprobante
    nuevo.querySelectorAll('[autofocus]').forEach(el => el.removeAttribute('autofocus'));
    const comprobanteClon = nuevo.querySelector('#input-comprobante');
    if (comprobanteClon) comprobanteClon.removeAttribute('id');
 
    // Limpiar todos los campos respetando alineaciones
    nuevo.querySelectorAll('input:not([type="hidden"])').forEach(inp => {
        inp.value = '';
        inp.readOnly = false;
        inp.style.backgroundColor = 'transparent';
        
        // FIX: Si es el campo HABER, mantener alineación derecha
        if (inp.classList.contains('input-haber')) {
            inp.style.textAlign = 'right';
        } else {
            inp.style.textAlign = 'left';
        }

        // Solo resetear estilos de fuente a los que NO son montos
        // para no interferir con la lógica visual de detectarLado
        if (!inp.classList.contains('input-monto')) {
            inp.style.fontStyle = 'normal';
            inp.style.color = '#333';
        }
    });

    nuevo.querySelectorAll('.hidden-id-cuenta').forEach(h  => { h.value = ''; });
    nuevo.querySelectorAll('.hidden-entidad-id').forEach(h => { h.value = ''; });
    nuevo.querySelectorAll('.hidden-vencimiento').forEach(h => { h.value = ''; });
 
    // Dejar solo la primera fila de movimientos
    const bloqueCont = nuevo.querySelector('.bloque-input-container');
    if (bloqueCont) {
        Array.from(bloqueCont.querySelectorAll('.fila-movimiento')).slice(1).forEach(f => f.remove());
    }
 
    document.getElementById('bloques-container').appendChild(nuevo);
 
    _initAutocompleteBloque(nuevo);
 
    nuevo.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const primerDia = nuevo.querySelector('.input-dia-asiento');
    if (primerDia) setTimeout(() => primerDia.focus(), 300);
 
    _actualizarContadorAsientos();
}
 
// ────────────────────────────────────────────────────────────
// Eliminar un bloque de asiento del lote
// ────────────────────────────────────────────────────────────
function eliminarAsiento(btn) {
    const bloque = btn.closest('.bloque-asiento-dinamico');
    if (!bloque || bloque.id === 'asiento-1') return;
 
    Swal.fire({
        title: '¿Eliminar este asiento?',
        text: 'Se perderán los datos del bloque.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#e74c3c',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar'
    }).then(r => {
        if (r.isConfirmed) {
            bloque.remove();
            _actualizarContadorAsientos();
        }
    });
}
 
// ────────────────────────────────────────────────────────────
// Actualizar contador visual y estado del botón "+ Añadir"
// ────────────────────────────────────────────────────────────
function _actualizarContadorAsientos() {
    const cantidad  = document.querySelectorAll('.bloque-asiento-dinamico').length;
    const MAX       = 6;
 
    const lbl = document.getElementById('lbl-contador-asientos');
    if (lbl) lbl.textContent = `${cantidad} de ${MAX}`;
 
    const btnAgregar = document.getElementById('btn-agregar-asiento');
    if (btnAgregar) {
        btnAgregar.disabled = cantidad >= MAX;
        btnAgregar.title    = cantidad >= MAX
            ? `Máximo ${MAX} asientos por envío`
            : 'Agregar otro asiento al lote';
    }
}
 
// ────────────────────────────────────────────────────────────
// Activar autocompletado en un bloque recién clonado
// ────────────────────────────────────────────────────────────
function _initAutocompleteBloque(bloque) {
    if (typeof setupAutocomplete !== 'function') return;
 
    const cuentasData = window._opcionesCuentas || [];
    bloque.querySelectorAll('.input-cuenta').forEach(inp => {
        inp.removeAttribute('list');
        if (cuentasData.length) setupAutocomplete(inp, cuentasData);
    });
 
    const comproData = window._opcionesCompro || [];
    bloque.querySelectorAll('.input-comprobante').forEach(inp => {
        inp.removeAttribute('list');
        if (comproData.length) setupAutocomplete(inp, comproData);
    });
}