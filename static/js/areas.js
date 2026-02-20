// static/js/area.js

let areasCache = [];

const qAreas = document.getElementById("qAreas");
const btnBuscarAreas = document.getElementById("btnBuscarAreas");
const btnNewArea = document.getElementById("btnNewArea");

const areasTbody = document.getElementById("areasTbody");
const areasEmpty = document.getElementById("areasEmpty");
const areasMsg = document.getElementById("areasMsg");

// Modal
const areaModalBg = document.getElementById("areaModalBg");
const areaModalTitle = document.getElementById("areaModalTitle");
const areaModalMsg = document.getElementById("areaModalMsg");
const btnCloseAreaModal = document.getElementById("btnCloseAreaModal");
const btnCancelArea = document.getElementById("btnCancelArea");
const areaForm = document.getElementById("areaForm");

const area_id = document.getElementById("area_id");
const area_nombre = document.getElementById("area_nombre");
const area_desc = document.getElementById("area_desc");

function escapeHtml(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showMsg(text, isError = false) {
  areasMsg.style.display = "block";
  areasMsg.textContent = text;
  areasMsg.style.color = isError ? "crimson" : "";
}

function hideMsg() {
  areasMsg.style.display = "none";
  areasMsg.textContent = "";
  areasMsg.style.color = "";
}

// ---------- API ----------
async function apiGetAreas() {
  const r = await fetch("/api/areas");
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || "No se pudo cargar el catálogo de áreas.");
  return j.data || [];
}

async function apiCreateArea(payload) {
  const r = await fetch("/api/areas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `Error creando área (${r.status}).`);
  return j;
}

async function apiUpdateArea(id, payload) {
  const r = await fetch(`/api/areas/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `Error actualizando área (${r.status}).`);
  return j;
}

async function apiDeleteArea(id) {
  const r = await fetch(`/api/areas/${id}`, { method: "DELETE" });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `Error eliminando área (${r.status}).`);
  return j;
}

// ---------- UI ----------
function renderAreas(rows) {
  areasTbody.innerHTML = "";

  if (!rows.length) {
    areasEmpty.style.display = "block";
    return;
  }
  areasEmpty.style.display = "none";

  for (const a of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(a.id)}</td>
      <td>${escapeHtml(a.nombre_area)}</td>
      <td>${escapeHtml(a.desc_area || "")}</td>
      <td style="display:flex; gap:8px;">
        <button class="au-btn" data-act="edit">
          <i class="fa fa-pencil" aria-hidden="true"></i>
        </button>
        <button class="au-btn" data-act="del">
          <i class="fa fa-trash" aria-hidden="true"></i>
        </button>
      </td>
    `;

    tr.querySelector('[data-act="edit"]').addEventListener("click", () => openEditModal(a));

    tr.querySelector('[data-act="del"]').addEventListener("click", async () => {
      const ok = confirm(`¿Eliminar el área #${a.id} "${a.nombre_area}"?\nEsta acción no se puede deshacer.`);
      if (!ok) return;

      hideMsg();
      try {
        await apiDeleteArea(a.id);
        await loadAreas();
      } catch (e) {
        showMsg(e.message, true);
      }
    });

    areasTbody.appendChild(tr);
  }
}

function filterAreas() {
  const q = (qAreas.value || "").trim().toLowerCase();
  if (!q) return areasCache;
  return areasCache.filter(a =>
    String(a.nombre_area || "").toLowerCase().includes(q) ||
    String(a.desc_area || "").toLowerCase().includes(q) ||
    String(a.id || "").includes(q)
  );
}

async function loadAreas() {
  hideMsg();
  try {
    areasCache = await apiGetAreas();
    renderAreas(filterAreas());
  } catch (e) {
    showMsg(e.message, true);
  }
}

// ---------- Modal ----------
function openNewModal() {
  areaModalTitle.textContent = "Nueva Área";
  areaModalMsg.textContent = "Captura los datos del área.";
  area_id.value = "";
  area_nombre.value = "";
  area_desc.value = "";
  areaModalBg.style.display = "flex";
  area_nombre.focus();
}

function openEditModal(a) {
  areaModalTitle.textContent = `Editar Área #${a.id}`;
  areaModalMsg.textContent = "Actualiza los datos y guarda cambios.";
  area_id.value = a.id;
  area_nombre.value = a.nombre_area || "";
  area_desc.value = a.desc_area || "";
  areaModalBg.style.display = "flex";
  area_nombre.focus();
}

function closeModal() {
  areaModalBg.style.display = "none";
}

btnNewArea?.addEventListener("click", openNewModal);
btnCloseAreaModal?.addEventListener("click", closeModal);
btnCancelArea?.addEventListener("click", closeModal);

btnBuscarAreas?.addEventListener("click", () => renderAreas(filterAreas()));
qAreas?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    renderAreas(filterAreas());
  }
});

areaForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  areaModalMsg.textContent = "Guardando...";

  const payload = {
    nombre_area: (area_nombre.value || "").trim(),
    desc_area: (area_desc.value || "").trim() || null,
  };

  try {
    if (!payload.nombre_area) throw new Error("El nombre del área es obligatorio.");

    const id = area_id.value ? Number(area_id.value) : null;

    if (id) {
      await apiUpdateArea(id, payload);
    } else {
      await apiCreateArea(payload);
    }

    closeModal();
    await loadAreas();
  } catch (err) {
    areaModalMsg.textContent = err.message || "Error guardando.";
  }
});

// Init
loadAreas();
