// ============================================================================
// SISTEMA DE ATAJOS PERSONALIZABLES
// ============================================================================

const ATAJOS_DEFAULT = {
    nuevoRenglon: { key: 'Enter', ctrl: false, alt: false, shift: false },
    guardar: { key: 'Enter', ctrl: false, alt: true, shift: false },
    autocompletar: { key: 'Tab', ctrl: false, alt: false, shift: false },
    focoComprobante: { key: 'ArrowDown', ctrl: true, alt: false, shift: false },
    abrirCalculadora: { key: 'c', ctrl: false, alt: true, shift: false }
};

let atajosConfig = cargarAtajosConfig();

function cargarAtajosConfig() {
    try {
        const saved = localStorage.getItem('atajos_diario');
        return saved ? JSON.parse(saved) : { ...ATAJOS_DEFAULT };
    } catch (e) {
        console.error('Error cargando atajos:', e);
        return { ...ATAJOS_DEFAULT };
    }
}

function guardarAtajosConfig() {
    try {
        localStorage.setItem('atajos_diario', JSON.stringify(atajosConfig));
        actualizarBadgesVisual();
    } catch (e) {
        console.error('Error guardando atajos:', e);
    }
}

function esAtajo(evento, accion) {
    const config = atajosConfig[accion];
    if (!config) return false;

    const keyNormalizada = evento.key.toLowerCase();
    const configKeyNormalizada = config.key.toLowerCase();

    return (
        keyNormalizada === configKeyNormalizada &&
        !!evento.ctrlKey === !!config.ctrl &&
        !!evento.altKey === !!config.alt &&
        !!evento.shiftKey === !!config.shift
    );
}

function formatearAtajo(config) {
    let partes = [];
    if (config.ctrl) partes.push('Ctrl');
    if (config.alt) partes.push('Alt');
    if (config.shift) partes.push('Shift');

    const keyFormateada = config.key === ' ' ? 'Space' :
        config.key.length === 1 ? config.key.toUpperCase() :
            config.key;
    partes.push(keyFormateada);

    return partes.join('+');
}

function actualizarBadgesVisual() {
    const badgeTab = document.getElementById('badge-tab');
    const badgeEnter = document.getElementById('badge-enter');
    const badgeGuardar = document.getElementById('badge-guardar');

    if (badgeTab) badgeTab.textContent = formatearAtajo(atajosConfig.autocompletar);
    if (badgeEnter) badgeEnter.textContent = formatearAtajo(atajosConfig.nuevoRenglon);
    if (badgeGuardar) badgeGuardar.textContent = formatearAtajo(atajosConfig.guardar);
}

// ============================================================================
// LÓGICA DEL MODAL DE CONFIGURACIÓN
// ============================================================================

function abrirConfigAtajos() {
    const modal = document.getElementById('modalAtajos');
    if (!modal) return;

    // Cargar valores actuales
    document.getElementById('input-key-nuevoRenglon').value = formatearAtajo(atajosConfig.nuevoRenglon);
    document.getElementById('input-key-guardar').value = formatearAtajo(atajosConfig.guardar);
    document.getElementById('input-key-autocompletar').value = formatearAtajo(atajosConfig.autocompletar);
    document.getElementById('input-key-focoComprobante').value = formatearAtajo(atajosConfig.focoComprobante);
    document.getElementById('input-key-abrirCalculadora').value = formatearAtajo(atajosConfig.abrirCalculadora);

    modal.style.display = 'flex';

    // Configurar capturadores de teclas
    document.querySelectorAll('.key-recorder').forEach(input => {
        input.onclick = () => capturarTecla(input);
    });
}

let inputActivo = null;

function capturarTecla(input) {
    inputActivo = input;
    input.value = 'Presiona teclas...';
    input.style.background = '#fff3cd';

    const capturador = (e) => {
        e.preventDefault();
        e.stopPropagation();

        // Ignorar solo modificadores sueltos
        if (['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) return;

        const nuevoAtajo = {
            key: e.key,
            ctrl: e.ctrlKey,
            alt: e.altKey,
            shift: e.shiftKey
        };

        input.value = formatearAtajo(nuevoAtajo);
        input.style.background = 'transparent';

        // Guardar en variable temporal del input
        input.dataset.atajo = JSON.stringify(nuevoAtajo);

        document.removeEventListener('keydown', capturador, true);
        inputActivo = null;
    };

    document.addEventListener('keydown', capturador, true);
}

function guardarAtajos(event) {
    event.preventDefault();

    // Extraer configuraciones de los inputs
    const extraerAtajo = (id) => {
        const input = document.getElementById(id);
        return input.dataset.atajo ? JSON.parse(input.dataset.atajo) : null;
    };

    const nuevo = extraerAtajo('input-key-nuevoRenglon');
    const guardar = extraerAtajo('input-key-guardar');
    const auto = extraerAtajo('input-key-autocompletar');
    const foco = extraerAtajo('input-key-focoComprobante');
    const calc = extraerAtajo('input-key-abrirCalculadora');

    if (nuevo) atajosConfig.nuevoRenglon = nuevo;
    if (guardar) atajosConfig.guardar = guardar;
    if (auto) atajosConfig.autocompletar = auto;
    if (foco) atajosConfig.focoComprobante = foco;
    if (calc) atajosConfig.abrirCalculadora = calc;

    guardarAtajosConfig();
    document.getElementById('modalAtajos').style.display = 'none';

    Swal.fire({
        toast: true, position: 'top-end', icon: 'success',
        title: 'Atajos actualizados', showConfirmButton: false, timer: 2000
    });
}

function restaurarAtajosDefault() {
    Swal.fire({
        title: '¿Restaurar atajos por defecto?',
        text: 'Se perderá tu configuración actual',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sí, restaurar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            atajosConfig = { ...ATAJOS_DEFAULT };
            guardarAtajosConfig();
            abrirConfigAtajos(); // Reabrir con valores actualizados

            Swal.fire({
                toast: true, position: 'top-end', icon: 'success',
                title: 'Atajos restaurados', showConfirmButton: false, timer: 2000
            });
        }
    });
}

// ============================================================================
// LISTENER PRINCIPAL DE TECLADO (REFACTORIZADO)
// ============================================================================

document.addEventListener('keydown', function (e) {
    // ATAJO: Guardar asiento
    if (esAtajo(e, 'guardar')) {
        e.preventDefault();
        document.getElementById('btn-guardar').click();
        return;
    }

    const activeElement = document.activeElement;

    // Eliminar línea (Ctrl+Delete - FIJO, no personalizable)
    if (e.ctrlKey && e.key === 'Delete') {
        const row = activeElement.closest('.fila-movimiento');
        if (row) {
            e.preventDefault();
            const btn = row.querySelector('.btn-eliminar-fila');
            if (btn) eliminarLinea(btn);
        }
        return;
    }

    // ATAJO: Nuevo renglón desde inputs de monto
    if (esAtajo(e, 'nuevoRenglon') &&
        (activeElement.classList.contains('input-debe') || activeElement.classList.contains('input-haber'))) {
        e.preventDefault();
        agregarLinea();
        const inputsCuenta = document.querySelectorAll('.input-cuenta');
        inputsCuenta[inputsCuenta.length - 1].focus();
        return;
    }


    // ATAJO: Autocompletar
    if (esAtajo(e, 'autocompletar') && activeElement.classList.contains('input-smart')) {
        const val = activeElement.value.toLowerCase();
        const listId = activeElement.getAttribute('list');

        if (val.length > 0 && listId) {
            const dataList = document.getElementById(listId);
            if (dataList) {
                const options = dataList.options;
                let match = null;

                for (let i = 0; i < options.length; i++) {
                    const rawText = options[i].value.toLowerCase();
                    const parts = rawText.split(' - ');
                    const nombreLimpio = parts.length > 1 ? parts[1] : rawText;
                    if (nombreLimpio.startsWith(val)) { match = options[i].value; break; }
                }

                if (!match) {
                    for (let i = 0; i < options.length; i++) {
                        if (options[i].value.toLowerCase().includes(val)) { match = options[i].value; break; }
                    }
                }

                if (match) {
                    e.preventDefault();
                    activeElement.value = match;
                    if (activeElement.classList.contains('input-cuenta')) {
                        buscarId(activeElement);
                        detectarVentaAutomatica(activeElement);
                        activeElement.closest('.fila-movimiento').querySelector('.input-debe').focus();
                    }
                }
            }
        }
        return;
    }

    // Navegación horizontal (Ctrl+Flechas - FIJO)
    if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && e.ctrlKey) {
        if (activeElement.tagName === 'INPUT') {
            const row = activeElement.closest('.fila-movimiento');
            if (row) {
                if (activeElement.classList.contains('input-debe') && e.key === 'ArrowRight') {
                    row.querySelector('.input-cuenta').focus();
                } else if (activeElement.classList.contains('input-cuenta')) {
                    if (e.key === 'ArrowRight') row.querySelector('.input-haber').focus();
                    if (e.key === 'ArrowLeft') row.querySelector('.input-debe').focus();
                } else if (activeElement.classList.contains('input-haber') && e.key === 'ArrowLeft') {
                    row.querySelector('.input-cuenta').focus();
                }
            }
        }
        return;
    }

    // ATAJO: Ir a comprobante
    if (esAtajo(e, 'focoComprobante')) {
        e.preventDefault();
        const inputComprobante = document.getElementById('input-comprobante');
        if (inputComprobante) {
            inputComprobante.focus();
            inputComprobante.click();
        }
        return;
    }
});

