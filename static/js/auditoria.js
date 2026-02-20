let offset = 0;

const fDesde = document.getElementById("fDesde");
const fHasta = document.getElementById("fHasta");
const fCorreo = document.getElementById("fCorreo");
const fAccion = document.getElementById("fAccion");
const fTexto  = document.getElementById("fTexto");
const fLimit  = document.getElementById("fLimit");

const btnBuscar = document.getElementById("btnBuscar");
const btnLimpiar = document.getElementById("btnLimpiar");
const btnPrev = document.getElementById("btnPrev");
const btnNext = document.getElementById("btnNext");

const tblBody = document.getElementById("tblBody");
const empty = document.getElementById("empty");
const metaInfo = document.getElementById("metaInfo");
const btnExport = document.getElementById("btnExport");

function buildQuery() {
  const params = new URLSearchParams();
  if (fDesde.value) params.set("date_from", fDesde.value);
  if (fHasta.value) params.set("date_to", fHasta.value);
  if (fCorreo.value.trim()) params.set("correo", fCorreo.value.trim());
  if (fAccion.value.trim()) params.set("accion", fAccion.value.trim());
  if (fTexto.value.trim()) params.set("q", fTexto.value.trim());
  params.set("limit", fLimit.value);
  params.set("offset", String(offset));
  return params.toString();
}

async function load() {
  const qs = buildQuery();
  const r = await fetch(`/api/auditoria?${qs}`);
  const data = await r.json();

  if (!r.ok) {
    tblBody.innerHTML = "";
    empty.style.display = "block";
    metaInfo.textContent = data.detail || `Error ${r.status}`;
    return;
  }

  const rows = data.rows || [];
  const total = data.total || 0;
  const limit = data.limit || Number(fLimit.value);

  tblBody.innerHTML = "";
  empty.style.display = rows.length ? "none" : "block";
  console.log(JSON.stringify(rows))

  rows.forEach(x => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${x.FECHA}</td>
      <td>${x.ROL}</td>
      <td>${x.RESPONSABLE}</td>
      <td>${x.CORREO}</td>
      <td><b>${x.accion}</b></td>
      <td>${escapeHtml(x.DESCRIPCION)}</td>
    `;
    tblBody.appendChild(tr);
  });

  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  metaInfo.textContent = `Mostrando ${from}–${to} de ${total} registros`;

  btnPrev.disabled = offset <= 0;
  btnNext.disabled = (offset + limit) >= total;
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[c]));
}

btnBuscar.addEventListener("click", () => { offset = 0; load(); });
btnLimpiar.addEventListener("click", () => {
  fDesde.value = ""; fHasta.value = "";
  fCorreo.value = ""; fAccion.value = ""; fTexto.value = "";
  fLimit.value = "100";
  offset = 0;
  load();
});
btnPrev.addEventListener("click", () => { offset = Math.max(0, offset - Number(fLimit.value)); load(); });
btnNext.addEventListener("click", () => { offset = offset + Number(fLimit.value); load(); });


btnExport.addEventListener("click", () => {
  const params = new URLSearchParams();
  params.set("report", "auditoria");
  if (fDesde.value) params.set("date_from", fDesde.value);
  if (fHasta.value) params.set("date_to", fHasta.value);
  if (fCorreo.value.trim()) params.set("correo", fCorreo.value.trim());
  if (fAccion.value.trim()) params.set("accion", fAccion.value.trim());
  if (fTexto.value.trim()) params.set("q", fTexto.value.trim());

  window.location.href = `/api/export/excel?${params.toString()}`;
});

load();