// static/js/catalogos.js

const fileExcel = document.getElementById("fileExcel");
const btnUpload = document.getElementById("btnUpload");
const uploadMsg = document.getElementById("uploadMsg");

const resultBox = document.getElementById("resultBox");
const resultSummary = document.getElementById("resultSummary");
const summaryTbody = document.getElementById("summaryTbody");

const errorsBox = document.getElementById("errorsBox");
const errorsTbody = document.getElementById("errorsTbody");

const notesBox = document.getElementById("notesBox");
const notesList = document.getElementById("notesList");

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setMsg(text, isError=false) {
  uploadMsg.textContent = text;
  uploadMsg.style.color = isError ? "crimson" : "";
}

function clearUI() {
  resultBox.style.display = "none";
  summaryTbody.innerHTML = "";
  errorsTbody.innerHTML = "";
  notesList.innerHTML = "";
  errorsBox.style.display = "none";
  notesBox.style.display = "none";
}

function renderSummary(summary) {
  summaryTbody.innerHTML = "";
  const sheets = Object.keys(summary || {});
  for (const sh of sheets) {
    const s = summary[sh];
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(sh)}</td>
      <td>${escapeHtml(s.inserted)}</td>
      <td>${escapeHtml(s.updated)}</td>
      <td>${escapeHtml(s.errors)}</td>
    `;
    summaryTbody.appendChild(tr);
  }
}

function renderRowErrors(rowErrors) {
  if (!rowErrors || !rowErrors.length) {
    errorsBox.style.display = "none";
    return;
  }
  errorsBox.style.display = "block";
  errorsTbody.innerHTML = "";
  for (const e of rowErrors) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(e.sheet)}</td>
      <td>${escapeHtml(e.row)}</td>
      <td>${escapeHtml(e.error)}</td>
    `;
    errorsTbody.appendChild(tr);
  }
}

function renderNotes(notes) {
  if (!notes || !notes.length) {
    notesBox.style.display = "none";
    return;
  }
  notesBox.style.display = "block";
  notesList.innerHTML = "";
  for (const n of notes) {
    const li = document.createElement("li");
    li.textContent = n;
    notesList.appendChild(li);
  }
}

btnUpload.addEventListener("click", async () => {
  clearUI();

  if (!fileExcel.files || !fileExcel.files.length) {
    setMsg("Selecciona un archivo Excel.", true);
    return;
  }

  const f = fileExcel.files[0];
  const fd = new FormData();
  fd.append("file", f);

  setMsg("Subiendo y procesando...", false);
  btnUpload.disabled = true;

  try {
    const r = await fetch("/api/catalogos/upload", { method: "POST", body: fd });
    const j = await r.json().catch(() => ({}));

    if (!r.ok) {
      const detail = j.detail || j.message || "Error al procesar.";
      setMsg(detail, true);

      // Si trae errors estructurales, muéstralos
      if (j.errors && Array.isArray(j.errors)) {
        resultBox.style.display = "block";
        resultSummary.innerHTML = `<b style="color:crimson;">Estructura inválida:</b><br>${j.errors.map(escapeHtml).join("<br>")}`;
      }else{
         resultBox.style.display = "block";
        resultSummary.innerHTML = `
        <b style="color:crimson;">Error:</b> ${escapeHtml(j.error || detail)}<br>
        ${j.traceback ? "<pre style='white-space:pre-wrap; margin-top:10px;'>" + escapeHtml(j.traceback) + "</pre>" : ""}
        `;
      }
      return;
    }

    setMsg("Procesado correctamente.", false);

    resultBox.style.display = "block";
    resultSummary.innerHTML = `
      <b>Archivo:</b> ${escapeHtml(j.file)}<br>
      <b>Mensaje:</b> ${escapeHtml(j.message)}<br>
      <b>Hojas procesadas:</b> ${escapeHtml(j.total_sheets)}
    `;

    renderSummary(j.summary);
    renderRowErrors(j.row_errors);
    renderNotes(j.notes);

  } catch (e) {
    setMsg(e.message || "Error inesperado.", true);
  } finally {
    btnUpload.disabled = false;
  }
});