// ============================================================================
// DOMCONTENTLOADED - INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // ACTUALIZAR BADGES VISUAL AL CARGAR LA PÁGINA
    actualizarBadgesVisual();

    const params = new URLSearchParams(window.location.search);

    // --- MODO AJUSTE INDIVIDUAL (CORREGIDO FINAL) ---
    if (params.get('modo') === 'ajuste_single') {
        const monto = parseFloat(params.get('monto'));
        const textoComprobante = params.get('leyenda');
        const esSalida = params.get('es_salida') === '1';
        const idBanco = params.get('id_banco');

        const fmt = (n) => Number(n).toString(); // Quita decimales .00

        const container = document.getElementById('input-container');

        // 1. LIMPIEZA SEGURA (NO BORRAMOS TODO, DEJAMOS 1)
        while (container.children.length > 1) {
            container.lastElementChild.remove();
        }

        // Si estaba vacío por error, restauramos
        if (container.children.length === 0) {
            container.innerHTML = `<div class="fila-movimiento">
                <div class="col-debe-val"><input type="number" step="0.01" name="debe[]" class="input-papel input-monto input-debe" placeholder="0.00" onkeyup="detectarLado(this)"></div>
                <div style="grid-column: 2 / 4; display: flex;"><input list="cuentas-list" class="input-papel input-cuenta input-smart" placeholder="Cuenta..." onchange="buscarId(this)" required><input type="hidden" name="cuenta_id[]" class="hidden-id-cuenta"></div>
                <div class="col-haber-val"><input type="number" step="0.01" name="haber[]" class="input-papel input-monto text-right input-haber" placeholder="0.00" onkeyup="detectarLado(this)"></div>
                <div class="col-accion"><button type="button" class="btn-eliminar-fila" onclick="eliminarLinea(this)">×</button></div>
            </div>`;
        }

        // Limpiar fila 1 (Reciclaje)
        const limpiarFila = (row) => {
            row.querySelectorAll('input').forEach(i => {
                i.value = ''; i.readOnly = false; i.style.backgroundColor = 'transparent';
                if (i.classList.contains('input-cuenta')) {
                    i.style.textAlign = 'left'; i.style.fontStyle = 'normal'; i.style.color = '#333';
                }
            });
        };
        limpiarFila(container.children[0]);

        // Agregar fila 2 (Ahora es seguro porque fila 1 existe)
        agregarLinea();

        const filas = container.querySelectorAll('.fila-movimiento');
        let filaBanco, filaContra;

        // 2. ORDEN VISUAL (Arriba DEBE, Abajo HABER)
        if (esSalida) {
            // GASTO:
            // Línea 1 (Arriba): CUENTA GASTO (Debe) -> Foco aquí
            // Línea 2 (Abajo): BANCO (Haber)
            filaContra = filas[0];
            filaBanco = filas[1];

            filaContra.querySelector('.input-debe').value = fmt(monto);
            detectarLado(filaContra.querySelector('.input-debe'));

            filaBanco.querySelector('.input-haber').value = fmt(monto);
            detectarLado(filaBanco.querySelector('.input-haber'));

        } else {
            // INGRESO:
            // Línea 1 (Arriba): BANCO (Debe)
            // Línea 2 (Abajo): CUENTA INGRESO (Haber) -> Foco aquí
            filaBanco = filas[0];
            filaContra = filas[1];

            filaBanco.querySelector('.input-debe').value = fmt(monto);
            detectarLado(filaBanco.querySelector('.input-debe'));

            filaContra.querySelector('.input-haber').value = fmt(monto);
            detectarLado(filaContra.querySelector('.input-haber'));
        }

        // 3. ASIGNAR BANCO
        const inpCuentaB = filaBanco.querySelector('.input-cuenta');
        const hiddenId = filaBanco.querySelector('.hidden-id-cuenta');
        const options = document.getElementById('cuentas-list').options;
        for (let i = 0; i < options.length; i++) {
            if (options[i].getAttribute('data-id') === idBanco) {
                inpCuentaB.value = options[i].value;
                hiddenId.value = idBanco;
                // inpCuentaB.readOnly = true; // Opcional: Bloquear para que no lo cambien
                break;
            }
        }

        // 4. CABECERAS
        const inputTipo = document.getElementById('input-comprobante');
        if (inputTipo) inputTipo.value = textoComprobante;

        const inputLeyenda = document.querySelector('input[name="leyenda"]');
        if (inputLeyenda) inputLeyenda.value = "Ajuste Conciliación";

        // 5. BUMERÁN
        const nextUrl = params.get('next');
        if (nextUrl) {
            let inputNext = document.querySelector('input[name="next_url"]');
            if (!inputNext) {
                inputNext = document.createElement('input');
                inputNext.type = 'hidden'; inputNext.name = 'next_url';
                document.getElementById('form-diario').appendChild(inputNext);
            }
            inputNext.value = nextUrl;
        }

        // 6. FOCO Y AVISO
        filaContra.querySelector('.input-cuenta').focus();
        Swal.fire({
            toast: true, position: 'top-end', icon: 'info',
            title: 'Completa la cuenta faltante', showConfirmButton: false, timer: 3000
        });
    }

    // ============================================================================
    // SETUP AUTOCOMPLETADO PERSONALIZADO
    // ============================================================================

    // 1. Cargar Datos de Cuentas
    const opcionesCuentas = [];
    document.querySelectorAll('#cuentas-list option').forEach(opt => {
        opcionesCuentas.push({ texto: opt.value, valor: opt.value, id: opt.getAttribute('data-id') });
    });

    // 2. Cargar Datos de Comprobantes
    const opcionesCompro = [];
    document.querySelectorAll('#lista-comprobantes option').forEach(opt => {
        opcionesCompro.push({ texto: opt.value, valor: opt.value });
    });

    // 3. Aplicar a inputs existentes (El primero y el comprobante)
    const primerCuenta = document.querySelector('.input-cuenta');
    if (primerCuenta) setupAutocomplete(primerCuenta, opcionesCuentas);

    const inputCompro = document.getElementById('input-comprobante');
    if (inputCompro) {
        inputCompro.removeAttribute('list');  // 👈 Esta línea faltaba
        setupAutocomplete(inputCompro, opcionesCompro);
    }

    // 4. IMPORTANTE: Sobrescribir agregarLinea para que las nuevas filas tengan autocompletado
    const oldAgregar = window.agregarLinea;
    window.agregarLinea = function () {
        // Llamar a la función original para que cree el HTML
        const container = document.getElementById('input-container');
        // Clonamos lógica manual porque necesitamos referencia al nuevo input
        const newRow = container.children[0].cloneNode(true);
        newRow.querySelectorAll('input').forEach(input => {
            input.value = ''; input.readOnly = false;
            input.style.backgroundColor = 'transparent';
            input.style.textAlign = 'left'; input.style.fontStyle = 'normal'; input.style.color = '#333';

        });
        container.appendChild(newRow); // Agregado manual

        // Aplicar magia al nuevo input
        const newInput = newRow.querySelector('.input-cuenta');
        // Quitar el atributo list nativo para que no salga el negro feo
        newInput.removeAttribute('list');
        setupAutocomplete(newInput, opcionesCuentas);

        return newRow;
    }
});

