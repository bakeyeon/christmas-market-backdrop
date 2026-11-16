"""Picture -> line-art SVG: bright strokes thinned to centre lines, drawn as yellow-to-orange strokes over an orange-to-purple gradient sky,
twinkling points and falling snow. Unlike to_lineart.py (Canny),
it traces the centre of each drawn stroke, which suits dense line drawings. Keeps the picture's own aspect.
Needs: pip install opencv-python numpy

Usage:  python to_lineart_orange_purple.py <picture> <out.svg> [line_budget=107000]
"""
import sys, random
import cv2
import numpy as np
random.seed(3)
src, out_svg = sys.argv[1], sys.argv[2]
BUDGET = int(sys.argv[3]) if len(sys.argv) > 3 else 107_000

img = cv2.imread(src)
h0, w0 = img.shape[:2]
W = 1500
H = round(W * h0 / w0)                     # keep the picture's own aspect (no crop)
img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# The source is already a line drawing (bright strokes on a dark sky), so instead of Canny (which outlines
# both sides of every stroke) pick out the bright strokes at 2x and thin them to 1px centre lines.
S = 2
big = cv2.resize(cv2.cvtColor(cv2.imread(src), cv2.COLOR_BGR2GRAY), (W * S, H * S), interpolation=cv2.INTER_CUBIC)
local = cv2.GaussianBlur(big, (0, 0), 6)
mask = ((big.astype(int) > local.astype(int) + 10) & (big > 50)).astype(np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

def thin(img):  # Zhang-Suen thinning
    img = img.copy()
    while True:
        changed = False
        for step in (0, 1):
            P = np.pad(img, 1)
            p2, p3, p4, p5 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:], P[2:, 2:]
            p6, p7, p8, p9 = P[2:, 1:-1], P[2:, :-2], P[1:-1, :-2], P[:-2, :-2]
            nb = [p2, p3, p4, p5, p6, p7, p8, p9]
            B = sum(n.astype(int) for n in nb)
            A = sum(((nb[i] == 0) & (nb[(i + 1) % 8] == 1)).astype(int) for i in range(8))
            c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0) if step == 0 else (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            rm = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if rm.any():
                img[rm] = 0; changed = True
        if not changed:
            return img

sk = thin(mask)
ys, xs = np.nonzero(sk)
on = set(zip(ys.tolist(), xs.tolist()))
N8 = [(-1, 0), (0, 1), (1, 0), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)]
nbrs = lambda p: [(p[0] + dy, p[1] + dx) for dy, dx in N8 if (p[0] + dy, p[1] + dx) in on]
seen = set()
def walk(start):
    # follow unvisited pixels; at a junction keep going in the straightest direction, so strokes stay long
    path = [start]; seen.add(start)
    while True:
        cur = path[-1]
        ns = [n for n in nbrs(cur) if n not in seen]
        if not ns:
            return path
        if len(path) > 1:
            back = path[max(0, len(path) - 5)]
            dy, dx = cur[0] - back[0], cur[1] - back[1]
            ns.sort(key=lambda n: -((n[0] - cur[0]) * dy + (n[1] - cur[1]) * dx) / (abs(n[0] - cur[0]) + abs(n[1] - cur[1])) ** .5)
        nx = ns[0]; seen.add(nx); path.append(nx)
contours = []
order = sorted(on, key=lambda p: (len(nbrs(p)) != 1, p))   # start at stroke ends first, then whatever is left
for p in order:
    if p not in seen:
        pts = walk(p)
        if len(pts) > 1:
            contours.append((np.array([[x, y] for y, x in pts], np.float32) / S).reshape(-1, 1, 2))
print('skeleton px', len(on), 'strokes', len(contours))

def encode(eps, min_len):
    parts, kept = [], 0
    for c in contours:
        if cv2.arcLength(c, False) < min_len:
            continue
        a = np.rint(cv2.approxPolyDP(c, eps, False).reshape(-1, 2)).astype(int)
        if len(a) < 2:
            continue
        x, y = int(a[0][0]), int(a[0][1])
        d = f'M{x} {y}l'
        for px, py in a[1:]:
            px, py = int(px), int(py)
            if (px, py) == (x, y):
                continue
            d += f'{px - x} {py - y} '
            x, y = px, py
        if d.endswith('l'):
            continue
        parts.append(d.rstrip().replace(' -', '-'))
        kept += 1
    return ''.join(parts), kept

