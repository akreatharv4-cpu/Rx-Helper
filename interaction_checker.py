import pandas as pd

# ---------------- LOAD INTERACTION DATABASE ----------------

try:
    interactions_df = pd.read_csv("drug_interactions.csv")

    # normalize drug names
    interactions_df["drug1"] = interactions_df["drug1"].str.lower()
    interactions_df["drug2"] = interactions_df["drug2"].str.lower()

except Exception:
    interactions_df = pd.DataFrame(columns=["drug1", "drug2", "severity", "message"])


# ---------------- INTERACTION CHECK ----------------

def check_interactions(medicine_list):

    alerts = []

    # normalize medicine names
    meds = [m.lower() for m in medicine_list]

    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):

            drug1 = meds[i]
            drug2 = meds[j]

            result = interactions_df[
                ((interactions_df["drug1"] == drug1) & (interactions_df["drug2"] == drug2)) |
                ((interactions_df["drug1"] == drug2) & (interactions_df["drug2"] == drug1))
            ]

            if not result.empty:

                row = result.iloc[0]

                alerts.append({
                    "drug1": drug1,
                    "drug2": drug2,
                    "severity": row["severity"],
                    "message": row["message"]
                })

    return alerts