// ============================================================================
// ASISTENTE INTELIGENTE (VENTAS Y CAPITAL)
// ============================================================================

function detectarVentaAutomatica(inputCuenta) {
    const val = inputCuenta.value.toLowerCase();
    const row = inputCuenta.closest('.fila-movimiento');

    // 1. ASISTENTE DE VENTAS
    // Detectar si escribe "Ventas" (y no es costo, ni iva, ni deudores)
    if (val.includes('ventas') &&
        !val.includes('costo') && !val.includes('iva') && !val.includes('deudores')) {
        const usaIVA = document.getElementById('check-iva').checked;
        if (!usaIVA) return;

        const haberInput = row.querySelector('.input-haber');
        if (haberInput.value !== "") return; // Si ya escribió algo, no molestamos

        let totalDebe = 0;
        document.querySelectorAll('.input-debe').forEach(inp => { totalDebe += parseFloat(inp.value) || 0; });

        if (totalDebe > 0) {
            // ... (Lógica de Ventas original intacta) ...
            const mainContainer = document.getElementById('main-container');
            let tasas = [];
            try { tasas = JSON.parse(mainContainer.getAttribute('data-tasas-iva') || '[]'); }
            catch (e) { console.error("Error leyendo tasas", e); }

            let opcionesHTML = '';
            if (tasas.length > 0) {
                tasas.forEach(t => { opcionesHTML += `<option value="${t.valor}">${t.nombre} (${t.valor}%)</option>`; });
            } else { opcionesHTML = '<option value="22">Básica (22%)</option>'; }

            Swal.fire({
                title: 'Asistente de Ventas',
                html: `
                    <div style="text-align:left; font-size:0.95em; margin-bottom:10px;">
                        <p>Total ingresado en DEBE: <b>$${totalDebe.toFixed(2)}</b></p>
                        <hr style="border-top:1px dashed #eee; margin:10px 0;">
                        <label style="display:block; margin-bottom:5px; font-weight:bold; color:#2c3e50;">1. Configuración de Tasa:</label>
                        <select id="swal-tasa" class="swal2-input" style="width: 100%; margin-top:5px;">${opcionesHTML}</select>
                        <label style="display:block; margin-top:15px; margin-bottom:5px; font-weight:bold; color:#2c3e50;">2. Cálculo:</label>
                        <div style="background:#f9f9f9; padding:10px; border-radius:5px; border:1px solid #eee;">
                            <label style="display:flex; align-items:center; gap:8px; cursor:pointer; margin-bottom:8px;">
                                <input type="radio" name="tipo_calculo" value="incluido" checked> <span><b>IVA Incluido</b> (Dividir)</span>
                            </label>
                            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
                                <input type="radio" name="tipo_calculo" value="mas_iva"> <span><b>Precio Neto</b> (Sumar)</span>
                            </label>
                        </div>
                    </div>
                `,
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: 'Calcular',
                cancelButtonText: 'Cancelar',
                confirmButtonColor: '#27ae60'
            }).then((result) => {
                if (result.isConfirmed) {
                    const tasa = parseFloat(document.getElementById('swal-tasa').value);
                    const modo = document.querySelector('input[name="tipo_calculo"]:checked').value;
                    let neto = 0, iva = 0;

                    if (modo === 'incluido') {
                        const factor = 1 + (tasa / 100);
                        neto = totalDebe / factor;
                        iva = totalDebe - neto;
                    } else {
                        neto = totalDebe;
                        iva = totalDebe * (tasa / 100);
                        Swal.fire({ toast: true, position: 'top-end', icon: 'info', title: 'Recuerda ajustar el DEBE.', timer: 3000 });
                    }
                    autocompletarVenta(row, neto, iva);
                }
            });
        }

        // 2. NUEVO: ASISTENTE DE CAPITAL (ECUACIÓN PATRIMONIAL)
    } else if (val.includes('capital')) {

        let totalDebe = 0;
        let totalHaber = 0;

        // Sumamos todo lo que hay en el asiento actualmente
        document.querySelectorAll('.input-debe').forEach(el => { totalDebe += parseFloat(el.value) || 0; });
        document.querySelectorAll('.input-haber').forEach(el => { totalHaber += parseFloat(el.value) || 0; });

        // Activo (Debe) - Pasivo (Haber) = Patrimonio (Capital)
        let diferencia = totalDebe - totalHaber;

        // Solo sugerimos si hay saldo positivo (Activo > Pasivo)
        if (diferencia > 0) {
            const haberInput = row.querySelector('.input-haber');
            // Solo si el campo está vacío para no sobrescribir datos
            if (haberInput.value === "") {
                Swal.fire({
                    title: '¿Calcular Capital Inicial?',
                    html: `Activo ($${totalDebe}) - Pasivo ($${totalHaber}) = <b>$${diferencia.toFixed(2)}</b><br>¿Deseas autocompletar el Capital?`,
                    icon: 'info',
                    showCancelButton: true,
                    confirmButtonColor: '#2c3e50',
                    confirmButtonText: 'Sí, cuadrar',
                    cancelButtonText: 'No'
                }).then((result) => {
                    if (result.isConfirmed) {
                        haberInput.value = diferencia.toFixed(2);
                        detectarLado(haberInput);
                        // Opcional: enfocar el botón de guardar o descripción
                    }
                });
            }
        }
    }
}


