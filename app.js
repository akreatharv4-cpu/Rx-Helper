async function analyze() {
    const text = document.getElementById("prescription").value;
    const output = document.getElementById("output");

    if (!text) {
        alert("Enter prescription");
        return;
    }

    output.innerHTML = "Analyzing...";

    // MOCK MODE (works without API)
    if (!window.API_KEY) {
        output.innerHTML = `
Patient Details: Missing\n
Drug Interaction: Possible (Metformin + Atenolol)\n
Dose Check: Looks acceptable\n
Advice: Monitor BP & glucose\n
Counseling: Take medicines regularly
        `;
        return;
    }

    const prompt = `Analyze this prescription: ${text}`;

    try {
        const res = await fetch("https://api.openai.com/v1/chat/completions", {
            method: "POST",
            headers: {
                "Authorization": "Bearer " + window.API_KEY,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                model: "gpt-4o-mini",
                messages: [{ role: "user", content: prompt }]
            })
        });

        const data = await res.json();

        if (!res.ok) {
            output.innerHTML = "Error: " + JSON.stringify(data);
            return;
        }

        output.innerHTML = data.choices[0].message.content;

    } catch (e) {
        output.innerHTML = "Error: " + e.message;
    }
}
