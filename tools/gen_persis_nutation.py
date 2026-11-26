"""Menghasilkan app/persis/nutation_tables.py dari js/core/nutation.js (persis-times-js).
Pemakaian: python tools/gen_persis_nutation.py <folder persis-times-js> """
import re, sys, pathlib

src = pathlib.Path(sys.argv[1], 'js/core/nutation.js').read_text(encoding='utf8')
NUM = r'([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)'
ARG = r'([-+\d\s*lpfdom]+)'
pat = re.compile(
    r's\s*\+=\s*\(\s*' + NUM + r'\s*\+\s*' + NUM + r'\s*\*\s*t\s*\)\s*\*\s*Math\.(sin|cos)\(([^)]*)\)\s*\+\s*' +
    NUM + r'\s*\*\s*Math\.(sin|cos)\(([^)]*)\)\s*;')
def parse_arg(a):
    m = re.fullmatch(r'\s*(-?\d+) \* l \+ (-?\d+) \* lp \+ (-?\d+) \* f \+ (-?\d+) \* d \+ (-?\d+) \* om\s*', a)
    return tuple(int(x) for x in m.groups())

def section(name_start, name_end):
    i = src.index(name_start); j = src.index(name_end, i)
    return src[i:j]
psi = section('nutationInLongitude(jd', 'nutationInObliquity(jd')
eps = section('nutationInObliquity(jd', 'meanObliquityOfEcliptic(jd')
def terms(txt, f1, f2):
    out = []
    for m in pat.finditer(txt):
        a, b, fn1, arg1, c, fn2, arg2 = m.groups()
        assert fn1 == f1 and fn2 == f2 and parse_arg(arg1) == parse_arg(arg2), m.group(0)
        out.append((parse_arg(arg1), float(a), float(b), float(c)))
    return out
tp = terms(psi, 'sin', 'cos'); te = terms(eps, 'cos', 'sin')
assert len(tp) == 77 and len(te) == 77, (len(tp), len(te))
o = ['"""Tabel nutasi IAU 1980 (77 suku) - DIHASILKAN oleh tools/gen_persis_nutation.py dari nutation.js; jangan disunting.',
     'Format: ((l, lp, f, d, om), A, B, C) dalam satuan 0,0001 detik busur.',
     'Δψ = Σ [(A + B·t)·sin(arg) + C·cos(arg)] ; Δε = Σ [(A + B·t)·cos(arg) + C·sin(arg)]."""', '']
for nm, t in (('PSI_TERMS', tp), ('EPS_TERMS', te)):
    o.append(nm + ' = (')
    for r in t: o.append('    (%r, %r, %r, %r),' % r)
    o.append(')'); o.append('')
pathlib.Path('app/persis/nutation_tables.py').write_text('\n'.join(o), encoding='utf8')
print('ok', len(tp), len(te))
