// app.js — improved and robust version

let uploadedFile = null;
let analysisData = null;

const fileInput = document.getElementById("fileInput");
const preview = document.getElementById("preview");
const analyzeBtn = document.getElementById("analyzeButton");
const downloadBtn = document.getElementById("downloadButton");
const spinner = document.getElementById("spinner"); // optional spinner element

// helper: escape text for safe insertion into HTML
function escapeHtml(unsafe) {
  if (unsafe === null || unsafe === undefined) return "";
  return String(unsafe)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// --- Setup listeners ---
if (fileInput) {
  fileInput.addEventListener("change", function () {
    uploadedFile = this.files && this.files[0] ? this.files[0] : null;
    previewImage(uploadedFile);
  });
}

if (analyzeBtn) {
  analyzeBtn.addEventListener("click", analyzePrescription);
}

if (downloadBtn) {
  downloadBtn.addEventListener("click", downloadReport);
}

// --- Preview ---
function previewImage(file) {
  if (!preview) return;
  if (!file) {
    preview.src = "";
    preview.style.display = "none";
    return;
  }

  const reader = new FileReader();
  reader.onload = function (e) {
    preview.src = e.target.result;
    preview.style.display = "block";
  };
  reader.readAsDataURL(file);
}

// --- Small UI helpers ---
function setBusy(isBusy) {
  if (analyzeBtn) analyzeBtn.disabled = !!isBusy;
  if (downloadBtn) downloadBtn.disabled = !!isBusy || !analysisData;
  if (spinner) spinner.style.display = isBusy ? "inline-block" : "none";
}

function showAlert(msg) {
  // you can customize where to show alerts; fallback to window.alert
  const alertsArea = document.getElementById("alerts");
  if (alertsArea) {
    alertsArea.innerHTML = `<div class="alert-info">${escapeHtml(msg)}</div>`;
  } else {
    alert(msg);
  }
}

// --- Analyze prescription ---
async function analyzePrescription() {
  if (!uploadedFile) {
    showAlert("Upload a prescription image first.");
    return;
  }

  setBusy(true);

  try {
    const formData = new FormData();
    formData.append("file", uploadedFile);

    const resp = await fetch("/upload", {
      method: "POST",
      body: formData
    });

    if (!resp.ok) {
      const txt = await resp.text().catch(() => "");
      throw new Error(`Server returned ${resp.status}: ${txt}`);
    }

    const data = await resp.json();
    analysisData = data;
    displayResults(data);
    setBusy(false);
  } catch (error) {
    console.error("Analysis failed:", error);
    showAlert("Analysis failed. See console for details.");
    setBusy(false);
  }
}

// --- Display results ---
function displayResults(data) {
  // dashboard fields
  const totalMedicinesEl = document.getElementById("totalMedicines");
  const polypharmacyEl = document.getElementById("polypharmacy");
  const antibioticEl = document.getElementById("antibioticCount");
  const injectionEl = document.getElementById("injectionCount");

  const dashboard = data.dashboard || {};

  if (totalMedicinesEl) totalMedicinesEl.innerText = dashboard.total_medicines ?? 0;
  if (polypharmacyEl) polypharmacyEl.innerText = dashboard.polypharmacy ? "YES ⚠" : "No";
  if (antibioticEl) antibioticEl.innerText = dashboard.antibiotic_count ?? 0;
  if (injectionEl) injectionEl.innerText = dashboard.injection_count ?? 0;

  // medicines_detected may be a list of strings OR list of objects (e.g. {matched_name,...})
  let meds = [];
  if (Array.isArray(data.medicines_detected)) {
    meds = data.medicines_detected.map(item => {
      if (typeof item === "string") return item;
      // common keys we might use
      if (item.matched_name) return item.matched_name;
      if (item.name) return item.name;
      if (item.medicine) return item.medicine;
      // fallback: stringify
      return String(item);
    });
  }

  // drug_classification might be a mapping { "paracetamol": "Analgesic" }
  const classification = data.drug_classification || {};

  const tbody = document.querySelector("#medicineTable tbody");
  if (tbody) {
    tbody.innerHTML = "";
    if (!meds || meds.length === 0) {
      tbody.innerHTML = "<tr><td colspan='2'>No medicines detected</td></tr>";
    } else {
      meds.forEach(m => {
        const cls = classification[m] || classification[m.toLowerCase()] || "Unknown";
        const row = document.createElement("tr");
        const cellName = document.createElement("td");
        const cellClass = document.createElement("td");
        cellName.innerHTML = escapeHtml(m);
        cellClass.innerHTML = escapeHtml(cls);
        row.appendChild(cellName);
        row.appendChild(cellClass);
        tbody.appendChild(row);
      });
    }
  }

  // interactions
  const alertsContainer = document.getElementById("alerts");
  if (alertsContainer) {
    alertsContainer.innerHTML = "";
    const interactions = Array.isArray(data.drug_interactions) ? data.drug_interactions : [];

    if (interactions.length > 0) {
      interactions.forEach(i => {
        const sev = escapeHtml(i.severity ?? "Info");
        const d1 = escapeHtml(i.drug1 ?? (i.drug_a ?? "Drug A"));
        const d2 = escapeHtml(i.drug2 ?? (i.drug_b ?? "Drug B"));
        const msg = escapeHtml(i.message ?? "");
        const div = document.createElement("div");
        div.className = "alert";
        div.innerHTML = `<b>${sev} interaction</b><br>${d1} + ${d2}<br>${msg}`;
        alertsContainer.appendChild(div);
      });
    } else {
      alertsContainer.innerHTML = "<div>No interactions detected</div>";
    }
  }

  // enable download button if report endpoint exists
  if (downloadBtn) downloadBtn.disabled = false;
}

// --- Download PDF report ---
async function downloadReport() {
  if (!analysisData) {
    showAlert("Analyze prescription before downloading the report.");
    return;
  }

  setBusy(true);

  try {
    const payload = {
      medicines: analysisData.medicines_detected ?? [],
      interactions: analysisData.drug_interactions ?? []
    };

    const resp = await fetch("/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const txt = await resp.text().catch(() => "");
      throw new Error(`Server returned ${resp.status}: ${txt}`);
    }

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "clinical_report.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    setBusy(false);
  } catch (error) {
    console.error("Report download failed:", error);
    showAlert("Report generation failed. See console for details.");
    setBusy(false);
  }
}

// --- optional: initialize UI state on load ---
document.addEventListener("DOMContentLoaded", () => {
  setBusy(false);
  if (preview) preview.style.display = preview.src ? "block" : "none";
  if (downloadBtn) downloadBtn.disabled = true;
});
