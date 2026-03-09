import pandas as pd

# ---------------- LOAD INTERACTION DATABASE ----------------

def load_interactions():

    try:

        df = pd.read_csv("drug_interactions.csv")

        # normalize drug names
        df["drug1"] = df["drug1"].astype(str).str.lower().str.strip()
        df["drug2"] = df["drug2"].astype(str).str.lower().str.strip()

        # normalize severity labels
        if "severity" in df.columns:
            df["severity"] = df["severity"].astype(str).str.title()
        else:
            df["severity"] = "Moderate"

        # ensure message column exists
        if "message" not in df.columns:

            if "description" in df.columns:
                df["message"] = df["description"]
            else:
                df["message"] = "Drug interaction detected"

        return df

    except Exception as e:

        print("⚠ Interaction database error:", e)

        return pd.DataFrame(columns=["drug1","drug2","severity","message"])


interactions_df = load_interactions()

# ---------------- INTERACTION CHECK ----------------

def check_interactions(medicine_list):

    alerts = []

    if interactions_df.empty:
        return alerts

    # normalize medicines
    meds = list(set([m.lower().strip() for m in medicine_list]))

    seen = set()

    for i in range(len(meds)):

        for j in range(i + 1, len(meds)):

            drug1 = meds[i]
            drug2 = meds[j]

            # prevent duplicate checks
            key = tuple(sorted([drug1, drug2]))

            if key in seen:
                continue

            seen.add(key)

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
