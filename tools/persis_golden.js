// Menghasilkan tests/fixtures/persis_golden.json dengan menjalankan pustaka JS asli (persis-times-js) di Node.
// Pemakaian: node tools/persis_golden.js <folder persis-times-js> <berkas keluaran>
const fs = require('fs'), vm = require('vm'), path = require('path');
const root = process.argv[2], out = process.argv[3];
const ctx = { console, performance }; vm.createContext(ctx);
const order = fs.readFileSync(path.join(root, 'index.html'), 'utf8').match(/src="([^"]+)"/g).map(s => s.slice(5, -1))
  .filter(f => !f.startsWith('js/app/'));
for (const f of order) vm.runInContext(fs.readFileSync(path.join(root, f), 'utf8'), ctx, { filename: f });
const L = vm.runInContext(`({SunFunction, DynamicalTime, JulianDay, NutationAndObliquity, WaktuSalat, SalatService, PrayerMethod,
  ArahKiblat, WaktuPelengkap, RasydulHarian, jd2jawa, jawa2jd, tahunJawa2noTahunJawa})`, ctx);
const sn = new L.SunFunction(), dt = new L.DynamicalTime(), jd = new L.JulianDay(), nt = new L.NutationAndObliquity();
const G = {};
// 1. Matahari pada beberapa JD
G.sun = [2451545.0, 2459000.3, 2461000.5, 2461367.25, 2440587.5, 2469807.1, 2305447.5].map(j => {
  const d = dt.deltaT(j);
  return { jd: j, dt: d, ra: sn.sunGeocentricRightAscension(j, d), dec: sn.sunGeocentricDeclination(j, d), lon: sn.sunGeocentricLongitude(j, d, 'Appa'),
    lat: sn.sunGeocentricLatitude(j, d), r: sn.earthRadiusVector(j, d), sd: sn.sunGeocentricSemidiameter(j, d), eot: sn.equationOfTime(j, d),
    dpsi: nt.nutationInLongitude(j, d), deps: nt.nutationInObliquity(j, d), eps: nt.trueObliquityOfEcliptic(j, d), gast: sn.greenwichApparentSiderialTime(j, d),
    ghurub: sn.jdGhurubSyams(Math.floor(j) + 0.5, -7.7956, 110.3695, 100, 7) };
});
// 2. Delta T pada banyak tahun
G.deltat = [-600, 100, 800, 1650, 1750, 1830, 1880, 1910, 1930, 1955, 1970, 1995, 2010, 2026, 2100, 3100].map(y => ({ y, jd: jd.kmjd(1, 7, y, 0, 0), dt: dt.deltaT(jd.kmjd(1, 7, y, 0, 0)) }));
// 3. Kalender
G.kmjd = [[1, 1, 2000, 12, 0], [17, 8, 1945, 0, 7], [4, 10, 1582, 0, 0], [15, 10, 1582, 0, 0], [28, 2, 2024, 18.5, 7], [32, 12, 2025, 3, 0], [10, 11, 2026, 6, 7]]
  .map(a => ({ a, jd: jd.kmjd(...a) }));
// 4. Waktu salat harian
const lokasi = [
  { n: 'Yogyakarta', lon: 110.3695, lat: -7.7956, elev: 100, tz: 7 },
  { n: 'Jakarta', lon: 106.8456, lat: -6.2088, elev: 8, tz: 7 },
  { n: 'Makassar', lon: 119.4327, lat: -5.1477, elev: 5, tz: 8 },
  { n: 'Jayapura', lon: 140.7181, lat: -2.5337, elev: 3, tz: 9 },
  { n: 'Makkah', lon: 39.8262, lat: 21.4225, elev: 300, tz: 3 },
  { n: 'London', lon: -0.1276, lat: 51.5072, elev: 11, tz: 0 },
  { n: 'Tromso', lon: 18.9553, lat: 69.6496, elev: 10, tz: 1 },
  { n: 'Sydney', lon: 151.2093, lat: -33.8688, elev: 58, tz: 10 },
];
const tgl = [[10, 11, 2026], [21, 6, 2026], [22, 12, 2026], [20, 3, 2026], [1, 1, 2025], [15, 6, 2026]];
const metode = ['persatuanIslam', 'muhammadiyah', 'muslimWorldLeague', 'ummulQura'];
G.salat = [];
const svc = new L.SalatService();
for (const l of lokasi) for (const [d, m, y] of tgl) for (const mk of metode) {
  const r = svc.waktuSalatHarian({ tglM: d, blnM: m, thnM: y, gLon: l.lon, gLat: l.lat, elev: l.elev, tmZn: l.tz, prayerMethod: L.PrayerMethod[mk], ihtySubuh: 2, ihtyZuhur: 3, ihtyAsar: 2, ihtyMagrib: 2, ihtyIsya: 2, ihtySyuruk: -2, isRamadan: false });
  const o = {}; for (const k of Object.keys(r)) o[k] = { t: r[k].time, s: r[k].status };
  G.salat.push({ lok: l, d, m, y, metode: mk, r: o });
}
// 5. Kiblat & Rasydul harian & istiwa
const ak = new L.ArahKiblat(), rd = new L.RasydulHarian(), wp = new L.WaktuPelengkap();
G.kiblat = lokasi.concat([{ n: 'Quito', lon: -78.4678, lat: -0.1807 }, { n: 'Wellington', lon: 174.7762, lat: -41.2866 }]).map(l => ({ lok: l, sph: ak.arahQiblatSpherical(l.lon, l.lat), ell: ak.arahQiblaWithEllipsoidCorrection(l.lon, l.lat),
  vin: ak.arahQiblaVincenty(l.lon, l.lat, 'PtoQ'), dist: ak.arahQiblaVincenty(l.lon, l.lat, 'Dist'), jarakSph: ak.jarakQiblatSpherical(l.lon, l.lat), jarakEll: ak.jarakQiblatEllipsoid(l.lon, l.lat) }));
