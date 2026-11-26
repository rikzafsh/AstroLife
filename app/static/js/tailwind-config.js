/* Konfigurasi Tailwind (CDN) bersama untuk seluruh halaman AstroLife.
   Warna memakai variabel CSS (theme-palette.css & theme.css) sehingga mode terang/gelap berganti tanpa mengubah kelas.
   Palet utama: 001f8e, 2a35e2, 29aafe, ed2124, 009339. */
(function (g) {
  const SH = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
  const fam = (p) => Object.fromEntries(SH.map((s) => [s, `rgb(var(--${p}-${s}) / <alpha-value>)`]));
  const pri = fam('pri'), deep = fam('deep'), sky = fam('sky'), red = fam('red'), grn = fam('grn'), amb = fam('amb');
  const sl = Object.fromEntries(SH.map((s) => [s, `rgb(var(--sl-${s}) / <alpha-value>)`]));
  g.tailwind = g.tailwind || {};
  g.tailwind.config = {
    darkMode: 'class',
    theme: {
      extend: {
        fontFamily: { sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'], display: ['"Space Grotesk"', '"Plus Jakarta Sans"', 'sans-serif'] },
        colors: {
          slate: sl, gray: sl, zinc: sl, neutral: sl, stone: sl,
          indigo: pri, blue: pri, violet: deep, purple: deep, fuchsia: deep,
          cyan: sky, sky: sky, teal: sky, rose: red, red: red, pink: red,
          emerald: grn, green: grn, amber: amb, yellow: amb, orange: amb,
          ink: 'rgb(var(--ink) / <alpha-value>)',
          brand: { deep: '#001f8e', blue: '#2a35e2', sky: '#29aafe', red: '#ed2124', green: '#009339' },
          space: { 950: sl[950], 900: sl[900], 850: sl[900], 800: sl[800], 700: sl[700], accent: pri[500], cyan: sky[500], gold: amb[500], emerald: grn[500] },
        },
      },
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
