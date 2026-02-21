// static/js/facturas_listado.js
/**
 * JavaScript para listado de facturas con filtros, paginación y exportación
 */

const FL = {
    currentPage: 1,
    perPage: 50,
    filters: {},
    filtrosOpciones: {},
};

// ====================
// Constantes
// ====================
function lf_qs(id) { return document.getElementById(id); }
// ====================
// Utilidades
// ====================

async function fl_fetch(url, opts = {}) {
    const res = await fetch(url, opts);
    const ct = res.headers.get("content-type") || "";
    const data = ct.includes("application/json") ? await res.json() : await res.text();
    if (!res.ok) throw data;
    return data;
}

function fl_qs(id) {
    return document.getElementById(id);
}

function fl_show(el, visible) {
    if (!el) return;
    el.style.display = visible ? "" : "none";
}

function fl_escape(str) {
    return (str || "").toString().replace(/[&<>"']/g, m => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;"
    }[m]));
}

function fl_formatCurrency(value) {
    if (!value && value !== 0) return "N/A";
    return new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: 'MXN'
    }).format(value);
}

function fl_formatDate(dateStr) {
    if (!dateStr) return "N/A";
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('es-MX');
    } catch {
        return dateStr;
    }
}

function fl_getBadgeClass(estatus) {
    const estatusUpper = (estatus || "").toUpperCase();
    if (estatusUpper === "ACTIVO") return "fl_badge_success";
    if (estatusUpper === "CANCELADO") return "fl_badge_danger";
    if (estatusUpper === "INACTIVO") return "fl_badge_warning";
    return "fl_badge_info";
}

// ====================
// Carga de filtros
// ====================

async function fl_cargarFiltrosOpciones() {
    try {
        const data = await fl_fetch("/api/facturas-listado/filtros");
        FL.filtrosOpciones = data;
        
        // Poblar select de áreas
        const areaSelect = fl_qs("fl_filter_area");
        areaSelect.innerHTML = '<option value="">-- Todas --</option>';
        (data.areas || []).forEach(area => {
            const opt = document.createElement("option");
            opt.value = area.id;
            opt.textContent = area.nombre;
            areaSelect.appendChild(opt);
        });
        
        // Poblar select de estados de orden
        const estatusSelect = fl_qs("fl_filter_estatus_os");
        estatusSelect.innerHTML = '<option value="">-- Todos --</option>';
        (data.estados_orden || []).forEach(estado => {
            const opt = document.createElement("option");
            opt.value = estado.id;
            opt.textContent = `${estado.estatus_general} - ${estado.estatus_reporte}`;
            estatusSelect.appendChild(opt);
        });
    } catch (err) {
        console.error("Error cargando filtros:", err);
        alert("Error cargando opciones de filtros");
    }
}

// ====================
// Aplicar filtros
// ====================

function fl_aplicarFiltros() {
    FL.filters = {
        proveedor: fl_qs("fl_filter_proveedor").value.trim(),
        uuid: fl_qs("fl_filter_uuid").value.trim(),
        area: fl_qs("fl_filter_area").value,
        estatus_os: fl_qs("fl_filter_estatus_os").value,
        fecha_inicio: fl_qs("fl_filter_fecha_inicio").value,
        fecha_fin: fl_qs("fl_filter_fecha_fin").value,
    };
    
    FL.perPage = parseInt(fl_qs("fl_per_page").value, 10);
    FL.currentPage = 1; // Resetear a primera página
    
    fl_cargarFacturas();
}

function fl_limpiarFiltros() {
    fl_qs("fl_filter_proveedor").value = "";
    fl_qs("fl_filter_uuid").value = "";
    fl_qs("fl_filter_area").value = "";
    fl_qs("fl_filter_estatus_os").value = "";
    fl_qs("fl_filter_fecha_inicio").value = "";
    fl_qs("fl_filter_fecha_fin").value = "";
    fl_qs("fl_per_page").value = "50";
    
    FL.filters = {};
    FL.perPage = 50;
    FL.currentPage = 1;
    
    fl_cargarFacturas();
}

// ====================
// Carga de datos
// ====================

async function fl_cargarFacturas() {
    const loading = fl_qs("fl_loading");
    const empty = fl_qs("fl_empty");
    const table = fl_qs("fl_table");
    const pagination = fl_qs("fl_pagination");
    
    // Mostrar loading
    fl_show(loading, true);
    fl_show(empty, false);
    fl_show(table, false);
    fl_show(pagination, false);
    
    try {
        // Construir query params
        const params = new URLSearchParams({
            page: FL.currentPage,
            per_page: FL.perPage,
        });
        
        // Agregar filtros solo si tienen valor
        Object.entries(FL.filters).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });
        
        const data = await fl_fetch(`/api/facturas-listado/lista?${params}`);
        
        fl_show(loading, false);
        
        if (!data.items || data.items.length === 0) {
            fl_show(empty, true);
            return;
        }
        
        // Renderizar tabla
        fl_renderTabla(data.items);
        fl_renderPaginacion(data);
        
        fl_show(table, true);
        fl_show(pagination, true);
        
    } catch (err) {
        fl_show(loading, false);
        console.error("Error cargando facturas:", err);
        alert("Error al cargar las facturas: " + (err?.detail || err?.message || "Error desconocido"));
    }
}

