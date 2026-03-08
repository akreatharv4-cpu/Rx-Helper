// ================= FILE STORAGE =================

let uploadedFile = null


// ================= DRAG DROP =================

const dropArea = document.getElementById("dropArea")

if(dropArea){

dropArea.addEventListener("dragover", e=>{
e.preventDefault()
})

dropArea.addEventListener("drop", e=>{

e.preventDefault()

uploadedFile = e.dataTransfer.files[0]

previewImage(uploadedFile)

})

}


// ================= FILE INPUT =================

const fileInput = document.getElementById("fileInput")

if(fileInput){

fileInput.addEventListener("change", function(){

uploadedFile = this.files[0]

previewImage(uploadedFile)

})

}


// ================= IMAGE PREVIEW =================

function previewImage(file){

let reader = new FileReader()

reader.onload = function(e){

let preview = document.getElementById("preview")

preview.src = e.target.result
preview.style.display = "block"

}

reader.readAsDataURL(file)

}


// ================= ANALYZE PRESCRIPTION =================

async function analyzePrescription(){

if(!uploadedFile){

alert("Upload prescription image first")
return

}

let formData = new FormData()

formData.append("file", uploadedFile)

try{

let response = await fetch("/upload",{
method:"POST",
body:formData
})

let data = await response.json()

displayResults(data)

}catch(err){

alert("Server error. Check backend.")

}

}


// ================= DISPLAY RESULTS =================

function displayResults(data){

// ---------------- DASHBOARD ----------------

if(data.dashboard){

document.getElementById("totalMedicines").innerText =
data.dashboard.total_medicines

document.getElementById("antibioticCount").innerText =
data.dashboard.antibiotic_count

document.getElementById("injectionCount").innerText =
data.dashboard.injection_count

document.getElementById("polypharmacy").innerText =
data.dashboard.polypharmacy ? "YES ⚠" : "No"

}


// ---------------- MEDICINE TABLE ----------------

let tableBody = document.querySelector("#medicineTable tbody")

tableBody.innerHTML = ""

if(data.medicines_detected){

data.medicines_detected.forEach(m=>{

let cls = data.drug_classification[m] || "Unknown"

tableBody.innerHTML += `
<tr>
<td>${m}</td>
<td>${cls}</td>
</tr>
`

})

}


// ---------------- INTERACTIONS ----------------

let alertsBox = document.getElementById("alerts")

alertsBox.innerHTML = ""

if(data.drug_interactions && data.drug_interactions.length > 0){

data.drug_interactions.forEach(i=>{

let color="orange"

if(i.severity==="high") color="red"
if(i.severity==="low") color="green"

alertsBox.innerHTML += `
<div class="alert" style="border-left:6px solid ${color}">
<b>${i.severity.toUpperCase()} interaction</b><br>
${i.drug1} + ${i.drug2}<br>
${i.message}
</div>
`

})

}else{

alertsBox.innerHTML =
"<div class='alert success'>No drug interactions detected</div>"

}


// ---------------- CHART ----------------

createChart(data)

}


// ================= MEDICINE CHART =================

let chart

function createChart(data){

let ctx = document.getElementById("medicineChart")

if(!ctx) return

if(chart) chart.destroy()

chart = new Chart(ctx,{

type:"bar",

data:{
labels:data.medicines_detected,
datasets:[{
label:"Detected Medicines",
data:data.medicines_detected.map(()=>1)
}]
},

options:{
responsive:true,
plugins:{
legend:{display:false}
}
}

})

}


// ================= DOWNLOAD PDF REPORT =================

async function downloadReport(){

try{

const response = await fetch("/report",{

method:"POST",
headers:{"Content-Type":"application/json"},

body:JSON.stringify({
medicines:[],
interactions:[]
})

})

const blob = await response.blob()

const url = window.URL.createObjectURL(blob)

const a = document.createElement("a")

a.href = url
a.download = "clinical_report.pdf"

a.click()

}catch(err){

alert("Report generation failed")

}

}

