"""Replay the real self-check output in a terminal-styled page and record it."""
import html
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from capture import OUT, Recorder

HERE = Path(__file__).parent
lines = (HERE / "selfcheck.txt").read_text(encoding="utf-8").splitlines()


def fmt(line: str) -> str:
    s = html.escape(line)
    s = s.replace("[PASS]", '<b class="ok">[PASS]</b>').replace("ALL CHECKS PASS", '<b class="ok">ALL CHECKS PASS</b>')
    if line and not line.startswith(" "):
        s = f'<span class="h">{s}</span>'
    return s


page_html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#f5f5f7;font-family:'JetBrains Mono',Consolas,monospace;height:100vh;display:grid;place-items:center}}
.win{{width:1640px;height:940px;background:#111214;border-radius:22px;box-shadow:0 40px 120px rgba(0,0,0,.35);overflow:hidden;display:flex;flex-direction:column}}
.bar{{height:44px;display:flex;align-items:center;gap:9px;padding:0 18px;background:#1c1d20}}
.dot{{width:13px;height:13px;border-radius:50%}} .t{{color:#8e8e93;font-size:14px;margin-left:16px}}
#out{{flex:1;padding:22px 30px;color:#d1d1d6;font-size:16.5px;line-height:1.42;white-space:pre;overflow:hidden}}
.ok{{color:#30d158}} .h{{color:#fff;font-weight:600}} .p{{color:#64d2ff}} .cur{{display:inline-block;width:9px;height:18px;background:#d1d1d6;vertical-align:-3px}}
</style></head><body><div class="win"><div class="bar"><span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span><span class="dot" style="background:#28c840"></span><span class="t">strata/backend</span></div><div id="out"></div></div>
<script>
const L = {json.dumps([fmt(l) for l in lines])};
const out = document.getElementById('out');
const NL = String.fromCharCode(10);
const cmd = 'uv run python -m pipeline.selfcheck';
window.play = async () => {{
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  out.innerHTML = '<span class="p">$ </span><span id="c"></span><span class="cur"></span>';
  const c = document.getElementById('c');
  for (const ch of cmd) {{ c.textContent += ch; await sleep(45); }}
  await sleep(500);
  out.querySelector('.cur').remove();
  out.innerHTML += NL;
  for (const l of L) {{ out.innerHTML += l + NL; out.scrollTop = out.scrollHeight; await sleep(l.trim() ? 70 : 140); }}
  await sleep(300);
}};
</script></body></html>"""
(HERE / "terminal.html").write_text(page_html, encoding="utf-8")

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2).new_page()
    page.goto((HERE / "terminal.html").as_uri())
    page.wait_for_timeout(500)
    rec = Recorder(page)
    rec.start()
    page.wait_for_timeout(400)
    page.evaluate("play()")
    page.wait_for_timeout(1500)
    rec.stop("r9_selfcheck")
    page.screenshot(path=str(OUT / "s15_selfcheck.png"))
    b.close()
