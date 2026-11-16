"""Picture -> braille-dot SVG: yellow-to-orange dots over an orange-to-purple gradient sky,
twinkling points on the brightest spots, falling snow. A variant of to_dots.py that keeps the picture's own aspect.
Needs: pip install pillow

Usage:  python to_dots_orange_purple.py <picture> <out.svg> [cols] [rows]
"""
import sys, random
from PIL import Image, ImageFilter
random.seed(3)
src, out_svg = sys.argv[1], sys.argv[2]

im = Image.open(src).convert('RGB')
W = 1500
H = round(W * im.height / im.width)          # keep the picture's own aspect (no crop)
COLS = int(sys.argv[3]) if len(sys.argv) > 3 else 656
ROWS = int(sys.argv[4]) if len(sys.argv) > 4 else round(H / (720 / 158))
cw, lh = W / COLS, H / ROWS

g = im.convert('L')
g = g.point(lambda v: 0 if v < 34 else min(255, int(((v - 34) / 190) ** .8 * 255)))
g = g.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))
dots = g.resize((COLS * 2, ROWS * 4), Image.LANCZOS).convert('1')  # Floyd-Steinberg dither
px = dots.load()
BITS = [((0, 0), 0x01), ((0, 1), 0x02), ((0, 2), 0x04), ((1, 0), 0x08), ((1, 1), 0x10), ((1, 2), 0x20), ((0, 3), 0x40), ((1, 3), 0x80)]
rows = []
for r in range(ROWS):
    line = []
    for c in range(COLS):
        b = 0
        for (dx, dy), bit in BITS:
            if px[c * 2 + dx, r * 4 + dy]:
                b |= bit
        line.append(chr(0x2800 + b))
    rows.append(''.join(line).rstrip('⠀'))
text = ''.join(f'<text lengthAdjust="spacingAndGlyphs" class="g{random.randrange(3)}" y="{(i + 1) * lh:.2f}" textLength="{len(ln) * cw:.1f}">{ln}</text>'
               for i, ln in enumerate(rows) if ln)

# twinkle points
SW, SH = 320, round(320 * H / W)
sx, sy = W / SW, H / SH
sky = round(SH * .28)
sm = im.convert('L').resize((SW, SH), Image.LANCZOS)
sp = sm.load()
cands = [(sp[x, y], x, y) for y in range(1, SH - 1) for x in range(1, SW - 1)
         if sp[x, y] > (170 if y < sky else 120) and sp[x, y] >= max(sp[x + dx, y + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
random.shuffle(cands)
cands.sort(key=lambda t: -t[0])
pts = [c for c in cands if c[2] < sky][:24] + [c for c in cands if c[2] >= sky][:250]
tw = ''.join(f'<circle class="t{random.randrange(4)}" cx="{(x + .5) * sx:.0f}" cy="{(y + .5) * sy:.0f}" r="{random.choice([1.2, 1.6, 2.1])}"/>' for _, x, y in pts)

# snow
snow = ''
for layer, (n, rr) in enumerate([(80, 1.1), (50, 1.9), (18, 2.8)]):
    for _ in range(n):
        snow += f'<g class="f{layer}{random.randrange(5)}"><g class="w{random.randrange(4)}"><circle cx="{random.uniform(0, W):.0f}" r="{rr * random.uniform(.8, 1.2):.1f}"/></g></g>'
tcss = ''
for layer, (lo, hi) in enumerate([(16, 24), (11, 16), (8, 11)]):
    for k in range(5):
        du = lo + (hi - lo) * k / 4
        tcss += f'.f{layer}{k}{{animation:fall {du:.1f}s linear infinite;animation-delay:-{du * (k * .37 % 1):.1f}s}}'
for k in range(4):
    tcss += f'.w{k}{{animation:sway {2.5 + k * .8:.1f}s ease-in-out infinite;animation-delay:-{k * .9:.1f}s}}'

css = ("text{font-family:'Segoe UI Symbol','DejaVu Sans','Apple Symbols',monospace;font-size:%.2fpx;white-space:pre}.g0{fill:url(#d0)}.g1{fill:url(#d1)}.g2{fill:url(#d2)}" % lh +
       "@keyframes tw{0%,100%{opacity:.1}50%{opacity:1}}.t0{animation:tw 1.6s ease-in-out infinite}.t1{animation:tw 2.3s ease-in-out infinite -.8s}"
       ".t2{animation:tw 2.9s ease-in-out infinite -1.5s}.t3{animation:tw 2s ease-in-out infinite -.4s}"
       f"@keyframes fall{{from{{transform:translateY(-40px)}}to{{transform:translateY({H + 60}px)}}}}@keyframes sway{{0%,100%{{transform:translateX(-10px)}}50%{{transform:translateX(10px)}}}}" + tcss)

# background: deep purple at the top of the sky -> violet -> magenta -> burnt orange at the bottom
BG = [(0, '#160a2e'), (.3, '#341458'), (.52, '#561e6c'), (.72, '#80285a'), (.88, '#a13a26'), (1, '#b8501c')]
bg = ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in BG)
# dots: yellow <-> orange, three gradients so neighbouring rows shimmer differently
D0 = [(0, '#ff9a1f'), (.5, '#ffc23d'), (1, '#ffe86b')]
D1 = [(0, '#ffe45c'), (.55, '#ffb22e'), (1, '#ff8a1a')]
D2 = [(0, '#ffd04a'), (.5, '#fff08a'), (1, '#ffa02a')]
st = lambda S: ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in S)
defs = ('<defs><filter id="bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">{bg}</linearGradient>'
        f'<linearGradient id="d0" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="170" y2="50" spreadMethod="reflect">{st(D0)}</linearGradient>'
        f'<linearGradient id="d1" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="-120" y2="90" spreadMethod="reflect">{st(D1)}</linearGradient>'
        f'<linearGradient id="d2" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="240" y2="-40" spreadMethod="reflect">{st(D2)}</linearGradient></defs>')
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice"><style>{css}</style>{defs}'
       f'<rect width="{W}" height="{H}" fill="url(#bg)"/><g>{text}</g>'
       f'<g fill="#fff3b0" filter="url(#bl)">{tw}</g><g fill="#fff" opacity=".8">{snow}</g></svg>')
open(out_svg, 'w', encoding='utf-8').write(svg)
print(len(svg), 'chars', W, 'x', H, 'cols', COLS, 'rows', ROWS, 'twinkles', len(pts))
