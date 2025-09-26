"""
Ankara'daki ilçeleri tarayan, belirlenen kategoriler
için Google Places API ile firma bilgilerini çekip Excel’e kaydeden script.
"""

import requests
import pandas as pd
import time
import sys
from urllib.parse import quote_plus

API_KEY = ""  # Buraya kendi API key'inizi local olarak ekleyin

OUTPUT_FILE = "ankara_anaokulu.xlsx"

ILCELER = [
    "Akyurt","Altındağ","Ayaş","Bala","Beypazarı","Çamlıdere","Çankaya",
    "Çubuk","Elmadağ","Etimesgut","Evren","Gölbaşı","Güdül","Haymana",
    "Kahramankazan","Kalecik","Keçiören","Kızılcahamam","Mamak","Nallıhan",
    "Polatlı","Pursaklar","Sincan","Şereflikoçhisar","Yenimahalle"
]

KATEGORILER = [
  "kreş",
  "anaokulu",
  "0-3 yaş",
  "3-6 yaş",
  "6+ yaş",
  "yaz okulu",
]

PAGE_TOKEN_WAIT = 2.5  
REQUEST_DELAY = 0.15   
SAVE_EVERY = 100        

if not API_KEY:
    print("Hata: API_KEY boş. Lütfen kendi Google API anahtarınızı ekleyin.")
    sys.exit(1)

session = requests.Session()
seen_place_ids = set()
results = []

def safe_get(url, params=None, max_retries=5, backoff=1.0):
    """Basit retry + backoff wrapper."""
    for i in range(max_retries):
        try:
            r = session.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            else:
                time.sleep(backoff * (i+1))
        except requests.RequestException:
            time.sleep(backoff * (i+1))
    return None

def process_textsearch(query):
    """Text Search ile tüm sayfaları çek, her place için detay al."""
    base = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": API_KEY}
    url = base
    while True:
        data = safe_get(url, params)
        if not data:
            print("Uyarı: TextSearch başarısız:", query)
            return

        for place in data.get("results", []):
            pid = place.get("place_id")
            if not pid or pid in seen_place_ids:
                continue

            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            dparams = {
                "place_id": pid,
                "fields": "name,formatted_address,formatted_phone_number,website,geometry",
                "key": API_KEY
            }
            ddata = safe_get(details_url, dparams)
            if not ddata:
                print("Uyarı: details başarısız:", pid)
                continue
            detay = ddata.get("result", {})

            results.append({
                "PlaceID": pid,
                "KategoriAranan": query,
                "Firma Adı": detay.get("name"),
                "Adres": detay.get("formatted_address"),
                "Telefon": detay.get("formatted_phone_number"),
                "Web Sitesi": detay.get("website"),
                "Konum (Lat,Lng)": (f"{detay['geometry']['location']['lat']}, {detay['geometry']['location']['lng']}"
                                    if "geometry" in detay else None)
            })
            seen_place_ids.add(pid)
            time.sleep(REQUEST_DELAY)

        token = data.get("next_page_token")
        if token:
            time.sleep(PAGE_TOKEN_WAIT)
            params = {"pagetoken": token, "key": API_KEY}
            url = base
        else:
            break

def save_progress():
    df = pd.DataFrame(results)
    df = df.drop_duplicates(subset=["PlaceID"])
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Kayıt kaydedildi → {OUTPUT_FILE} (toplam kayıt: {len(df)})")


try:
    total_queries = len(ILCELER) * len(KATEGORILER)
    qcount = 0
    for ilce in ILCELER:
        for kategori in KATEGORILER:
            qcount += 1
            query = f"{kategori} {ilce} Ankara, Turkey"
            print(f"[{qcount}/{total_queries}] Aranıyor: {query}")
            process_textsearch(query)

            if len(results) >= SAVE_EVERY and len(results) % SAVE_EVERY < 5:
                save_progress()

    save_progress()
    print("Bitti. Toplam benzersiz kayıt:", len(seen_place_ids))

except KeyboardInterrupt:
    print("İptal edildi. Şu ana kadar veriler kaydediliyor...")
    save_progress()
except Exception as e:
    print("Hata oluştu:", e)
    save_progress()