G.rasydulHarian = [];
for (const l of lokasi.slice(0, 5)) for (const [d, m, y] of [[10, 11, 2026], [28, 5, 2026], [1, 3, 2026], [20, 9, 2026]]) {
  const Q = ak.arahQiblatSpherical(l.lon, l.lat);
  G.rasydulHarian.push({ lok: l, d, m, y, Q, ev: rd.hari(d, m, y, l.lat, l.lon, l.tz, Q) });
}
G.istiwa = lokasi.map(l => ({ lok: l, r: wp.istiwa(10, 11, 2026, l.lon, l.lat, l.tz), sm: wp.sepertigaMalam(10, 11, 2026, l.lon, l.lat, l.elev, l.tz, L.PrayerMethod.persatuanIslam) }));
G.sunAltAz = [[2461000.3, -7.8, 110.4], [2461200.9, 40.7, -74], [2461100.1, -33.9, 151.2]].map(([j, la, lo]) => ({ j, la, lo, r: rd.sunAltAz(j, la, lo) }));
// 6. Rasydulqiblat tahunan & antipoda
G.rasydul = []; for (const y of [2025, 2026, 2027]) for (const tz of [7, 3]) for (const opt of [1, 2]) {
  G.rasydul.push({ y, tz, opt, r: ak.rashdulQiblat(y, tz, opt), a: ak.antipodaKabah(y, tz, opt), b: ak.bayanganQiblatHarian(110.3695, -7.7956, 10, 11, y, 7, 'spherical', opt) });
}
// 7. Kalender Jawa & Hijriah aritmetis
G.jawa = [2441317.5, 2431679.5, 2461000.5, 2461367.5, 2459000.5, 2300000.5].map(j => ({ jd: j, r: L.jd2jawa(j), no: L.tahunJawa2noTahunJawa(L.jd2jawa(j).tahunJawa) }));
G.jawa2jd = [[1, 1, 1960], [15, 6, 1955], [29, 12, 1948]].map(a => ({ a, jd: L.jawa2jd(...a) }));
G.hijri = []; for (const j of [2461000.5, 2461367.5, 2431679.5, 2459000.5, 2441317.5]) for (const [e, l] of [[2, 2], [1, 1], [2, 3], [2, 4]])
  G.hijri.push({ jd: j, e, l, r: [jd.jdkh(j, 7, e, l, 'TGL'), jd.jdkh(j, 7, e, l, 'BLN'), jd.jdkh(j, 7, e, l, 'THN'), jd.jdkh(j, 7, e, l, 'NMBLNH'), jd.jdkh(j, 7, e, l)], cj: jd.cjdnkh(Math.floor(j + 0.5 + 7 / 24), { hCalE: e, hCalL: l, optResult: 'PS' }) });
G.khcjdn = [[1, 9, 1447, 2, 2], [17, 10, 1448, 2, 2], [1, 1, 1, 1, 1], [29, 12, 1300, 2, 3]].map(a => ({ a, r: jd.khcjdn(...a) }));
fs.writeFileSync(out, JSON.stringify(G));
console.log('ok', Object.keys(G).map(k => k + ':' + (G[k].length || '')).join(' '));
