import pandas as pd

def check_interactions(medicine_list):

    interactions = pd.read_csv("drug_interactions.csv")

    alerts = []

    for i in range(len(medicine_list)):
        for j in range(i+1, len(medicine_list)):

            drug1 = medicine_list[i]
            drug2 = medicine_list[j]

            result = interactions[
                ((interactions["drug1"] == drug1) & (interactions["drug2"] == drug2)) |
                ((interactions["drug1"] == drug2) & (interactions["drug2"] == drug1))
            ]

            if not result.empty:
                alerts.append(result.iloc[0].to_dict())

    return alerts
