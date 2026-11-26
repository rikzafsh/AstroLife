# app/persis — port persis-times-js ke Python

Port dari `persis-times-js` (turunan pustaka Dart `persis_times`, © Abu Sabda / Dewan Hisab dan Rukyat PP PERSIS, MIT;
lihat `LICENSE-persis_times.txt`). Algoritma dan keanehan kecilnya dipertahankan supaya hasilnya sama dengan JS.

| Berkas | Sumber JS | Isi |
|---|---|---|
| `core.py` | math_utils, julian_day, dynamical_time, nutation, sun | `kmjd`, `jdkm`, ΔT, nutasi 77 suku, Matahari VSOP87D (bujur, RA, deklinasi, perata waktu, waktu sideris) |
| `salat.py` | waktu_salat, prayer_method, salat_service, jadwal_service | 9 metode, Subuh–Isya, Syuruk/Duha/Nisfu lail, ihtiyat, jadwal lengkap (fajar/senja sipil-nautis-astronomis, lama siang) |
| `kiblat.py` | arah_kiblat, pelengkap_service | arah bola/elipsoid/Vincenty, jarak, rasydulqiblat & antipoda tahunan, bayangan kiblat harian, rasydulqiblat harian, istiwa, tafawut, ⅓ malam |
| `kalender.py` | julian_day (Hijriah), kalender_jawa | Hijriah aritmetis (4 pola kabisat, 2 epoch), kalender Jawa Sultan Agungan |
| `_data/sun_vsop87d.npz`, `nutation_tables.py` | data/sun_vsop87d.js, nutation.js | dihasilkan otomatis (jangan disunting); `tools/gen_persis_nutation.py` |

## Validasi
`tests/test_persis.py` membandingkan Python dengan hasil JS asli yang dijalankan di Node (`tests/fixtures/persis_golden.json`,
dibuat oleh `node tools/persis_golden.js <folder persis-times-js> tests/fixtures/persis_golden.json`): 192 jadwal salat
× 8 waktu (8 lokasi termasuk Tromsø/Sydney, 6 tanggal, 4 metode), Matahari di 7 JD, ΔT 16 tahun, kiblat 10 lokasi,
rasydulqiblat tahunan/antipoda/harian, istiwa, kalender Jawa & Hijriah. Selisih < 1e-7 jam (≈ 0,4 ms).

## Belum diport (butuh efemeris Bulan ELP-MPP02, ±4 MB data)
Bulan terbit/terbenam, rasydulqiblat Bulan, hisab awal bulan (ijtimak, MABIMS/Wujudul Hilal/Turki, peta visibilitas hilal),
gerhana, fase/tithi/pañcāṅga versi JS. Ramadan untuk Isya Ummul Qura di sini memakai kalender aritmetis (JS memakai
`Intl` Ummul Qura peramban), jadi bisa berbeda 1 hari pada malam batas.
