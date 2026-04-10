const fileInput = document.getElementById("fileInput");
const loader = document.getElementById("loader");
const manualText = document.getElementById("manualText");
const chatInput = document.getElementById("chatInput");
const chatBox = document.getElementById("chat-box");

// Store last analysis for PDF export
let lastAnalysisData = null;

/* ---------------- INITIALIZATION ---------------- */
if (fileInput) fileInput.addEventListener("change", handleUpload);

/* ---------------- CORE ANALYSIS HANDLER ---------------- */

// Mode can be 'upload' (file) or 'manual' (typed text)
async function analyze(mode = 'upload') {
    loader.style.display = "block";
    let endpoint = "/upload";
    let body = null;
    let headers = {};

    try {
        if (mode === 'manual') {
            const text = manualText.value.trim();
            if (!text) { alert("Please enter prescription text."); return; }
            endpoint = "/analyze-text";
            headers = { 'Content-Type': 'application/json' };
            body = JSON.stringify({ text: text });
        } else {
            const file = fileInput.files[0];
            if (!file) { alert("Please select a file first."); return; }
            body = new FormData();
            body.append("file", file);
        }

        const response = await fetch(endpoint, {
            method: "POST",
            headers: headers,
            body: body
        });

        if (!response.ok) throw new Error("Analysis failed");

        const data = await response.json();
        lastAnalysisData = data; // Save for PDF
        displayResults(data);

    } catch (err) {
        console.error("Clinical Analysis Error:", err);
        alert("Error analyzing prescription. Check console for details.");
    } finally {
        loader.style.display = "none";
    }
}

/* ---------------- DISPLAY RESULTS & WHO INDICATORS ---------------- */

function displayResults(data) {
    // 1. Update WHO Indicator Cards (The Pharmacy Intern metrics)
    if (data.who_indicators) {
        const who = data.who_indicators;
        updateIndicator("val-count", who.drugs_per_encounter, "");
        updateIndicator("val-generic", who.pc_generic, "%");
        updateIndicator("val-abx", who.pc_antibiotic, "%");
        updateIndicator("val-inj", who.pc_injection, "%");
        
        // Color coding indicators based on WHO Norms
        applyWHOColorCoding(who);
    }

    // 2. Display Medicines (Using BioBERT/CSV match data)
    const medicines = data.medicines || data.medicines_detected || [];
    const classes = data.drug_classes || {};
    const medContainer = document.getElementById("medList");

    medContainer.innerHTML = medicines.length === 0 
        ? "<p class='muted'>No medicines identified.</p>" 
        : medicines.map(m => `
            <div class="drug-badge">
                <i class="fas fa-pills"></i> 
                ${m.toUpperCase()} 
                <small style="display:block; font-size:10px; opacity:0.7;">${classes[m] || 'Clinical Class Unknown'}</small>
            </div>
        `).join("");

    // 3. Display Interactions (Alert Mechanism)
    const interactions = data.drug_interactions || data.interactions || [];
    const intContainer = document.getElementById("interactionList");

    intContainer.innerHTML = interactions.length === 0
        ? `<div class="success"><i class="fas fa-check-circle"></i> No drug-drug interactions detected.</div>`
        : interactions.map(i => {
            const sev = (i.severity || "Minor").toLowerCase();
            return `
                <div class="interaction-item ${sev}">
                    <strong>${i.drug1} + ${i.drug2}</strong> 
                    <span class="badge">${i.severity.toUpperCase()}</span>
                    <p style="margin:5px 0 0 0; font-size:0.9rem;">${i.message}</p>
                </div>
            `;
        }).join("");

    // 4. Raw Text Toggle
    const rawContainer = document.getElementById("rawText");
    if (rawContainer) rawContainer.innerText = data.raw_text || "";
}

/* ---------------- HELPERS & UI ---------------- */

function updateIndicator(id, value, suffix) {
    const el = document.getElementById(id);
    if (el) el.innerText = value + suffix;
}

function applyWHOColorCoding(who) {
    // High Antibiotic or Injection use flags (WHO standards)
    const abxCard = document.getElementById("val-abx").parentElement;
    if (who.pc_antibiotic > 30) abxCard.style.border = "1px solid var(--danger)";
    
    const genCard = document.getElementById("val-generic").parentElement;
    if (who.pc_generic < 100) genCard.style.border = "1px solid var(--warning)";
}

/* ---------------- AI CLINICAL CHAT ---------------- */

async function sendChat() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Append user message
    chatBox.innerHTML += `<div style="text-align:right; margin:10px 0;"><span style="background:#3b82f6; color:white; padding:8px 12px; border-radius:15px; display:inline-block;">${message}</span></div>`;
    chatInput.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                context: lastAnalysisData ? lastAnalysisData.medicines : [] 
            })
        });
        const data = await res.json();
        
        // Append AI response
        chatBox.innerHTML += `<div style="margin:10px 0;"><span style="background:#f1f5f9; padding:8px 12px; border-radius:15px; display:inline-block; border:1px solid #e2e8f0;"><b>AI:</b> ${data.reply}</span></div>`;
    } catch (e) {
        chatBox.innerHTML += `<div class="error">AI offline. Check backend.</div>`;
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

/* ---------------- PDF EXPORT ---------------- */

function downloadPDF() {
    if (!lastAnalysisData) {
        alert("Analyze a prescription first to generate a report.");
        return;
    }
    // For a clinical tool, window.print() formatted via CSS @media print is best
    // But we can also trigger a browser print specifically for the results card
    window.print();
}

/* ---------------- DRAG & DROP ---------------- */
const dropZone = document.getElementById("upload-card"); // Match your ID
if (dropZone) {
    ['dragover', 'dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            if (evt === 'dragover') dropZone.style.background = "#eff6ff";
            if (evt === 'dragleave') dropZone.style.background = "";
            if (evt === 'drop') {
                const file = e.dataTransfer.files[0];
                fileInput.files = e.dataTransfer.files;
                analyze('upload');
            }
        });
    });
}