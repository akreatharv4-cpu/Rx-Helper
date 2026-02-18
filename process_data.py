import pandas as pd
import plotly.express as px
import os

# 1. Load and Clean Data
df = pd.read_csv('OPD  CSV.csv')
cols_to_fill = ['Sr.No', 'Patient Name', 'Age', 'Gender', 'Ward']
df[cols_to_fill] = df[cols_to_fill].ffill()

# 2. WHO Indicators
total_rx = df['Sr.No'].nunique()
avg_drugs = len(df) / total_rx
abx_mask = df['Drug Name'].str.contains('Amox|Cipro|Doxy|Azithro|Cef|Metronidazole', case=False, na=False)
pct_abx = (df[abx_mask].groupby('Sr.No').size().count() / total_rx) * 100
inj_mask = df['Dosage form'].str.contains('injection|inj|iv|im', case=False, na=False)
pct_inj = (df[inj_mask].groupby('Sr.No').size().count() / total_rx) * 100

# 3. Clinical Flags
poly_cases = (df.groupby('Sr.No').size() > 5).sum()
severe_ddi = df['Drug-drug interaction'].str.contains('Severe', case=False, na=False).sum()

# 4. Generate Visuals
fig = px.bar(df[abx_mask]['Drug Name'].value_counts().reset_index(), x='index', y='Drug Name', title="Antibiotic Distribution")

# 5. Create HTML Interface
html_content = f"""
<html>
<head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>body{{padding:40px; background:#f8f9fa;}} .card{{padding:20px; text-align:center; box-shadow:0 4px 8px rgba(0,0,0,0.1);}}</style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4 text-primary">RxHelper Clinical Audit</h1>
        <div class="row mb-4">
            <div class="col-md-3"><div class="card"><h5>Avg Drugs</h5><h2>{avg_drugs:.2f}</h2></div></div>
            <div class="col-md-3"><div class="card"><h5>Abx Rate</h5><h2>{pct_abx:.1f}%</h2></div></div>
            <div class="col-md-3"><div class="card"><h5>Inj Rate</h5><h2>{pct_inj:.1f}%</h2></div></div>
            <div class="col-md-3"><div class="card text-danger"><h5>Polypharmacy</h5><h2>{poly_cases}</h2></div></div>
        </div>
        <div class="card">{fig.to_html(full_html=False, include_plotlyjs='cdn')}</div>
        <div class="card mt-4"><h3>Severe DDI Detected: {severe_ddi}</h3></div>
    </div>
</body>
</html>
"""
with open("index.html", "w") as f:
    f.write(html_content)
