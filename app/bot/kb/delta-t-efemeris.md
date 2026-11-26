---
judul: ΔT dan efemeris yang dipakai AstroLife
kategori: Astronomi
kata_kunci: delta t, efemeris, vsop87, elp, elpmpp02, skyfield, de440, jpl, nutasi, akurasi, posisi matahari, posisi bulan, persamaan waktu, equation of time
ringkas: AstroLife menghitung posisi Matahari, Bulan, dan planet sendiri; ΔT menyelaraskan waktu bumi dengan waktu seragam.
tautan: 
---
- **Matahari**: teori VSOP87D (dengan nutasi IAU 1980 dan aberasi).
- **Bulan**: ELPMPP02 yang **diringkas** menurut amplitudo (±1.000 suku) agar ringan; selisih terhadap deret penuh pada orde detik busur (bujur ≤ 0,2″).
- **Planet (Katalog Event)**: efemeris NASA JPL DE440 lewat Skyfield bila terpasang; bila tidak, mesin sementara dengan galat ±2 menit busur.
- **ΔT** = TT − UT1, koreksi akibat rotasi Bumi tak seragam (±70 detik pada 2026), dihitung dengan polinom Espenak–Meeus.
- **Persamaan waktu**: selisih waktu Matahari sebenarnya dan rata-rata, menggeser kulminasi hingga ±16 menit.
