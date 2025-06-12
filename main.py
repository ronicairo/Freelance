from dotenv import load_dotenv
from datetime import datetime
import os
import requests
import pandas as pd

load_dotenv()

#Etape 0
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_INTERVENTIONS_ID = os.getenv("DB_INTERVENTIONS_ID")
DB_INVOICES_ID = os.getenv("DB_INVOICES_ID")

#Etape 1
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def convert_date_fr_to_iso(date_str: str) -> str:
    return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")

def get_database_properties(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

props = get_database_properties(DB_INTERVENTIONS_ID)

#Etape 2
def query_unbilled_entries(date_begin: str, date_end: str, a_ete_facture: bool):

    """
    Récupère les interventions dont la case 'A facturer' est cochée ou non,
    et qui ont une date comprise entre date_begin et date_end.
    """
    date_begin_fr = convert_date_fr_to_iso(date_begin)
    date_end_fr = convert_date_fr_to_iso(date_end)
    
    query = {
        "filter": {
            "and": [
                {
                    "property": "Facturé",
                    "checkbox": {"equals": a_ete_facture}
                },
                {
                    "property": "Date de début",
                    "date": {"on_or_after": date_begin_fr}
                },
                {
                    "property": "Date de fin",
                    "date": {"on_or_before": date_end_fr}
                }
            ]
        }
    }

    if a_ete_facture is None :
        query = {
            "filter": {
                "and": [
                    {
                        "property": "Date de début",
                        "date": {"on_or_after": date_begin_fr}
                    },
                    {
                        "property": "Date de fin",
                        "date": {"on_or_before": date_end_fr}
                    }
                ]
            }
        }

    response = requests.post(
        f"https://api.notion.com/v1/databases/{DB_INTERVENTIONS_ID}/query",
        headers=HEADERS,
        json=query
    )
    response.raise_for_status()
    return response.json()["results"]


date_begin_fr = "01/06/2025"
date_end_fr = "30/06/2025"
resultats = query_unbilled_entries(date_begin_fr, date_end_fr, a_ete_facture=False)

# for r in resultats:
#     props = r["properties"]
#     cours = props["Cours"]["title"][0]["text"]["content"]
#     date = props["Date de début"]["date"]["start"]
#     facture = props["Facturé"]["checkbox"]
# print(f"Interventions à facturer entre {date_begin_fr} et {date_end_fr} :")
# print(f"- {cours} | Date : {date} | Facturé : {facture}")

def parse_interventions_to_dataframe(results):
    rows = []
    for page in results:
        props = page["properties"]

        try:
            ville = props.get("Ville", {}).get("select", {}).get("name", "Inconnu")
            ecole = props.get("Ecole", {}).get("select", {}).get("name", "Inconnue")
            classe = props.get("Classe", {}).get("select", {}).get("name", "Inconnue")
            heures = float(props.get("Nombre d’heures", {}).get("number", 0))
            tarif = float(props.get("Tarif horaire", {}).get("number", 0))
            total = heures * tarif
            date_debut_str = props.get("Date de début", {}).get("date", {}).get("start")
            date_debut = pd.to_datetime(date_debut_str) if date_debut_str else None

            rows.append({
                "Ville": ville,
                "Ecole": ecole,
                "Classe": classe,
                "Heures": heures,
                "Tarif horaire": tarif,
                "Total": total,
                "Date de début": date_debut
            })

        except Exception as e:
            print("Erreur parsing d'une ligne:", e)
            continue

    return pd.DataFrame(rows)

#Affichage des résultats avec dataframe
date_begin_fr = "01/06/2025"
date_end_fr = "30/06/2025"
resultats = query_unbilled_entries(date_begin_fr, date_end_fr, a_ete_facture=False)
df = parse_interventions_to_dataframe(resultats)
print(df.head())
