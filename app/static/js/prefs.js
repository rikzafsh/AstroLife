/* Pengaturan pengguna AstroLife: lokasi, kriteria waktu salat, dan kriteria kalender Hijriah.
   Disimpan di localStorage ('astrolife.prefs.v1') sehingga tidak hilang saat halaman dimuat ulang dan sama di semua tab/halaman.
   Perubahan menyiarkan peristiwa 'astrolife:prefs' (juga ke tab lain lewat peristiwa 'storage').
   Cara pakai di halaman:  AstroPrefs.get().lokasi.lat   |   AstroPrefs.set({hijriah:{kriteria:'mabims'}})
                           document.addEventListener('astrolife:prefs', e => e.detail.berubah.includes('lokasi') && muatUlang()) */
(function (g) {
  'use strict';
  var KEY = 'astrolife.prefs.v1';
  var D = g.ASTRO_DEFAULTS || { nama: 'Yogyakarta', lat: -7.7956, lon: 110.3695 };
  var KOTA = [
    ['Yogyakarta', -7.7956, 110.3695], ['Jakarta', -6.2088, 106.8456], ['Bandung', -6.9175, 107.6191], ['Surabaya', -7.2575, 112.7521],
    ['Medan', 3.5952, 98.6722], ['Makassar', -5.1477, 119.4327], ['Denpasar', -8.65, 115.2167], ['Pontianak', -0.0263, 109.3425],
    ['Jayapura', -2.5337, 140.7181], ['Makkah', 21.4225, 39.8262]
  ];
  var DEF = {
    lokasi: { nama: D.nama, lat: D.lat, lon: D.lon, elev: 0, tz: null },     // tz null = otomatis dari bujur
    salat: { metode: 'persatuanIslam', ihtiyat: 2, imsak: 10 },
    hijriah: { kriteria: 'aritmetis' }
  };
  var NAMA_KRITERIA = { aritmetis: 'Aritmetis', mabims: 'MABIMS', ummulqura: 'Ummul Qura', wujudulhilal: 'Wujudul Hilal', turki: 'KHGT' };

  function salin(o) { return JSON.parse(JSON.stringify(o)); }
  function gabung(dst, src) {
    Object.keys(src || {}).forEach(function (k) {
      if (src[k] && typeof src[k] === 'object' && !Array.isArray(src[k]) && dst[k] && typeof dst[k] === 'object') gabung(dst[k], src[k]);
      else dst[k] = src[k];
    });
    return dst;
  }
  function tzDariBujur(lon) { return (lon >= 95 && lon < 115) ? 7 : (lon >= 115 && lon < 130) ? 8 : (lon >= 130 && lon <= 141.5) ? 9 : Math.round(lon / 15); }
  function labelTz(tz) { return { 7: 'WIB', 8: 'WITA', 9: 'WIT' }[tz] || ('UTC' + (tz >= 0 ? '+' : '-') + Math.abs(tz)); }

  function bersihkan(p) {                         // validasi supaya data rusak di localStorage tidak merusak halaman
    var o = salin(DEF), l = p.lokasi || {}, s = p.salat || {};
    var lat = parseFloat(l.lat), lon = parseFloat(l.lon), el = parseFloat(l.elev), tz = (l.tz === null || l.tz === '' || l.tz === undefined) ? null : parseFloat(l.tz);
    if (isFinite(lat) && lat >= -90 && lat <= 90 && isFinite(lon) && lon >= -180 && lon <= 180) { o.lokasi.lat = lat; o.lokasi.lon = lon; o.lokasi.nama = String(l.nama || '').slice(0, 60); }
    o.lokasi.elev = isFinite(el) && el >= -400 && el <= 9000 ? el : 0;
    o.lokasi.tz = tz !== null && isFinite(tz) && tz >= -12 && tz <= 14 ? tz : null;
    if (typeof s.metode === 'string' && s.metode) o.salat.metode = s.metode;
    var ih = parseInt(s.ihtiyat, 10), im = parseInt(s.imsak, 10);
    o.salat.ihtiyat = isFinite(ih) && ih >= 0 && ih <= 10 ? ih : 2;
    o.salat.imsak = isFinite(im) && im >= 0 && im <= 60 ? im : 10;
    if (p.hijriah && NAMA_KRITERIA[p.hijriah.kriteria]) o.hijriah.kriteria = p.hijriah.kriteria;
    return o;
  }
  function baca() {
    var raw = null;
    try { raw = JSON.parse(g.localStorage.getItem(KEY) || 'null'); } catch (e) {}
    if (!raw) {                                    // pertama kali: ambil lokasi terakhir dari halaman Katalog lama bila ada
      try {
        var k = JSON.parse(g.localStorage.getItem('astrolife.catalog.v3') || 'null');
        if (k && isFinite(parseFloat(k.lat)) && isFinite(parseFloat(k.lon))) raw = { lokasi: { nama: '', lat: k.lat, lon: k.lon } };
      } catch (e) {}
    }
    return bersihkan(raw || {});
  }
  var cache = baca();
  function nama() {                                // nama kota: dari pilihan, atau dari daftar bila koordinat cocok
    var l = cache.lokasi;
    if (l.nama) return l.nama;
    for (var i = 0; i < KOTA.length; i++) if (Math.abs(KOTA[i][1] - l.lat) < 0.002 && Math.abs(KOTA[i][2] - l.lon) < 0.002) return KOTA[i][0];
    return 'Koordinat sendiri';
  }
  function siarkan(berubah) {
    isi();
    g.document.dispatchEvent(new CustomEvent('astrolife:prefs', { detail: { prefs: cache, berubah: berubah } }));
  }
  function bandingkan(a, b) {
    return Object.keys(a).filter(function (k) { return JSON.stringify(a[k]) !== JSON.stringify(b[k]); });
  }
  function set(patch) {
    var lama = cache, baru = bersihkan(gabung(salin(cache), patch));
    var ber = bandingkan(lama, baru);
    cache = baru;
    try { g.localStorage.setItem(KEY, JSON.stringify(cache)); } catch (e) {}
    if (ber.length) siarkan(ber);
    return cache;
  }
  function reset() { cache = salin(DEF); try { g.localStorage.removeItem(KEY); } catch (e) {} siarkan(['lokasi', 'salat', 'hijriah']); }

  g.addEventListener('storage', function (e) {     // perubahan dari tab lain
    if (e.key !== KEY && e.key !== null) return;
    var lama = cache; cache = baca(); var ber = bandingkan(lama, cache);
    if (ber.length) siarkan(ber);
  });

  /* Query lokasi untuk API (lat, lon, elev, tz) */
  function qsLokasi() {
    var l = cache.lokasi, q = new URLSearchParams({ lat: l.lat, lon: l.lon, elev: l.elev || 0 });
    if (l.tz !== null) q.set('tz', l.tz);
    return q;
  }
  function ringkas() {
    var l = cache.lokasi, tz = l.tz !== null ? l.tz : tzDariBujur(l.lon);
    return {
      lokasi: nama(),
      koordinat: Math.abs(l.lat).toFixed(2) + '°' + (l.lat < 0 ? 'S' : 'N') + ', ' + Math.abs(l.lon).toFixed(2) + '°' + (l.lon >= 0 ? 'E' : 'W'),
      zona: labelTz(tz), hijriah: NAMA_KRITERIA[cache.hijriah.kriteria]
    };
  }
  /* Isi elemen penanda: <span data-pref="lokasi|koordinat|zona|hijriah|ringkas"> */
  function isi() {
    var r = ringkas();
    r.ringkas = r.lokasi + ' · ' + r.hijriah;
    g.document.querySelectorAll('[data-pref]').forEach(function (el) { var v = r[el.dataset.pref]; if (v !== undefined) el.textContent = v; });
  }

  g.AstroPrefs = {
    get: function () { return cache; }, set: set, reset: reset, qsLokasi: qsLokasi, ringkas: ringkas, isi: isi,
    kota: KOTA, namaKriteria: NAMA_KRITERIA, tzDariBujur: tzDariBujur, labelTz: labelTz, nama: nama
  };
  if (g.document.readyState === 'loading') g.document.addEventListener('DOMContentLoaded', isi); else isi();
})(window);
