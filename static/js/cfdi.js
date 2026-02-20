// static/js/cfdi.js
const AU = {
  isAlta: () => window.location.pathname.includes("/cfdi/nuevo"),
};

async function au_fetch(url, opts = {}) {
  const res = await fetch(url, opts);
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) throw data;
  return data;
}

function au_qs(id) { return document.getElementById(id); }

function au_show(el, yes) {
  if (!el) return;
  el.style.display = yes ? "" : "none";
}

function au_setCheck(id, ok, label) {
  const el = au_qs(id);
  if (!el) return;
  el.classList.remove("au_ok", "au_bad");
  el.classList.add(ok ? "au_ok" : "au_bad");
  el.textContent = `${label}: ${ok ? "OK" : "NO"}`;
}

function au_escape(s) {
  return (s ?? "").toString().replace(/[&<>"']/g, m => ({
    "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"
  }[m]));
}

 
// --------------------- LISTADO ---------------------
async function au_loadList() {
  const q = (au_qs("au_q")?.value || "").trim();
  const data = await au_fetch(`/api/cfdi?q=${encodeURIComponent(q)}`);
  const items = data.items || [];
  const tbody = au_qs("au_tbody");
  tbody.innerHTML = "";
 
  au_show(au_qs("au_empty"), items.length === 0);
 
  for (const it of items) {
    const relOk = (it.os_tiene_partida && it.partida_existe && it.contrato_existe);
    const relTxt = relOk ? "OK" : "REVISAR";
    const relCls = relOk ? "au_badge_ok" : "au_badge_warn";
 
    const prov = `${au_escape(it.proveedor_razon || "")}<br><span class="au_muted">${au_escape(it.proveedor_rfc || "")}</span>`;
 
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${it.cfdi_id}</td>
      <td class="au_mono">${au_escape(it.uuid || "")}</td>
      <td class="au_mono">${au_escape(it.rfc_emisor || "")}</td>
      <td>${prov}</td>
      <td>${it.contrato ?? ""}</td>
      <td>${it.tipo_de_contrato ?? ""}</td>
      <td>${it.partida ?? ""}</td>
      <td><span class="au_badge au_badge_neu">${au_escape(it.estatus_reporte || "EN CAPTURA")}</span></td>
      <td><span class="au_badge au_badge_neu">${au_escape(it.cfdi_estatus || "ACTIVO")}</span></td>
      <td>
        <button class="au_btn au_btn_sm" data-act="detalle" data-id="${it.cfdi_id}">Ver detalle</button>
        <button class="au_btn au_btn_sm au_btn_secondary" data-act="editar" data-id="${it.cfdi_id}">Editar</button>
      </td>
    `;
    tbody.appendChild(tr);
  }
 
  tbody.querySelectorAll("button[data-act]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id, 10);
      const act = btn.dataset.act;
      if (act === "detalle") return au_openDetalle(id);
      if (act === "editar") return au_openEdit(id);
    });
  });
}
 
// --------------------- Modal Detalle CFDI ---------------------

// Función para formatear moneda
function au_formatCurrency(value) {
  if (value === null || value === undefined || value === 0) return '$0.00';
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN'
  }).format(value);
}

// Función para formatear fecha
function au_formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  const date = new Date(dateStr);
  return date.toLocaleDateString('es-MX', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

// Convierte fechas a formato yyyy-mm-dd para backend
function au_formatToBackend(dateStr) {
  if (!dateStr) return "";
 
  // Si ya viene en yyyy-mm-dd, regresarla tal cual
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;
 
  // Si viene en MM/DD/YY o MM/DD/YYYY
  const parts = dateStr.split("/");
  if (parts.length !== 3) return "";
 
  let [mm, dd, yy] = parts;
  if (yy.length === 2) yy = "20" + yy;
 
  return `${yy}-${mm.padStart(2,"0")}-${dd.padStart(2,"0")}`;
}

// Función para crear un campo
function au_createField(label, value, mono = false, highlight = false) {
  const displayValue = value ?? 'N/A';
  return `
    <div class="au_detail_field ${highlight ? 'au_detail_highlight' : ''}">
      <div class="au_detail_label">${label}</div>
      <div class="au_detail_value ${mono ? 'au_mono' : ''}">${displayValue}</div>
    </div>
  `;
}

// Función para crear badge de estatus
function au_createStatusBadge(status) {
  const badgeClass = status === 'ACTIVO' ? 'au_badge_ok' : 
                     status === 'CANCELADO' ? 'au_badge_warn' : 'au_badge_neu';
  return `<span class="au_badge ${badgeClass}">${status}</span>`;
}

// Toggle XML
function au_toggleXML() {
  const xmlContent = au_qs('au_xmlContent');
  const btn = au_qs('au_btnToggleXml');
  if (xmlContent.style.display === 'none') {
    xmlContent.style.display = 'block';
    btn.textContent = 'Ocultar XML';
  } else {
    xmlContent.style.display = 'none';
    btn.textContent = 'Mostrar XML';
  }
}

async function au_openDetalle(cfdiId) {
  const bg = au_qs("au_modalBg");
  const body = au_qs("au_modalBody");
  const title = au_qs("au_modalTitle");
  const subtitle = au_qs("au_modalSubtitle");
  
  au_show(bg, true);
  body.innerHTML = '<div class="au_detail_loading">Cargando información...</div>';

  try {
    const data = await au_fetch(`/api/cfdi/${cfdiId}/detalle`);
    const item = data.item || {};

    // Actualizar título y subtítulo
    title.textContent = `Detalle CFDI #${item.id || cfdiId}`;
    subtitle.textContent = `UUID: ${item.uuid || 'N/A'}`;

    // Renderizar el contenido completo
    body.innerHTML = `
      <!-- Estadísticas principales -->
      <div class="au_detail_stats">
        <div class="au_detail_stat">
          <div class="au_detail_stat_label">Monto Total</div>
          <div class="au_detail_stat_value">${au_formatCurrency(item.monto_total)}</div>
        </div>
        <div class="au_detail_stat">
          <div class="au_detail_stat_label">Saldo Disponible</div>
          <div class="au_detail_stat_value">${au_formatCurrency(item.saldo_disponible)}</div>
        </div>
        <div class="au_detail_stat">
          <div class="au_detail_stat_label">Monto Ejercido</div>
          <div class="au_detail_stat_value">${au_formatCurrency(item.monto_ejercido)}</div>
        </div>
        <div class="au_detail_stat">
          <div class="au_detail_stat_label">Estatus</div>
          <div class="au_detail_stat_value">${item.estatus || 'N/A'}</div>
        </div>
      </div>

      <!-- Información del CFDI -->
      <div class="au_detail_section">
        <div class="au_detail_section_title">Información del CFDI</div>
        <div class="au_detail_grid">
          ${au_createField('ID CFDI', item.id)}
          ${au_createField('UUID', item.uuid, true, true)}
          ${au_createField('RFC Emisor', item.rfc_emisor, true)}
          ${au_createField('Fecha Emisión', au_formatDate(item.fecha_emision))}
          ${au_createField('Fecha Recepción', au_formatDate(item.fecha_recepcion))}
          ${au_createField('Estatus', au_createStatusBadge(item.estatus))}
          ${au_createField('Orden Suministro', item.orden_suministro)}
          ${au_createField('Observaciones', item.onservaciones || item.observaciones)}
          ${au_createField('Fecha Captura',item.fecha_captura)}

        </div>
      </div>

      <!-- Información del Proveedor -->
      <div class="au_detail_section">
        <div class="au_detail_section_title">Información del Proveedor</div>
        <div class="au_detail_grid">
          ${au_createField('ID Proveedor', item.proveedor)}
          ${au_createField('RFC', item.proveedor_rfc, true)}
          ${au_createField('Razón Social', item.proveedor_razon)}
        </div>
      </div>

      <!-- Información de la Orden de Suministro -->
      <div class="au_detail_section">
        <div class="au_detail_section_title">Orden de Suministro</div>
        <div class="au_detail_grid">
          ${au_createField('Fecha Orden', au_formatDate(item.fecha_orden))}
          ${au_createField('Folio Oficio', item.folio_oficio)}
          ${au_createField('Fecha Factura', au_formatDate(item.fecha_factura))}
          ${au_createField('Folio Interno', item.folio_interno)}
          ${au_createField('Cuenta Bancaria', item.cuenta_bancaria)}
          ${au_createField('Banco', item.banco)}
          ${au_createField('Mes de Servicio', item.mes_servicio, false, true)}
          ${au_createField('Fecha Pago', au_formatDate(item.fecha_pago))}
          ${au_createField('Archivo', item.archivo)}
        </div>
      </div>

      <!-- Información del Contrato -->
      <div class="au_detail_section">
        <div class="au_detail_section_title">Información del Contrato</div>
        <div class="au_detail_grid">
          ${au_createField('ID Contrato', item.contrato)}
          ${au_createField('Número de Contrato', item.num_contrato, false, true)}
          ${au_createField('RFC PP', item.rfc_pp, true)}
          ${au_createField('Ejercicio', item.ejercicio)}
          ${au_createField('Mes', item.mes)}
          ${au_createField('Fecha Inicio', au_formatDate(item.f_inicio))}
          ${au_createField('Fecha Fin', au_formatDate(item.f_fin))}
          ${au_createField('Monto Máximo', au_formatCurrency(item.monto_maximo))}
          ${au_createField('Monto Ejercido', au_formatCurrency(item.monto_ejercido))}
          ${au_createField('Saldo Disponible', au_formatCurrency(item.saldo_disponible), false, true)}
          ${au_createField('Área', item.area)}
          ${au_createField('Tipo de contrato', item.tipo_de_contrato)}
        </div>
      </div>

      <!-- Información de la Partida -->
      <div class="au_detail_section">
        <div class="au_detail_section_title">Información de la Partida Presupuestal</div>
        <div class="au_detail_grid">
          ${au_createField('ID Partida', item.partida)}
          ${au_createField('Capítulo', `${item.capitulo || ''} - ${item.des_cap || ''}`)}
          ${au_createField('Concepto', `${item.concepto || ''} - ${item.des_concepto || ''}`)}
          ${au_createField('Uso Partida', `${item.uso_partida || ''} - ${item.des_uso_partida || ''}`)}
          ${au_createField('Partida Específica', `${item.partida_especifica || ''} - ${item.des_pe || ''}`, false, true)}
          ${au_createField('Tipo de Gasto', item.tipo_gasto)}
          ${au_createField('Austeridad', item.austeridad)}
          ${au_createField('Programa Presupuestario', `${item.pp || ''} - ${item.des_pp || ''}`)}
          ${au_createField('Entidad', item.entidad)}
        </div>
      </div>

      <!-- Montos e Impuestos -->
      <div class="au_detail_section">
        <div class="au_detail_section_title">Montos e Impuestos</div>
        <div class="au_detail_grid">
          ${au_createField('Monto sin IVA', au_formatCurrency(item.monto_siniva))}
          ${au_createField('IVA', au_formatCurrency(item.iva))}
          ${au_createField('Monto con IVA', au_formatCurrency(item.monto_c_iva))}
          ${au_createField('ISR', au_formatCurrency(item.isr))}
          ${au_createField('IEPS', au_formatCurrency(item.ieps))}
          ${au_createField('Descuento', au_formatCurrency(item.descuento))}
          ${au_createField('Otras Contribuciones', au_formatCurrency(item.otras_contribuciones))}
          ${au_createField('Retenciones', au_formatCurrency(item.retenciones))}
          ${au_createField('Penalización', au_formatCurrency(item.penalizacion))}
          ${au_createField('Deductiva', au_formatCurrency(item.deductiva))}
          ${au_createField('Importe Pago', au_formatCurrency(item.importe_pago))}
          ${au_createField('Importe P. Compromiso', au_formatCurrency(item.importe_p_compromiso))}
          ${au_createField('No. Compromiso', item.no_compromiso)}
        </div>
      </div>

      <!-- XML Completo -->
      ${item.xml_factura ? `
        <div class="au_detail_section">
          <div class="au_detail_section_title">XML de la Factura</div>
          <button class="au_btn au_btn_sm au_btn_secondary" id="au_btnToggleXml" onclick="au_toggleXML()">Mostrar XML</button>
          <pre class="au_xml_content" id="au_xmlContent" style="display: none;">${au_escape(item.xml_factura)}</pre>
        </div>
      ` : ''}
    `;
  } catch (err) {
    body.innerHTML = `
      <div class="au_detail_error">
        <strong>Error al cargar el detalle:</strong>
        <p>${err?.detail || err?.message || JSON.stringify(err)}</p>
      </div>
    `;
  }
}

