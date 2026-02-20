let editing = null;

const tbl = document.getElementById("tbl");
const btnNuevo = document.getElementById("btnNuevo");
const modalBg = document.getElementById("modalBg");
const form = document.getElementById("form");

const f = (id) => document.getElementById(id);

function openModal(data=null){
  modalBg.style.display = "flex";
  editing = data?.id || null;
  f("id").value = data?.id || "";
  f("id").disabled = !!editing;
  f("nombre").value = data?.nombre || "";
  f("estatus").value = data?.estatus || "ACTIVO";
}

function closeModal(){ modalBg.style.display = "none"; }

btnNuevo.onclick = () => openModal();
modalBg.onclick = (e) => { if(e.target === modalBg) closeModal(); };

async function api(path, opts){
  const r = await fetch(path, opts);
  const d = await r.json();
  if(!r.ok) throw new Error(d.detail);
  return d;
}

async function load(){
  const { data } = await api("/api/entidades");
  tbl.innerHTML = "";
  data.forEach(e => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${e.id}</td>
      <td>${e.nombre}</td>
      <td>${e.estatus}</td>
      <td>
        <button class="au-btn">
            <i class="fa fa-pencil" aria-hidden="true"></i>
        </button>
    </td>
    `;
    tr.querySelector("button").onclick = () => openModal(e);
    tbl.appendChild(tr);
  });
}

form.onsubmit = async (e) => {
  e.preventDefault();
  const payload = {
    id: f("id").value.toUpperCase(),
    nombre: f("nombre").value,
    estatus: f("estatus").value
  };
  try{
    if(editing){
      await api(`/api/entidades/${editing}`, {
        method:"PUT",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify(payload)
      });
    }else{
      await api(`/api/entidades`, {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify(payload)
      });
    }
    closeModal();
    load();
  }catch(err){ alert(err.message); }
};

load();
