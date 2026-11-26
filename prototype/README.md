# Mesin posisi & pencari event

Paket ini menghitung posisi benda langit dan mencari peristiwa darinya. Dipakai oleh `catalog/` (generator katalog dan
keterlihatan).

| Berkas | Isi |
|---|---|
| `ephem_skyfield.py` | mesin akurat: Skyfield + JPL DE440s (unduhan ±32 MB sekali); API vektor `eq_many`, `ecl_many`, `moon_radii_many` |
| `ephem_lite.py` | mesin cepat tanpa data eksternal (Meeus untuk Bulan/Matahari, elemen Keplerian JPL untuk planet); galat planet ~2 menit busur |
| `engine.py` | memilih mesin dari `ASTROLIFE_ENGINE` (`lite` bawaan | `skyfield`) |
| `find_events.py` | pencari fase, konjungsi/pendekatan terdekat, okultasi, oposisi, elongasi, dikotomi/kecerahan; alat akar/minimum vektor |
| `magnitudes.py` | magnitudo tampak planet/Bulan dan bintang tetap |
| `verify_engine.py` | bandingkan mesin cepat vs Skyfield, konsistensi jalur vektor vs skalar, dan kecepatan |

## Perintah
```powershell
python -m prototype.verify_engine                         # butuh Skyfield terpasang
python -m prototype.find_events 2026 11                   # daftar event sebulan (WIB)
$env:ASTROLIFE_ENGINE = "skyfield"                        # pilih mesin akurat untuk perintah berikutnya
python -m unittest discover -s tests
```

## Catatan
- Definisi yang dipakai: *konjungsi* = konjungsi asensio rekta; *pendekatan terdekat* = jarak sudut geosentris minimum;
  elongasi maksimum Merkurius/Venus = selisih bujur ekliptika; jendela okultasi global = jarak sudut < semidiameter Bulan + paralaks horizontal.
- Jalur vektor mereproduksi hasil jalur skalar (acuan beku di `tests/fixtures/find_window_reference.json`).
  `ASTROLIFE_BATCH=0` memaksa jalur skalar.
- Belum dicakup: komet, "well placed" gugus bintang, Merkurius tertinggi di langit pagi, dan hujan meteor di luar tabel kurasi.
