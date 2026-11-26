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

## Bulan & hisab awal bulan
`bulan.py` (efemeris Bulan ELPMPP02, terbit/transit/terbenam, ijtimak) dan `hisab.py` (awal bulan MABIMS, Ummul Qura, Wujudul Hilal, KHGT/Turki;
tabel perbandingan kalender). Agar ringan, deret ELPMPP02 diringkas menurut amplitudo (1.036 suku, ±41 KB, `_data/moon_elp_ringkas.npz`,
dibuat oleh `tools/gen_persis_moon.py`). Terhadap JS (deret penuh): bujur ≤0,19″, lintang ≤0,07″, ijtimak ≤0,52 detik, awal bulan identik
pada 1.008 kombinasi bulan-kriteria (Hijriah 1440–1460). Di luar rentang itu belum diuji.
Ramadan untuk Isya Ummul Qura memakai kriteria Ummul Qura (ijtimak sebelum matahari terbenam di Makkah dan Bulan terbenam sesudahnya).

## Belum diport
Peta visibilitas hilal, gerhana, fase/tithi/pañcāṅga versi JS, rasydulqiblat Bulan (`rashdulQiblatBulan`).
