# AstroLife: Pengetahuan Proyek

Dokumen ini merangkum semua pengetahuan yang diberikan pemilik proyek selama pengerjaan (deskripsi, keputusan, preferensi,
data dari komputernya) beserta keputusan teknis dan fakta acuan yang diverifikasi. Bagian ditandai **[Pengguna]** bila
bersumber dari pemilik proyek, **[Verifikasi]** bila dihasilkan/diverifikasi saat pengerjaan, **[Belum terbukti]** bila masih asumsi.
Gunakan dokumen ini sebagai konteks awal setiap sesi pengerjaan berikutnya.

---

## 1. Deskripsi proyek [Pengguna]
Sumber: berkas `Final Project Description` (mata kuliah **Aplikasi Web**, pemilik: Mohamad Rikza Sholihin).

**Judul:** AstroLife: Platform Web untuk Eksplorasi Astronomi Modern, Sistem Kalender Historis, dan Perencanaan Pengamatan Fenomena Langit.

**Tujuan (6):**
1. Memudahkan pengguna memperoleh informasi fenomena astronomi dan kondisi langit.
2. Menggabungkan informasi astronomi dengan prakiraan cuaca untuk merencanakan pengamatan.
3. Sarana mempelajari, mengonversi, dan membandingkan beberapa sistem penanggalan.
4. Waktu salat, rekomendasi puasa sunah, dan rasydulqiblat berdasarkan prinsip astronomi.
5. Penerapan pengumpulan, pengolahan, analisis, dan visualisasi data dalam aplikasi web.
6. Chatbot interaktif untuk membantu pengguna mengakses informasi dan fitur.

**Fitur utama:**
- **A. Astronomy Explorer & Observation Planner:** fenomena (gerhana, hujan meteor, fase Bulan, konjungsi planet, dll.), waktu & lokasi,
  prakiraan cuaca (tutupan awan, curah hujan, kelembapan, jarak pandang), estimasi kelayakan pengamatan, rekomendasi, kalender fenomena.
- **B. Calendar Laboratory:** konversi Masehi dan Hijriah aritmetis; Jawa Mataraman (pasaran, wuku, windu); sistem penanggalan Jawa Kuno
  (prasasti, sumber sejarah); unsur Jyotiṣa (astronomi matematis, penanggalan); perbandingan antar kalender; sejarah dan prinsip hitung.