for eps, min_len in [(0.5, 4), (0.6, 6), (0.7, 8), (0.8, 10), (0.8, 12), (0.9, 12), (0.9, 13), (1.0, 14), (1.2, 18), (1.4, 22), (1.6, 28), (1.9, 34)]:
    d, kept = encode(eps, min_len)
    print(f'eps {eps} min_len {min_len}: {kept} lines, {len(d)} chars')
    if len(d) <= BUDGET:
        break

# twinkles
SW, SH = 320, round(320 * H / W)
sx, sy = W / SW, H / SH
sky = round(SH * .28)
sm = cv2.resize(gray, (SW, SH), interpolation=cv2.INTER_AREA)
cands = []
for yy in range(1, SH - 1):
    for xx in range(1, SW - 1):
        v = int(sm[yy, xx])
        if v > (170 if yy < sky else 120) and v >= sm[yy - 1:yy + 2, xx - 1:xx + 2].max():
            cands.append((v, xx, yy))
random.shuffle(cands); cands.sort(key=lambda t: -t[0])
pts = [c for c in cands if c[2] < sky][:24] + [c for c in cands if c[2] >= sky][:250]
tw = ''.join(f'<circle class="t{random.randrange(4)}" cx="{(x + .5) * sx:.0f}" cy="{(y + .5) * sy:.0f}" r="{random.choice([1.2, 1.6, 2.1])}"/>' for _, x, y in pts)

snow = ''
for layer, (n, rr) in enumerate([(80, 1.1), (50, 1.9), (18, 2.8)]):
    for _ in range(n):
        snow += f'<g class="f{layer}{random.randrange(5)}"><g class="w{random.randrange(4)}"><circle cx="{random.uniform(0, W):.0f}" r="{rr * random.uniform(.8, 1.2):.1f}"/></g></g>'
tcss = ''
for layer, (lo, hi) in enumerate([(16, 24), (11, 16), (8, 11)]):
    for kk in range(5):
        du = lo + (hi - lo) * kk / 4
        tcss += f'.f{layer}{kk}{{animation:fall {du:.1f}s linear infinite;animation-delay:-{du * (kk * .37 % 1):.1f}s}}'
for kk in range(4):
    tcss += f'.w{kk}{{animation:sway {2.5 + kk * .8:.1f}s ease-in-out infinite;animation-delay:-{kk * .9:.1f}s}}'
css = ("@keyframes tw{0%,100%{opacity:.1}50%{opacity:1}}.t0{animation:tw 1.6s ease-in-out infinite}.t1{animation:tw 2.3s ease-in-out infinite -.8s}"
       ".t2{animation:tw 2.9s ease-in-out infinite -1.5s}.t3{animation:tw 2s ease-in-out infinite -.4s}"
       f"@keyframes fall{{from{{transform:translateY(-40px)}}to{{transform:translateY({H + 60}px)}}}}@keyframes sway{{0%,100%{{transform:translateX(-10px)}}50%{{transform:translateX(10px)}}}}" + tcss)

# same palette as the dot version
BG = [(0, '#160a2e'), (.3, '#341458'), (.52, '#561e6c'), (.72, '#80285a'), (.88, '#a13a26'), (1, '#b8501c')]
LN = [(0, '#ff9a1f'), (.35, '#ffc23d'), (.65, '#ffe86b'), (1, '#ffa02a')]
st = lambda S: ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in S)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice"><style>{css}</style>'
       '<defs><filter id="bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
       '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
       f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">{st(BG)}</linearGradient>'
       f'<linearGradient id="ln" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="260" y2="70" spreadMethod="reflect">{st(LN)}</linearGradient></defs>'
       f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
       f'<path d="{d}" fill="none" stroke="url(#ln)" stroke-width=".85" stroke-opacity=".95" stroke-linecap="round" stroke-linejoin="round"/>'
       f'<g fill="#fff3b0" filter="url(#bl)">{tw}</g><g fill="#fff" opacity=".8">{snow}</g></svg>')
print('total', len(svg))
open(out_svg, 'w', encoding='utf-8').write(svg)