function au_closeDetalle() {
  au_show(au_qs("au_modalBg"), false);
}

// --------------------- EDICIÓN ---------------------
let AU_CONTRATOS = [];

async function au_loadContratos(selectEl,val=1) {
  const data = await au_fetch("/api/cfdi/catalogos/contratos");
  AU_CONTRATOS = data.items || [];
  selectEl.innerHTML = `<option value="0">— Sin cambio —</option>` + AU_CONTRATOS.map(c =>
    `<option value="${c.id}" ${c.id===val ? "selected" : ""}>${au_escape(c.num_contrato)} (${au_escape(c.rfc_pp || "")})</option>`
  ).join("");
}

async function au_loadPartidas(contratoId, selectEl,val=1) {
  selectEl.innerHTML = `<option value="0">— Sin cambio —</option>`;
  if (!contratoId) return;
  const data = await au_fetch(`/api/cfdi/catalogos/contratos/${contratoId}/partidas`);
  const items = data.items || [];
  selectEl.innerHTML = `<option value="0">— Sin cambio —</option>` + items.map(p =>
    `<option value="${p.id}" ${p.id === val ? "selected" : ""}>${au_escape(p.partida_especifica)} - ${au_escape(p.des_pe || "")}</option>`
  ).join("");
}

async function au_loadEstadoAdmin(selectEl,val=1){
  const data = await au_fetch("/api/cfdi/catalogos/estado-orden");
  const items = data.items || [];
  selectEl.innerHTML = items.map(x => {
    const txt = `${x.estatus_general} - ${x.estatus_reporte}`;
    return `<option value="${x.id}" ${x.id === val ? "selected" : ""}>${au_escape(txt)}</option>`;
  }).join("");
}

