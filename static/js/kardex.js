/* static/js/kardex.js */

document.addEventListener('DOMContentLoaded', function() {
    
    // 1. REFERENCIAS A ELEMENTOS DEL DOM
    const inputFecha = document.getElementById('inputFecha');
    const selectTipo = document.getElementById('selectTipo');
    const inputCosto = document.getElementById('inputCosto');

    // 2. LÓGICA DE FECHA AUTOMÁTICA (HOY)
    // Solo si el campo está vacío (para no sobrescribir si el navegador recuerda el dato)
    if (inputFecha && !inputFecha.value) {
        const hoy = new Date();
        // Ajuste de zona horaria para obtener la fecha local correcta
        const fechaLocal = new Date(hoy.getTime() - (hoy.getTimezoneOffset() * 60000))
                            .toISOString().split('T')[0];
        inputFecha.value = fechaLocal;
    }

    // 3. FUNCIÓN: GESTIÓN DEL CAMPO DE COSTO
    function actualizarEstadoCosto() {
        if (!selectTipo || !inputCosto) return;

        if (selectTipo.value === 'SALIDA') {
            // Caso VENTA: Bloqueamos el costo
            inputCosto.value = "";       
            inputCosto.disabled = true;  
            inputCosto.placeholder = "Calculado Auto"; 
            inputCosto.style.backgroundColor = "#e9ecef"; // Feedback visual gris
        } else {
            // Caso COMPRA: Permitimos escribir
            inputCosto.disabled = false; 
            inputCosto.placeholder = "$ Costo Unitario";
            inputCosto.style.backgroundColor = "white";
        }
    }

    // 4. LISTENERS (EVENTOS)
    if (selectTipo) {
        // Cuando el usuario cambia el select
        selectTipo.addEventListener('change', actualizarEstadoCosto);
    }

    // Ejecutar una vez al inicio para establecer el estado correcto
    actualizarEstadoCosto();
});