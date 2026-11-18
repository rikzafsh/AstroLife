# Perbandingan hitungan vs in-the-sky.org, 2026-11

Sumber pembanding: `data/datasets/astronomy_events.json`. Waktu dalam WIB. Mesin: skyfield + JPL DE440s.

| Event sumber | Jam sumber | Jam hitungan | Selisih (menit) | Jenis |
|---|---|---|---|---|
| Moon at Last Quarter | 02 Nov 03:28 | 02 Nov 03:28 | +0 | last_quarter |
| Close approach of the Moon and M44 | 02 Nov 00:34 | 02 Nov 00:35 | +2 | close |
| Close approach of the Moon and Mars | 02 Nov 20:39 | 02 Nov 20:39 | +0 | close |
| Close approach of the Moon and Jupiter | 03 Nov 05:45 | 03 Nov 05:45 | +1 | close |
| Lunar occultation of Mars [mulai jendela] | 02 Nov 19:15 | 02 Nov 19:14 | -0 | occ_window_start |
| Lunar occultation of Mars [akhir jendela] | 02 Nov 22:02 | 02 Nov 22:03 | +1 | occ_window_end |
| Lunar occultation of Jupiter [mulai jendela] | 03 Nov 03:45 | 03 Nov 03:45 | +0 | occ_window_start |
| Lunar occultation of Jupiter [akhir jendela] | 03 Nov 07:45 | 03 Nov 07:46 | +2 | occ_window_end |
| Conjunction of the Moon and Mars | 02 Nov 21:24 | 02 Nov 21:25 | +1 | conj_ra |
| Conjunction of the Moon and Jupiter | 03 Nov 06:09 | 03 Nov 06:09 | +1 | conj_ra |
| Lunar occultation of Regulus [mulai jendela] | 03 Nov 13:59 | 03 Nov 13:59 | +0 | occ_window_start |
| Lunar occultation of Regulus [akhir jendela] | 03 Nov 17:24 | 03 Nov 17:25 | +2 | occ_window_end |
| Lunar occultation of Venus [mulai jendela] | 07 Nov 16:26 | 07 Nov 16:24 | -2 | occ_window_start |
| Lunar occultation of Venus [akhir jendela] | 07 Nov 18:59 | 07 Nov 19:01 | +2 | occ_window_end |
| Lunar occultation of Antares [mulai jendela] | 11 Nov 09:24 | 11 Nov 09:23 | -1 | occ_window_start |
| Lunar occultation of Antares [akhir jendela] | 11 Nov 13:52 | 11 Nov 13:51 | -0 | occ_window_end |
| Lunar occultation of Sigma Sagittarii [mulai jendela] | 14 Nov 03:01 | 14 Nov 03:00 | -1 | occ_window_start |
| Lunar occultation of Sigma Sagittarii [akhir jendela] | 14 Nov 07:39 | 14 Nov 07:39 | +1 | occ_window_end |
| Conjunction of Jupiter and Mars | 15 Nov 09:42 | 15 Nov 09:35 | -7 | conj_ra |
| Close approach of Jupiter and Mars | 16 Nov 09:04 | 16 Nov 09:04 | +1 | close |
| Moon at First Quarter | 17 Nov 18:48 | 17 Nov 18:47 | -0 | first_quarter |
| Mercury at dichotomy | 18 Nov 15:55 | 18 Nov 15:47 | -7 | dichotomy |
| Close approach of the Moon and Saturn | 21 Nov 03:02 | 21 Nov 03:03 | +1 | close |
| Mercury at greatest elongation west | 21 Nov 07:33 | 21 Nov 07:33 | +1 | greatest_elongation_west |
| Conjunction of the Moon and Saturn | 21 Nov 08:26 | 21 Nov 08:26 | +1 | conj_ra |
| Full Moon | 24 Nov 21:53 | 24 Nov 21:53 | +1 | full_moon |
| Close approach of the Moon and M45 | 24 Nov 18:45 | 24 Nov 18:36 | -9 | close |
| Uranus at opposition | 26 Nov 05:33 | 26 Nov 05:41 | +8 | opposition |
| Lunar occultation of Beta Tauri [mulai jendela] | 26 Nov 05:15 | 26 Nov 05:16 | +1 | occ_window_start |
| Lunar occultation of Beta Tauri [akhir jendela] | 26 Nov 07:53 | 26 Nov 07:54 | +2 | occ_window_end |
| Venus at greatest brightness | 28 Nov 01:37 | 28 Nov 01:36 | -0 | greatest_brightness |
| Close approach of the Moon and M44 | 29 Nov 07:10 | 29 Nov 07:12 | +2 | close |
| Close approach of the Moon and Jupiter | 30 Nov 15:24 | 30 Nov 15:25 | +1 | close |
| Close approach of the Moon and Mars | 30 Nov 23:54 | 30 Nov 23:55 | +1 | close |
| Lunar occultation of Jupiter [mulai jendela] | 30 Nov 14:15 | 30 Nov 14:15 | +1 | occ_window_start |
| Lunar occultation of Jupiter [akhir jendela] | 30 Nov 16:32 | 30 Nov 16:34 | +2 | occ_window_end |
| Lunar occultation of Regulus [mulai jendela] | 30 Nov 20:11 | 30 Nov 20:11 | +0 | occ_window_start |
| Lunar occultation of Regulus [akhir jendela] | 30 Nov 22:36 | 30 Nov 22:38 | +3 | occ_window_end |
| Conjunction of the Moon and Jupiter | 30 Nov 16:15 | 30 Nov 16:16 | +1 | conj_ra |

