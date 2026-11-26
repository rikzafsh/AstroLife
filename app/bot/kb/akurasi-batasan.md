---
judul: Akurasi dan batasan perhitungan AstroLife
kategori: Fitur
kata_kunci: akurasi, ketelitian, batasan, keterbatasan, benarkah, bisa dipercaya, resmi, kemenag, berbeda dengan, selisih, sumber data, validasi
ringkas: Hasil dihitung dari rumus astronomi dan divalidasi terhadap pustaka sumbernya, namun bukan penetapan resmi.
tautan: 
---
- **Salat, kiblat, rasydulqiblat**: diport dari pustaka *persis-times* dan diuji terhadap kodenya (selisih < 1e-7 jam). Jadwal resmi daerah Anda dapat berbeda beberapa menit karena ihtiyat atau kriteria.
- **Awal bulan Hijriah**: hasil hisab sesuai kriteria yang dipilih; **bukan** keputusan resmi (sidang isbat). Dapat beda 1–2 hari.
- **Bulan**: deret ELPMPP02 diringkas; selisih terhadap deret penuh sangat kecil (ijtimak < 1 detik pada pengujian 1440–1460 H), di luar rentang itu belum diuji.
- **Planet pada Katalog**: akurat bila Skyfield/DE440 terpasang; mesin sementara galatnya ±2 menit busur.
- **Cuaca**: bergantung pada layanan Open-Meteo dan perlu internet.

Untuk ibadah, ikuti penetapan resmi lembaga/ulama setempat.
