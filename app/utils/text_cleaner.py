import re

def clean_text(text: str) -> str:
    text = text.upper()
    text = re.sub(r'[^A-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
