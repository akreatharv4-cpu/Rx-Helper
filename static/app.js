// ================= PRESCRIPTION STORAGE =================

let prescriptions = []

// Drug classification database
const antibiotics = ["amoxicillin","azithromycin","ciprofloxacin","ceftriaxone"]
const injections = ["ceftriaxone","insulin","diclofenac injection"]
const edl = ["paracetamol","amoxicillin","metformin","insulin","atorvastatin"]


// ================= IMAGE PREVIEW =================

document.getElementById("prescriptionImage").addEventListener("change",function(){

let file=this.files[0]

if(file){

let reader=new FileReader()

reader.onload=function(e){

let preview=document.getElementById("preview")

preview.src=e.target.result
preview.style.display="block"

}

reader.readAsDataURL(file)

}

})


// ================= IMAGE PRESCRIPTION UPLOAD =================

document.getElementById("uploadForm").addEventListener("submit", async function(e){

e.preventDefault()

let file=document.getElementById("prescriptionImage").files[0]

if(!file){
alert("Upload prescription image")
return
}

let formData=new FormData()
formData.append("file",file)

try{

let response=await fetch("/upload",{method:"POST",body:formData})

let result=await response.json()

displayResults(result)

}catch(err){

alert("Server error. Check backend.")

}

})


// ================= MANUAL PRESCRIPTION ENTRY =================

document.getElementById("manualForm").addEventListener("submit", async function(e){

e.preventDefault()

let inputs=document.querySelectorAll("#manualForm input")

let drug=inputs[1].value.toLowerCase()
let dose=inputs[2].value
let frequency=inputs[3].value
let duration=inputs[4].value

let prescription={drug,dose,frequency,duration}

prescriptions.push(prescription)

analyzeLocal()

let text=`${drug} ${dose}`

try{

let response=await fetch("/analyze",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({text:text})
})

let result=await response.json()

displayResults(result)

}catch(err){

alert("Server error while analyzing")

}

this.reset()

})


// ================= DISPLAY RESULTS =================

function displayResults(result){

// ---------- medicine table ----------

let tableBody=document.querySelector("#medicineTable tbody")

tableBody.innerHTML=""

if(result.detected_medicines){

result.detected_medicines.forEach(m=>{

tableBody.innerHTML+=`

<tr>
<td>${m}</td>
</tr>
`

})

}


// ---------- interactions ----------

let alertsBox=document.getElementById("alerts")

alertsBox.innerHTML=""

if(result.interactions && result.interactions.length>0){

result.interactions.forEach(i=>{

alertsBox.innerHTML+=`

<div class="alert danger">
<b>${i.severity} interaction</b><br>
${i.message}
</div>

`

})

}else{

alertsBox.innerHTML="<div class='alert success'>No drug interactions detected</div>"

}


// ---------- safety score ----------

if(result.safety_score){

let score=result.safety_score

document.getElementById("scoreValue").innerText="Safety Score: "+score+"/100"

let bar=document.getElementById("scoreBar")

bar.style.width=score+"%"

if(score>80) bar.style.background="green"
else if(score>60) bar.style.background="orange"
else bar.style.background="red"

}

}


// ================= LOCAL WHO ANALYSIS =================

function analyzeLocal(){

let totalDrugs=prescriptions.length

if(totalDrugs===0) return

let antibioticCount=0
let injectionCount=0
let genericCount=0
let edlCount=0

prescriptions.forEach(p=>{

if(antibiotics.includes(p.drug)) antibioticCount++

if(injections.includes(p.drug)) injectionCount++

if(edl.includes(p.drug)) edlCount++

if(p.drug) genericCount++

})

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


// ================= CHART =================

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