async function au_openEdit(cfdiId) {
  //alert(cfdiId)
   // Crear formulario dinámico
  const form = document.createElement("form");
  form.method = "POST";
  form.action = "/cfdi/edit";
  // Campo oculto id_cfdi
  const input = document.createElement("input");
  input.type = "hidden";
  input.id = "id_cfdi";
  input.value = cfdiId;
  form.appendChild(input);
  // Agregar al body
  document.body.appendChild(form);
  // Enviar formulario
  form.submit();
}

function au_closeEdit() {
  au_show(au_qs("au_editBg"), false);
}

async function au_submitEdit(e) {
  e.preventDefault();
  const id = parseInt(au_qs("au_edit_cfdi_id").value, 10);
  const form = new FormData();
  form.append("cfdi_estatus", au_qs("au_edit_estatus").value);
  form.append("estatus_os", au_qs("au_edit_os_estatus").value || "1");
  form.append("fecha_pago", au_qs("au_edit_fecha_pago").value || "");
  form.append("observaciones_os", au_qs("au_edit_obs_os").value.trim());
  form.append("fecha_emision", au_formatToBackend(au_qs("au_edit_femi").value));
  form.append("fecha_recepcion", au_formatToBackend(au_qs("au_edit_frec").value));
  form.append("tipo_de_contrato", au_qs("au_tipo_contrato").value);

  const pid = parseInt(au_qs("au_edit_partida").value, 10) || 0;
  form.append("partida_id", pid.toString());
  if (!confirm("¿Dese acontinuar con la actualización?")) return;
  try {
    const res = await au_fetch(`/api/cfdi/${id}`, { method: "PUT", body: form });
    au_qs("au_editMsg").textContent = "Guardado.";
    au_closeEdit();
    await au_loadList();
  } catch (err) {
    au_qs("au_editMsg").textContent = (err?.detail || err?.message || JSON.stringify(err));
  }
}



