# Prototipe: menghitung event astronomi sendiri

Tujuan: menguji apakah AstroLife bisa menghitung katalog event tanpa scraping (lihat diskusi di chat).

## Menjalankan
    python -m prototype.find_events 2026 11          # daftar event (WIB, Jakarta untuk okultasi)
    python -m prototype.compare                      # bandingkan dengan data/datasets/astronomy_events.json
    python -m prototype.compare path/baru.json 2026 11   # bandingkan dengan hasil scraping Anda yang baru (termasuk level 2+)
    python -m unittest tests.test_prototype -v

Hasil perbandingan tersimpan di `prototype/output/compare_2026-11.md`.

## Status mesin
`ephem_lite.py` adalah mesin SEMENTARA (Meeus untuk Bulan/Matahari; elemen Keplerian JPL Standish untuk planet)
karena Skyfield/DE440 tidak tersedia di lingkungan pengembangan tanpa internet. Antarmukanya (`eq`, `ecl`,
`topo_moon`, dst.) dibuat agar bisa diganti Skyfield tanpa mengubah `find_events.py`.

## Temuan
- Definisi in-the-sky.org yang teridentifikasi: *Conjunction* = konjungsi asensio rekta; *Close approach* = jarak sudut
  geosentris minimum; elongasi maksimum Merkurius = selisih bujur ekliptika.
- Galat posisi planet mesin ini ~2 menit busur: Bulan-planet meleset <= ~10 menit, planet-planet lambat bisa ~2 jam.
- Belum dicakup: hujan meteor (butuh tabel IMO), "well placed", "highest altitude in morning sky".


## Mesin Skyfield + JPL DE440s (disarankan untuk hasil akhir)
    pip install -r requirements-prototype.txt
    python -m prototype.verify_engine                         # cek adapter: selisih vs ephem_lite (menit busur)
    $env:ASTROLIFE_ENGINE = "skyfield"                        # PowerShell; Linux/macOS: export ASTROLIFE_ENGINE=skyfield
    python -m prototype.compare data/datasets/astronomy_events.json 2026 11
    python -m unittest tests.test_skyfield -v                 # dilewati otomatis bila Skyfield belum ada

Unduhan pertama (de440s.bsp, ~32 MB) disimpan di `data/ephemeris/` (diabaikan git). Pencarian sebulan penuh dengan
Skyfield lebih lambat daripada ephem_lite (puluhan detik) dan hanya perlu dijalankan sekali untuk membuat katalog.
STATUS: adapter belum pernah dijalankan oleh penulisnya; hasil `verify_engine` adalah ujian pertamanya.
