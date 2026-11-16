# AstroLife 🌌
**Platform Web untuk Eksplorasi Astronomi Modern, Sistem Kalender Historis, dan Perencanaan Pengamatan Fenomena Langit**

---

## 📌 Ringkasan Proyek
AstroLife adalah platform web berbasis Python Flask yang menggabungkan:
1. **Astronomy Explorer & Observation Planner**: Scraping peristiwa astronomi dari `in-the-sky.org` dan prakiraan cuaca (Google Weather API / fallback) untuk scoring kelayakan observasi langit.
2. **Calendar Laboratory**: Konversi dan komparasi kalender Masehi, Hijriah Aritmetis, Jawa Mataraman (Pasaran, Wuku, Windu), dan Jyotiṣa / Jawa Kuno.
3. **Islamic Astronomy & Timekeeping**: Jadwal salat, rekomendasi puasa sunah, dan perhitungan presisi Rasydulqiblat tahunan (27-28 Mei & 15-16 Juli) serta harian.
4. **Data Analytics & Machine Learning**: Linear Regression kecenderungan cuaca, K-Means Clustering kondisi langit, dan Sentiment Analysis persepsi publik.
5. **AstroBot & Knowledge Center**: Chatbot interaktif edukasi astronomi dan ensiklopedia materi falak/budaya.

---

## 📂 Struktur Direktori

```text
astrolife/
├── app/
│   ├── __init__.py                 # Application Factory & Blueprint Registration
│   ├── routes/                     # Blueprint Endpoints
│   │   ├── main.py                 # Landing page
│   │   ├── observation.py          # Observation planner & in-the-sky scraper API
│   │   ├── calendar.py             # Calendar Laboratory routes
│   │   ├── islamic.py              # Prayer times & Rasydulqiblat routes
│   │   ├── analytics.py            # Machine learning & data visual routes
│   │   └── bot.py                  # AstroBot assistant endpoints
│   ├── services/                   # Business Logic & Algorithms
│   │   ├── scraper_service.py      # Scraper in-the-sky.org with caching
│   │   ├── weather_service.py      # Weather API & observation feasibility scoring
│   │   ├── calendar_service.py     # Ported calendar engines
│   │   ├── islamic_service.py      # Ported falak & Rasydulqiblat logic
│   │   └── analytics_service.py    # Regression, clustering, sentiment
│   └── templates/                  # Jinja2 UI Templates (Tailwind CSS Dark Theme)
├── config.py                       # Application configuration
├── requirements.txt                # Python dependencies
├── run.py                          # Application entry point
├── .env.example                    # Sample environment variables
└── README.md
```

---

## 🚀 Panduan Menjalankan Proyek

### 1. Masuk ke Direktori Proyek
```bash
cd "C:\Users\USER\.gemini\antigravity\scratch\astrolife"
```

### 2. Pasang Dependensi Python
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Variabel Lingkungan (.env)
Salin `.env.example` menjadi `.env` dan masukkan API Key jika tersedia:
```env
GOOGLE_WEATHER_API_KEY=your_key_here
```
*(Catatan: Jika API Key Google Weather belum diisi, sistem otomatis menggunakan fallback service sehingga aplikasi tetap berjalan lancar untuk pengembangan).*

### 4. Jalankan Server Flask
```bash
python run.py
```
Buka browser di `http://127.0.0.1:5000`.

## Observation Planner (fenomena + prakiraan cuaca)

- `app/services/weather_service.py`: prakiraan per jam Open-Meteo (awan rendah/menengah/tinggi, kelembapan, peluang hujan, jarak pandang). Di luar 16 hari memakai klimatologi (ditandai "indikatif"). Jika semua gagal: skor tidak dihitung (tidak ada data mock).
- `app/services/planner_service.py`: skor kelayakan 0-100 + rincian pengurang (awan, hujan, kelembapan, jarak pandang, cahaya Bulan bila Bulan di atas ufuk, siang hari) dan rekomendasi terbaik.
- Endpoint: `POST /observation/api/feasibility`, `POST /observation/api/event-forecast`, `GET /observation/api/plan?lat=&lon=&instrument=`.
- Uji: `python -m unittest discover -s tests -v` (cuaca ditiru, tidak butuh internet).

Catatan: `calendar_service.py`, `islamic_service.py`, `astro_core.py` sudah berisi mesin perhitungan (teruji terhadap tanggal acuan) tetapi rute/UI-nya belum disambungkan.