// --------------------- ALTA ---------------------
let AU_LAST_VALID = null;

async function au_validarXML() {
  const f = au_qs("au_file")?.files?.[0];
  if (!f) return alert("Selecciona un XML.");

  const fd = new FormData();
  fd.append("file", f);

  au_setCheck("au_ck_xml", false, "XML");
  au_setCheck("au_ck_xsd", false, "XSD");
  au_setCheck("au_ck_timbre", false, "Timbre");
  au_setCheck("au_ck_rfc", false, "RFC catálogo");

  au_show(au_qs("au_val_msgs"), true);
  const ul = au_qs("au_val_list");
  ul.innerHTML = `<li class="au_muted">Validando...</li>`;

  try {
    const res = await au_fetch("/api/cfdi/validar", { method: "POST", body: fd });
    AU_LAST_VALID = res;
    // Si RFC catálogo OK, resolver proveedor por RFC y poblar campos
    const extracted = res?.extracted;
    const rfc = extracted?.rfc_emisor;
    if (rfc) {
      const rfcInput = au_qs("au_proveedor_rfc");
      if (rfcInput) rfcInput.value = rfc;

      try {
        const pr = await au_fetch(`/api/cfdi/catalogos/proveedor-by-rfc?rfc=${encodeURIComponent(rfc)}`);
        const pid = pr?.item?.id;
        if (pid) au_qs("au_proveedor_id").value = pid;
        au_qs("au_razon").value = pr?.item?.razon_social;
        au_qs("au_uuid").value= extracted?.uuid;
        au_qs("au_fecha_factura").value= extracted?.fecha_emision;
        au_qs("au_iva").value = (extracted?.iva);
        au_qs("au_monto_siniva").value = (extracted?.subtotal);
        au_qs("au_monto_c_iva").value = (extracted?.con_iva);
        au_qs("au_isr").value = (extracted?.isr);
        au_qs("au_descuento").value = (extracted?.descuento);
        au_qs("au_importe_pago").value = (extracted?.importe_pago);

      } catch (e) {
        // Si no encuentra, limpia id
        if (au_qs("au_proveedor_id")) au_qs("au_proveedor_id").value = "";
      }
    }


    au_setCheck("au_ck_xml", !!res.xml_ok, "XML");
    au_setCheck("au_ck_xsd", !!res.xsd_ok, "XSD");
    au_setCheck("au_ck_timbre", !!res.timbre_ok, "Timbre");
    au_setCheck("au_ck_rfc", !!res.rfc_ok, "RFC catálogo");

    ul.innerHTML = "";
    registrado = "";
    visible = true;
    (res.messages || []).forEach(m => {
      const li = document.createElement("li");
      li.textContent = m;
      registrado = m;
      li.className = res.ok ? "verde_t" : "rojo_t";
      ul.appendChild(li);
    });
    if(!res.ok){
      visible = registrado.includes("UUID ya registrado") ? confirm(registrado+", ¿Desea Continuar?") : false;  
    }
    au_show(au_qs("au_formBox"), visible);
    
   
  } catch (err) {
    ul.innerHTML = "";
    const li = document.createElement("li");
    li.textContent = (err?.detail || err?.message || JSON.stringify(err));
    ul.appendChild(li);
    au_show(au_qs("au_formBox"), false);
  }
}