/* EN DIARIO.JS - Actualizar autocompletarVenta */

function autocompletarVenta(roworigen, neto, iva) {
    // 1. Llenar la fila original (Venta neta)
    // Asumiendo que roworigen ya existe y es la fila donde escribiste "Ventas"
    const inputHaberOrigen = roworigen.querySelector('.input-haber');
    const inputDebeOrigen = roworigen.querySelector('.input-debe');

    // Limpiamos el Debe por si acaso
    if (inputDebeOrigen) inputDebeOrigen.value = "";

    // Ponemos el Neto en el Haber
    if (inputHaberOrigen) {
        inputHaberOrigen.value = neto.toFixed(2);
        if (typeof detectarLado === 'function') detectarLado(inputHaberOrigen);
    }

    // 2. AGREGAR FILA DE IVA (Usando la nueva función robusta)
    // Llamamos a agregarLinea para crear una fila BIEN FORMADA
    agregarLinea();

    // Buscamos la fila que acabamos de crear (la última)
    const container = document.getElementById('input-container');
    const filas = container.querySelectorAll('.fila-movimiento');
    const filaIVA = filas[filas.length - 1];

    if (filaIVA) {
        // Llenamos los datos del IVA
        const inpNombre = filaIVA.querySelector('.input-cuenta');
        const inpId = filaIVA.querySelector('.hidden-id-cuenta');
        const inpHaber = filaIVA.querySelector('.input-haber');

        if (inpNombre) inpNombre.value = "IVA Ventas"; // O el nombre que uses
        // IMPORTANTE: Aquí deberías poner el ID real del IVA si lo tienes a mano, si no '0'
        if (inpId) inpId.value = "0";

        if (inpHaber) {
            inpHaber.value = iva.toFixed(2);
            if (typeof detectarLado === 'function') detectarLado(inpHaber);
        }
    }
}
// ============================================================================
// FUNCIONES UI BÁSICAS
// ============================================================================

/* EN DIARIO.JS - Reemplazar/Agregar esta función fundamental */

function agregarLinea() {
    const container = document.getElementById('input-container'); // Asegúrate que este ID exista en tu HTML (el div que envuelve las filas)
    if (!container) return;

    // 1. Crear el contenedor de la fila
    const div = document.createElement('div');
    div.className = 'fila-movimiento';
    div.style.display = 'flex'; // Asegurar estilo si falta CSS
    div.style.gap = '10px';
    div.style.marginBottom = '10px';

    // 2. INYECTAR EL HTML COMPLETO (Aquí estaba el fallo, antes estaba vacío)
    div.innerHTML = `
        <input type="hidden" name="cuenta_id[]" class="hidden-id-cuenta" value="0">
        <input type="hidden" name="entidad_id[]" class="hidden-entidad-id" value="">
        <input type="hidden" name="vencimiento[]" class="hidden-vencimiento" value="">
        
        <input type="text" name="cuenta_nombre[]" class="input-cuenta input-papel" 
        placeholder="Selecciona cuenta..." autocomplete="off" 
        onblur="setTimeout(() => detectarCuentaCorriente(this), 200)"
         style="flex: 2; min-width: 200px;">
        
        <input type="number" step="0.01" name="debe[]" class="input-debe input-papel" 
               placeholder="0.00" oninput="detectarLado(this)" style="flex: 1;">
        
        <input type="number" step="0.01" name="haber[]" class="input-haber input-papel" 
               placeholder="0.00" oninput="detectarLado(this)" style="flex: 1;">
        
        <button type="button" class="btn-delete" onclick="eliminarLinea(this)" tabindex="-1" style="color:red; border:none; background:none; cursor:pointer;">✖</button>
    `;

    // 3. Agregar al DOM
    container.appendChild(div);

    // 4. REACTIVAR LA INTELIGENCIA (Autocompletado y Eventos)
    // Esto es vital: la nueva fila es "tonta" hasta que le conectamos el cerebro
    const nuevoInput = div.querySelector('.input-cuenta');

    // Conectar autocompletado (asumiendo que setupAutocomplete existe y listaComprobantes/cuentas está global)
    // Si tienes la lista de cuentas en una variable global 'listaCuentas' o en el HTML:
    const mainData = document.getElementById('main-container');
    let cuentasData = [];
    try { cuentasData = JSON.parse(mainData.getAttribute('data-cuentas') || '[]'); } catch (e) { }

    if (typeof setupAutocomplete === 'function') {
        setupAutocomplete(nuevoInput, cuentasData); // Reactivamos el autocompletado
    }

    // Conectar el detector de ventas al nuevo input
    nuevoInput.addEventListener('input', function () {
        if (typeof detectarVentaAutomatica === 'function') detectarVentaAutomatica(this);
    });

    return div; // Devolvemos la fila por si alguien la necesita
}

function eliminarLinea(btn) {
    const container = document.getElementById('input-container');
    const filas = container.querySelectorAll('.fila-movimiento');
    if (filas.length <= 1) {
        const row = filas[0];
        row.querySelectorAll('input').forEach(input => {
            input.value = ''; input.readOnly = false; input.style.backgroundColor = 'transparent';
            if (input.classList.contains('input-cuenta')) {
                input.style.textAlign = 'left'; input.style.fontStyle = 'normal'; input.style.color = '#333';
            }
        });
        row.querySelector('.input-debe').focus();
        return;
    }
    const row = btn.closest('.fila-movimiento');
    row.remove();
}

function toggleIVA() {
    const check = document.getElementById('check-iva');
    check.nextElementSibling.style.color = check.checked ? "#1a73e8" : "#666";
}

