"""Render real source excerpts from the repo as editor-style stills (1920x1080 @2x)."""
from pathlib import Path

from playwright.sync_api import sync_playwright
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).parent / "shots"
SHOTS = [
    ("c1_llm", "backend/pipeline/llm.py", 70, 84, [76, 81, 82]),
    ("c2_bm25", "backend/pipeline/retrieve.py", 67, 91, [84]),
    ("c3_verify", "backend/pipeline/textmatch.py", 15, 39, [17, 18, 37, 38, 39]),
    ("c4_engine", "backend/pipeline/engine.py", 60, 82, [69, 72, 76]),
]
CSS = """
body{margin:0;height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 30% 20%,#2a2a40,#0d0d12 70%);font-family:'JetBrains Mono',Consolas,monospace}
.win{width:1820px;background:#15161b;border-radius:22px;box-shadow:0 40px 120px rgba(0,0,0,.55);overflow:hidden;border:1px solid #2a2b33}
.bar{height:46px;display:flex;align-items:center;gap:9px;padding:0 18px;background:#1d1e24;color:#8e8e93;font-size:15px}
.dot{width:13px;height:13px;border-radius:50%}
.highlight{background:transparent!important}.highlight pre{margin:0;padding:22px 30px 22px 0;font-size:25px;line-height:1.48;color:#e6edf3;white-space:pre;overflow:hidden}
.linenos{color:#4b4d57;padding:0 20px 0 26px!important}.hll{background:rgba(94,230,214,.12)!important;display:block}
table.highlighttable{border-spacing:0}td.linenos .normal{color:#4b4d57}
"""
fmt_style = "github-dark"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
    for name, path, a, z, hl in SHOTS:
        code = "\n".join((ROOT / path).read_text(encoding="utf-8").splitlines()[a - 1:z])
        f = HtmlFormatter(style=fmt_style, linenos="table", linenostart=a, hl_lines=[n - a + 1 for n in hl], cssclass="highlight")
        page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{f.get_style_defs('.highlight')}{CSS}</style></head>
<body><div class="win"><div class="bar"><span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span><span class="dot" style="background:#28c840"></span><span style="margin-left:16px">{path}</span></div>{highlight(code, PythonLexer(stripnl=False), f)}</div></body></html>"""
        pg.set_content(page); pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        print("saved", name)
    b.close()
