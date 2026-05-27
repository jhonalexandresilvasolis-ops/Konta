/* static/js/conciliacion.js */

let selBanco = null;
let selSistema = null;

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('tabla-carga')) {
        if (document.querySelectorAll('#tbody-carga tr').length === 0) agregarFilaCarga();

        // --- ATAJOS DE TECLADO PARA LA CARGA MANUAL ---
        document.getElementById('tbody-carga').addEventListener('keydown', function (e) {
            const active = document.activeElement;
            const tr = active.closest('tr');

            // ENTER: Nueva fila
            if (e.key === 'Enter') {
                e.preventDefault();
                agregarFilaCarga();
                // Foco a la nueva fecha
                const inputs = document.querySelectorAll('.i-fecha');
                inputs[inputs.length - 1].focus();
            }
            // DELETE + CTRL: Borrar fila
            if (e.key === 'Delete' && e.ctrlKey && tr) {
                e.preventDefault();
                if (document.querySelectorAll('#tbody-carga tr').length > 1) {
                    tr.remove();
                    validarSuma();
                }
            }
            // FLECHAS: Navegación básica
            if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                // (Implementación básica opcional, el Tab nativo ya funciona bien)
            }
        });
    }

    if (document.getElementById('mesaApp')) {
        actualizarHoja();
    }
});