function detectarLado(input) {
    const row = input.closest('.fila-movimiento');
    const debeInput = row.querySelector('.input-debe');
    const haberInput = row.querySelector('.input-haber');
    const cuentaInput = row.querySelector('.input-cuenta');

    if (input.classList.contains('input-debe')) {
        if (input.value !== "") {
            haberInput.readOnly = true; haberInput.style.backgroundColor = '#f0f0f0'; haberInput.value = "";
            cuentaInput.style.textAlign = 'left'; cuentaInput.style.fontStyle = 'normal';
            cuentaInput.style.color = '#333'; cuentaInput.style.paddingRight = '0';
        } else {
            haberInput.readOnly = false; haberInput.style.backgroundColor = 'transparent';
        }
    } else if (input.classList.contains('input-haber')) {
        if (input.value !== "") {
            debeInput.readOnly = true; debeInput.style.backgroundColor = '#f0f0f0'; debeInput.value = "";
            cuentaInput.style.textAlign = 'right'; cuentaInput.style.fontStyle = 'italic';
            cuentaInput.style.color = '#555'; cuentaInput.style.paddingRight = '10px';
        } else {
            debeInput.readOnly = false; debeInput.style.backgroundColor = 'transparent';
            cuentaInput.style.textAlign = 'left'; cuentaInput.style.fontStyle = 'normal';
            cuentaInput.style.color = '#333'; cuentaInput.style.paddingRight = '0';
        }
    }
}

