// Prescription storage
let prescriptions = []

// Drug classification database
const antibiotics = ["amoxicillin","azithromycin","ciprofloxacin","ceftriaxone"]
const injections = ["ceftriaxone","insulin","diclofenac injection"]
const edl = ["paracetamol","amoxicillin","metformin","insulin","atorvastatin"]

// ---------- MANUAL PRESCRIPTION ENTRY ----------

document.getElementById("manualForm").addEventListener("submit", async function(e){

e.preventDefault()

let inputs = document.querySelectorAll("#manualForm input")

let drug = inputs[1].value.toLowerCase()
let dose = inputs[2].value
let frequency = inputs[3].value
let duration = inputs[4].value

let prescription = {drug,dose,frequency,duration}

prescriptions.push(prescription)

analyzeLocal()

let text = `${drug} ${dose}`

let response = await fetch("/analyze",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({text:text})
})

let result = await response.json()

showInteractions(result.interactions)
showAdvancedResults(result)

this.reset()

})

// ---------- IMAGE PRESCRIPTION UPLOAD ----------

document.getElementById("uploadForm").addEventListener("submit", async function(e){

e.preventDefault()

let file = document.getElementById("prescriptionImage").files[0]

if(!file){
alert("Upload prescription image")
return
}

let formData = new FormData()
formData.append("file",file)

let response = await fetch("/upload",{method:"POST",body:formData})

let result = await response.json()

showInteractions(result.interactions)
showAdvancedResults(result)

})

// ---------- LOCAL WHO ANALYSIS ----------

function analyzeLocal(){

let totalDrugs = prescriptions.length
let antibioticCount = 0
let injectionCount = 0
let genericCount = 0
let edlCount = 0

let alerts=[]

prescriptions.forEach(p=>{

if(antibiotics.includes(p.drug)) antibioticCount++

if(injections.includes(p.drug)) injectionCount++

if(edl.includes(p.drug)) edlCount++

if(p.drug) genericCount++

if(!p.dose || !p.frequency || !p.duration)
alerts.push("Incomplete prescription information")

})

if(totalDrugs>5) alerts.push("Polypharmacy detected")

let antibioticPercent=(antibioticCount/totalDrugs)*100
let injectionPercent=(injectionCount/totalDrugs)*100
let genericPercent=(genericCount/totalDrugs)*100
let edlPercent=(edlCount/totalDrugs)*100

document.getElementById("avgDrugs").innerText=totalDrugs
document.getElementById("antibioticPercent").innerText=antibioticPercent.toFixed(1)+"%"
document.getElementById("injectionPercent").innerText=injectionPercent.toFixed(1)+"%"
document.getElementById("genericPercent").innerText=genericPercent.toFixed(1)+"%"
document.getElementById("edlPercent").innerText=edlPercent.toFixed(1)+"%"

updateChart(antibioticPercent,injectionPercent,genericPercent,edlPercent)

}

// ---------- INTERACTION DISPLAY ----------

function showInteractions(interactions){

let box=document.getElementById("alerts")

box.innerHTML=""

if(!interactions || interactions.length===0){

box.innerHTML="<div class='alert success'>No drug interactions detected</div>"

return
}

interactions.forEach(i=>{

box.innerHTML+=`

<div class="alert danger">
<b>${i.severity} interaction</b><br>
${i.msg}
</div>
`

})

}

// ---------- ADVANCED RESULTS ----------

function showAdvancedResults(result){

let box=document.getElementById("alerts")

// Safety score
if(result.safety_score){
box.innerHTML+=`

<div class="scoreBox">
Safety Score: ${result.safety_score}/100
</div>
`
}

// Detected medicines
if(result.detected_medicines){

box.innerHTML+=`<h3>Detected Medicines</h3><ul>`

result.detected_medicines.forEach(m=>{
box.innerHTML+=`<li>${m}</li>`
})

box.innerHTML+=`</ul>`

}

}

// ---------- CHART ----------

let chart

function updateChart(a,i,g,e){

let ctx=document.getElementById("chart").getContext("2d")

if(chart) chart.destroy()

chart=new Chart(ctx,{
type:"bar",
data:{
labels:["Antibiotics %","Injections %","Generic %","EDL %"],
datasets:[{
label:"WHO Prescribing Indicators",
data:[a,i,g,e],
backgroundColor:[
"#ff7675",
"#74b9ff",
"#55efc4",
"#ffeaa7"
]
}]
},
options:{responsive:true}
})

}
