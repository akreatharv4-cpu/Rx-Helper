import re

def clean_text(text):
    text = text.upper()  # Convert to uppercase
    text = re.sub(r'[^A-Z0-9\s]', ' ', text)  # Remove symbols
    text = re.sub(r'\s+', ' ', text)  # Remove extra spaces
    return text.strip()