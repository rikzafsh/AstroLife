# Katalog event astronomi (hitung sendiri)

## Membuat katalog
    .\.venv\Scripts\Activate.ps1
    $env:ASTROLIFE_ENGINE = "skyfield"                 # disarankan untuk rilis (DE440s; unduhan sekali ~32 MB)
    python -m catalog.generate 2026 2027               # -> data/catalog/events.json
    python -m catalog.generate 2026 2027 --force       # abaikan cache bulanan

Cache per bulan ada di `data/catalog/cache/` sehingga proses yang terhenti dapat dilanjutkan. Tanpa
`ASTROLIFE_ENGINE=skyfield` generator memakai mesin sementara (cepat, tetapi galat planet ~2 menit busur) dan memberi peringatan.

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
