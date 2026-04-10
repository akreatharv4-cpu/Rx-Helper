from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "drug_interactions.csv"


def load_interactions():
    try:
        df = pd.read_csv(CSV_PATH)

        if "drug1" not in df.columns or "drug2" not in df.columns:
            raise ValueError("drug_interactions.csv must contain drug1 and drug2 columns")

        df["drug1"] = df["drug1"].astype(str).str.lower().str.strip()
        df["drug2"] = df["drug2"].astype(str).str.lower().str.strip()

        severity_map = {
            "high": "Severe",
            "major": "Severe",
            "severe": "Severe",
            "moderate": "Moderate",
            "medium": "Moderate",
            "low": "Mild",
            "mild": "Mild",
        }

        if "severity" in df.columns:
            df["severity"] = (
                df["severity"]
                .astype(str)
                .str.strip()
                .str.lower()
                .map(severity_map)
                .fillna("Moderate")
            )
        else:
            df["severity"] = "Moderate"

        if "message" not in df.columns:
            if "description" in df.columns:
                df["message"] = df["description"].astype(str)
            else:
                df["message"] = "Drug interaction detected"

        return df[["drug1", "drug2", "severity", "message"]]

    except Exception as e:
        print("⚠ Interaction database error:", e)
        return pd.DataFrame(columns=["drug1", "drug2", "severity", "message"])


interactions_df = load_interactions()


def severity_icon(severity):
    return {
        "Severe": "🔴",
        "Moderate": "🟠",
        "Mild": "🟡"
    }.get(severity, "⚪")


def check_interactions(medicine_list):
    alerts = []

    if interactions_df.empty or not medicine_list:
        return alerts

    meds = []
    seen_meds = set()
    for m in medicine_list:
        if not m:
            continue
        cleaned = str(m).lower().strip()
        if cleaned and cleaned not in seen_meds:
            seen_meds.add(cleaned)
            meds.append(cleaned)

    seen_pairs = set()

    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):
            drug1 = meds[i]
            drug2 = meds[j]
            key = tuple(sorted([drug1, drug2]))

            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            result = interactions_df[
                ((interactions_df["drug1"] == drug1) & (interactions_df["drug2"] == drug2)) |
                ((interactions_df["drug1"] == drug2) & (interactions_df["drug2"] == drug1))
            ]

            if not result.empty:
                row = result.iloc[0]
                alerts.append({
                    "pair": f"{drug1.upper()} + {drug2.upper()}",
                    "severity": f"{severity_icon(row['severity'])} {row['severity']}",
                    "warning": row["message"]
                })

    return alerts