// ====================
// Renderizado
// ====================
 
function fl_renderTabla(items) {
    const tbody = fl_qs("fl_tbody");
    tbody.innerHTML = "";
   
    items.forEach(item => {
        const badgeClass = fl_getBadgeClass(item.estatus_general);
       
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${item.cfdi_id || "N/A"}</td>
            <td>${fl_escape(item["ID"] || "").substring(0, 20)}...</td>
            <td>
                <div>${fl_escape(item["PROVEEDOR"] || "N/A")}</div>
                <div class="fl_mono" style="font-size: 11px; color: #6c757d;">${fl_escape(item["RFC"] || "")}</div>
            </td>
            <td>${item['UNIDAD EJECUTORA DEL GASTO'] || "N/A"}</td>
            <td>${fl_escape(item["CONTRATO"] || "N/A")}</td>
            <td>${fl_escape(item["PARTIDA PRESUPUESTAL"] || "N/A")}</td>
            <td>${fl_formatCurrency(item.monto_total)}</td>
            <td>${fl_formatDate(item["FECHA DE RECEPCION"])}</td>
            <td>
                <span class="fl_badge ${badgeClass}">${fl_escape(item.estatus_general || "N/A")}</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function fl_renderPaginacion(data) {
    const info = fl_qs("fl_pagination_info");
    const controls = fl_qs("fl_pagination_controls");
    const inicio = ((data.page - 1) * data.per_page) + 1;
    const fin = Math.min(data.page * data.per_page, data.total);
    
    info.textContent = `Mostrando ${inicio} - ${fin} de ${data.total} facturas`;
    
    // Botones de paginación
    controls.innerHTML = "";
    
    // Botón "Anterior"
    const btnPrev = document.createElement("button");
    btnPrev.className = "fl_page_btn";
    btnPrev.textContent = "« Anterior";
    btnPrev.disabled = data.page <= 1;
    btnPrev.onclick = () => fl_cambiarPagina(data.page - 1);
    controls.appendChild(btnPrev);
    
    // Páginas numeradas (máximo 7)
    const maxBotones = 7;
    let startPage = Math.max(1, data.page - Math.floor(maxBotones / 2));
    let endPage = Math.min(data.total_pages, startPage + maxBotones - 1);
    
    if (endPage - startPage < maxBotones - 1) {
        startPage = Math.max(1, endPage - maxBotones + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const btn = document.createElement("button");
        btn.className = "fl_page_btn" + (i === data.page ? " active" : "");
        btn.textContent = i;
        btn.onclick = () => fl_cambiarPagina(i);
        controls.appendChild(btn);
    }
    
    // Botón "Siguiente"
    const btnNext = document.createElement("button");
    btnNext.className = "fl_page_btn";
    btnNext.textContent = "Siguiente »";
    btnNext.disabled = data.page >= data.total_pages;
    btnNext.onclick = () => fl_cambiarPagina(data.page + 1);
    controls.appendChild(btnNext);
}

function fl_cambiarPagina(page) {
    FL.currentPage = page;
    fl_cargarFacturas();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ====================
// Exportación
// ====================

async function fl_exportarExcel() {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = "Generando...";
    btn.disabled = true;
    
    try {
        // Construir query params con filtros actuales
        const params = new URLSearchParams();
        
        Object.entries(FL.filters).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });
        
        // Descargar archivo
        const url = `/api/facturas-listado/exportar-excel?${params}`;
        window.location.href = url;
        
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
        
    } catch (err) {
        console.error("Error exportando:", err);
        alert("Error al exportar: " + (err?.detail || err?.message || "Error desconocido"));
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// ====================
// Ver detalle
// ====================

function fl_verDetalle(cfdiId) {
    // Redirigir a la página de detalle (puedes adaptar esto según tu sistema)
    // O abrir modal con la función au_openDetalle existente
    if (typeof au_openDetalle === 'function') {
        au_openDetalle(cfdiId);
    } else {
        window.location.href = `/cfdi?id=${cfdiId}`;
    }
}

// ====================
// Inicialización
// ====================

window.addEventListener("DOMContentLoaded", async () => {
    //listado
    lf_qs("flClean").addEventListener("click",fl_limpiarFiltros);
    lf_qs("flSeekF").addEventListener("click",fl_aplicarFiltros);
    lf_qs("flExport").addEventListener("click",fl_exportarExcel);
        
    // Event listener para Enter en campos de texto
    ["fl_filter_proveedor", "fl_filter_uuid"].forEach(id => {
        fl_qs(id)?.addEventListener("keypress", (e) => {
            if (e.key === "Enter") fl_aplicarFiltros();
        });
    });
    
    //await fl_cargarFiltrosOpciones();
    await fl_cargarFacturas();
});
