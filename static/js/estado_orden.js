let editingId = null;

const tbl = document.getElementById("tbl");
const empty = document.getElementById("empty");

const btnNuevo = document.getElementById("btnNuevo");
const modalBg = document.getElementById("modalBg");
const btnCerrar = document.getElementById("btnCerrar");

const modalTitle = document.getElementById("modalTitle");
const modalMsg = document.getElementById("modalMsg");
const form = document.getElementById("form");

const f = (id) => document.getElementById(id);

function openModal(mode, data=null){
  modalBg.style.display = "flex";
  modalMsg.textContent = "";
  modalTitle.textContent = mode === "edit" ? "Editar Estatus del Contrato" : "Estatus del Contrato";

  editingId = data?.id || null;
  f("id").value = data?.id || "";
  f("estatus_general").value = data?.estatus_general || "";
  f("estatus_reporte").value = data?.estatus_reporte || "";
  f("estado_resumen").value = data?.estado_resumen || "";
}

function closeModal(){ modalBg.style.display = "none"; }
btnCerrar.onclick = closeModal;
modalBg.onclick = (e) => { if(e.target === modalBg) closeModal(); };

async function api(path, opts){
  const r = await fetch(path, opts);
  const d = await r.json().catch(() => ({}));
  if(!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
  return d;
}

async function load(){
  const { data } = await api("/api/estado-orden");
  tbl.innerHTML = "";
  empty.style.display = data.length ? "none" : "block";

  data.forEach(x => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${x.id}</td>
      <td>${escapeHtml(x.estatus_general)}</td>
      <td>${escapeHtml(x.estatus_reporte)}</td>
      <td>${escapeHtml(x.estado_resumen)}</td>
      <td>
        <button class="au-btn">
          <i class="fa fa-pencil" aria-hidden="true"></i>
        </button>
      </td>
    `;
    tr.querySelector("button").onclick = () => openModal("edit", x);
    tbl.appendChild(tr);
  });
}

function escapeHtml(s){
  return (s || "").replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[c]));
}

btnNuevo.onclick = () => openModal("create");

form.onsubmit = async (e) => {
  e.preventDefault();
  modalMsg.textContent = "Guardando...";

  const payload = {
    estatus_general: f("estatus_general").value.trim(),
    estatus_reporte: f("estatus_reporte").value.trim(),
    estado_resumen: f("estado_resumen").value.trim(),
  };

  try{
    if(editingId){
      await api(`/api/estado-orden/${editingId}`, {
        method:"PUT",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify(payload)
      });
    } else {
      const r = await api(`/api/estado-orden`, {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify(payload)
      });
    }
    closeModal();
    load();
  }catch(err){
    modalMsg.textContent = err.message || "Error guardando";
  }
};

load().catch(err => {
  console.error(err);
  empty.style.display = "block";
  empty.textContent = "No se pudo cargar el catálogo.";
});
