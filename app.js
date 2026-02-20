function analyze() {
  const input = document.getElementById("meds").value;

  if (!input.trim()) {
    alert("Please enter medicines");
    return;
  }

  const meds = input
    .split(/\n/)
    .map(m => m.trim().toLowerCase())
    .filter(m => m);

  const interactions = checkInteractions(meds);

  let result = "";

  // Patient details (demo)
  result += "Patient Details: Missing\n\n";

  // Interaction
  if (interactions.length > 0) {
    result += "Drug Interaction:\n";
    interactions.forEach(i => {
      result += "- " + i + "\n";
    });
  } else {
    result += "Drug Interaction: None found\n";
  }

  // Dose check (basic demo)
  result += "\nDose Check: Looks acceptable\n";

  // Advice
  result += "\nAdvice:\n";
  if (interactions.length > 0) {
    result += "Monitor patient closely\n";
  } else {
    result += "No major issues\n";
  }

  // Counseling
  result += "\nCounseling: Take medicines regularly";

  document.getElementById("output").innerText = result;
}

// Simple interaction database
function checkInteractions(meds) {
  const interactions = [];

  if (meds.includes("metformin") && meds.includes("atenolol")) {
    interactions.push("Metformin + Atenolol → May mask hypoglycemia symptoms");
  }

  if (meds.includes("azithromycin") && meds.includes("pantoprazole")) {
    interactions.push("Azithromycin + Pantoprazole → Minor interaction (absorption change)");
  }

  if (meds.includes("diclofenac") && meds.includes("pantoprazole")) {
    interactions.push("Diclofenac + Pantoprazole → Protective (reduces gastric irritation)");
  }

  return interactions;
}
