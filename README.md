# AstroLife 🌌
**Platform web untuk eksplorasi astronomi modern, sistem kalender historis, dan perencanaan pengamatan langit.**

AstroLife menghitung sendiri peristiwa langit dari posisi Matahari, Bulan, dan planet (efemeris NASA JPL DE440 lewat
Skyfield), menilai keterlihatannya dari lokasi pengguna, lalu memeriksa prakiraan cuacanya (Open-Meteo).

## Status modul
| Modul | Status |
|---|---|
| Katalog Event (`/catalog/`) | siap: fase Bulan, konjungsi, okultasi, gerhana, elongasi, oposisi, hujan meteor; label keterlihatan & kelangkaan |
| Observasi & Cuaca (`/observation/`) | siap: skor kelayakan per waktu/lokasi + rekomendasi event berdasarkan cuaca |
| Beranda (`/`) | siap: tanggal, fase Bulan, cuaca malam ini, event mendatang (semuanya dihitung, bukan data tetap) |
| Waktu Salat & Kiblat (`/islamic/`) | siap: jadwal salat 9 metode (hisab berdetik + ihtiyat), imsak, fajar/senja, istiwa, ⅓ malam, arah kiblat (bola/elipsoid/Vincenty), rasydulqiblat harian & tahunan, puasa sunah |
| Lab Kalender (`/calendar/`) | siap: Masehi ↔ Hijriah (aritmetis + hisab MABIMS/Ummul Qura/Wujudul Hilal/KHGT) ↔ Jawa (siklus kurup) + weton/pawukon + Jyotiṣa, plus tabel perbandingan kalender Hijriah & Jawa |
| AstroBot | dalam pengembangan |

## Menjalankan
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```
Buka `http://127.0.0.1:5000/catalog/`. Pada pemakaian pertama tekan **Buat katalog**: prosesnya berjalan di latar belakang
dari halaman itu sendiri (tanpa terminal) dan progresnya tampil. Mesin **Akurat** (Skyfield + JPL DE440) mengunduh ±32 MB
data efemeris sekali saja (butuh internet); mesin **Cepat** dipakai untuk mencoba.

Alternatif lewat terminal: `python -m catalog.generate 2026 2027` (set `ASTROLIFE_ENGINE=skyfield` untuk mesin akurat).

## Struktur
```text
astrolife/
├── app/
│   ├── routes/            main (beranda, tentang), catalog, observation, calendar, islamic, bot
│   ├── persis/            port persis-times-js (MIT): core (JD, ΔT, nutasi, Matahari VSOP87D), salat, kiblat, kalender, _data/
│   ├── services/          astro_core, planner_service, weather_service, home_service, timezones, calendar_service, islamic_service (puasa), falak_service
│   ├── templates/         halaman Jinja2
│   └── static/css/        gaya halaman beranda & tentang
├── catalog/               generator katalog (generate, job_runner, jobs), events, visibility, rarity, service
├── prototype/             mesin posisi (ephem_lite, ephem_skyfield), pencari event (find_events), magnitudo, verifikasi
├── data/
│   ├── catalog/           events.json (dibuat aplikasi), meteor_showers.json (tabel kurasi), status.json, cache/
│   └── ephemeris/         de440s.bsp (diunduh Skyfield)
├── tools/                 persis_golden.js (pembuat fixture dari JS asli), gen_persis_nutation.py
├── tests/                 unittest (python -m unittest discover -s tests)
├── config.py   run.py   requirements.txt   .env.example   knowledge.md
```

## Konfigurasi
- Lokasi bawaan: `Config.DEFAULT_LOCATION` di `config.py` (dipakai bilah atas, beranda, katalog, observasi).
- `ASTROLIFE_ENGINE` = `lite` (bawaan) | `skyfield`: mesin posisi untuk keterlihatan saat aplikasi berjalan.
  Pembuatan katalog dari antarmuka memilih mesinnya sendiri lewat formulir.
- `ASTROLIFE_BATCH=0` mematikan jalur vektor pencari event (jalur skalar lama).

## Tes
```powershell
python -m unittest discover -s tests
```
Tes cuaca memakai respons tiruan (tanpa internet). Tes khusus Skyfield dilewati otomatis bila Skyfield/DE440s belum ada.

## Dokumentasi tambahan
`knowledge.md` (pengetahuan proyek), `catalog/README.md` (katalog, keterlihatan, kelangkaan), `prototype/README.md` (mesin posisi), `app/persis/README.md` (port falak, validasi, batasan).


## Tampilan: tema terang/gelap & palet
- Palet utama: `#001f8e`, `#2a35e2`, `#29aafe`, `#ed2124`, `#009339`. Skala warnanya dibuat oleh `python tools/gen_theme.py` → `app/static/css/theme-palette.css` (hasilnya sudah ada di repo).
- Tombol tema (terang / ikut sistem / gelap) ada di header semua halaman; pilihan disimpan di `localStorage` (`astrolife.theme`) dan dibaca sebelum halaman digambar agar tidak berkedip.
- Warna netral memakai variabel di `app/static/css/theme.css`; konfigurasi Tailwind bersama ada di `app/static/js/tailwind-config.js` (kelas lama seperti `slate-*`, `indigo-*`, `cyan-*` otomatis mengikuti palet dan tema). Teks judul memakai `text-ink` (bukan `text-white`).
- Komponen bersama: `.ui-btn`, `.ui-btn-primary`, `.ui-field`, `.ui-label`, `.ui-chip`.
- Tes: `tests/test_tema.py`.