## Ringkasan selisih per jenis (menit)

| Jenis | n | rata-rata \|selisih\| | maks \|selisih\| |
|---|---|---|---|
| close | 9 | 2.0 | 9 |
| conj_ra | 5 | 2.1 | 7 |
| dichotomy | 1 | 7.3 | 7 |
| first_quarter | 1 | 0.2 | 0 |
| full_moon | 1 | 0.6 | 1 |
| greatest_brightness | 1 | 0.1 | 0 |
| greatest_elongation_west | 1 | 0.8 | 1 |
| last_quarter | 1 | 0.5 | 0 |
| occ_window_end | 9 | 1.6 | 3 |
| occ_window_start | 9 | 0.7 | 2 |
| opposition | 1 | 8.3 | 8 |

Dibandingkan: **39** titik waktu. Median |selisih| = **1.0** menit; 39 dari 39 berselisih <= 15 menit.

## Event sumber yang BELUM dicakup pencari (8)

- Comet 69P/Taylor passes perihelion
- Northern Taurid meteor shower 2026
- Leonid meteor shower 2026
- The Pleiades cluster is well placed
- α-Monocerotid meteor shower 2026
- Mercury at highest altitude in morning sky
- November Orionid meteor shower 2026
- The Hyades cluster is well placed

## Event hitungan yang TIDAK ada di data sumber (18)

(bisa berarti sumber memfilternya atau definisi kita terlalu longgar)

- 02 Nov 00:21 Konjungsi (asensio rekta) Bulan - M44 (Praesepe) -  -  (sep 0.4°)
- 03 Nov 15:42 Close approach Bulan - Regulus -  -  (sep 0.8°)
- 07 Nov 17:42 Close approach Bulan - Venus -  -  (sep 1.0°)
- 07 Nov 18:33 Konjungsi (asensio rekta) Bulan - Venus -  -  (sep 1.1°)
- 08 Nov 19:32 Close approach Bulan - Merkurius -  -  (sep 5.7°)
- 08 Nov 23:33 Konjungsi (asensio rekta) Bulan - Merkurius -  -  (sep 6.1°)
- 09 Nov 14:02 Bulan Baru
- 11 Nov 11:37 Close approach Bulan - Antares -  -  (sep 0.3°)
- 14 Nov 05:20 Close approach Bulan - Sigma Sagittarii -  -  (sep 0.1°)
- 20 Nov 15:29 Close approach Bulan - Neptunus -  -  (sep 4.4°)
- 20 Nov 19:35 Konjungsi (asensio rekta) Bulan - Neptunus -  -  (sep 5.0°)
- 24 Nov 18:54 Konjungsi (asensio rekta) Bulan - M45 (Pleiades) -  -  (sep 0.9°)
- 25 Nov 00:13 Close approach Bulan - Uranus -  -  (sep 5.1°)
- 25 Nov 01:39 Konjungsi (asensio rekta) Bulan - Uranus -  -  (sep 5.2°)
- 26 Nov 06:35 Close approach Bulan - Beta Tauri -  -  (sep 1.0°)
- 29 Nov 07:07 Konjungsi (asensio rekta) Bulan - M44 (Praesepe) -  -  (sep 0.1°)
- 29 Nov 12:08 Merkurius paling terang
- 30 Nov 21:25 Close approach Bulan - Regulus -  -  (sep 1.0°)