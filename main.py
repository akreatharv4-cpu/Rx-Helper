from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n\napp = FastAPI()\n\napp.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])\n\n@app.get("/analyze-text")\ndef analyze_text(text: str):\n    # Your text analysis logic here\n    return {"result": "Analysis complete."}
import pandas as pd
import chardet

# 1. Detect the encoding of the file
try:
    with open('OPD CSV.csv', 'rb') as f:
        # Reading the first 10,000 bytes is usually enough to guess correctly
        rawdata = f.read(10000)
        result = chardet.detect(rawdata)
        encoding_found = result['encoding']
        print(f"Detected encoding: {encoding_found}")

    # 2. Use the detected encoding (or fallback to latin1 if detection fails)
    df = pd.read_csv('OPD CSV.csv', encoding=encoding_found or 'latin1')
    
    # Just to confirm it worked:
    print("File loaded successfully!")
    print(df.head())

except FileNotFoundError:
    print("Error: The file 'OPD CSV.csv' was not found in the directory.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