function buscarId(inputElement) {
    const val = inputElement.value;
    const list = document.getElementById('cuentas-list');
    const hiddenInputId = inputElement.nextElementSibling;
    const options = list.children;
    let foundId = "";
    for (let i = 0; i < options.length; i++) {
        if (options[i].value === val) {
            foundId = options[i].getAttribute('data-id');
            break;
        }
    }
    hiddenInputId.value = foundId;
}
// ============================================================================
// AUDITORÍA
// ============================================================================
function auditoriaFinal(event) {
    const inputComprobante = document.getElementById('input-comprobante');
    const tipoTexto = (inputComprobante.value || "").toLowerCase().trim();
    const usaIVA = document.getElementById('check-iva') ? document.getElementById('check-iva').checked : false;

    // NUEVO ESCUDO: preventDefault() es la magia que evita que la página se recargue
    const mostrarError = (titulo, mensaje) => {
        if (event) { event.preventDefault(); }
        Swal.fire({ icon: 'error', title: titulo, text: mensaje, confirmButtonColor: '#2c3e50' });
    };

    if (tipoTexto === "") { mostrarError("Falta información", "Indica un Tipo de Comprobante."); return false; }

    let totalDebe = 0; let totalHaber = 0;
    let cuentasNombres = []; let movimientos = [];
    const filas = document.querySelectorAll('#input-container .fila-movimiento');

    for (let i = 0; i < filas.length; i++) {
        const fila = filas[i];
        const textoInput = fila.querySelector('.input-cuenta').value;
        let nombreLimpio = "";
        if (textoInput) nombreLimpio = textoInput.includes('-') ? textoInput.split('-')[1].trim().toLowerCase() : textoInput.trim().toLowerCase();

        const debe = parseFloat(fila.querySelector('.input-debe').value) || 0;
        const haber = parseFloat(fila.querySelector('.input-haber').value) || 0;

        // NUEVO ESCUDO ANTI-HACKERS: Bloquear negativos en el Frontend
        if (debe < 0 || haber < 0) {
            mostrarError("Monto Inválido", "En contabilidad no existen los montos negativos. Usa el Debe o el Haber según corresponda.");
            return false;
        }

        if (nombreLimpio || debe > 0 || haber > 0) {
            if (!nombreLimpio && (debe > 0 || haber > 0)) { mostrarError("Incompleto", "Faltan nombres de cuentas."); return false; }
            cuentasNombres.push(nombreLimpio);
            movimientos.push({ nombre: nombreLimpio, debe, haber });
            totalDebe += debe; totalHaber += haber;
        }
    }

    if (cuentasNombres.length === 0) { mostrarError("Vacío", "No hay cuentas."); return false; }
    if (Math.abs(totalDebe - totalHaber) > 0.01) { mostrarError("Error", `El asiento no cuadra.\nDiferencia: ${Math.abs(totalDebe - totalHaber).toFixed(2)}`); return false; }

    return true;
}
// ============================================================================
// LÓGICA DE BORRADO
// ============================================================================
function ejecutarBorradoMasivo() {
    const checks = document.querySelectorAll('.check-borrar:checked');
    if (checks.length === 0) { Swal.fire('Info', 'Selecciona asientos.', 'info'); return; }
    Swal.fire({
        title: `¿Borrar ${checks.length}?`, icon: 'warning', showCancelButton: true, confirmButtonColor: '#c0392b', confirmButtonText: 'Sí, borrar'
    }).then((result) => {
        if (result.isConfirmed) {
            const form = document.getElementById('form-borrado-masivo');
            checks.forEach(c => {
                const input = document.createElement('input'); input.type = 'hidden'; input.name = 'ids_a_borrar'; input.value = c.value; form.appendChild(input);
            });
            form.submit();
        }
    });
}
function confirmarBorrado(id) {
    Swal.fire({ title: '¿Eliminar asiento?', icon: 'warning', showCancelButton: true, confirmButtonColor: '#c0392b', confirmButtonText: 'Sí' }).then((r) => {
        if (r.isConfirmed) {
            const form = document.getElementById('form-borrar-individual');
            form.action = '/borrar_asiento/' + id; form.submit();
        }
    })
}
// ============================================================================
// AUTOCOMPLETADO PERSONALIZADO
// ============================================================================
function setupAutocomplete(inp, arrDatos) {
    let currentFocus;
    // Función principal al escribir
    // Función principal al escribir
    inp.addEventListener("input", function (e) {
        this.dataset.ignorarAsistente = "false";
        let a, b, i, val = this.value;
        closeAllLists();
        if (!val) return false;
        currentFocus = -1;

        // Crear el contenedor de la lista
        a = document.createElement("DIV");
        a.setAttribute("id", this.id + "autocomplete-list");
        a.setAttribute("class", "autocomplete-items");
        this.parentNode.style.position = "relative";
        this.parentNode.appendChild(a);

        // ============================================================================
        // ASISTENTE CONTABLE INTEGRAL (Ventas, Capital, IVA, Descuentos 2.0)
        // ============================================================================

        function detectarVentaAutomatica(inputCuenta) {
            const val = inputCuenta.value.toLowerCase();
            const row = inputCuenta.closest('.fila-movimiento');

            if (inputCuenta.dataset.ignorarAsistente === "true") return;

            // Callback para activar el escudo si el usuario cancela
            const onCancel = () => {
                inputCuenta.dataset.ignorarAsistente = "true";
                setTimeout(() => inputCuenta.focus(), 100);
            };

            // 1. ASISTENTE DE VENTAS (INTEGRACIÓN INTELIGENTE)
            // Usamos la nueva función global que analiza la naturaleza contable
            if (typeof esVentaDeResultado === 'function' && esVentaDeResultado(val)) {

                const usaIVA = document.getElementById('check-iva').checked;
                if (!usaIVA) return;

                const haberInput = row.querySelector('.input-haber');
                if (haberInput.value !== "") return; // Si ya escribió algo, no molestamos

                let totalDebe = 0;
                document.querySelectorAll('.input-debe').forEach(inp => { totalDebe += parseFloat(inp.value) || 0; });

                if (totalDebe > 0) {
                    // Función auxiliar para mostrar el modal (ya la tienes definida al final de diario.js)
                    preguntarVenta(row, totalDebe, () => {
                        // Callback si cancela: Bloquear asistente temporalmente
                        inputCuenta.dataset.ignorarAsistente = "true";
                        setTimeout(() => inputCuenta.focus(), 100);
                    });
                }

                // 2. ASISTENTE DE CAPITAL (Sin cambios)
            } else if (val.includes('capital')) {
                let totalDebe = 0, totalHaber = 0;
                document.querySelectorAll('.input-debe').forEach(el => { totalDebe += parseFloat(el.value) || 0; });
                document.querySelectorAll('.input-haber').forEach(el => { totalHaber += parseFloat(el.value) || 0; });
                let diferencia = totalDebe - totalHaber;
                if (diferencia > 0) {
                    const haberInput = row.querySelector('.input-haber');
                    if (haberInput.value === "") {
                        Swal.fire({
                            title: '¿Calcular Capital?',
                            html: `Diferencia detectada: <b>$${diferencia.toFixed(2)}</b>`,
                            icon: 'info', showCancelButton: true, confirmButtonText: 'Sí, cuadrar'
                        }).then((r) => { if (r.isConfirmed) { haberInput.value = diferencia.toFixed(2); detectarLado(haberInput); } });
                    }
                }

                // 3. ASISTENTE DE IVA COMPRAS (Sin cambios)
            } else if (val.includes('iva') && (val.includes('compras') || val.includes('credito') || val.includes('crédito'))) {
                let base = 0;
                document.querySelectorAll('.input-debe').forEach(inp => { if (!row.contains(inp)) base += parseFloat(inp.value) || 0; });
                if (base > 0 && row.querySelector('.input-debe').value === "") preguntarCompra(row, base, row.querySelector('.input-debe'));

                // 4. ASISTENTE DE DESCUENTOS (Lógica Inversa: Bruto a Neto)
            } else if (val.includes('descuentos') || val.includes('bonificaciones')) {

                let tipoDescuento = '';
                let montoBrutoDetectado = 0;
                let inputDestino = null;

                // D.1 Descuentos Concedidos (Pérdida -> DEBE). Buscamos dinero en el DEBE.
                if (val.includes('concedidos') || val.includes('cedidos')) {
                    tipoDescuento = 'concedido';
                    inputDestino = row.querySelector('.input-debe');
                    document.querySelectorAll('.input-debe').forEach(inp => {
                        if (!row.contains(inp)) montoBrutoDetectado += parseFloat(inp.value) || 0;
                    });

                    // D.2 Descuentos Obtenidos (Ganancia -> HABER). Buscamos deuda en el HABER.
                } else if (val.includes('obtenidos') || val.includes('ganados')) {
                    tipoDescuento = 'obtenido';
                    inputDestino = row.querySelector('.input-haber');
                    document.querySelectorAll('.input-haber').forEach(inp => {
                        if (!row.contains(inp)) montoBrutoDetectado += parseFloat(inp.value) || 0;
                    });
                }

                if (tipoDescuento && montoBrutoDetectado > 0 && inputDestino.value === "") {
                    // Preparamos las tasas
                    const mainContainer = document.getElementById('main-container');
                    let tasas = [];
                    try { tasas = JSON.parse(mainContainer.getAttribute('data-tasas-iva') || '[]'); } catch (e) { }
                    let opcionesHTML = tasas.length > 0 ? '' : '<option value="22">Básica (22%)</option>';
                    tasas.forEach(t => { opcionesHTML += `<option value="${t.valor}">${t.nombre} (${t.valor}%)</option>`; });

                    Swal.fire({
                        title: 'Calculadora de Descuentos',
                        html: `
                    <div style="text-align:left; font-size:0.9em;">
                        <p>1. Monto con IVA detectado (Bruto):</p>
                        <input type="number" id="swal-bruto" class="swal2-input" value="${montoBrutoDetectado.toFixed(2)}" step="0.01">
                        <p style="margin-top:10px;">2. Tasa de IVA (para hallar el Neto):</p>
                        <select id="swal-tasa-desc" class="swal2-input" style="height:40px;">${opcionesHTML}</select>
                        <p style="margin-top:10px;">3. Porcentaje de Descuento (sobre Neto):</p>
                        <div style="display:flex; align-items:center; gap:5px;">
                            <input type="number" id="swal-porc" class="swal2-input" placeholder="Ej: 5" style="width:100px;">
                            <span style="font-weight:bold; font-size:1.2em;">%</span>
                        </div>
                    </div>
                `,
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonText: 'Calcular y Ajustar',
                        cancelButtonText: 'Cancelar',
                        confirmButtonColor: '#e67e22',
                        preConfirm: () => {
                            return {
                                bruto: parseFloat(document.getElementById('swal-bruto').value) || 0,
                                tasa: parseFloat(document.getElementById('swal-tasa-desc').value) || 0,
                                porc: parseFloat(document.getElementById('swal-porc').value) || 0
                            }
                        }
                    }).then((result) => {
                        if (result.isConfirmed) {
                            const { bruto, tasa, porc } = result.value;
                            const neto = bruto / (1 + (tasa / 100)); // Neto real
                            const montoDescuento = neto * (porc / 100); // Descuento sobre neto

                            inputDestino.value = montoDescuento.toFixed(2);
                            detectarLado(inputDestino);
                            ajustarContraparteDescuento(tipoDescuento, bruto, montoDescuento, row);
                            actualizarTotales();
                        } else {
                            onCancel(); // Activamos escudo si cancela
                        }
                    });
                }
            }
        }
        // ============================================================
        // LÓGICA DE BÚSQUEDA Y FILTRADO (ESTO ES LO QUE FALTABA)
        // ============================================================

        const valUpper = val.toUpperCase();

        // 1. Filtrar coincidencias (Buscar texto dentro del nombre)
        let resultados = arrDatos.filter(item => item.texto.toUpperCase().includes(valUpper));

        // 2. Ordenar inteligentemente
        resultados.sort((a, b) => {
            const txtA = a.texto.toUpperCase();
            const txtB = b.texto.toUpperCase();

            // Prioridad A: Empieza con lo que escribiste (Ej: "Vent" -> "Ventas")
            const empiezaA = txtA.startsWith(valUpper);
            const empiezaB = txtB.startsWith(valUpper);

            if (empiezaA && !empiezaB) return -1;
            if (!empiezaA && empiezaB) return 1;

            // Prioridad B: El más corto gana (Ej: "Ventas" gana a "Ventas Exentas")
            return txtA.length - txtB.length;
        });

        // 3. DEFINIR LA VARIABLE resultadosFinales (Limitar a 10)
        const resultadosFinales = resultados.slice(0, 10);

        // ============================================================
        // --- RENDERIZADO LIMPIO (SIN NEGRITAS) ---
        for (i = 0; i < resultadosFinales.length; i++) {
            b = document.createElement("DIV");

            // Texto simple, sin etiquetas HTML extrañas
            b.innerHTML = resultadosFinales[i].texto;

            // Input oculto con el valor real y el ID
            b.innerHTML += "<input type='hidden' value='" + resultadosFinales[i].valor + "' data-id='" + (resultadosFinales[i].id || '') + "'>";

            b.addEventListener("click", function (e) {
                inp.value = this.getElementsByTagName("input")[0].value;
                const dataId = this.getElementsByTagName("input")[0].getAttribute('data-id');

                if (inp.classList.contains('input-cuenta')) {
                    const hiddenInput = inp.nextElementSibling;
                    if (hiddenInput) hiddenInput.value = dataId;
                    detectarVentaAutomatica(inp);
                }
                closeAllLists();
            });
            a.appendChild(b);
        }
    });
    // Navegación con teclado
    inp.addEventListener("keydown", function (e) {
        let x = document.getElementById(this.id + "autocomplete-list");
        if (x) x = x.getElementsByTagName("div");
        if (e.key === "ArrowDown") {
            currentFocus++;
            addActive(x);
        } else if (e.key === "ArrowUp") {
            currentFocus--;
            addActive(x);

        } else if (esAtajo(e, 'nuevoRenglon') || e.key === "Enter") {
            // Mantenemos e.key === "Enter" como fallback por si configuran otra cosa para nuevo renglón
            // pero quieren seguir seleccionando con Enter en el menú.
            if (currentFocus > -1) {
                if (x) x[currentFocus].click();
                e.preventDefault();
            }
            // CORRECCIÓN: Usar esAtajo para el autocompletar
        } else if (esAtajo(e, 'autocompletar')) {
            if (x && x.length > 0) {
                if (currentFocus > -1) {
                    x[currentFocus].click();
                } else {
                    x[0].click();
                }
                // ANTES: NO prevenimos el default aquí...

                // NUEVO: Bloqueamos la escritura SOLO si la tecla no es Tab
                // Si es Tab, dejamos que pase para que cambie de campo (foco)
                if (e.key !== 'Tab') {
                    e.preventDefault();
                }
            }

        }
    });

    function addActive(x) {
        if (!x) return false;
        removeActive(x);
        if (currentFocus >= x.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = (x.length - 1);
        x[currentFocus].classList.add("autocomplete-active");
    }

    function removeActive(x) {
        for (let i = 0; i < x.length; i++) {
            x[i].classList.remove("autocomplete-active");
        }
    }

    function closeAllLists(elmnt) {
        const x = document.getElementsByClassName("autocomplete-items");
        for (let i = 0; i < x.length; i++) {
            if (elmnt != x[i] && elmnt != inp) {
                x[i].parentNode.removeChild(x[i]);
            }
        }
    }

    document.addEventListener("click", function (e) {
        closeAllLists(e.target);
    });
}
// ============================================================================
// FUNCIONES AUXILIARES DEL ASISTENTE (PEGAR AL FINAL DE DIARIO.JS)
// ============================================================================

function preguntarVenta(row, totalDebe, onCancelCallback) {
    const mainContainer = document.getElementById('main-container');
    let tasas = [];
    try { tasas = JSON.parse(mainContainer.getAttribute('data-tasas-iva') || '[]'); } catch (e) { }
    let opcionesHTML = tasas.length > 0 ? '' : '<option value="22">Básica (22%)</option>';
    tasas.forEach(t => { opcionesHTML += `<option value="${t.valor}">${t.nombre} (${t.valor}%)</option>`; });

    Swal.fire({
        title: 'Asistente de Ventas',
        html: `
            <div style="text-align:left;">
                <p>Total ingresado en DEBE: <b>$${totalDebe.toFixed(2)}</b></p>
                <label>Tasa de IVA:</label>
                <select id="swal-tasa" class="swal2-input" style="width:100%;">${opcionesHTML}</select>
                <div style="margin-top:15px; background:#f9f9f9; padding:10px; border-radius:5px;">
                    <label><input type="radio" name="tipo_calculo" value="incluido" checked> <b>IVA Incluido</b> (Dividir)</label><br>
                    <label><input type="radio" name="tipo_calculo" value="mas_iva"> <b>Precio Neto</b> (Sumar)</label>
                </div>
            </div>`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Calcular',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            let tasa = parseFloat(document.getElementById('swal-tasa').value) || 0;
            if (tasa > 0 && tasa <= 1) tasa = tasa * 100; // PARCHE ANTI-DOBLE DIVISIÓN

            const modo = document.querySelector('input[name="tipo_calculo"]:checked').value;
            let neto = 0, iva = 0;
            if (modo === 'incluido') {
                const factor = 1 + (tasa / 100);
                neto = totalDebe / factor;
                iva = totalDebe - neto;
            } else {
                neto = totalDebe;
                iva = totalDebe * (tasa / 100);
                Swal.fire({ toast: true, position: 'top-end', icon: 'info', title: 'Recuerda ajustar el DEBE.', timer: 3000 });
            }
            autocompletarVenta(row, neto, iva);
        } else {
            // AQUÍ ESTÁ LA CLAVE: Si cancela, ejecutamos el callback para activar el escudo
            if (onCancelCallback) onCancelCallback();
        }
    });
}

