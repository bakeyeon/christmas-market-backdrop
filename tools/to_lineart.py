"""Turn a picture into a white line-art backdrop scene: Canny edges (30/100) -> contours -> SVG paths,
simplified until it fits the Claude Code backdrop's 131,072-character limit, plus twinkles and snow.

Usage:  python to_lineart.py <picture.png> <out_scene.js> <out.svg> [line_budget=100000]
Needs:  pip install opencv-python numpy
"""
import sys, json, random
import cv2
import numpy as np
random.seed(3)
src, out_js, out_svg = sys.argv[1], sys.argv[2], sys.argv[3]
BUDGET = int(sys.argv[4]) if len(sys.argv) > 4 else 100_000
W, H = 1280, 720

img = cv2.imread(src)
h0, w0 = img.shape[:2]
ch = round(w0 * 9 / 16); y0 = 40
img = cv2.resize(img[y0:y0 + ch], (W, H), interpolation=cv2.INTER_AREA)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Canny edges, then a light close to join broken strokes
edges = cv2.Canny(gray, 30, 100)
k = np.ones((2, 2), np.uint8)
edges = cv2.erode(cv2.dilate(edges, k, iterations=1), k, iterations=1)
contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

def encode(eps, min_len):
    parts, kept = [], 0
    for c in contours:
        if cv2.arcLength(c, False) < min_len:
            continue
        a = cv2.approxPolyDP(c, eps, False).reshape(-1, 2)
        if len(a) < 2:
            continue
        x, y = int(a[0][0]), int(a[0][1])
        d = f'M{x} {y}l'
        for px, py in a[1:]:
            px, py = int(px), int(py)
            d += f'{px - x} {py - y} '
            x, y = px, py
        parts.append(d.rstrip().replace(' -', '-'))
        kept += 1
    return ''.join(parts), kept

# loosen simplification until the line data fits
for eps, min_len in [(0.8, 10), (1.0, 14), (1.2, 18), (1.4, 22), (1.6, 28), (1.9, 34), (2.2, 42), (2.6, 52)]:
    d, kept = encode(eps, min_len)
    print(f'eps {eps} min_len {min_len}: {kept} lines, {len(d)} chars')
    if len(d) <= BUDGET:
        break

# twinkles on the brightest spots (a few stars, most on the town's lights)
sm = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
cands = []
for yy in range(1, 179):
    for xx in range(1, 319):
        v = int(sm[yy, xx])
        if v > (170 if yy < 50 else 120) and v >= sm[yy - 1:yy + 2, xx - 1:xx + 2].max():
            cands.append((v, xx, yy))
random.shuffle(cands); cands.sort(key=lambda t: -t[0])
pts = [c for c in cands if c[2] < 50][:22] + [c for c in cands if c[2] >= 50][:250]
tw = ''.join(f'<circle class="t{random.randrange(4)}" cx="{x * 4 + 2}" cy="{y * 4 + 2}" r="{random.choice([1.2, 1.6, 2.1])}"/>' for _, x, y in pts)

snow = ''
for layer, (n, rr) in enumerate([(70, 1.1), (44, 1.9), (16, 2.8)]):
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
       "@keyframes fall{from{transform:translateY(-40px)}to{transform:translateY(780px)}}@keyframes sway{0%,100%{transform:translateX(-10px)}50%{transform:translateX(10px)}}" + tcss)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice"><style>{css}</style>'
       '<defs><filter id="bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
       '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
       f'<rect width="{W}" height="{H}" fill="#121620"/>'
       f'<path d="{d}" fill="none" stroke="#fff" stroke-width=".8" stroke-opacity=".9" stroke-linecap="round" stroke-linejoin="round"/>'
       f'<g fill="#fff4d6" filter="url(#bl)">{tw}</g><g fill="#fff" opacity=".85">{snow}</g></svg>')
print('total', len(svg))
open(out_svg, 'w', encoding='utf-8').write(svg)
open(out_js, 'w', encoding='utf-8').write("// Generated: Canny line art of a picture, with twinkles and snow.\nexport const SCENE = " + json.dumps(svg) + '\n')
