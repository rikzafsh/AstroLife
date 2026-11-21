# Katalog event astronomi (hitung sendiri)

## Membuat katalog
    .\.venv\Scripts\Activate.ps1
    $env:ASTROLIFE_ENGINE = "skyfield"                 # disarankan untuk rilis (DE440s; unduhan sekali ~32 MB)
    python -m catalog.generate 2026 2027               # -> data/catalog/events.json
    python -m catalog.generate 2026 2027 --force       # abaikan cache bulanan

Cache per bulan ada di `data/catalog/cache/` sehingga proses yang terhenti dapat dilanjutkan. Tanpa
`ASTROLIFE_ENGINE=skyfield` generator memakai mesin sementara (cepat, tetapi galat planet ~2 menit busur) dan memberi peringatan.

## Kecepatan
Pencarian memakai panggilan VEKTOR ke mesin posisi (`eq_many`, `ecl_many`, `moon_radii_many`): satu panggilan Skyfield untuk
ratusan waktu sekaligus, lalu penghalusan pada grid halus lokal. Pada Skyfield, pencarian sebulan turun dari ~40 detik
(43.772 panggilan skalar) menjadi taksiran ~2 detik (392 skalar + 552 vektor). Angka itu TAKSIRAN dari jumlah panggilan;
ukur sendiri dengan `python -m prototype.verify_engine` dan `tests.test_skyfield`.
Jalur skalar lama tetap ada: `$env:ASTROLIFE_BATCH = "0"`.

## Isi katalog (global, UTC)
fase Bulan, konjungsi & pendekatan terdekat (digabung), okultasi (jendela global), gerhana Bulan & Matahari,
elongasi maksimum, oposisi, dikotomi/kecerahan maksimum planet dalam, hujan meteor (tabel `data/catalog/meteor_showers.json`).

## Keterlihatan (dihitung per lokasi saat halaman dibuka) -- lihat docstring `catalog/visibility.py`
Ketinggian topocentris, ketinggian Matahari (gelap/senja/siang), magnitudo tampak, gangguan cahaya Bulan, okultasi lokal
(jam hilang/muncul), keadaan lokal gerhana Matahari; alat = magnitudo benda terredup vs batas magnitudo efektif langit.

## Kelangkaan -- lihat `catalog/rarity.py`
Berbasis aturan kualitatif (common, uncommon, rare, epic, legendary), BUKAN statistik hasil pemindaian katalog.

## Halaman & API
`/catalog/` dan `/catalog/api/events?year=&month=&lat=&lon=&langit=kota|pinggiran|gelap&tz=`

## Yang harus diverifikasi sebelum rilis
- `meteor_showers.json`: bujur Matahari/ZHR ditulis dari ingatan atas daftar IMO; cocokkan dengan kalender IMO terbaru.
- Ambang (batas magnitudo mata telanjang, 5 derajat ketinggian minimum, bobot cahaya Bulan) adalah parameter rancangan.
- Magnitudo Saturnus (koreksi cincin) kasar, +-0,5 mag.

## Halaman /catalog/
Sidebar (lokasi, bulan dengan tombol sebelumnya/berikutnya, kualitas langit, "Dapat diamati/Semua", "alat yang saya punya",
kelangkaan minimal, kategori), kartu Sorotan, dan daftar dikelompokkan per hari. Klik baris untuk detail. Pengaturan lokasi dan
filter utama diingat di peramban (localStorage). Bendera `observable` pada API: di atas ufuk dan langit memadai, okultasi benar-benar
terjadi di lokasi, atau gerhana Matahari benar-benar terlihat dari lokasi.

## Waktu, tema, dan tautan cuaca
- **Semua waktu di halaman dalam waktu lokal lokasi** (WIB/WITA/WIT dari bujur; di luar Indonesia: bujur/15). UTC hanya ada di JSON katalog.
  API mengembalikan `times_local` dan `lokasi.tz_label`.
- **Tema**: Otomatis / Gelap / Terang (disimpan di peramban). Berlaku untuk halaman katalog (variabel CSS pada `.cat`);
  halaman lain tetap gelap.
- **Analisis cuaca**: tombol pada tiap event membuka `/observation/?lat=&lon=&dt=&best=&peak=&title=&type=&inst=&moon=` dengan kolom
  "Waktu analisis" (waktu lokal) terisi: waktu terbaik bila event dapat diamati, selain itu waktu puncak. Dua tombol waktu tersedia di halaman tujuan.
- **Waktu terbaik**: bila peristiwa itu sendiri dapat diamati dan cukup tinggi (>= 10 derajat), itulah waktu yang dinilai; bila tidak,
  dicari waktu terdekat yang terbaik. Gerhana Bulan dinilai pada fase umbra; okultasi pada saat terjadi di lokasi.
