async function analyzePrescription() {
    const text = document.getElementById("prescription").value;
    const output = document.getElementById("output");

    if (!text) {
        alert("Please enter prescription text");
        return;
    }

    output.innerHTML = "Analyzing... ⏳";

    const prompt = `
You are a clinical pharmacist.

Analyze this prescription:
${text}

Check:
1. Missing patient details
2. Drug interactions
3. Dose appropriateness
4. ADR risks
5. Counseling points

Give clear structured output.
`;

    try {
        const response = await fetch("https://api.openai.com/v1/chat/completions", {
            method: "POST",
            headers: {
                "Authorization": "Bearer YOUR_API_KEY",
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                model: "gpt-4o-mini",
                messages: [{ role: "user", content: prompt }]
            })
        });

        const data = await response.json();

        output.innerHTML = data.choices[0].message.content;

    } catch (error) {
        output.innerHTML = "Error: " + error.message;
    }
}
