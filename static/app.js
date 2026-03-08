let uploadedFile = null
let analysisData = null

const fileInput = document.getElementById("fileInput")

if (fileInput) {

fileInput.addEventListener("change", function () {

uploadedFile = this.files[0]

previewImage(uploadedFile)

})

}

// ---------------- IMAGE PREVIEW ----------------

function previewImage(file) {

let reader = new FileReader()

reader.onload = function (e) {

let preview = document.getElementById("preview")

preview.src = e.target.result

preview.style.display = "block"

}

reader.readAsDataURL(file)

}

// ---------------- ANALYZE PRESCRIPTION ----------------

async function analyzePrescription() {

if (!uploadedFile) {

alert("Upload prescription image first")

return

}

let formData = new FormData()

formData.append("file", uploadedFile)

try {

let response = await fetch("/upload", {

method: "POST",

body: formData

})

let data = await response.json()

analysisData = data

displayResults(data)

} catch (error) {

alert("Analysis failed")

console.error(error)

}

}

// ---------------- DISPLAY RESULTS ----------------

function displayResults(data) {

document.getElementById("totalMedicines").innerText =
data.dashboard.total_medicines || 0

document.getElementById("polypharmacy").innerText =
data.dashboard.polypharmacy ? "YES ⚠" : "No"

// optional values (avoid JS crash)

document.getElementById("antibioticCount").innerText =
data.dashboard.antibiotic_count || 0

document.getElementById("injectionCount").innerText =
data.dashboard.injection_count || 0


let table = document.querySelector("#medicineTable tbody")

table.innerHTML = ""

if (!data.medicines_detected || data.medicines_detected.length === 0) {

table.innerHTML =
"<tr><td colspan='2'>No medicines detected</td></tr>"

} else {

data.medicines_detected.forEach(m => {

let cls = data.drug_classification ?
(data.drug_classification[m] || "Unknown") : "Unknown"

table.innerHTML += `
<tr>
<td>${m}</td>
<td>${cls}</td>
</tr>
`

})

}

// ---------------- INTERACTION ALERTS ----------------

let alerts = document.getElementById("alerts")

alerts.innerHTML = ""

if (data.drug_interactions && data.drug_interactions.length > 0) {

data.drug_interactions.forEach(i => {

alerts.innerHTML += `
<div class="alert">
<b>${i.severity} interaction</b><br>
${i.drug1} + ${i.drug2}<br>
${i.message}
</div>
`

})

} else {

alerts.innerHTML =
"<div>No interactions detected</div>"

}

}

// ---------------- DOWNLOAD REPORT ----------------

async function downloadReport() {

if (!analysisData) {

alert("Analyze prescription first")

return

}

const response = await fetch("/report", {

method: "POST",

headers: { "Content-Type": "application/json" },

body: JSON.stringify({

medicines: analysisData.medicines_detected,
interactions: analysisData.drug_interactions

})

})

const blob = await response.blob()

const url = window.URL.createObjectURL(blob)

const a = document.createElement("a")

a.href = url
a.download = "clinical_report.pdf"

a.click()

}
