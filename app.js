// Store prescriptions
let prescriptions = []

// Sample drug classification database
const antibiotics = ["amoxicillin","azithromycin","ciprofloxacin","ceftriaxone"]
const injections = ["ceftriaxone","insulin","diclofenac injection"]
const edl = ["paracetamol","amoxicillin","metformin","insulin","atorvastatin"]

// Manual prescription form
document.getElementById("manualForm").addEventListener("submit", function(e){

e.preventDefault()

let drug = document.querySelectorAll("#manualForm input")[1].value.toLowerCase()
let dose = document.querySelectorAll("#manualForm input")[2].value
let frequency = document.querySelectorAll("#manualForm input")[3].value
let duration = document.querySelectorAll("#manualForm input")[4].value

let prescription = {
drug,
dose,
frequency,
duration
}

prescriptions.push(prescription)

analyzePrescription()

this.reset()

})

function analyzePrescription(){

let totalDrugs = prescriptions.length
let antibioticCount = 0
let injectionCount = 0
let genericCount = 0
let edlCount = 0

let alerts = []

prescriptions.forEach(p=>{

if(antibiotics.includes(p.drug))
antibioticCount++

if(injections.includes(p.drug))
injectionCount++

if(edl.includes(p.drug))
edlCount++

if(p.drug)
genericCount++

if(!p.dose || !p.frequency || !p.duration)
alerts.push("Incomplete prescription information")

})

if(totalDrugs > 5)
alerts.push("Polypharmacy detected (>5 drugs)")

// WHO indicators
let avgDrugs = totalDrugs
let antibioticPercent = (antibioticCount/totalDrugs)*100
let injectionPercent = (injectionCount/totalDrugs)*100
let genericPercent = (genericCount/totalDrugs)*100
let edlPercent = (edlCount/totalDrugs)*100

// Update UI
document.getElementById("avgDrugs").innerText = avgDrugs.toFixed(2)
document.getElementById("antibioticPercent").innerText = antibioticPercent.toFixed(1)+"%"
document.getElementById("injectionPercent").innerText = injectionPercent.toFixed(1)+"%"
document.getElementById("genericPercent").innerText = genericPercent.toFixed(1)+"%"
document.getElementById("edlPercent").innerText = edlPercent.toFixed(1)+"%"

// Show alerts
let alertBox = document.getElementById("alerts")
alertBox.innerHTML = ""

if(alerts.length === 0){
alertBox.innerHTML = "<p>No errors detected</p>"
}else{

alerts.forEach(a=>{
let p = document.createElement("p")
p.innerText = "⚠ "+a
alertBox.appendChild(p)
})

}

// Update chart
updateChart(antibioticPercent,injectionPercent,genericPercent,edlPercent)

}

let chart

function updateChart(a,i,g,e){

let ctx = document.getElementById("chart").getContext("2d")

if(chart)
chart.destroy()

chart = new Chart(ctx,{
type:"bar",
data:{
labels:[
"Antibiotics %",
"Injections %",
"Generic %",
"EDL %"
],
datasets:[{
label:"WHO Prescribing Indicators",
data:[a,i,g,e]
}]
}
})

}