- **C. Islamic Astronomy & Timekeeping:** jadwal salat per lokasi; kalender Hijriah & tanggal penting; rekomendasi puasa sunah (Senin-Kamis,
  Ayyamul Bidh, dll.); rasydulqiblat tahunan (Matahari di atas Ka'bah) dan harian (azimuth Matahari = azimuth kiblat); dasar astronomis waktu salat & kiblat.
- **D. AstroBot & Knowledge Center:** chatbot (rule-based atau retrieval-based), bantuan fitur, artikel edukasi, penjelasan istilah.
- **E. Data Analytics & Visualization:** statistik fenomena, perbandingan cuaca, visualisasi kelayakan, pengelompokan, analisis sentimen.

**Teknologi & metode (dokumen):** Python + Flask satu aplikasi; web scraping; dataset processing; sentiment analysis; regresi linier; clustering;
data visualization; chatbot; perhitungan astronomi untuk kalender, salat, rasydulqiblat, dan fenomena langit.

> **Penyimpangan dari dokumen, atas keputusan pemilik [Pengguna]:** web scraping dihapus (diganti perhitungan sendiri, lihat 2.4) dan bagian
> *Data Analytics & Machine Learning* (E) dihapus dari aplikasi. Sesuaikan narasi laporan dengan keputusan ini.

---

## 2. Keputusan & preferensi pemilik proyek [Pengguna]

### 2.1 Cara kerja
- Bahasa: **Indonesia** (UI, komentar, pesan).
- **Setiap kali memberi berkas, sertakan pesan commit** yang menjelaskan perubahan apa saja yang dilakukan (permintaan eksplisit).
- Pemilik memakai **git** dan menjalankan perintah di **PowerShell (Windows)**.
- Berkas yang dikirim berupa zip *kode saja*; **jangan menimpa folder `data/`** pemilik (pernah terjadi: zip lama menimpa hasil scraping).
- Ingin penjelasan jujur tentang batas akurasi dan hal yang belum teruji; ragu terhadap klaim yang tidak terbukti (pola: bertanya "apakah benar...?").
- Berkas JS referensi untuk **konversi kalender, rasydulqiblat, dan waktu salat** akan diberikan kemudian, lengkap dengan arahan fitur, untuk **di-port ke Python**
  dan dipakai memperbaiki perhitungan waktu salat dan kalender (belum diterima saat dokumen ini ditulis).

### 2.2 Urutan prioritas yang ditetapkan
1. Fokus dulu pada **fenomena astronomi + prakiraan cuaca** (Observation Planner); kalender/rasydulqiblat/salat menyusul.
2. Pastikan data event benar-benar dari sumbernya, tanpa pengisian karangan; jam prakiraan cuaca harus sama dengan jam event.
3. Ganti sumber event: dari scraping menjadi **katalog hasil hitung aplikasi**.
4. Perbaiki UI katalog; lalu rapikan aplikasi (hapus analytics/ML, perbaiki beranda).

### 2.3 Kekhawatiran yang disampaikan
- Scraping butuh **peramban asli di latar belakang**, rumit, tidak realistis di **ponsel**, dan **mungkin dianggap ilegal** (ketentuan situs tidak ditemukan saat dicek).
- Data hasil scraping **tidak lengkap/akurat** (contoh: jam hilang/muncul okultasi, deskripsi tidak terbaca).
- Mengunggah iCalendar dianggap meribetkan, tidak otomatis, rawan salah lokasi dan tingkat kesulitan.

### 2.4 Arah yang dipilih
AstroLife **menghitung sendiri** semua peristiwa astronomi dengan data **NASA JPL** (Skyfield + DE440; sebelumnya pemilik menyebut Swiss Ephemeris).
Pemilik menyadari ini keluar dari deskripsi awal tetapi yakin lebih akurat dan ringan.

### 2.5 Permintaan fitur
- **Label keterlihatan** per event: mata telanjang, binokular, dst., dihitung dari **posisi di atas/bawah ufuk** dan **magnitudo tampak**, dsb.
- **Label kelangkaan**: *common, rare, legendary* (atau serupa).
- **UI katalog:** kolom/wadah agar tidak mepet tepi dan tidak terlalu lebar di desktop; **waktu lokal sesuai lokasi terpilih** (bukan UTC);
  **tombol analisis cuaca** pada tiap event yang langsung di-set ke hari dan jam event; **mode gelap/terang**.
- **Pembuatan katalog dari dalam aplikasi** (tanpa perintah terminal).
- Hapus semua keterkaitan dengan **in-the-sky.org**, terutama di halaman Observasi; semua event dari katalog yang dihasilkan aplikasi.
- Hapus bagian **Data Analytics & Machine Learning**; perbaiki **halaman beranda**; buat `knowledge.md` (dokumen ini).

---

## 3. Lingkungan pemilik [Pengguna]
- OS Windows, PowerShell; proyek di `C:\Users\USER\.gemini\antigravity\scratch\astrolife`, virtualenv `.venv`.
  Python global: 3.14 (`C:\Python314`); versi Python di dalam `.venv` tidak diketahui (roda `sgp4` bertanda cp311-abi3, jadi minimal 3.11).
  Aktifkan: `.\.venv\Scripts\Activate.ps1`. Bila lupa aktivasi: `ModuleNotFoundError: skyfield` (Python global dipakai).
- Aplikasi dibuka di `127.0.0.1:5000` pada peramban berbasis Chromium; scraper lama memakai Microsoft Edge.
- Internet tersedia di komputer pemilik (Skyfield berhasil mengunduh `de440s.bsp`, Open-Meteo terjangkau). Sandbox pengembang **tidak** punya internet,
  sehingga Skyfield dan Tailwind CDN tidak dapat dijalankan/dirender di sana.
- Hasil terukur di komputer pemilik:
  - `verify_engine`: selisih posisi mesin cepat vs Skyfield: Bulan 0,3-1,0'; Matahari 0,1-0,2'; Merkurius-Venus-Mars <0,5'; Jupiter ~1,5'; **Saturnus ~4,4'**; Uranus ~0,55'; Neptunus ~0,9'; bintang <0,6'.
  - Pencarian event dengan Skyfield (jalur skalar lama): **39-60 detik per bulan**; tes Skyfield 50-80 detik. Jalur vektor baru belum diukur oleh pemilik.
  - Perbandingan dengan data acuan November 2026: **39 dari 39 titik waktu ≤15 menit**, median 1,0 menit, maksimum 9 menit (lihat 6.2). 50 tes lulus (sebelum refaktor ini).
  - Lokasi bawaan aplikasi: `Config.DEFAULT_LOCATION` (saat ini Yogyakarta); zona waktu dari bujur (WIB/WITA/WIT).

---

## 4. Arsitektur saat ini [Verifikasi]
```text
app/            Flask: routes (main, catalog, observation, calendar, islamic, bot), services, templates, static/css
catalog/        generate, job_runner, jobs (pembuatan di latar belakang), service, events (gerhana/meteor/normalisasi), visibility, rarity
prototype/      mesin posisi (ephem_lite, ephem_skyfield), engine (pilih lewat ASTROLIFE_ENGINE), find_events, magnitudes, verify_engine
data/catalog/   events.json (dibuat aplikasi), meteor_showers.json (tabel kurasi), status.json, generate.log, cache/
tests/          unittest; helpers.py (respons cuaca tiruan); fixtures/find_window_reference.json
```

**Alur data:** `generate` (Skyfield, global/geosentris, UTC) → `events.json` → `service.decorate` menghitung keterlihatan + kelangkaan **per lokasi** saat halaman dibuka
(dengan mesin cepat) → halaman Katalog / Observasi / Beranda. Cuaca: Open-Meteo per jam, dibulatkan ke jam terdekat.

**Pembuatan katalog dari aplikasi:** `POST /catalog/api/generate` → proses terpisah `python -m catalog.job_runner` (mesin dipilih lewat env; Skyfield mengunduh DE440s ±32 MB saat pertama)
→ menulis `status.json` per langkah → halaman polling `/catalog/api/generate/status`. Satu pekerjaan sekali jalan (409 bila ganda); status tanpa detak >10 menit dianggap terhenti.

**Variabel lingkungan:** `ASTROLIFE_ENGINE` (`lite` bawaan | `skyfield`), `ASTROLIFE_BATCH=0` (jalur skalar).

**Endpoint:** `/catalog/api/events`, `/catalog/api/upcoming`, `/catalog/api/generate{,/status,/options}`, `/observation/api/feasibility` (POST), `/observation/api/plan`.

---

## 5. Aturan perhitungan [Verifikasi]

### 5.1 Pencarian event (`prototype/find_events.py`)
- *Konjungsi* = konjungsi **asensio rekta**; *pendekatan terdekat* = jarak sudut geosentris minimum; Bulan-objek digabung menjadi satu event konjungsi.
- *Elongasi maksimum* Merkurius/Venus = selisih **bujur ekliptika** (jarak sudut memberi waktu berbeda ~1 jam karena puncaknya datar).
- *Dikotomi* = sudut fase 90°; *paling terang* memakai rumus magnitudo Astronomical Almanac (model Mallama dapat dipilih lewat `USE_MALLAMA`, puncaknya bergeser ~3 hari).
- *Okultasi (global)*: jarak sudut Bulan-objek < semidiameter Bulan + paralaks horizontal; jendelanya dipakai sebagai rentang waktu. Okultasi **lokal** dihitung topocentris per lokasi.
- *Gerhana Bulan*: jarak ke sumbu bayangan Bumi; jari-jari bayangan diperbesar 2% (Danjon). *Gerhana Matahari*: gamma ≈ sin(sep)/sin(HP); sentral bila < 0,9972, sebagian < 1,5433.
- *Hujan meteor*: puncak saat bujur Matahari (IMO, ekuinoks J2000) tercapai; ketidakpastian jam-hari.
- Pencarian vektor: grid kasar + penghalusan pada grid halus lokal; minimum jarak sudut dicari pada f² (eksak parabolik). Jalur vektor mereproduksi jalur skalar (acuan beku).

### 5.2 Keterlihatan (`catalog/visibility.py`)
- Benda penentu harus ≥ 5° di atas ufuk (refraksi dasar; Bulan topocentris) dan Matahari ≤ -6° (gerhana Matahari: Matahari di atas ufuk).
- Waktu event dipakai bila dapat diamati dan ≥ 10°; selain itu dicari waktu terbaik di jendela. Jendela: ±10 jam (cepat), ±36 jam (elongasi, oposisi, fase planet, hujan meteor, konjungsi planet-planet);
  gerhana Bulan: fase umbra; okultasi lokal: saat terjadi.
- Alat: magnitudo benda terredup (selain Bulan/Matahari) vs batas efektif: mata telanjang = batas langit (4,0 kota / 5,0 pinggiran / 6,0 gelap) - gangguan Bulan - kehilangan senja;
  binokular 9,0; teleskop kecil 11,0; teleskop 4-inci 12,5; di atasnya teleskop besar. Gangguan Bulan = 1,5 × iluminasi × min(1, tinggi/20°) bila Bulan bukan objek.
- Dikotomi minimal teleskop kecil. Bulan baru: tidak teramati. Gerhana Matahari: wajib filter surya.
- `observable` = di atas ufuk & langit memadai, atau okultasi benar-benar terjadi di lokasi, atau gerhana Matahari benar-benar terlihat di lokasi.

### 5.3 Kelangkaan (`catalog/rarity.py`) — aturan kualitatif, bukan statistik
common < uncommon < rare < epic < legendary. Contoh: fase & konjungsi Bulan-planet umum; gerhana Bulan total langka; gerhana Matahari total epik, **legendaris bila lokasi di jalur totalitas**;
okultasi planet yang benar-benar terjadi di lokasi langka; konjungsi besar Jupiter-Saturnus <0,5° legendaris. [Belum terbukti sebagai statistik; ambang adalah rancangan.]

### 5.4 Skor cuaca (`planner_service.calculate_observation_feasibility`)
100 - penalti (awan efektif × bobot alat; hujan; kelembapan; jarak pandang; cahaya Bulan bila Bulan di atas ufuk dan bukan objek; siang). Bobot awan: teleskop 0,90; meteor 0,85; binokular 0,75; mata 0,65.
Skor `None` bila cuaca tak tersedia (tidak pernah dikarang). Prakiraan per jam ≤16 hari; di luar itu klimatologi (ditandai indikatif).

### 5.5 Zona waktu
WIB 7 (bujur 95-115), WITA 8 (115-130), WIT 9 (130-141,5); di luar itu round(bujur/15). Semua waktu UI = waktu lokal; UTC hanya di JSON katalog.

---

## 6. Fakta acuan yang diverifikasi [Verifikasi]

### 6.1 Kalender (untuk modul Kalender)
- Pasaran: jangkar **17 Agustus 1945 = Jumat Legi** (juga cocok: 1 Jan 1970 Kamis Wage; 16 Jun 2026 Selasa Wage; 17 Jun 2026 Rabu Kliwon).
- Wuku: jangkar **Galungan 2 Agustus 2023 = Rabu Kliwon, Wuku Dungulan** (210 hari; Galungan 4 Jan 2023 juga cocok); pawukon 30 wuku × 7 hari.
- Windu: **1 Sura 1555 AJ = Alip**; tahun Jawa = tahun Hijriah + 512; Alip, Ehé, Jimawal, Jé, Dal, Bé, Wawu, Jimakir. 2026: tahun **Bé 1960**.
- Hijriah aritmetis (hisab urfi, epoch sipil Jumat 16 Juli 622 Julian); dapat berbeda 1-2 hari dari penetapan resmi. 1 Muharam 1448 (urfi) = 17 Jun 2026 (cocok dengan Sura 1960 versi Jawa).
- Jyotiṣa: tithi dari elongasi/12°, nakshatra dari bujur sidereal Bulan (ayanamsa Lahiri), bulan amanta dari rasi Matahari saat bulan baru. **Prasasti Laguna Copperplate: Saka 822, Waisakha, Krsnapaksa tithi 4, Senin = 21 April 900 (Julian)**: cocok persis.
- ~~`calendar_service.py` dan `islamic_service.py` belum disambungkan~~ → **Diganti**: waktu salat, kiblat, rasydulqiblat kini dari `app/persis` (port JS pemilik, lihat bagian 10); `islamic_service.py` tinggal puasa sunah/tanggal penting; `calendar_service.py` tetap dipakai untuk weton/pawukon/Jyotiṣa dan Beranda.
- Rasydulqiblat tahunan (UTC): ±28 Mei 09:18 dan ±16 Juli 09:27 (Ka'bah 21,42255°LU 39,82620°BT). [Dari modul awal proyek; belum diuji ulang.]

### 6.2 Astronomi (validasi, November 2026 dan 2026)
- Gerhana Bulan 2026: total 3 Mar (puncak ±11:33 UTC, magnitudo umbra ~1,151), sebagian 28 Agu (~04:13 UTC, ~0,930). Gerhana Matahari 2026: cincin 17 Feb (~12:12 UTC), total 12 Agu (~17:46 UTC). Hasil hitung cocok dalam menit.
- Data acuan (pemilik, November 2026, WIB): Bulan Kuartal Akhir 2 Nov 03:28; Purnama 24 Nov 21:53; Kuartal Awal 17 Nov 18:48; Merkurius elongasi barat maks. 21 Nov 07:33; dikotomi 18 Nov 15:55;
  **okultasi Jupiter 3 Nov**: jendela global 03:45-07:45, terlihat dari Jakarta hilang 04:39 (tinggi 51,5°) dan muncul 06:08; sembilan okultasi pada bulan itu
  (Mars, Jupiter ×2, Regulus ×2, Venus, Antares, Sigma Sagittarii, Beta Tauri); Uranus oposisi 26 Nov (05:33 WIB); Venus paling terang 28 Nov 01:37.
- Selisih terbesar hasil hitung (Skyfield) vs acuan: Moon-M45 -9 menit (dugaan: titik pusat gugus berbeda), oposisi Uranus +8, dikotomi Merkurius -7, konjungsi Jupiter-Mars -7; lainnya ≤3 menit.
- Mesin cepat: galat planet ~2' busur (Jupiter-Mars meleset ~2 jam; pasangan Bulan-planet ≤10 menit). Skyfield + DE440 menurunkannya ke ≤7 menit pada kasus terburuk.
- Halaman sumber lama menampilkan zona waktu **sesuai lokasi/IP pengunjung** (pernah IST), dan teks jam bisa berformat "at HH:MM" atau "from ... to ..."; ini salah satu alasan scraping ditinggalkan.

### 6.3 Cuaca
Open-Meteo (tanpa kunci API): `forecast` per jam hingga 16 hari (awan total/rendah/menengah/tinggi, kelembapan, peluang hujan, curah hujan, jarak pandang), `archive` (klimatologi). Waktu lokal lokasi dari `utc_offset_seconds`.

---

## 7. Pelajaran teknis [Verifikasi]
- Jangan membuka berkas untuk ditulis sebelum dibaca (`open(p,'w').write(open(p).read())` mengosongkan berkas; pernah terjadi).
- Catatan label "tidak dirilis sumber" harus akurat: bedakan *tidak tersedia* dari *gagal dibaca*.
- Respons API tiruan di tes harus memakai `utc_offset_seconds` sesuai lokasi; jendela prakiraan ±16 hari; port 5060 diblokir Chromium.
- Skyfield: impor modul mengunduh DE440s; pilih mesin per proses (`ASTROLIFE_ENGINE`), makanya pembuatan katalog dijalankan sebagai proses terpisah.
- Tailwind CDN tidak ada di sandbox: halaman katalog/beranda memakai CSS sendiri agar dapat dirender dan diperiksa; halaman lain bergaya Tailwind (gelap) belum diperiksa visual.
- Tema gelap/terang saat ini hanya untuk halaman Katalog (variabel CSS pada `.cat`); halaman lain tetap gelap.

---

## 8. Daftar tugas ke depan
1. ~~Port JS pemilik: salat, kiblat, rasydulqiblat, Hijriah aritmetis, Jawa~~ **selesai** (bagian 10). **Sisa port**: butuh efemeris Bulan ELP-MPP02 (Bulan terbit/terbenam, rasydul Bulan, hisab awal bulan MABIMS/WH/Turki, peta hilal, gerhana versi JS, fase/tithi/pañcāṅga JS). (Bulan & hisab awal bulan sudah diport dengan ELP ringkas; sisa: peta hilal, gerhana, fase/tithi/pañcāṅga JS, rasydul Bulan.)
2. AstroBot (retrieval/rule-based) dan pusat pengetahuan.
3. Ukur kecepatan jalur vektor Skyfield di komputer pemilik (`verify_engine`, `tests.test_skyfield`).
4. Verifikasi tabel hujan meteor `data/catalog/meteor_showers.json` ke kalender IMO; tambah Taurid, α-Monocerotid, Orionid November.
5. Perluas cakupan katalog: komet, "gugus tampak malam ini", Merkurius tertinggi pagi; daftar nama objek.
6. Rekomendasi: skor cuaca per event pada daftar Katalog; ekspor `.ics`; mode terang global.
7. Opsional: unduh efemeris tanpa internet (berkas `de440s.bsp` dapat disalin manual ke `data/ephemeris/`).

## 9. Perintah yang sering dipakai
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py                                   # lalu buka /catalog/ dan tekan "Buat katalog"
python -m unittest discover -s tests            # suite lengkap
python -m prototype.verify_engine               # mesin cepat vs Skyfield, konsistensi vektor, kecepatan
python -m catalog.generate 2026 2027            # alternatif terminal (ASTROLIFE_ENGINE=skyfield untuk akurat)
```


---

## 10. Port persis-times-js [Verifikasi]
Sumber: `persis-times-js` (berkas dari pemilik; lisensi MIT Abu Sabda/PP PERSIS). Hasilnya di `app/persis/` (lihat `app/persis/README.md`).
- Salat, kiblat, rasydulqiblat, istiwa, Hijriah aritmetis, kalender Jawa **cocok dengan JS asli** (uji `tests/test_persis.py` terhadap fixture dari Node; selisih < 1e-7 jam).
- Acuan nyata 2026 (Yogyakarta): Rasydul 1 = 28 Mei 16:17:58 WIB (09:17:58 UTC), Rasydul 2 = 15 Jul 16:26:42 WIB; antipoda 14 Jan & 29 Nov. Cocok dengan fakta di 6.1. 1 Muharam 1448 (urfi) = 17 Jun 2026 = 1 Sura 1960.
- Kiblat Yogyakarta (bola) 294°42′40″, Vincenty 294°35′02″ (lazim dikutip ±294°43′ = bola).
- Metode salat bawaan UI: Persatuan Islam (Subuh −20°, Isya −18°), ihtiyat 2 menit, imsak 10 menit; 9 metode tersedia. Jadwal = menit hisab dibulatkan ke bawah + ihtiyat.
- **Tanggal Jawa** kini hanya satu: siklus kurup JS (`persis.kalender.jd_ke_jawa`). Versi lama Hijriah + 512 dibuang; weton/pawukon tetap dari `calendar_service`.
- Ramadan (Isya Ummul Qura) memakai kriteria Ummul Qura hasil hisab (`hisab.ramadan_malam_uq`), bukan tabel resmi Umm al-Qura; dapat beda 1 hari dari kalender cetak resmi.
- Lab Kalender: tabel perbandingan (`/calendar/api/compare`) memakai lokasi/kriteria bawaan tiap kalender; tampilan halaman belum diperiksa visual (hanya sintaks JS dan API).
- Tidak diverifikasi: tampilan halaman di peramban (Tailwind CDN tak ada di sandbox); skrip halaman hanya diperiksa sintaksnya dan endpoint-nya diuji.
- Pemakaian: `python -m unittest discover -s tests` (tes `test_persis` ±17 detik karena 192 jadwal × ~8 waktu).


## 11. Tampilan (UI)
- Tema terang/gelap global (`html.dark`), variabel CSS di `theme.css` + `theme-palette.css`; palet 001f8e, 2a35e2, 29aafe, ed2124, 009339. Halaman Katalog tidak lagi punya pemilih tema sendiri (ikut global).
- Warna semantik puasa di Lab Kalender: wajib = 2a35e2, haram = ed2124, sunah = skala hijau 009339, makruh tetap kuning (palet tidak punya kuning).
- Halaman Salat menandai waktu salat berikutnya bila tanggal = hari ini di lokasi terpilih.
- Diperiksa lewat tangkapan layar (Chrome headless, Tailwind dibangun lokal dengan konfigurasi yang sama) pada 1366 px dan 390 px, mode terang dan gelap. Daftar event Katalog belum diperiksa visual karena butuh katalog yang sudah dibuat.

## 12. Pengaturan pengguna
- Satu sumber kebenaran: `AstroPrefs` (`prefs.js`) → lokasi, metode salat, kriteria Hijriah. Halaman hanya membaca dari sana dan mendengarkan peristiwa `astrolife:prefs`; kontrol lokasi/metode di halaman Katalog, Observasi, dan Salat sudah digantikan ringkasan + tombol "Ubah" (elemen lamanya disembunyikan agar JS halaman tetap bekerja).
- Kriteria Hijriah bawaan = Aritmetis (perilaku lama). Kriteria hisab hanya berlaku untuk tahun 1700–2300 M.
- Kriteria Hijriah tidak mengubah deteksi Ramadan untuk Isya Ummul Qura (selalu memakai kriteria Ummul Qura).
- Opsi epoch/pola kabisat aritmetis tetap ada di Lab Kalender (tidak ikut disimpan di Pengaturan).


## 13. AstroBot
- Alur `jawab()`: sapaan/bantuan → (jika bukan pertanyaan konsep) intent operasional → perbandingan kriteria → retrieval BM25. Pertanyaan berpola "apa itu/kenapa/bedanya/jelaskan" selalu ke artikel.
- Slot lanjutan (`kota`, `tanggal`, `intent`) dikembalikan ke klien dan dikirim lagi; hanya dipakai untuk pesan pendek tanpa kata kunci intent lain. Slot dikosongkan saat Pengaturan berubah.
- Evaluasi retrieval (`tests/test_bot.py`, 54 soal): top-1 98%, top-3 100%. Soal ditulis oleh pengembang yang sama dengan artikel, jadi angka ini **optimistis**; uji dengan pertanyaan pengguna nyata.
- Batas: tidak memahami kalimat bebas di luar pola/artikel; kota hanya yang ada di `kota.py` (±70); tanggal Hijriah per kriteria memakai pindai ±4 hari dari perkiraan aritmetis; tahun Hijriah 1300–1800.
- Artikel KB ditulis ringkas dan perlu ditinjau ahli falak sebelum dipakai rujukan; angka hujan meteor dan sudut metode bersifat perkiraan umum.
- Pertanyaan yang tak terjawab tidak dicatat (privasi).

### Gazetir kota (kota_data.csv)
- Sumber: data pemilik proyek (500 baris; Provinsi, Kota_Kabupaten, Pusat_Koordinat, Lintang, Bujur, Elevasi, Zona_Waktu; desimal koma). Dibaca apa adanya; pencocokan tanpa spasi/huruf besar ("Lubuk Linggau" = "Lubuklinggau").
- Bot memakai lintang, bujur, **elevasi**, dan **zona waktu** dari data ini (bukan perkiraan dari bujur). Nama ganda (Martapura, Sukadana, Tanjung) ditanyakan ulang atau dibedakan lewat nama provinsi.
- Kota yang disebut tetapi tidak ada di data dilaporkan "belum dikenal"; bot tidak lagi diam-diam memakai lokasi Pengaturan. Koordinat langsung ("-3.2954, 102.8655") juga diterima.
- Koreksi di kode (`kota.py`): Tarakan lintang bertanda minus di sumber → dibalik ke +3,298°; "Limapuluh" (lintang 3,17 untuk Sumatera Barat) ditolak, gunakan "Sarilamak". Belum dikoreksi: Langsa elevasi 610 m (kemungkinan keliru), "Dolok" berlabel Papua Barat padahal di wilayah Papua Selatan.
- Kata biasa yang juga nama tempat (sumber, tanjung, batu, pati, serang, ...) baru dianggap kota bila didahului "di/dari/untuk/kota/...".

### Intent tambahan (setelah masukan pengguna)
- `jumlah_hari` (umur bulan Hijriah per kriteria: selisih 1 bulan itu dan 1 bulan berikutnya), `weton` (weton, neptu, pawukon, wuku), `cuaca` (ringkasan per bagian hari dari Open-Meteo), `observasi` (7 malam ke depan: fase/penerangan/tinggi Bulan pukul 20.00 + skor kelayakan bila prakiraan ada; event Katalog bila katalog sudah dibuat).
- Cuaca dan skor **memerlukan internet dari server**. Tanpa itu bot berkata jujur tidak dapat memuat dan (untuk observasi) hanya merekomendasikan dari cahaya Bulan. Jalur ini diuji dengan prakiraan buatan; **panggilan Open-Meteo sungguhan tidak dapat diuji di sandbox**.
- "hari ini" saja tidak lagi memicu intent tanggal; harus ada kata tanggal/weton/kalender/dsb.
- Artikel baru: `keamanan-pengamatan` (hujan meteor, gerhana, mitos).

### Intent tambahan (ronde 3)
- `fase_berikut` (bulan baru/purnama/kuartal berikutnya dari `prototype.find_events.moon_phases`), `gerhana` (gerhana Matahari/Bulan 6 tahun ke depan dihitung langsung oleh `catalog.events` — tidak perlu katalog sudah dibangun — lalu dinilai keterlihatannya dari lokasi lewat `catalog.service.decorate`), `tahun` (Masehi, Hijriah per kriteria, Jawa, Saka), `banding_salat` (selisih waktu salat dua kota pada saat sebenarnya; jam hisab tanpa ihtiyat).
- Pemeriksaan silang: bulan baru 6 Feb 2027 16:00 UTC (gerhana cincin) dan 2 Agt 2027 (total), 26 Jan 2028 (cincin), 22 Jul 2028 (total) cocok dengan data gerhana yang saya ketahui; waktu puncak lokal belum divalidasi terhadap almanak resmi.
- Belum didukung: istilah "Tubin" dan "Tulat" (tidak ada di kode proyek ini maupun di sumber yang saya temukan; butuh definisi dari pemilik proyek).

### Istilah hari relatif
Dari pemilik proyek: H-4 dst. senantu; H-3 kila mulai; H-2 selumbari/basarai/kemarin dulu/kemarin lusa; H-1 kemarin; H+1 besok/esok; H+2 lusa/besok lusa; H+3 tulat/langkat; H+4 tubin/tungging; H+5 cekelong; H+6 dst. embute. Dipakai oleh semua intent bertanggal (`REL` di `app/bot/mesin.py`) dan dijelaskan di artikel `istilah-hari-relatif`. Istilah terbuka (senantu, embute) dijawab dengan tanggal terdekatnya.

## Padanan Lab Kalender (ringkas + rincian)
Empat baris, masing-masing satu tanggal ringkas dengan tombol rincian (`falak_service.padanan`, kunci `padanan` pada `/calendar/api/convert`):
- **Masehi (AD)**: tanggal saja (`27 November 2026 AD`); rincian: Gregorian dan Julian (`tanggal_julian`, proleptik; sebelum 15 Okt 1582 baris utama memakai Julian dan diberi tanda).
- **Hijriah (AH)**: satu tanggal menurut kriteria di Pengaturan; rincian: aritmetis tipe I–IV (epoch sesuai form) dan kriteria astronomis lainnya.
- **Jawa Mataraman (AJ)**: tanggal tanpa nama tahun; rincian: nama tahun, nama windu, kurup.
  Kurup = singkatan hari+pasaran 1 Sura tahun Alip pertama siklus 120 tahun (1867 → Asapon, 1747 → Aboge). Nama windu (Kuntara, Sengara, Sancaya, Adi; bergilir 4) **dijangkarkan pada contoh pengguna (1960 = Sancaya)**, belum dicocokkan dengan sumber lain.
- **Jawa Kuno (AS)**: `{tithi}{š|k} {bulan Saka} {tahun Saka} AS`; rincian: jyotisa lengkap. Ejaan "Karttika" hanya untuk baris ini.

## Beranda & Pengaturan lokasi (pembaruan)
- Kartu Modul memakai ikon Lucide yang sama dengan menu atas (telescope, sparkles, calendar, compass, bot); label status ("Siap"/"Dalam pengembangan") dihapus di Beranda dan Tentang Proyek.
- Event mendatang menampilkan cuaca pada waktu event (`wx.default` = waktu terbaik atau puncak) lewat `POST /observation/api/feasibility` per event: awan, peluang hujan, skor. Di luar jangkauan prakiraan (~16 hari) tertulis "rata-rata historis"; bila layanan tak terjangkau tertulis "tidak tersedia".
- Pengaturan > Lokasi: kolom cari kota (autocomplete dari gazetir `kota_data.csv` lewat `GET /api/kota?q=`, minimal 2 huruf, nama/provinsi, spasi diabaikan; panah/Enter/Esc didukung). Memilih kota mengisi lintang, bujur, elevasi, dan zona waktu dari CSV.
- Koordinat manual: format Desimal atau Seksagesimal (° ′ ″ dengan LU/LS dan BT/BB); kedua format saling sinkron.

## Cuaca otomatis di Katalog Event
Tiap baris event mendatang menampilkan cuaca ringkas tanpa klik (awan, peluang hujan, kondisi pada waktu terbaik/puncak yang sama dengan tombol "Cuaca"). Satu panggilan `POST /observation/api/weather-batch` (maks. 300 event) memakai satu pengambilan prakiraan Open-Meteo yang dicache 1 jam. Hanya prakiraan per jam: event > ~15 hari ke depan ditulis "prakiraan belum tersedia", event yang sudah lewat tidak diberi cuaca, dan bila layanan mati tertulis "tidak tersedia". Klimatologi sengaja tidak dipakai di sini (lambat untuk banyak event); analisis lengkap tetap lewat tombol Cuaca.

## Peta kode & konvensi (hasil pembersihan)
- Komentar dan nama dalam bahasa Indonesia; setiap modul diawali docstring satu paragraf tentang tanggung jawabnya.
- `app/bot/mesin.py` hanya mengatur alur (`jawab`, `_normalisasi`, `_jawab_lanjutan`, `_urutan_intent`); logika per tema ada di `intent_*.py`, bahan bersama di `dasar.py`. Urutan intent di `_urutan_intent` adalah urutan prioritas: yang lebih spesifik harus di atas.
- `catalog/visibility.evaluate` memakai pembantu `_pilih_sampel_terbaik` dan `_alasan`; hasilnya dibandingkan dengan versi sebelum refaktor untuk 271 event × 4 lokasi (identik).
- Kegagalan layanan cuaca dicatat lewat `logging` (bukan `print`).
- Cek mutu yang dipakai: `ruff check . --select F,B,SIM` (tanpa temuan F), `vulture`, `radon cc`. Fungsi yang masih kompleks dan sengaja dibiarkan: `persis/*` (port persis-times-js, dijaga sama dengan sumber JS), `catalog/rarity.rarity` (aturan kelangkaan berurutan), `hukum_puasa`.
