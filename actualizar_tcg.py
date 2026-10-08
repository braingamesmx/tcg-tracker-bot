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

# 2. Los IDs de tus tres hojas de Google Sheets
SHEET_IDS = {
    "Magic": "1xK3muMQsNsTTOC3w64AvusEHG79r_6q5yo0c1zgmAdU",
    "OnePiece": "1djKLXm6NJFZr-EYB7C0MMAm7SyusKMGS6wObdk3PEGU",
    "Pokemon": "1fkZaCom_cWS4tlnhW26JSHbSPxt58BhAX1FHBiaCFQo"
}

# Mapeo para identificar las categorías de tus juegos de interés
JUEGOS_OBJETIVO = ["Magic", "Pokemon", "One Piece"]

def obtener_precios_optimizados():
    """
    Descarga únicamente los precios de las categorías objetivo (Magic, Pokémon, One Piece)
    para evitar recorrer todo el catálogo global y hacer el proceso instantáneo.
    """
    headers = {
        "User-Agent": "BrainGamesMX-TCG-Automator/1.0 (contacto@braingamesmx.com)"
    }
    
    # Diccionario separado por juego para alimentar cada BaseCSV correspondiente
    precios_por_juego = {
        "Magic": {},
        "Pokemon": {},
        "OnePiece": {}
    }
    
    try:
        url = "https://tcgcsv.com/tcgplayer/categories"
        print("Conectando con la API de TCGCSV...")
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            categorias = response.json().get("results", [])
            
            for cat in categorias:
                cat_name = cat.get("name", "")
                cat_id = cat.get("categoryId")
                
                # Identificar a qué juego corresponde esta categoría
                juego_key = None
                if "Magic" in cat_name:
                    juego_key = "Magic"
                elif "Pokemon" in cat_name:
                    juego_key = "Pokemon"
                elif "One Piece" in cat_name:
                    juego_key = "OnePiece"
                
                if juego_key:
                    print(f"Descargando sets para {juego_key}...")
                    groups_url = f"https://tcgcsv.com/tcgplayer/{cat_id}/groups"
                    g_resp = requests.get(groups_url, headers=headers, timeout=10)
                    
                    if g_resp.status_code == 200:
                        groups = g_resp.json().get("results", [])
                        for group in groups:
                            group_id = group.get("groupId")
                            prices_url = f"https://tcgcsv.com/tcgplayer/{cat_id}/{group_id}/prices"
                            p_resp = requests.get(prices_url, headers=headers, timeout=10)
                            
                            if p_resp.status_code == 200:
                                prices_data = p_resp.json().get("results", [])
                                for item in prices_data:
                                    prod_id = str(item.get("productId"))
                                    market_price = item.get("marketPrice") or item.get("midPrice")
                                    if prod_id and market_price:
                                        precios_por_juego[juego_key][prod_id] = market_price
        else:
            print(f"Error al conectar con categorías: {response.status_code}")
            
    except Exception as e:
        print(f"Excepción crítica durante la descarga: {e}")
        
    return precios_por_juego

def ejecutar_actualizacion():
    print("Iniciando actualización rápida de precios...")
    precios_totales = obtener_precios_optimizados()

    for name, sheet_id in SHEET_IDS.items():
        print(f"--- Actualizando Google Sheet de {name} ---")
        precios_juego = precios_totales.get(name, {})
        
        if not precios_juego:
            print(f"No se encontraron precios para {name} en esta ejecución.")
            continue

        try:
            spreadsheet = client.open_by_key(sheet_id)
            
            # Asegurar que existe la pestaña BaseCSV
            try:
                base_ws = spreadsheet.worksheet("BaseCSV")
            except gspread.exceptions.WorksheetNotFound:
                base_ws = spreadsheet.add_worksheet(title="BaseCSV", rows=100, cols=2)
                base_ws.append_row(["TCGplayer Item #", "Precio Base Actual (USD)"])

            # Limpiar y actualizar la pestaña BaseCSV
            base_ws.clear()
            base_ws.append_row(["TCGplayer Item #", "Precio Base Actual (USD)"])
            
            filas_a_insertar = [[item_num, precio] for item_num, precio in precios_juego.items()]
            
            if filas_a_insertar:
                base_ws.append_rows(filas_a_insertar)
                print(f"BaseCSV de {name} actualizada con éxito ({len(filas_a_insertar)} productos).")

        except Exception as e:
            print(f"Error al escribir en la hoja {name}: {e}")

if __name__ == "__main__":
    ejecutar_actualizacion()
