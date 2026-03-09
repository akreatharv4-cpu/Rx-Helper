const fileInput = document.getElementById("fileInput");
const loader = document.getElementById("loader");

fileInput.addEventListener("change", handleUpload);

async function handleUpload(e){

    const file = e.target.files[0];

    if(!file){
        alert("Please select a file");
        return;
    }

    loader.style.display="block";

    const formData = new FormData();
    formData.append("file", file);

    try{

        const response = await fetch("/upload",{
            method:"POST",
            body:formData
        });

        if(!response.ok){
            throw new Error("Upload failed");
        }

        const data = await response.json();

        displayResults(data);

    }catch(err){

        console.error(err);
        alert("Error analyzing prescription");

    }finally{

        loader.style.display="none";

    }

}

function displayResults(data){

    const medicines = data.medicines_detected || [];
    const classes = data.drug_classes || {};
    const interactions = data.drug_interactions || [];
    const warnings = data.dose_warnings || [];
    const rawText = data.raw_text || "";

    /* ---------------- Medicines ---------------- */

    const medContainer=document.getElementById("medList");

    if(medicines.length===0){

        medContainer.innerHTML="<p>No medicines detected</p>";

    }else{

        medContainer.innerHTML = medicines.map(m => `
            <div class="drug-card">
                <b>${m.toUpperCase()}</b><br>
                <span>${classes[m] || "Unknown class"}</span>
            </div>
        `).join("");

    }

    /* ---------------- Dose Warnings ---------------- */

    const warnContainer=document.getElementById("doseWarnings");

    if(warnings.length===0){

        warnContainer.innerHTML="No dose warnings";

    }else{

        warnContainer.innerHTML = warnings.map(w => `
            <div class="warning">
                ⚠ ${w.drug} dose ${w.dose}mg exceeds limit ${w.limit}mg
            </div>
        `).join("");

    }

    /* ---------------- Interactions ---------------- */

    const intContainer=document.getElementById("interactionList");

    if(interactions.length===0){

        intContainer.innerHTML=`
        <p style="color:var(--success)">
        <i class="fas fa-check-circle"></i>
        No interactions detected
        </p>
        `;

    }else{

        intContainer.innerHTML = interactions.map(i=>{

            let severityClass="minor";

            if(i.severity==="High") severityClass="high";
            if(i.severity==="Moderate") severityClass="moderate";

            return `
            <div class="interaction ${severityClass}">
                <strong>${i.drug1?.toUpperCase()} + ${i.drug2?.toUpperCase()}</strong><br>
                Severity: ${i.severity}<br>
                ${i.message}
            </div>
            `;

        }).join("");

    }

    /* ---------------- OCR TEXT ---------------- */

    document.getElementById("rawText").innerText = rawText;

}


/* ---------------- Drag & Drop Upload ---------------- */

const dropZone=document.getElementById("dropZone");

if(dropZone){

dropZone.addEventListener("dragover",(e)=>{
    e.preventDefault();
    dropZone.style.background="#eef7ff";
});

dropZone.addEventListener("dragleave",()=>{
    dropZone.style.background="";
});

dropZone.addEventListener("drop",(e)=>{

    e.preventDefault();

    const file=e.dataTransfer.files[0];

    fileInput.files=e.dataTransfer.files;

    handleUpload({target:{files:[file]}});

});

}
 
