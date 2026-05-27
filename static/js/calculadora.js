/* static/js/calculadora.js */

document.addEventListener('DOMContentLoaded', function() {
    crearCalculadora(); 
    
    // --- LISTENER GLOBAL DE TECLADO ---
    document.addEventListener('keydown', function(e) {
        
        // 1. RECUPERAR CONFIGURACIÓN
        let config = { key: 'c', alt: true, ctrl: false, shift: false };
        try {
            const saved = localStorage.getItem('atajos_diario');
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed.abrirCalculadora) config = parsed.abrirCalculadora;
            }
        } catch(err) { console.error(err); }

        // 2. DETECTAR ATAJO
        const keyPressed = e.key.toLowerCase();
        const configKey = config.key.toLowerCase();
        const esAtajo = (
            keyPressed === configKey &&
            e.altKey === !!config.alt &&
            e.ctrlKey === !!config.ctrl &&
            e.shiftKey === !!config.shift
        );

        if (esAtajo) {
            e.preventDefault();
            toggleCalculadora();
            return;
        }

        // 3. LÓGICA DE ESCRITURA (INTELIGENTE)
        const calc = document.getElementById('konta-calc');
        if (calc && calc.style.display !== 'none') {
            
            // Si el usuario escribe en otro lado, ignoramos
            const activeEl = document.activeElement;
            const esInputExterno = (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA') && activeEl.id !== 'calc-display';
            
            if (esInputExterno) return;

            const k = e.key;
            if (/[0-9]/.test(k)) calcInput(k);
            else if (['+','-','*','/','.'].includes(k)) calcInput(k);
            else if (k === 'Enter') { e.preventDefault(); calcInput('='); }
            else if (k === 'Backspace') calcInput('DEL');
            else if (k === 'Escape') toggleCalculadora();
            else if (k.toLowerCase() === 'c' && !e.altKey && !e.ctrlKey) calcInput('C');
        }
    });
});

function toggleCalculadora() {
    const calc = document.getElementById('konta-calc');
    if (calc.style.display === 'none') {
        calc.style.display = 'flex'; // IMPORTANTE: Flex para que el contenido se estire
        document.getElementById('calc-display').focus();
    } else {
        calc.style.display = 'none';
        document.activeElement.blur();
    }
}

function crearCalculadora() {
    if (document.getElementById('konta-calc')) return;

    const html = `
    <div id="konta-calc" style="
        display:none; 
        flex-direction: column; /* Apilar header y cuerpo */
        position:fixed; 
        bottom:20px; right:20px; 
        width:280px; height:400px;
        min-width:220px; min-height:300px; /* Límite de seguridad */
        background:#2c3e50; 
        border-radius:8px; 
        box-shadow:0 15px 35px rgba(0,0,0,0.6); 
        z-index:9999; 
        border:1px solid #34495e; 
        font-family:monospace;
        overflow: hidden; 
        resize: both; /* Redimensionado nativo */
    ">
        <div id="konta-calc-header" style="
            background:#1a252f; 
            color:#ecf0f1; 
            padding:10px; 
            cursor:move; 
            display:flex; 
            justify-content:space-between; 
            align-items:center; 
            user-select:none;
            border-bottom: 1px solid #34495e;
            height: 40px;
            flex-shrink: 0; /* No se encoge */
        ">
            <span style="font-weight:bold; letter-spacing:1px;">🧮 KONTA</span>
            <span onclick="toggleCalculadora()" style="cursor:pointer; color:#e74c3c; font-weight:bold; padding:0 5px;">✕</span>
        </div>

        <div style="
            padding:10px; 
            flex-grow: 1; /* Ocupa todo el espacio sobrante */
            display:flex; 
            flex-direction:column;
            min-height: 0; /* Permite al hijo encogerse */
        ">
            <input type="text" id="calc-display" style="
                width:100%; 
                background:#ecf0f1; 
                border:none; 
                padding:10px; 
                font-size:1.5em; 
                text-align:right; 
                margin-bottom:10px; 
                border-radius:6px; 
                color:#2c3e50; 
                outline:none;
                font-weight:bold;
                flex-shrink: 0; /* El display no se encoge */
            " readonly>
            
            <div style="
                display:grid; 
                grid-template-columns: repeat(4, 1fr); 
                grid-template-rows: repeat(5, 1fr); /* 5 filas iguales */
                gap:5px; 
                flex-grow:1; /* Se estira para llenar el hueco */
                min-height: 0;
            ">
                <button class="btn-calc op" onclick="calcInput('C')">C</button>
                <button class="btn-calc op" onclick="calcInput('/')">÷</button>
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

        <div style="
            position: absolute;
            bottom: 2px;
            right: 2px;
            width: 0;
            height: 0;
            border-style: solid;
            border-width: 0 0 15px 15px;
            border-color: transparent transparent #95a5a6 transparent;
            pointer-events: none; /* Dejar pasar el clic al resize nativo */
            opacity: 0.6;
        "></div>
        <div style="
            position: absolute; bottom: 4px; right: 3px; 
            width: 8px; height: 1px; background: #2c3e50; transform: rotate(-45deg); pointer-events: none;
        "></div>
        <div style="
            position: absolute; bottom: 7px; right: 6px; 
            width: 8px; height: 1px; background: #2c3e50; transform: rotate(-45deg); pointer-events: none;
        "></div>

    </div>
    <style>
        .btn-calc { 
            border:none; 
            background:#34495e; 
            color:white; 
            border-radius:4px; 
            font-size:1.1em; 
            cursor:pointer; 
            transition:0.1s; 
            width:100%; 
            height:100%; /* Llenar la celda del grid */
            font-weight:bold;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .btn-calc:hover { background:#4b6584; }
        .btn-calc:active { background:#2c3e50; }
        .btn-calc.op { background:#e67e22; }
        .btn-calc.op:hover { background:#d35400; }
        .btn-calc.equal:hover { background:#2ecc71; }
        
        #konta-calc ::-webkit-scrollbar { width: 0px; }
    </style>
    `;

    document.body.insertAdjacentHTML('beforeend', html);
    hacerDraggable(document.getElementById('konta-calc'));
}

window.calcInput = function(val) {
    const display = document.getElementById('calc-display');
    if(!display) return;
    
    if (val === 'C') display.value = '';
    else if (val === 'DEL') display.value = display.value.slice(0, -1);
    else if (val === '=') {
        try { display.value = eval(display.value); } catch { 
            display.value = 'Err'; 
            setTimeout(() => display.value = '', 1000);
        }
    } else {
        display.value += val;
    }
    display.scrollLeft = display.scrollWidth;
};

function hacerDraggable(elmnt) {
    var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    const header = document.getElementById(elmnt.id + "-header");
    
    if (header) {
        header.onmousedown = dragMouseDown;
    }

    function dragMouseDown(e) {
        e = e || window.event;
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
        elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
    }

    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}