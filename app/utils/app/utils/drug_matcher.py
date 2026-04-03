from rapidfuzz import process

DRUG_LIST = [
  # Antibiotics (Macrolides, Penicillins, Cephalosporins)
    "AZITHROMYCIN",
    "AMOXICILLIN",
    "CLARITHROMYCIN",
    "CEFIXIME",
    "CEFOPODOXIME",
    "AMOXICILLIN-CLAVULANATE",

    # Analgesics & Antipyretics (NSAIDs)
    "PARACETAMOL",
    "IBUPROFEN",
    "DICLOFENAC",
    "ACECLOFENAC",
    "NIMESULIDE",

    # Antihistamines & Respiratory
    "LEVOCETIRIZINE",
    "CETIRIZINE",
    "FEXOFENADINE",
    "LORATADINE",
    "MONTELUKAST",

    # Gastrointestinal (PPIs & H2 Blockers)
    "PANTOPRAZOLE",
    "OMEPRAZOLE",
    "RABEPRAZOLE",
    "FAMOTIDINE",
    "DOMPERIDONE",

    # Miscellaneous / Common Clinical Meds
    "METFORMIN",
    "AMLODIPINE",
    "ATORVASTATIN",
    "TELMISARTAN",
    "METRONIDAZOLE"
]
]

def find_drugs(text: str):
    words = text.split()
    detected = []

    for word in words:
        result = process.extractOne(word, DRUG_LIST)
        
        if result:
            match, score, _ = result
            
            if score > 80:
                detected.append(match)

    return list(set(detected))