async function au_initAltaCatalogos() {
  const selC = au_qs("au_contrato");
  const selP = au_qs("au_partida");
  const sel = au_qs("au_estatus_os");

  if (!selC || !selP) return;
  if (!sel) return;
  const data = await au_fetch("/api/cfdi/catalogos/estado-orden");
  const items = data.items || [];
  sel.innerHTML = items.map(x => {
    const txt = `${x.estatus_general} - ${x.estatus_reporte}`;
    return `<option value="${x.id}">${au_escape(txt)}</option>`;
  }).join("");

  const dataC = await au_fetch("/api/cfdi/catalogos/contratos");
  const itemsC = dataC.items || [];

  
  // guardar globalmente
  AU_CONTRATOS = itemsC;

  selC.innerHTML = itemsC.map(x => {
    //alert(x.id)
    return `<option value="${x.id}">${x.num_contrato}</option>`;
  }).join("");
  
      const hoy = new Date();
      const yyyy = hoy.getFullYear();
      const mm = String(hoy.getMonth() + 1).padStart(2, "0");
      const dd = String(hoy.getDate()).padStart(2, "0");

      const hoyMX = `${yyyy}-${mm}-${dd}`;
      //alert(hoyMX)  
      const fcInput = au_qs("au_fecha_captura");
      if (fcInput) {
        fcInput.value = hoyMX;
      }
 // await au_initAltaCatalogos();
  //await au_initEstadoOrden();

  selC.onchange = async () => {
    const cid = parseInt(selC.value, 10) || 0;

    // buscar contrato seleccionado
    const contrato = AU_CONTRATOS.find(c => c.id === cid);
    
    // llenar tipo contrato
    au_qs("au_tipo_contrato").value = contrato?.tipo_de_contrato  || "";


    await au_loadPartidas(cid, selP);
  };
  // Disparar una vez para que cargue el primero
  selC.dispatchEvent(new Event("change"));
}

