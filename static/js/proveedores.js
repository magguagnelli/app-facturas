let editingId = null;

const q = document.getElementById("q");
const btnBuscar = document.getElementById("btnBuscar");
const btnNuevo = document.getElementById("btnNuevo");
const tbl = document.getElementById("tbl");
const empty = document.getElementById("empty");

const modalBg = document.getElementById("modalBg");
const btnCerrar = document.getElementById("btnCerrar");
const modalTitle = document.getElementById("modalTitle");
const modalMsg = document.getElementById("modalMsg");
const form = document.getElementById("form");

const f = (id) => document.getElementById(id);

function openModal(mode) {
  modalBg.style.display = "flex";
  modalMsg.textContent = "";
  modalTitle.textContent = mode === "edit" ? "Editar proveedor" : "Nuevo proveedor";
}
function closeModal() {
  modalBg.style.display = "none";
}

btnCerrar.addEventListener("click", closeModal);
modalBg.addEventListener("click", (e) => { if (e.target === modalBg) closeModal(); });

function setForm(data) {
  editingId = data?.id || null;
  f("id").value = data?.id || "";
  f("rfc").value = data?.rfc || "";
  f("razon_social").value = data?.razon_social || "";
  f("nombre_comercial").value = data?.nombre_comercial || "";
  f("tipo_persona").value = data?.tipo_persona || "MORAL";
  f("telefono").value = data?.telefono || "";
  f("email").value = data?.email || "";
  f("estatus").value = data?.estatus || "ACTIVO";
}

async function api(path, opts) {
  const r = await fetch(path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data;
}

function rfcUpper() {
  f("rfc").value = (f("rfc").value || "").toUpperCase().trim();
}

async function load() {
  const params = new URLSearchParams();
  if (q.value.trim()) params.set("q", q.value.trim());
  const { data } = await api(`/api/proveedores?${params.toString()}`);

  tbl.innerHTML = "";
  empty.style.display = data.length ? "none" : "block";

  data.forEach(p => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><b>${p.rfc}</b></td>
      <td>${escapeHtml(p.razon_social)}</td>
      <td>${escapeHtml(p.nombre_comercial || "")}</td>
      <td>${p.tipo_persona}</td>
      <td><span class="pv-chip">${p.estatus}</span></td>
      <td><button class="pv-btn secondary btnEdit">Editar</button></td>
    `;
    tr.querySelector(".btnEdit").addEventListener("click", () => edit(p.id));
    tbl.appendChild(tr);
  });
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[c]));
}

btnBuscar.addEventListener("click", () => load());
btnNuevo.addEventListener("click", () => { setForm(null); openModal("create"); });

async function edit(id) {
  const { data } = await api(`/api/proveedores/${id}`);
  setForm(data);
  openModal("edit");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  modalMsg.textContent = "Guardando...";
  rfcUpper();

  const payload = {
    rfc: f("rfc").value,
    razon_social: f("razon_social").value,
    nombre_comercial: f("nombre_comercial").value || null,
    tipo_persona: f("tipo_persona").value,
    telefono: f("telefono").value || null,
    email: f("email").value || null,
    estatus: f("estatus").value,
  };

  try {
    if (editingId) {
      await api(`/api/proveedores/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await api(`/api/proveedores`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    modalMsg.textContent = "Guardado correctamente.";
    await load();
    closeModal();
  } catch (err) {
    modalMsg.textContent = err.message || "Error guardando";
  }
});

load().catch(err => {
  console.error(err);
  empty.style.display = "block";
  empty.textContent = "No se pudieron cargar proveedores.";
});
