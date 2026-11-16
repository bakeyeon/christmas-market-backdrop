"""Turn a picture into a braille-dot backdrop scene: dithered white dots on navy, twinkling points on its
brightest spots, and falling snow. Fits the Claude Code backdrop's 131,072-character limit.

Usage:  python to_dots.py <picture.png> <out_scene.js> <out.svg> [cols=560] [rows=158]
Needs:  pip install pillow
To start from an SVG, render it to PNG first, e.g. with headless Chrome:
  chrome --headless=new --hide-scrollbars --window-size=2400,1792 --screenshot=picture.png file:///path/to/drawing.svg
"""
import sys, json, random, html
from PIL import Image, ImageOps, ImageFilter
random.seed(3)
src, out_js, out_svg = sys.argv[1], sys.argv[2], sys.argv[3]
COLS, ROWS = int(sys.argv[4]) if len(sys.argv) > 4 else 560, int(sys.argv[5]) if len(sys.argv) > 5 else 158
W, H = 1280, 720
cw, lh = W / COLS, H / ROWS

im = Image.open(src).convert('RGB')
# crop the 4:3 drawing to 16:9, keeping the tower tops
cw_px = im.width; ch_px = round(cw_px * 9 / 16); y0 = 40
im = im.crop((0, y0, cw_px, y0 + ch_px))
g = im.convert('L')
# stretch: navy background to black, bright lines to white; slight sharpening keeps lines crisp
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
text = ''.join(f'<text y="{(i + 1) * lh:.2f}" textLength="{len(ln) * cw:.1f}">{ln}</text>' for i, ln in enumerate(rows) if ln)

# twinkle points: the brightest small spots of the drawing
sm = im.convert('L').resize((320, 180), Image.LANCZOS)
sp = sm.load()
cands = [(sp[x, y], x, y) for y in range(1, 179) for x in range(1, 319)
         if sp[x, y] > (170 if y < 50 else 120) and sp[x, y] >= max(sp[x + dx, y + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
random.shuffle(cands)
cands.sort(key=lambda t: -t[0])
sky_pts = [c for c in cands if c[2] < 50][:22]            # a few stars
low = [c for c in cands if c[2] >= 50]                     # the town: tree, wheel, garlands, stalls
pts = sky_pts + low[:250]
tw = ''.join(f'<circle class="t{random.randrange(4)}" cx="{x * 4 + 2}" cy="{y * 4 + 2}" r="{random.choice([1.2, 1.6, 2.1])}"/>' for _, x, y in pts)

# snow, with shared timing classes
snow = ''
for layer, (n, rr) in enumerate([(70, 1.1), (44, 1.9), (16, 2.8)]):
    for _ in range(n):
        snow += f'<g class="f{layer}{random.randrange(5)}"><g class="w{random.randrange(4)}"><circle cx="{random.uniform(0, W):.0f}" r="{rr * random.uniform(.8, 1.2):.1f}"/></g></g>'
tcss = ''
for layer, (lo, hi) in enumerate([(16, 24), (11, 16), (8, 11)]):
    for k in range(5):
        du = lo + (hi - lo) * k / 4
        tcss += f'.f{layer}{k}{{animation:fall {du:.1f}s linear infinite;animation-delay:-{du * (k * .37 % 1):.1f}s}}'
for k in range(4):
    tcss += f'.w{k}{{animation:sway {2.5 + k * .8:.1f}s ease-in-out infinite;animation-delay:-{k * .9:.1f}s}}'

css = ("text{font-family:'Segoe UI Symbol','DejaVu Sans','Apple Symbols',monospace;font-size:%.2fpx;fill:#eef0f8;white-space:pre}" % (lh * 1.0) +
       "@keyframes tw{0%,100%{opacity:.1}50%{opacity:1}}.t0{animation:tw 1.6s ease-in-out infinite}.t1{animation:tw 2.3s ease-in-out infinite -.8s}"
       ".t2{animation:tw 2.9s ease-in-out infinite -1.5s}.t3{animation:tw 2s ease-in-out infinite -.4s}"
       "@keyframes fall{from{transform:translateY(-40px)}to{transform:translateY(780px)}}@keyframes sway{0%,100%{transform:translateX(-10px)}50%{transform:translateX(10px)}}" + tcss)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice"><style>{css}</style>'
       '<defs><filter id="bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
       '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#090d24"/><stop offset=".45" stop-color="#151a3d"/><stop offset=".7" stop-color="#231d4a"/><stop offset="1" stop-color="#1a1636"/></linearGradient><radialGradient id="hz" cx=".5" cy=".62" r=".6"><stop offset="0" stop-color="#3a2d6e" stop-opacity=".55"/><stop offset="1" stop-color="#3a2d6e" stop-opacity="0"/></radialGradient></defs>'
       f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#hz)"/><g lengthAdjust="spacingAndGlyphs">{text}</g>'
       f'<g fill="#fff4d6" filter="url(#bl)">{tw}</g><g fill="#fff" opacity=".85">{snow}</g></svg>')
# lengthAdjust must sit on each <text>; add it via a CSS-free attribute rewrite
svg = svg.replace('<text y=', '<text lengthAdjust="spacingAndGlyphs" y=')
print(len(svg), 'rows', len(rows), 'twinkles', len(pts))
open(out_svg, 'w', encoding='utf-8').write(svg)
open(out_js, 'w', encoding='utf-8').write("// Generated: a picture as braille dots, with twinkles and snow.\nexport const SCENE = " + json.dumps(svg) + '\n')