async function au_submitAlta(e) {
  e.preventDefault();
  const f = au_qs("au_file")?.files?.[0];
  if (!f) return alert("Selecciona un XML.");
 
  if (!AU_LAST_VALID?.ok) return alert("Primero Se debe cargar un CFDI válido.");
 
  const fd = new FormData();
 
  //Contrato
  const pid = parseInt(au_qs("au_partida").value, 10) || 0;
  fd.append("partida_id", pid.toString());
  fd.append("mes_servicio", au_qs("au_mes_servicio").value.trim());
  fd.append("fecha_orden", au_qs("au_fecha_captura").value);
  fd.append("estatus_os", au_qs("au_estatus_os").value);
 
  //info CFDI
  fd.append("file", f);
  fd.append("proveedor_id", au_qs("au_proveedor_id").value);
  fd.append("fecha_recepcion", au_qs("au_fecha_captura").value);
  fd.append("monto_partida", au_qs("au_monto_partida").value || 0);
  fd.append("ieps", au_qs("au_ieps").value);
  fd.append("descuento", au_qs("au_descuento").value);
  fd.append("otras_contribuciones", au_qs("au_otras").value);
  fd.append("retenciones", au_qs("au_retenciones").value);au_ret_imp_nom
  fd.append("penalizacion", au_qs("au_penalizacion").value);
  fd.append("deductiva", au_qs("au_deductiva").value);
  fd.append("importe_pago", au_qs("au_importe_pago").value);
  fd.append("observaciones_cfdi", au_qs("au_obs_cfdi").value.trim());
 
 
  //OS
  fd.append("orden_suministro", au_qs("au_orden_suministro").value);
  fd.append("fecha_solicitud", au_qs("au_fecha_orden").value);
  fd.append("folio_oficio", au_qs("au_folio_oficio").value.trim());
  fd.append("folio_interno", au_qs("au_folio_interno").value.trim());
  fd.append("cuenta_bancaria", au_qs("au_cuenta_bancaria").value.trim());
  fd.append("banco", au_qs("au_banco").value.trim());
  fd.append("importe_p_compromiso", au_qs("au_importe_comp").value);
  fd.append("no_compromiso", au_qs("au_no_comp").value);
  fd.append("archivo", au_qs("au_archivo").value.trim());
  fd.append("fecha_pago", au_qs("au_fecha_pago").value || "");
  fd.append("validacion", au_qs("au_validacion").value);
  fd.append("cincomillar", au_qs("au_5millar").value);
  fd.append("risr", au_qs("au_risr").value);
  fd.append("riva", au_qs("au_riva").value);
  fd.append("solicitud", au_qs("au_solicitud").value);
  fd.append("observaciones_os", au_qs("au_obs_os").value.trim());

   //Facturacion
  fd.append("fecha_fiscalizacion", au_qs("au_fecha_fiscalizacion").value);  
  fd.append("fiscalizador", au_qs("au_fiscalizador").value);  
  fd.append("responsable_fis", au_qs("au_responsable_fis").value);  
  fd.append("fecha_carga_sicop", au_qs("au_fecha_carga_sicop").value);
  fd.append("responsable_carga_sicop", au_qs("au_responsable_carga_sicop").value);
  fd.append("estatus_siaf", au_qs("au_estatus_siaf").value);  
  fd.append("numero_solicitud", au_qs("au_numero_solicitud_pago").value);  
  fd.append("clc", au_qs("au_clc").value);

  //Devolucion
  fd.append("oficio_dev", au_qs("au_oficio_dev").value);  
  fd.append("fecha_dev", au_qs("au_fecha_dev").value);  
  fd.append("motivo_dev", au_qs("au_motivo_dev").value);  
 
  //finals
  fd.append("ret_imp_nom", au_qs("au_ret_imp_nom").value);
  fd.append("fecha_pr", au_qs("au_fecha_pr").value);
  fd.append("inmueble", au_qs("au_inmueble").value);
  fd.append("periodo", au_qs("au_periodo").value);
  fd.append("recargos", au_qs("au_recargos").value);
  fd.append("corte_presupuesto", au_qs("au_corte_presupuesto").value);
  fd.append("fecha_turno", au_qs("au_fecha_turno").value);
  fd.append("obs_pr", au_qs("au_obs_pr").value);
  fd.append("numero_solicitud25", au_qs("au_numero_solicitud_pago25").value);  
  fd.append("clc25", au_qs("au_clc25").value);
  fd.append("numero_solicitud26", au_qs("au_numero_solicitud_pago26").value);  
  fd.append("clc26", au_qs("au_clc26").value);
  fd.append("numero_solicitud27", au_qs("au_numero_solicitud_pago27").value);  
  fd.append("clc27", au_qs("au_clc27").value);  
  fd.append("capturista", au_qs("au_correo").value);  
 

  const msg = au_qs("au_altaMsg");
  msg.textContent = "Registrando...";
 
  try {
    //console.log("form Save CFDI:", fd);
    const res = await au_fetch("/api/cfdi/alta", { method: "POST", body: fd });
    msg.textContent = res?.message;
    if(res.ok){
      alert("CFDI Registrado correctamente: "+res?.message)
      window.location.href = "/cfdi";
    }
    //msg.textContent = `OK. CFDI id=${res.cfdi_id}, OS id=${res.os_id}, uuid=${res.uuid}`;
   
  } catch (err) {
    msg.textContent = (JSON.stringify(err?.detail?.message) || JSON.stringify(err?.message) || JSON.stringify(err));
  }
}

// --------------------- INIT ---------------------
window.addEventListener("DOMContentLoaded", async () => {
  if (AU.isAlta()) {
    au_qs("au_btnValidar")?.addEventListener("click", au_validarXML);
    au_qs("au_altaForm")?.addEventListener("submit", au_submitAlta);
    await au_initAltaCatalogos();
    //await au_initEstadoOrden();
    return;
  }

  // listado
  au_qs("au_btnBuscar")?.addEventListener("click", au_loadList);
  au_qs("au_btnCloseModal")?.addEventListener("click", au_closeDetalle);
  au_qs("au_btnCloseEdit")?.addEventListener("click", au_closeEdit);
  au_qs("au_editForm")?.addEventListener("submit", au_submitEdit);
  au_qs("au_btnDelete")?.addEventListener("click", au_deleteCfdi);

  await au_loadList();
});