import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

def obtener_precios_masivos():
    """
    Consulta la fuente de datos masiva diaria estructurada para obtener 
    los precios actualizados por ID de producto (Item Number).
    """
    precios_dict = {}
    try:
        # Nota: Puedes apuntar a la categoría o catálogo general de referencias diarias
        # Usamos una consulta general de precios sincronizados
        url = "https://tcgcsv.com/tcgplayer/categories"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            categorias = response.json().get("results", [])
            # Iteramos sobre las categorías de TCG (Magic, Pokemon, One Piece, etc.)
            for cat in categorias:
                cat_id = cat.get("categoryId")
                # Obtenemos los grupos/sets de cada categoría
                groups_url = f"https://tcgcsv.com/tcgplayer/{cat_id}/groups"
                g_resp = requests.get(groups_url, timeout=10)
                if g_resp.status_code == 200:
                    groups = g_resp.json().get("results", [])
                    for group in groups:
                        group_id = group.get("groupId")
                        # Consultamos los precios de los productos de este grupo
                        prices_url = f"https://tcgcsv.com/tcgplayer/{cat_id}/{group_id}/prices"
                        p_resp = requests.get(prices_url, timeout=10)
                        if p_resp.status_code == 200:
                            prices_data = p_resp.json().get("results", [])
                            for item in prices_data:
                                prod_id = str(item.get("productId"))
                                # Tomamos el marketPrice o midPrice como referencia base
                                market_price = item.get("marketPrice") or item.get("midPrice")
                                if prod_id and market_price:
                                    precios_dict[prod_id] = market_price
    except Exception as e:
        print(f"Error al descargar la base de precios masiva: {e}")
        
    return precios_dict

def ejecutar_actualizacion():
    print("Descargando actualización diaria de precios...")
    precios_mercado = obtener_precios_masivos()
    
    if not precios_mercado:
        print("No se pudieron obtener precios en esta ejecución.")
        return

    for name, sheet_id in SHEET_IDS.items():
        print(f"--- Procesando hoja de {name} ---")
        try:
            spreadsheet = client.open_by_key(sheet_id)
            
            # Asegurar que existe la pestaña BaseCSV
            try:
                base_ws = spreadsheet.worksheet("BaseCSV")
            except gspread.exceptions.WorksheetNotFound:
                base_ws = spreadsheet.add_worksheet(title="BaseCSV", rows=100, cols=2)
                base_ws.append_row(["TCGplayer Item #", "Precio Base Actual (USD)"])

            # Limpiar y actualizar la pestaña BaseCSV con la información más reciente
            base_ws.clear()
            base_ws.append_row(["TCGplayer Item #", "Precio Base Actual (USD)"])
            
            filas_a_insertar = []
            for item_num, precio in precios_mercado.items():
                filas_a_insertar.append([item_num, precio])
            
            if filas_a_insertar:
                base_ws.append_rows(filas_a_insertar)
                print(f"BaseCSV actualizada con éxito para {name} ({len(filas_a_insertar)} registros cargados).")

        except Exception as e:
            print(f"Error al actualizar la hoja {name}: {e}")

if __name__ == "__main__":
    ejecutar_actualizacion()
