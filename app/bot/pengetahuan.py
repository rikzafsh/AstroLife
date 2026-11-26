"""Basis pengetahuan: artikel Markdown di app/bot/kb (+ data/knowledge_base buatan pengguna) dan pencarian BM25."""
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .teks import token

KB_DIR = Path(__file__).resolve().parent / 'kb'
BOBOT = {'judul': 4.0, 'kata_kunci': 3.0, 'ringkas': 2.0, 'isi': 1.0}
K1, B = 1.4, 0.75


def _parse(path: Path) -> dict | None:
    raw = path.read_text(encoding='utf8')
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', raw, re.S)
    if not m:
        return None
    meta = {}
    for ln in m.group(1).splitlines():
        if ':' in ln:
            k, v = ln.split(':', 1)
            meta[k.strip()] = v.strip()
    isi = m.group(2).strip()
    return {'id': path.stem, 'judul': meta.get('judul', path.stem), 'kategori': meta.get('kategori', 'Umum'),
            'kata_kunci': [x.strip() for x in meta.get('kata_kunci', '').split(',') if x.strip()],
            'ringkas': meta.get('ringkas', ''), 'tautan': meta.get('tautan', ''), 'isi': isi}


class Basis:
    def __init__(self, folder_tambahan: Path | None = None):
        self.artikel = {}
        for d in [KB_DIR] + ([folder_tambahan] if folder_tambahan and folder_tambahan.is_dir() else []):
            for p in sorted(d.glob('*.md')):
                a = _parse(p)
                if a:
                    self.artikel[a['id']] = a
        self._bangun()

    def _bangun(self):
        self.dok = []                                  # satu dokumen = satu artikel (bidang berbobot)
        for a in self.artikel.values():
            tf = Counter()
            for bidang, teks in (('judul', a['judul']), ('kata_kunci', ' '.join(a['kata_kunci'])), ('ringkas', a['ringkas']), ('isi', a['isi'])):
                for t in token(teks):
                    tf[t] += BOBOT[bidang]
            self.dok.append((a['id'], tf, sum(tf.values())))
        n = len(self.dok)
        df = Counter(t for _, tf, _ in self.dok for t in tf)
        self.idf = {t: math.log(1 + (n - c + .5) / (c + .5)) for t, c in df.items()}
        self.avg = sum(l for _, _, l in self.dok) / max(n, 1)

    def cari(self, q: str, k: int = 3) -> list[tuple[float, dict]]:
        qt = token(q)
        if not qt:
            return []
        hasil = []
        for aid, tf, dl in self.dok:
            s = 0.0
            for t in set(qt):
                f = tf.get(t)
                if f:
                    s += self.idf.get(t, 0) * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / self.avg))
            if s > 0:
                hasil.append((s, self.artikel[aid]))
        hasil.sort(key=lambda x: -x[0])
        return hasil[:k]

    def potongan(self, a: dict, q: str, maks: int = 700) -> str:
        """Bagian artikel yang paling relevan dengan pertanyaan (per bagian '## ...'), dipangkas bila panjang."""
        bagian = re.split(r'\n(?=## )', a['isi'])
        qt = set(token(q))
        def skor(b):
            return sum(1 for t in token(b) if t in qt)
        terbaik = max(bagian, key=skor) if len(bagian) > 1 and any(skor(b) for b in bagian) else bagian[0]
        if len(a['isi']) <= maks:
            return a['isi']
        if len(terbaik) > maks:
            terbaik = terbaik[:maks].rsplit('\n', 1)[0]
        return terbaik


@lru_cache(maxsize=1)
def basis(folder: str | None = None) -> Basis:
    return Basis(Path(folder) if folder else None)
