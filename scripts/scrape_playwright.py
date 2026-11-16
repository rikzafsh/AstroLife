"""
Skrip Scraper Astronomi in-the-sky.org: Multi-Level maxdiff & Detail Extractor
=============================================================================
1. Melakukan perulangan maxdiff=1 s/d maxdiff=5:
   - maxdiff=1 -> Naked Eye
   - maxdiff=2 -> Binoculars (yang belum ada di maxdiff=1)
   - maxdiff=3 -> Small Telescope (yang belum ada di maxdiff=1 & 2)
   - maxdiff=4 -> 4-Inch Telescope
   - maxdiff=5 -> Large Telescope
2. Mengunjungi masing-masing URL (news.php?id=...) untuk mengambil:
   - Jam terbit (rising at ... WIB)
   - Jam fajar/hilang (dawn breaks at ...)
   - Sudut elevasi (altitude, misal: 58°)
   - Arah mata angin (misal: north-eastern horizon)
   - Rasi bintang (constellation)
   - Objek yang terlibat (Bulan, Planet, Bintang)
   - Teks ilmiah asli dari in-the-sky.org
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("\n[!] Pustaka 'playwright' belum terpasang.")
    print("    Jalankan: pip install playwright && playwright install chromium\n")
    sys.exit(1)

# Import parser detail yang sudah diuji
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
from app.services.detail_parser import parse_in_the_sky_detail_html

OUTPUT_FILE = BASE_DIR / "data" / "datasets" / "astronomy_events.json"
CACHE_DIR = BASE_DIR / "data" / "cache"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DIFF_NAMES = {
    1: 'naked_eye',
    2: 'binoculars',
    3: 'small_telescope',
    4: 'telescope_4inch',
    5: 'large_telescope'
}

DIFF_LABELS = {
    1: 'Mata Telanjang (Naked Eye)',
    2: 'Binokular',
    3: 'Teleskop Kecil',
    4: 'Teleskop 4-Inch',
    5: 'Teleskop Besar'
}


def run_multi_level_scraper(year: int = 2026, month: int = 11, max_details: int = 25, headless: bool = False):
    all_events_dict = {}  # key: url -> { 'url', 'date', 'title', 'diff_level', 'diff_key', 'diff_label' }

    print("\n" + "="*70)
    print(f" ASTROLIFE MULTI-LEVEL SCRAPER: in-the-sky.org")
    print(f" Periode: Bulan {month:02d} / {year}")
    print("="*70)

    with sync_playwright() as p:
        try:
            print("[Info] Membuka peramban Microsoft Edge...")
            browser = p.chromium.launch(
                channel="msedge",
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception:
            print("[Info] Fallback ke Chromium standar...")
            browser = p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        )
        page = context.new_page()

        try:
            # -------------------------------------------------------------
            # TAHAP 1: Perulangan maxdiff=1 hingga maxdiff=5
            # -------------------------------------------------------------
            print("\n[Tahap 1/2] Mengumpulkan peristiwa berdasarkan tingkat kesulitan (maxdiff 1-5)...")
            
            for level in range(1, 6):
                url = f"https://in-the-sky.org/newscal.php?year={year}&month={month}&maxdiff={level}"
                diff_key = DIFF_NAMES[level]
                diff_label = DIFF_LABELS[level]

                print(f"\n  -> Mengakses maxdiff={level} ({diff_label})...")
                page.goto(url, timeout=60000, wait_until="commit")

                # Tunggu tautan kalender muncul
                try:
                    page.wait_for_selector("a[href*='news.php']", timeout=30000)
                    page.wait_for_timeout(2000)
                except Exception:
                    print(f"     [Info] Waktu tunggu habis untuk level {level}, memeriksa link yang ada...")

                anchors = page.query_selector_all("a[href*='news.php?id=']")
                new_found = 0

                for a in anchors:
                    href = a.get_attribute("href") or ""
                    title = a.inner_text().strip()

                    if not href or len(title) < 4:
                        continue

                    # Perbaikan: Cek apakah href sudah berupa URL absolut atau masih relatif
                    if href.startswith("http://") or href.startswith("https://"):
                        full_url = href
                    else:
                        full_url = "https://in-the-sky.org/" + href.lstrip("/")
                    
                    # Logika himpunan selisih (Set Difference):
                    # Jika event BELUM ADA di level sebelumnya, maka ini adalah level minimumnya!
                    if full_url not in all_events_dict:
                        # Ekstrak tanggal dari ID (contoh: id=20261102_15_101)
                        date_match = re.search(r'id=(\d{4})(\d{2})(\d{2})_', href)
                        date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}" if date_match else f"{year}-{month:02d}"

                        all_events_dict[full_url] = {
                            'url': full_url,
                            'title': title,
                            'date': date_str,
                            'difficulty_level': level,
                            'difficulty_key': diff_key,
                            'difficulty_label': diff_label
                        }
                        new_found += 1

                print(f"     Berhasil menambahkan {new_found} event baru untuk tingkat {diff_label}.")
                time.sleep(1)

            total_events = len(all_events_dict)
            print(f"\n[Tahap 1 Selesai] Total {total_events} peristiwa unik terklasifikasi secara bertingkat.")

            # -------------------------------------------------------------
            # TAHAP 2: Buka masing-masing URL detail (news.php?id=...)
            # -------------------------------------------------------------
            target_list = list(all_events_dict.values())[:max_details]
            print(f"\n[Tahap 2/2] Membuka halaman detail untuk {len(target_list)} peristiwa teratas...")
            
            final_records = []

            for idx, item in enumerate(target_list, start=1):
                print(f"  [{idx:02d}/{len(target_list):02d}] {item['date']} - {item['title'][:40]}...")
                
                try:
                    page.goto(item['url'], timeout=30000, wait_until="commit")
                    page.wait_for_timeout(1500)
                    detail_html = page.content()

                    # Gunakan parser detail resmi
                    details = parse_in_the_sky_detail_html(detail_html, item['url'])

                    # Gabungkan seluruh atribut riil
                    record = {
                        'id': f"evt-{item['date'].replace('-', '')}-{idx}",
                        'date': item['date'],
                        'title': details['title'] or item['title'],
                        'difficulty_level': item['difficulty_level'],
                        'difficulty_key': item['difficulty_key'],
                        'difficulty_label': item['difficulty_label'],
                        'difficulty_alt': details['difficulty_alt'],
                        'peak_event_time': details['peak_event_time'],
                        'rising_time': details['rising_time'],
                        'fading_time': details['fading_time'],
                        'altitude': details['altitude'],
                        'azimuth_direction': details['azimuth_direction'],
                        'constellation': details['constellation'],
                        'objects': details['objects'],
                        'visibility_summary': details['visibility_summary'],
                        'description': details['description'],
                        'url': item['url'],
                        'source': 'in-the-sky.org'
                    }
                    final_records.append(record)

                except Exception as err:
                    print(f"     [!] Terjadi kendala pada event ini, menyimpan data dasar: {err}")
                    final_records.append({
                        'id': f"evt-{item['date'].replace('-', '')}-{idx}",
                        'date': item['date'],
                        'title': item['title'],
                        'difficulty_level': item['difficulty_level'],
                        'difficulty_key': item['difficulty_key'],
                        'difficulty_label': item['difficulty_label'],
                        'url': item['url'],
                        'source': 'in-the-sky.org'
                    })

                time.sleep(0.5)

        except Exception as e:
            print(f"[!] Terjadi kesalahan fatal: {e}")
        finally:
            browser.close()

    # Simpan hasil akhir
    if final_records:
        print("\n" + "="*70)
        print(f"[SUKSES] Menyimpan {len(final_records)} data peristiwa astronomi LENGKAP ke:")
        print(f"         {OUTPUT_FILE}")
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_records, f, ensure_ascii=False, indent=2)

        cache_file = CACHE_DIR / f"events_{year}_{month:02d}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({'timestamp': datetime.now().timestamp(), 'events': final_records}, f, ensure_ascii=False, indent=2)

        print("Data astronomi resmi in-the-sky.org telah terpasang di sistem AstroLife!\n")


if __name__ == "__main__":
    run_multi_level_scraper(year=2026, month=11, max_details=25)
