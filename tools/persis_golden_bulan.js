// Fixture bagian Bulan/hisab awal bulan dari JS asli (deret ELPMPP02 penuh).
// Pemakaian: node tools/persis_golden_bulan.js <folder persis-times-js> <berkas keluaran> [tahunH awal] [tahunH akhir]
const fs = require('fs'), vm = require('vm'), path = require('path');
const root = process.argv[2], out = process.argv[3], y0 = +(process.argv[4] || 1440), y1 = +(process.argv[5] || 1460);
const ctx = { console, performance }; vm.createContext(ctx);
const order = fs.readFileSync(path.join(root, 'index.html'), 'utf8').match(/src="([^"]+)"/g).map(s => s.slice(5, -1)).filter(f => !f.startsWith('js/app/'));
for (const f of order) vm.runInContext(fs.readFileSync(path.join(root, f), 'utf8'), ctx, { filename: f });
const L = vm.runInContext('({MoonFunction, MoonLongitude, MoonLatitude, MoonDistance, CalendarService, DynamicalTime, JulianDay, jd2jawa})', ctx);
const mo = new L.MoonFunction(), cal = new L.CalendarService(), dt = new L.DynamicalTime(), ml = new L.MoonLongitude(), mb = new L.MoonLatitude(), md = new L.MoonDistance();
const G = { posisi: [], terbit: [], awal: [], ijtimak: [], hijri: [] };
for (const j of [2451545.0, 2459000.3, 2461000.5, 2461371.25, 2455000.7, 2465000.1]) {
  const d = dt.deltaT(j);
  G.posisi.push({ jd: j, dt: d, lon: ml.moonGeocentricLongitude(j, d, 'Appa'), lat: mb.moonGeocentricLatitude(j, d, 'Appa'), r: md.moonGeocentricDistance(j, d, 'KM'),
    ra: mo.moonGeocentricRightAscension(j, d), dec: mo.moonGeocentricDeclination(j, d), elong: mo.moonSunGeocentricElongation(j, d),
    alt: mo.moonGeocentricAltitude(j, d, 110.37, -7.8), htoc: mo.moonTopocentricAltitude(j, d, 110.37, -7.8, 10, 1010, 10, 'htoc'), htou: mo.moonTopocentricAltitude(j, d, 110.37, -7.8, 10, 1010, 10, 'htou') });
}
for (const [la, lo, el, tz] of [[-7.7956, 110.3695, 100, 7], [21.4225, 39.8262, 304, 3], [51.5, -0.12, 11, 0], [-33.87, 151.2, 58, 10]])
  for (const [d, m, y] of [[10, 11, 2026], [26, 11, 2026], [1, 6, 2026], [14, 3, 2025]])
    for (const t of ['RISE', 'TRANSIT', 'SET']) G.terbit.push({ la, lo, el, tz, d, m, y, t, v: mo.moonTransitRiseSet(d, m, y, lo, la, el, tz, t, 3) });
for (let y = y0; y <= y1; y++) for (let m = 1; m <= 12; m++) {
  const nm = mo.geocentricConjunction(m, y, 0.0, 'Ijtimak'), d = dt.deltaT(nm);
  G.ijtimak.push({ m, y, jd: mo.geocentricConjunction(m, y, d, 'Ijtimak') });
  G.awal.push({ m, y, mabims: cal.abqMabims(m, y), uq: cal.abqUmmulQura(m, y), wh: cal.abqWujudulHilal(m, y), turki: cal.abqTurki(m, y) });
}
for (const [d, m, y] of [[10, 11, 2026], [17, 6, 2026], [18, 6, 2026], [26, 11, 2026], [20, 3, 2026], [21, 3, 2026], [10, 3, 2024], [11, 3, 2024]])
  G.hijri.push({ d, m, y, mabims: cal.serviceKalenderHijriahMABIMS(d, m, y), uq: cal.serviceKalenderHijriahUQ(d, m, y), wh: cal.serviceKalenderHijriahWH(d, m, y), turki: cal.serviceKalenderHijriahTURKI(d, m, y) });
fs.writeFileSync(out, JSON.stringify(G));
console.log('ok', Object.keys(G).map(k => k + ':' + G[k].length).join(' '));