/* --- UTILIDADES --- */
function formatoNumero(num) {
    if (!num) return "0";
    let n = parseFloat(num);
    let str = Number.isInteger(n) ? n.toString() : n.toFixed(2);
    return str.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function parseMonto(str) {
    if (!str) return 0;
    return parseFloat(str.replace(/,/g, '').replace(/[()]/g, '')) || 0;
}

/* --- FASE 1: CARGA MANUAL --- */
function agregarFilaCarga() {
    const tbody = document.getElementById('tbody-carga');
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="date" class="i-fecha"></td>
        <td><input type="text" class="i-concepto" list="conceptos-banco" placeholder="Concepto..."></td>
        <td><input type="number" class="i-debe" placeholder="0" onkeyup="validarSuma()"></td>
        <td><input type="number" class="i-haber" placeholder="0" onkeyup="validarSuma()"></td>
        <td style="text-align:right; font-weight:bold; color:#555; padding:10px;"><span class="i-saldo">0</span></td>
        <td style="text-align:center;"><button onclick="this.closest('tr').remove(); validarSuma()" style="color:#c0392b;border:none;background:none;cursor:pointer;font-weight:bold;font-size:1.2em;">&times;</button></td>
    `;
    tbody.appendChild(tr);
}

function validarSuma() {
    let acumulado = 0;
    document.querySelectorAll('#tbody-carga tr').forEach(tr => {
        const d = parseFloat(tr.querySelector('.i-debe').value) || 0;
        const h = parseFloat(tr.querySelector('.i-haber').value) || 0;
        // Lógica de SALDO para el Banco (Pasivo para ellos, pero para cuadrar extracto):
        // Usualmente Extracto muestra: Debe (Salidas) / Haber (Entradas).
        // Saldo = Anterior + Haber - Debe.
        acumulado += (h - d);

        const span = tr.querySelector('.i-saldo');
        span.innerText = formatoNumero(acumulado);
        span.style.color = acumulado < 0 ? '#c0392b' : '#2c3e50';
    });

    const obj = parseFloat(document.getElementById('saldo-final-input').value) || 0;
    const diff = Math.abs(acumulado - obj);
    const alerta = document.getElementById('validacion-suma');
    const btn = document.querySelector('.btn-guardar-ext');

    if (diff > 0.05) {
        alerta.style.display = 'block';
        alerta.innerHTML = `⚠️ Diferencia: <b>$${formatoNumero(diff)}</b> (Calc: ${formatoNumero(acumulado)})`;
        btn.disabled = true; btn.style.opacity = "0.5";
    } else {
        alerta.style.display = 'none';
        btn.disabled = false; btn.style.opacity = "1";
    }
}

document.getElementById('saldo-final-input')?.addEventListener('keyup', validarSuma);

function guardarExtracto() {
    if (document.querySelector('.btn-guardar-ext').disabled) return;
    const items = [];
    document.querySelectorAll('#tbody-carga tr').forEach(tr => {
        const fecha = tr.querySelector('.i-fecha').value;
        const concepto = tr.querySelector('.i-concepto').value;
        const d = parseFloat(tr.querySelector('.i-debe').value) || 0;
        const h = parseFloat(tr.querySelector('.i-haber').value) || 0;
        if (fecha && (d > 0 || h > 0)) items.push({ fecha, concepto, debe: d, haber: h });
    });

    const params = new URLSearchParams(window.location.search);
    fetch('/guardar_extracto', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            cuenta_id: params.get('cuenta_id'),
            fecha_corte: params.get('fecha_corte'),
            saldo_final: document.getElementById('saldo-final-input').value || 0,
            items: items
        })
    }).then(r => r.json()).then(d => {
        if (d.status === 'ok') location.reload();
        else Swal.fire('Error', d.msg, 'error');
    });
}

function alternarVistaT() {
    const modal = document.getElementById('modal-vista-t');
    const contenedor = document.getElementById('contenido-t-render');

    let html = `<div class="contenedor-t"><div class="cabecera-t"><div class="titulo-columna debe">DEBE (Salidas)</div><div class="titulo-columna haber">HABER (Entradas)</div></div><div class="cuerpo-t">`;
    let sumD = 0, sumH = 0;

    document.querySelectorAll('#tbody-carga tr').forEach(tr => {
        const c = tr.querySelector('.i-concepto').value || '-';
        const d = parseFloat(tr.querySelector('.i-debe').value) || 0;
        const h = parseFloat(tr.querySelector('.i-haber').value) || 0;
        if (d > 0 || h > 0) {
            html += `<div class="fila-t">
                <div class="celda-t izq">${d > 0 ? `${c} <b>${formatoNumero(d)}</b>` : ''}</div>
                <div class="celda-t der">${h > 0 ? `<b>${formatoNumero(h)}</b> ${c}` : ''}</div>
            </div>`;
            sumD += d; sumH += h;
        }
    });
    html += `</div><div class="fila-total"><div class="total-box izq">${formatoNumero(sumD)}</div><div class="total-box der">${formatoNumero(sumH)}</div></div></div>`;
    contenedor.innerHTML = html;
    modal.style.display = 'flex';
}

function confirmarBorrarHoja(cid, fecha) {
    Swal.fire({
        title: '¿Reiniciar Conciliación?',
        text: "Se borrará el extracto cargado y se liberarán los movimientos del libro diario para volver a puntear.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#c0392b',
        confirmButtonText: 'Sí, reiniciar',
        cancelButtonText: 'Cancelar'
    }).then((r) => {
        if (r.isConfirmed) {
            window.location.href = `/borrar_conciliacion?cuenta_id=${cid}&fecha_corte=${fecha}`;
        }
    });
}

/* --- FASE 2: PUNTEO --- */

function seleccionarItem(dom, lado, id) {

    const setSel = (v) => { if (lado === 'banco') selBanco = v; else selSistema = v; };
    const getSel = () => lado === 'banco' ? selBanco : selSistema;

    let current = getSel();
    if (current && current.dom) current.dom.classList.remove('selected');
    if (current && current.id === id) { setSel(null); return; }

    dom.classList.add('selected');
    setSel({ dom, id });
}
function accionRevertir() {
    if (!selBanco && !selSistema) {
        Swal.fire('', 'Selecciona un ítem para deshacer su estado.', 'info');
        return;
    }
    // 1. Si es PENDIENTE (Círculo Rojo) -> Solo quitamos la clase visual
    if ((selBanco && selBanco.dom.classList.contains('pendiente')) ||
        (selSistema && selSistema.dom.classList.contains('pendiente'))) {

        if (selBanco) selBanco.dom.classList.remove('pendiente');
        if (selSistema) selSistema.dom.classList.remove('pendiente');

        // Limpiamos selección y actualizamos hoja
        if (selBanco) { selBanco.dom.classList.remove('selected'); selBanco = null; }
        if (selSistema) { selSistema.dom.classList.remove('selected'); selSistema = null; }
        actualizarHoja();
        return;
    }

    // 2. Si es CONCILIADO (Gris) -> Llamada a Backend para poner estado = 0
    // Preparamos datos, enviamos 0 si hay selección, null si no
    const idExtracto = selBanco ? selBanco.id : null;
    const idSistema = selSistema ? selSistema.id : null;

    fetch('/conciliar_par', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // ENVIAMOS estado: 0 (Falso/No conciliado)
        body: JSON.stringify({ id_extracto: idExtracto, id_sistema: idSistema, estado: 0 })
    }).then(r => r.json()).then(data => {
        if (data.status === 'ok') {
            if (selBanco) {
                selBanco.dom.classList.remove('conciliado', 'selected');
                selBanco = null;
            }
            if (selSistema) {
                selSistema.dom.classList.remove('conciliado', 'selected');
                selSistema = null;
            }
            actualizarHoja(); // Por si afectaba saldos (aunque conciliado no afecta pendiente)

            const Toast = Swal.mixin({ toast: true, position: 'top-end', showConfirmButton: false, timer: 2000 });
            Toast.fire({ icon: 'info', title: 'Estado revertido' });
        } else {
            Swal.fire('Error', data.msg, 'error');
        }
    });
}

function accionConciliar() {
    if (!selBanco || !selSistema) { Swal.fire('', 'Selecciona uno de cada lado.', 'info'); return; }

    const m1 = parseMonto(selBanco.dom.getAttribute('data-monto'));
    const m2 = parseMonto(selSistema.dom.getAttribute('data-monto'));

    if (Math.abs(m1 - m2) > 0.05) {
        Swal.fire('Montos distintos', `Banco: ${m1} vs Libro: ${m2}`, 'warning');
        return;
    }

    fetch('/conciliar_par', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_extracto: selBanco.id, id_sistema: selSistema.id, estado: 1 })
    }).then(() => {
        selBanco.dom.classList.replace('selected', 'conciliado');
        selSistema.dom.classList.replace('selected', 'conciliado');
        selBanco = null; selSistema = null;
        actualizarHoja();
    });
}

function autoConciliar() {
    const filasBanco = document.querySelectorAll('.lado-banco .item-row:not(.conciliado)');
    const filasLibro = document.querySelectorAll('.lado-empresa .item-row:not(.conciliado)');
    let matches = 0;

    filasBanco.forEach(fb => {
        if (fb.classList.contains('conciliado')) return;
        const montoB = fb.getAttribute('data-monto');

        for (let fl of filasLibro) {
            if (fl.classList.contains('conciliado')) continue;
            if (fl.getAttribute('data-monto') === montoB) {
                // Simulación visual (En producción, hacer fetch batch)
                // Aquí solo marcamos visualmente para la demo
                fb.classList.add('conciliado');
                fl.classList.add('conciliado');
                matches++;
                break;
            }
        }
    });

    if (matches > 0) Swal.fire('Auto-Conciliación', `Se encontraron ${matches} coincidencias por monto exacto.`, 'success');
    else Swal.fire('Auto-Conciliación', 'No se encontraron coincidencias automáticas.', 'info');
}

function accionPendiente() {
    const marcar = (s) => { if (s) { s.dom.classList.toggle('pendiente'); s.dom.classList.remove('selected'); } };
    if (!selBanco && !selSistema) return;
    marcar(selBanco); selBanco = null;
    marcar(selSistema); selSistema = null;
    actualizarHoja();
}

function actualizarHoja() {
    const ulBanco = document.getElementById('lista-ajuste-banco'); 
    const ulEmpresa = document.getElementById('lista-ajuste-empresa'); 
    ulBanco.innerHTML = ''; ulEmpresa.innerHTML = '';

    let adjBanco = 0; 
    let adjEmpresa = 0; 

    // AJUSTES AL BANCO (Columna Izquierda)
    document.querySelectorAll('.lado-empresa .pendiente').forEach(el => {
        const concepto = el.querySelector('.concepto').innerText;
        // CORRECCIÓN: Verificamos si la celda 2 (Debe) tiene contenido
        const esDebe = el.children[2].innerText.trim() !== "";
        const valorRaw = parseMonto(el.getAttribute('data-monto'));
        
        let valorFinal = 0; let textoMonto = "";
        
        if (esDebe) { valorFinal = valorRaw; textoMonto = formatoNumero(valorFinal); } 
        else { valorFinal = -valorRaw; textoMonto = `(${formatoNumero(valorRaw)})`; }

        adjBanco += valorFinal;
        ulBanco.innerHTML += `<li>${concepto} <span class="float-right ${valorFinal < 0 ? 'negativo' : ''}">${textoMonto}</span></li>`;
    });

    // AJUSTES A LA EMPRESA (Columna Derecha - Donde está el botón)
    document.querySelectorAll('.lado-banco .pendiente').forEach(el => {
        const concepto = el.querySelector('.concepto').innerText;
        
        // CORRECCIÓN CLAVE: Detectar correctamente si es salida
        // Columna 2 = Debe (Salida del Banco) | Columna 3 = Haber (Entrada al Banco)
        const esDebe = el.children[2].innerText.trim() !== ""; 
        const valorRaw = parseMonto(el.getAttribute('data-monto'));

        let valorFinal = 0; let textoMonto = "";
        let esSalidaNuestra = false; // true = Gasto (Haber nuestro), false = Ingreso (Debe nuestro)

        if (esDebe) { 
            // Banco DEBE (Salida suya) -> Nosotros pagamos -> HABER nuestro
            valorFinal = -valorRaw; 
            textoMonto = `(${formatoNumero(valorRaw)})`;
            esSalidaNuestra = true; 
        } else { 
            // Banco HABER (Entrada suya) -> Nosotros cobramos -> DEBE nuestro
            valorFinal = valorRaw; 
            textoMonto = formatoNumero(valorFinal);
            esSalidaNuestra = false;
        }

        adjEmpresa += valorFinal;
        
        // El botón envía 'true' si es Salida, 'false' si es Ingreso
        const btnHtml = `<button onclick="registrarItemIndividual('${concepto.replace(/'/g, "")}', ${valorRaw}, ${esSalidaNuestra})" class="btn-mini-ajuste" title="Crear Asiento">⚡</button>`;

        ulEmpresa.innerHTML += `
            <li class="item-ajuste">
                <span class="concepto-ajuste">${concepto}</span>
                <div class="acciones-ajuste">
                    <span class="${valorFinal < 0 ? 'negativo' : ''}">${textoMonto}</span>
                    ${btnHtml}
                </div>
            </li>`;
    });

    // Totales... (Igual que antes)
    const saldoBancoFinal = SALDO_EXTRACTO_INICIAL + adjBanco;
    const saldoLibroFinal = SALDO_LIBRO_INICIAL + adjEmpresa;

    document.getElementById('saldo-adj-banco').innerText = formatoNumero(saldoBancoFinal);
    document.getElementById('saldo-adj-empresa').innerText = formatoNumero(saldoLibroFinal);

    const diff = Math.abs(saldoBancoFinal - saldoLibroFinal);
    const boxDiff = document.getElementById('resultado-final-box');
    const spanDiff = document.getElementById('diff-final');
    
    spanDiff.innerText = formatoNumero(diff);
    
    if (diff < 0.05) {
        boxDiff.className = "resultado-final success";
        boxDiff.innerHTML = `✅ CONCILIADO | Diferencia: 0`;
    } else {
        boxDiff.className = "resultado-final error";
        spanDiff.innerText = formatoNumero(diff);
    }
}

function registrarItemIndividual(concepto, monto, esSalida) {
    const params = new URLSearchParams();
    params.set('modo', 'ajuste_single');

    // Limpiamos el concepto de caracteres raros por si acaso
    const conceptoLimpio = concepto.replace(/[\n\r]+/g, ' ').trim();

    params.set('leyenda', conceptoLimpio); // Esto irá al "Tipo de Comprobante"
    params.set('monto', monto);
    params.set('es_salida', esSalida ? '1' : '0');

    const urlParams = new URLSearchParams(window.location.search);
    params.set('id_banco', urlParams.get('cuenta_id'));

    const currentUrl = window.location.pathname + window.location.search;
    params.set('next', currentUrl);

    window.location.href = `/diario?${params.toString()}`;
}
/* --- AL FINAL DE static/js/conciliacion.js --- */

function confirmarAccion(url, titulo, texto, tipo = 'warning', colorConfirm = '#3085d6') {
    Swal.fire({
        title: titulo,
        text: texto,
        icon: tipo,
        showCancelButton: true,
        confirmButtonColor: colorConfirm,
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sí, confirmar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = url;
        }
    });
}