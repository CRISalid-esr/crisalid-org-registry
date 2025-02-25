import json
import os
import zipfile

import pandas as pd
import psycopg2
import requests

conn = psycopg2.connect("dbname=organizations host=localhost user=postgres")
cur = conn.cursor()

DATA_DIR = "/tmp"
ROR_ZIP_PATH = os.path.join(DATA_DIR, "ror-data.zip")
ROR_JSON_PATH = None  # Will be determined at runtime
UAI_JSON_PATH = os.path.join(DATA_DIR, "uai-data.json")

os.makedirs(DATA_DIR, exist_ok=True)

# ---- Download UAI dataset ----
UAI_URL = "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets/fr-esr-principaux-etablissements-enseignement-superieur/exports/json"
print(f"Downloading UAI dataset from {UAI_URL}...")
uai_response = requests.get(UAI_URL, stream=True)
if uai_response.status_code == 200:
    with open(UAI_JSON_PATH, "wb") as f:
        for chunk in uai_response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"UAI dataset saved to {UAI_JSON_PATH}")
else:
    print(f"Failed to download UAI dataset: {uai_response.status_code}")
    exit(1)

# ---- Download ROR dataset ----
ROR_URL = "https://zenodo.org/records/14728473/files/v1.59-2025-01-23-ror-data.zip?download=1"
print(f"Downloading ROR dataset from {ROR_URL}...")
ror_response = requests.get(ROR_URL, stream=True)
if ror_response.status_code == 200:
    with open(ROR_ZIP_PATH, "wb") as f:
        for chunk in ror_response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"ROR dataset saved to {ROR_ZIP_PATH}")
else:
    print(f"Failed to download ROR dataset: {ror_response.status_code}")
    exit(1)

# ---- Extract the ROR dataset ----
print("Extracting ROR dataset...")
with zipfile.ZipFile(ROR_ZIP_PATH, "r") as zip_ref:
    zip_ref.extractall(DATA_DIR)
    # Find the extracted file that ends with "ror-data.json"
    for filename in zip_ref.namelist():
        if filename.endswith("ror-data.json"):
            ROR_JSON_PATH = os.path.join(DATA_DIR, filename)
            break

if not ROR_JSON_PATH:
    print("ROR JSON file not found in the extracted archive!")
    exit(1)

print(f"ROR dataset extracted to {ROR_JSON_PATH}")

print("Loading ROR dataset into PostgreSQL...")

seen_ror_ids = set()  # ROR registry dump contains duplicates

with open(ROR_JSON_PATH, "r", encoding="utf-8") as f:
    ror_data = json.load(f)

    for org in ror_data:
        ror_id = org.get("id").replace("https://ror.org/", "")  # Extract ID

        if ror_id in seen_ror_ids:
            continue
        seen_ror_ids.add(ror_id)

        name = org.get("name")
        aliases = org.get("aliases", [])
        institution_type = org.get("types", [])
        country = org.get("country", {}).get("country_name")

        addresses = org.get("addresses", [])
        city = addresses[0].get("city") if addresses else None
        latitude = addresses[0].get("lat") if addresses else None
        longitude = addresses[0].get("lng") if addresses else None
        address = addresses[0].get("line") if addresses else None
        postal_code = addresses[0].get("postcode") if addresses else None

        website = org.get("links", [None])
        website = website[0] if website else None
        wikipedia = org.get("wikipedia_url")
        relationships = json.dumps(org.get("relationships", []))
        identifiers = json.dumps(org.get("external_ids", {}))
        metadata = json.dumps(org)

        cur.execute("""
            INSERT INTO organizations (
                ror_id, name, aliases, institution_type, country, city, latitude, longitude, address, postal_code, 
                website, wikipedia, relationships, identifiers, metadata
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ror_id) DO NOTHING;
        """, (ror_id, name, aliases, institution_type, country, city, latitude, longitude, address,
              postal_code,
              website, wikipedia, relationships, identifiers, metadata))

print("ROR dataset imported successfully.")

print("Loading UAI dataset into PostgreSQL...")
uai_df = pd.read_json(UAI_JSON_PATH)

for _, row in uai_df.iterrows():
    uai_id = row["uai"]
    ror_id = row.get("identifiant_ror", [None])

    ror_id = ror_id[0] if ror_id else None

    name = row["uo_lib"]
    short_name = row["nom_court"]
    sector = row["secteur_d_etablissement"]
    institution_type = row["type_d_etablissement"]
    legal_status = row["statut_juridique_long"]
    city = row["com_nom"]
    country = "France"
    latitude = row["coordonnees"]["lat"] if isinstance(row["coordonnees"], dict) else None
    longitude = row["coordonnees"]["lon"] if isinstance(row["coordonnees"], dict) else None
    address = row["adresse_uai"]
    postal_code = row["code_postal_uai"]
    website = row["url"]
    wikipedia = row["wikipedia"]

    identifiers = {
        "siret": row.get("siret", []),
        "siren": row.get("siren", []),
        "wikidata": row.get("identifiant_wikidata", []),
        "idref": row.get("identifiant_idref", [])
    }
    identifiers_json = json.dumps(identifiers)
    metadata = row.to_json()

    if ror_id and ror_id in seen_ror_ids:
        cur.execute("""
            UPDATE organizations
            SET 
                uai_id = %s,
                short_name = %s,
                sector = %s,
                institution_type = %s,
                legal_status = %s,
                city = %s,
                country = %s,
                latitude = %s,
                longitude = %s,
                address = %s,
                postal_code = %s,
                website = %s,
                wikipedia = %s,
                identifiers = %s,
                metadata = %s
            WHERE ror_id = %s;
        """, (uai_id, short_name, sector, institution_type, legal_status, city, country, latitude,
              longitude,
              address, postal_code, website, wikipedia, identifiers_json, metadata, ror_id))
        print(f"Updated existing ROR institution: {ror_id} with UAI data.")

    else:
        cur.execute("""
            INSERT INTO organizations (uai_id, name, short_name, sector, institution_type, legal_status, city, country, latitude, longitude, address, postal_code, website, wikipedia, identifiers, metadata) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (uai_id, name, short_name, sector, institution_type, legal_status, city, country,
              latitude, longitude, address, postal_code, website, wikipedia, identifiers_json,
              metadata))
        print(f"Inserted new UAI institution: {uai_id}")

print("UAI dataset imported successfully.")

# ---- Commit Changes & Close Connection ----
conn.commit()
cur.close()
conn.close()
print("Database update complete!")

# ---- Clean Up ----
os.remove(ROR_ZIP_PATH)
os.remove(ROR_JSON_PATH)
os.remove(UAI_JSON_PATH)

print("All downloaded files removed.")
