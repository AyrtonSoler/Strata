# Isometric strata slabs: a top face plus two side faces per slab.
def slab(cx, y, w, h, t, top, left, right):
    # rhombus top: (cx,y) (cx+w,y+h) (cx,y+2h) (cx-w,y+h); thickness t
    T = f"M{cx} {y} L{cx+w} {y+h} L{cx} {y+2*h} L{cx-w} {y+h} Z"
    L = f"M{cx-w} {y+h} L{cx} {y+2*h} L{cx} {y+2*h+t} L{cx-w} {y+h+t} Z"
    R = f"M{cx+w} {y+h} L{cx} {y+2*h} L{cx} {y+2*h+t} L{cx+w} {y+h+t} Z"
    j = 'stroke-linejoin="round"'
    return (f'<path d="{L}" fill="{left}" stroke="{left}" stroke-width="1.2" {j}/>'
            f'<path d="{R}" fill="{right}" stroke="{right}" stroke-width="1.2" {j}/>'
            f'<path d="{T}" fill="{top}" stroke="{top}" stroke-width="1.2" {j}/>')

INK = ("#3a3a3c", "#1d1d1f", "#000000")
IND = ("#7d7bf0", "#4a48c4", "#3b39a8")
TEAL = ("#22c3b2", "#08897c", "#06705f")

def mark(dot=False, gap=6.2):
    w, h, t = 12, 6, 2.6
    s = slab(16, 4 + 2 * gap, w, h, t, *INK) + slab(16, 4 + gap, w, h, t, *IND) + slab(16, 4, w, h, t, *TEAL)
    if dot:
        s += '<circle cx="16" cy="10" r="2.2" fill="#fff"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">{s}</svg>'

open("a_slabs.svg", "w").write(mark())
open("b_slabs_dot.svg", "w").write(mark(dot=True))
# C: refined bars with an address dot cut into the top bar
c = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
     '<rect x="2" y="3" width="20" height="5" rx="2.5" fill="#5856d6"/>'
     '<rect x="5" y="9.5" width="17" height="5" rx="2.5" fill="#0a9e8f"/>'
     '<rect x="8" y="16" width="14" height="5" rx="2.5" fill="#1d1d1f"/>'
     '<circle cx="18.5" cy="18.5" r="1.3" fill="#ffd60a"/></svg>')
open("c_bars_dot.svg", "w").write(c)

cards = ""
for f, name in [("current", "Actual"), ("a_slabs", "A · Placas isométricas"), ("b_slabs_dot", "B · Placas + dirección"), ("c_bars_dot", "C · Barras + punto")]:
    src = "../../frontend/public/strata.svg" if f == "current" else f + ".svg"
    cards += f'''<div class="c"><img src="{src}" width="160"><div class="row"><img src="{src}" width="28"><span>Strata</span></div><p>{name}</p></div>'''
open("compare.html", "w", encoding="utf-8").write(f'''<html><body style="margin:0;background:#f5f5f7;font-family:Inter,Segoe UI,sans-serif">
<div style="display:flex;gap:28px;padding:40px">{cards}</div>
<style>.c{{background:#fff;border-radius:24px;padding:32px;display:flex;flex-direction:column;align-items:center;gap:24px;width:260px}}
.row{{display:flex;align-items:center;gap:10px;font-size:24px;font-weight:600}} p{{color:#86868b;margin:0}}</style></body></html>''')