function preguntarCompra(row, base, inputDebe, onCancelCallback) {
    const mainContainer = document.getElementById('main-container');
    let tasas = [];
    try { tasas = JSON.parse(mainContainer.getAttribute('data-tasas-iva') || '[]'); } catch (e) { }
    let opcionesHTML = tasas.length > 0 ? '' : '<option value="22">Básica (22%)</option>';
    tasas.forEach(t => { opcionesHTML += `<option value="${t.valor}">${t.nombre} (${t.valor}%)</option>`; });

    Swal.fire({
        title: 'Calculadora de IVA Compras',
        html: `
            <div style="text-align:left;">
                <p>Base Compras detectada: <b>$${base.toFixed(2)}</b></p>
                <label>Tasa a aplicar:</label>
                <select id="swal-tasa-compra" class="swal2-input" style="width:100%;">${opcionesHTML}</select>
            </div>`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Calcular',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            let tasa = parseFloat(document.getElementById('swal-tasa-compra').value) || 0;
            if (tasa > 0 && tasa <= 1) tasa = tasa * 100; // PARCHE ANTI-DOBLE DIVISIÓN

            const montoIVA = base * (tasa / 100);
            inputDebe.value = montoIVA.toFixed(2);
            detectarLado(inputDebe);
            if (typeof actualizarTotales === 'function') actualizarTotales();
        } else {
            // Si cancela, activamos el escudo
            if (onCancelCallback) onCancelCallback();
        }
    });
}

