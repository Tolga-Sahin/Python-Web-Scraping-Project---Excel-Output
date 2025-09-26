"""
Ankara'daki 25 ilçeyi tek tek tarayan, belirlenen kategoriler
için Google Places Text Search ile tüm sayfaları (pagetoken)
gezen ve Place Details ile:
  - Firma Adı
  - Adres
  - Telefon
  - Web Sitesi
  - Konum (lat,lng)
çekip Excel'e kaydeden script.

"""

import requests
import pandas as pd
import time
import sys
from urllib.parse import quote_plus


API_KEY = "AIzaSyAaQsmaxA_fIBNFyHI4hp6yGBHD5TevdyA"
OUTPUT_FILE = "ankara_tum_otomotiv_kategorili.xlsx"


ILCELER = [
    "Akyurt","Altındağ","Ayaş","Bala","Beypazarı","Çamlıdere","Çankaya",
    "Çubuk","Elmadağ","Etimesgut","Evren","Gölbaşı","Güdül","Haymana",
    "Kahramankazan","Kalecik","Keçiören","Kızılcahamam","Mamak","Nallıhan",
    "Polatlı","Pursaklar","Sincan","Şereflikoçhisar","Yenimahalle"
]

KATEGORILER = [
    "otomotiv",
    "oto servis",
    "araç kiralama",
    "oto galeri",
    "benzin istasyonu",
    "lastik",
    "oto yedek parça"
]

# Limits / beklemeler
PAGE_TOKEN_WAIT = 2.5   
REQUEST_DELAY = 0.15    
SAVE_EVERY = 100        
# ------------------------------------

if API_KEY == "XXXXXXXXXXXXXXXXXXXXXXXX":
    print("Lütfen API_KEY değişkenine Google API anahtarınızı yazın ve tekrar çalıştırın.")
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
                # kısa bekle ve tekrar
                time.sleep(backoff * (i+1))
        except requests.RequestException as e:
            time.sleep(backoff * (i+1))
    return None

def process_textsearch(query):
    """Text Search ile bütün sayfaları çek, her place için detay al."""
    base = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": API_KEY}
    url = base
    while True:
        data = safe_get(url, params)
        if not data:
            print("Uyarı: TextSearch isteği başarısız oldu veya zaman aşımı:", query)
            return

        # results
        for place in data.get("results", []):
            pid = place.get("place_id")
            if not pid or pid in seen_place_ids:
                continue
            # Place Details çağrısı
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            dparams = {
                "place_id": pid,
                "fields": "name,formatted_address,formatted_phone_number,website,geometry",
                "key": API_KEY
            }
            ddata = safe_get(details_url, dparams)
            if not ddata:
                print("Uyarı: details isteği başarısız:", pid)
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
     
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
       
            continue
        else:
            break

def save_progress():
    df = pd.DataFrame(results)
    # Tekrarlı kayıtları PlaceID ile temizle
    df = df.drop_duplicates(subset=["PlaceID"])
    df.to_excel(r"C:\Users\Msi\Desktop\tum_ankara_otomotiv_firmalari.xlsx", index=False)
    print(f"Geçici kayıt kaydedildi → {OUTPUT_FILE} (toplam kayıt: {len(df)})")


total_queries = len(ILCELER) * len(KATEGORILER)
qcount = 0

try:
    for ilce in ILCELER:
        for kategori in KATEGORILER:
            qcount += 1
            query = f"{kategori} {ilce} Ankara, Turkey"
            print(f"[{qcount}/{total_queries}] Aranıyor: {query}")
            process_textsearch(query)

            # Ara kayıt
            if len(results) >= SAVE_EVERY and len(results) % SAVE_EVERY < 5:
                save_progress()

    # Son kaydet
    save_progress()
    print("Bitti. Toplam benzersiz kayıt:", len(seen_place_ids))

except KeyboardInterrupt:
    print("İptal edildi. Şu ana kadar toplanan veriler kaydediliyor...")
    save_progress()
except Exception as e:
    print("Hata oluştu:", e)
    save_progress()

