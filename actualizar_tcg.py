import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# 1. Configurar credenciales de Google Cloud desde los Secrets de GitHub
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
sa_key_json = os.environ.get("GCP_SA_KEY")

if not sa_key_json:
    raise ValueError("No se encontró la variable de entorno GCP_SA_KEY.")

creds_dict = json.loads(sa_key_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# 2. Los IDs de tus tres hojas de Google Sheets (Magic, One Piece, Pokémon)
SHEET_IDS = {
    "Magic": "1xK3muMQsNsTTOC3w64AvusEHG79r_6q5yo0c1zgmAdU",
    "OnePiece": "1djKLXm6NJFZr-EYB7C0MMAm7SyusKMGS6wObdk3PEGU",
    "Pokemon": "1fkZaCom_cWS4tlnhW26JSHbSPxt58BhAX1FHBiaCFQo"
}

def obtener_precio_tcg(item_number):
    if not item_number:
        return None
    url = f"https://infinite-api.tcgplayer.com/product/{item_number}/pricing"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.6; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                return data["results"][0].get("marketPrice") or data["results"][0].get("listingPrice")
    except Exception as e:
        print(f"Error consultando Item #{item_number}: {e}")
    return None

def ejecutar_actualizacion():
    for name, sheet_id in SHEET_IDS.items():
        print(f"--- Procesando hoja de {name} ---")
        try:
            spreadsheet = client.open_by_key(sheet_id)
            for worksheet in spreadsheet.worksheets():
                data = worksheet.get_all_values()
                if len(data) < 2:
                    continue
                
                # Recorre las filas buscando el Item Number en la Columna B (índice 1)
                for i, row in enumerate(data[1:], start=2):
                    if len(row) > 1 and row[1]:
                        item_number = str(row[1]).strip()
                        precio = obtener_precio_tcg(item_number)
                        if precio:
                            # Actualiza la Columna D (Precio Base TCG USD, índice 4)
                            worksheet.update_cell(i, 4, precio)
                            print(f"Item #{item_number} actualizado con éxito a: ${precio}")
        except Exception as e:
            print(f"Error al actualizar la hoja {name}: {e}")

if __name__ == "__main__":
    ejecutar_actualizacion()
