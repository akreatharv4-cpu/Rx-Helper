from transformers import AutoTokenizer, AutoModel

model_name = "emilyalsentzer/Bio_ClinicalBERT"

print(f"Fetching {model_name}...")
print("(Note: This will download the model weights the first time you run it.)")

# Load Tokenizer and Model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

print("ClinicalBERT loaded successfully!\n")

# Run a test prescription through the model
test_prescription = "Rx: Tab. Metformin 500mg PO BID for Type 2 Diabetes."
print(f"Analyzing text: '{test_prescription}'")

# Tokenize and process
inputs = tokenizer(test_prescription, return_tensors="pt")
outputs = model(**inputs)

print("\nSuccess! The AI system processed the text.")
print(f"Output tensor shape: {outputs.last_hidden_state.shape}")