function ajustarContraparteDescuento(tipo, montoBase, descuento, rowDescuento) {
    let selector = (tipo === 'concedido') ? '.input-debe' : '.input-haber';
    const inputs = document.querySelectorAll(selector);
    let ajustado = false;

    inputs.forEach(inp => {
        if (rowDescuento.contains(inp)) return;
        const val = parseFloat(inp.value) || 0;

        // Si el valor coincide con el Bruto (con tolerancia de 1 peso)
        if (Math.abs(val - montoBase) < 1.0) {
            const nuevoValor = val - descuento;
            inp.value = nuevoValor.toFixed(2);

            inp.style.backgroundColor = "#fff3cd";
            setTimeout(() => inp.style.backgroundColor = "", 2000);

            Swal.fire({
                toast: true, position: 'top-end', icon: 'success',
                title: `Se ajustó la cuenta de dinero a $${nuevoValor.toFixed(2)}`, timer: 3000
            });
            ajustado = true;
        }
    });

    if (!ajustado) {
        Swal.fire({
            toast: true, position: 'top-end', icon: 'info',
            title: 'Descuento aplicado. Recuerda ingresar el Neto en Caja/Bancos.', timer: 4000
        });
    }
}
function toggleCalculadora() {
    crearCalculadora(); // Asegura que el HTML exista
    const calc = document.getElementById('konta-calc');
    if (calc.style.display === 'none') {
        calc.style.display = 'block';
        document.getElementById('calc-display').focus();
    } else {
        calc.style.display = 'none';
    }
}

function crearCalculadora() {
    if (document.getElementById('konta-calc')) return;

    const html = `
    <div id="konta-calc" style="display:none; position:fixed; bottom:20px; right:20px; width:260px; background:#2c3e50; border-radius:10px; box-shadow:0 10px 25px rgba(0,0,0,0.5); z-index:9999; border:1px solid #34495e; overflow:hidden; font-family:monospace;">
        <div id="calc-header" style="background:#1a252f; color:white; padding:10px; cursor:move; display:flex; justify-content:space-between; align-items:center; user-select:none;">
            <span>🧮 Calculadora</span>
            <span onclick="toggleCalculadora()" style="cursor:pointer; color:#e74c3c; font-weight:bold;">✕</span>
        </div>
        <div style="padding:15px;">
            <input type="text" id="calc-display" style="width:100%; background:#ecf0f1; border:none; padding:10px; font-size:1.5em; text-align:right; margin-bottom:10px; border-radius:5px; color:#2c3e50;" readonly>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:5px;">
                <button class="btn-calc op" onclick="calcInput('C')">C</button>
                <button class="btn-calc op" onclick="calcInput('/')">/</button>
                <button class="btn-calc op" onclick="calcInput('*')">×</button>
                <button class="btn-calc op" onclick="calcInput('DEL')">⌫</button>
                <button class="btn-calc" onclick="calcInput('7')">7</button>
                <button class="btn-calc" onclick="calcInput('8')">8</button>
                <button class="btn-calc" onclick="calcInput('9')">9</button>
                <button class="btn-calc op" onclick="calcInput('-')">-</button>
                <button class="btn-calc" onclick="calcInput('4')">4</button>
                <button class="btn-calc" onclick="calcInput('5')">5</button>
                <button class="btn-calc" onclick="calcInput('6')">6</button>
                <button class="btn-calc op" onclick="calcInput('+')">+</button>
                <button class="btn-calc" onclick="calcInput('1')">1</button>
                <button class="btn-calc" onclick="calcInput('2')">2</button>
                <button class="btn-calc" onclick="calcInput('3')">3</button>
                <button class="btn-calc equal" onclick="calcInput('=')" style="grid-row: span 2; background:#27ae60; color:white;">=</button>
                <button class="btn-calc" onclick="calcInput('0')" style="grid-column: span 2;">0</button>
                <button class="btn-calc" onclick="calcInput('.')">.</button>
            </div>
        </div>
    </div>
    <style>
        .btn-calc { padding:15px 0; border:none; background:#34495e; color:white; border-radius:4px; font-size:1.1em; cursor:pointer; transition:0.2s; }
        .btn-calc:hover { background:#2c3e50; filter:brightness(1.2); }
        .btn-calc.op { background:#e67e22; }
    </style>
    `;
    document.body.insertAdjacentHTML('beforeend', html);

    // Hacer arrastrable
    const elmnt = document.getElementById('konta-calc');
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    document.getElementById('calc-header').onmousedown = function (e) {
        e.preventDefault(); pos3 = e.clientX; pos4 = e.clientY;
        document.onmouseup = () => { document.onmouseup = null; document.onmousemove = null; };
        document.onmousemove = (e) => {
            e.preventDefault(); pos1 = pos3 - e.clientX; pos2 = pos4 - e.clientY;
            pos3 = e.clientX; pos4 = e.clientY;
            elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
            elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
        };
    };
}

window.calcInput = function (val) {
    const display = document.getElementById('calc-display');
    if (val === 'C') display.value = '';
    else if (val === 'DEL') display.value = display.value.slice(0, -1);
    else if (val === '=') { try { display.value = eval(display.value); } catch { display.value = 'Err'; } }
    else display.value += val;
};

/* =========================================================
   NUEVA LÓGICA DE DETECCIÓN INTELIGENTE (Copiada del generador)
   ========================================================= */
function esVentaDeResultado(nombreCuenta) {
    if (!nombreCuenta || typeof nombreCuenta !== 'string') return false;

    // 1. Normalizar: minúsculas, sin tildes
    const cuentaNorm = nombreCuenta.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();

    // 2. FASE 1: LISTA NEGRA (Exclusiones Prioritarias)
    // Si tiene esto, NUNCA es una venta (es Activo, Pasivo o Pérdida)
    const patronesExcluidos = [
        'deudor',       // Deudores por Ventas
        'cobrar',       // Documentos a Cobrar
        'cliente',      // Clientes
        'anticipo',     // Anticipos
        'costo',        // Costo de Ventas (Pérdida)
        'devolucion',   // Devoluciones (Regularizadora)
        'descuento',    // Descuentos
        'bonificacion', // Bonificaciones
        'cheque',       // Cheques a Cobrar
        'iva',          // IVA Ventas (Pasivo)
        'pagar'         // Cuentas a Pagar
    ];

    for (const patron of patronesExcluidos) {
        if (cuentaNorm.includes(patron)) return false;
    }

    // 3. FASE 2: LISTA BLANCA (Debe tener palabras de Ganancia)
    const patronesValidos = ['venta', 'ingreso', 'ganancia', 'facturacion', 'servicio'];
    let posibleVenta = false;

    for (const patron of patronesValidos) {
        if (cuentaNorm.includes(patron)) {
            posibleVenta = true;
            break;
        }
    }

    // 4. FASE 3: DECISIÓN FINAL
    // Si pasó la lista negra y tiene una palabra de la lista blanca, es Venta.
    return posibleVenta;
}