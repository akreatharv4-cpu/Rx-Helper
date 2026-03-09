<script>

const fileInput = document.getElementById('fileInput');
const resultsArea = document.getElementById('resultsArea');
const loader = document.getElementById('loader');

fileInput.addEventListener("change", handleUpload);

async function handleUpload(e){

    const file = e.target.files[0];

    if(!file){
        alert("Please select a file");
        return;
    }

    resultsArea.style.display = "none";
    loader.style.display = "block";

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

        loader.style.display = "none";

    }

}

function displayResults(data){

    resultsArea.style.display = "block";

    const medicines = data.medicines_detected || [];
    const interactions = data.drug_interactions || [];
    const rawText = data.raw_text || "";

    // Medicines
    const medContainer = document.getElementById("medList");

    if(medicines.length === 0){
        medContainer.innerHTML = "<p>No medicines detected</p>";
    }else{
        medContainer.innerHTML = medicines
        .map(m => `<span class="medicine-tag">${m.toUpperCase()}</span>`)
        .join("");
    }

    // Interactions
    const intContainer = document.getElementById("interactionList");

    if(interactions.length === 0){

        intContainer.innerHTML = `
        <p style="color: var(--success)">
        <i class="fas fa-check-circle"></i>
        No interactions detected
        </p>
        `;

    }else{

        intContainer.innerHTML = interactions.map(i => `
            <div class="interaction-item">
                <strong>${i.drug1?.toUpperCase()} + ${i.drug2?.toUpperCase()}</strong><br>
                <span style="color: var(--danger)">Severity: ${i.severity}</span><br>
                <small>${i.message}</small>
            </div>
        `).join("");

    }

    // Raw OCR text
    document.getElementById("rawText").innerText = rawText;

}

</script>
const dropZone = document.getElementById("dropZone");

dropZone.addEventListener("dragover", (e)=>{
    e.preventDefault();
    dropZone.style.background = "#eef7ff";
});

dropZone.addEventListener("dragleave", ()=>{
    dropZone.style.background = "";
});

dropZone.addEventListener("drop", (e)=>{
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    fileInput.files = e.dataTransfer.files;
    handleUpload({target:{files:[file]}});
});
