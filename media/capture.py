"""Capture real stills and screen recordings of the Strata app for the videos.

Stills: 1920x1080 @2x PNG. Recordings: CDP screencast frames -> 30 fps H.264 (1920x1080).
Usage: uv run --with playwright --with imageio-ffmpeg python media/capture.py [job ...]
"""
import base64
import time
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

BASE = os.environ.get("STRATA_URL", "http://localhost:5173")
OUT = Path(__file__).parent / "shots"
REC = Path(__file__).parent / "rec"
OUT.mkdir(exist_ok=True)
REC.mkdir(exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


class Recorder:
    """Collects screencast frames with timestamps and encodes them at a constant 30 fps."""

    def __init__(self, page):
        self.cdp = page.context.new_cdp_session(page)
        self.frames: list[tuple[float, bytes]] = []
        self.cdp.on("Page.screencastFrame", self._on_frame)

    def _on_frame(self, ev):
        self.frames.append((ev["metadata"]["timestamp"], base64.b64decode(ev["data"])))
        self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

    def start(self):
        self.frames.clear()
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 95, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1})

    def stop(self, name):
        self.cdp.send("Page.stopScreencast")
        frames = self.frames
        tail = max(0.5, time.time() - frames[-1][0]) if frames else 0.5
        if len(frames) < 2:
            print("FAILED", name, "no frames")
            return
        with tempfile.TemporaryDirectory() as tmp:
            lines = []
            for i, (ts, data) in enumerate(frames):
                f = Path(tmp) / f"{i:05d}.jpg"
                f.write_bytes(data)
                dur = (frames[i + 1][0] - ts) if i + 1 < len(frames) else tail
                lines += [f"file '{f.as_posix()}'", f"duration {max(dur, 0.001):.4f}"]
            lines.append(f"file '{(Path(tmp) / f'{len(frames) - 1:05d}.jpg').as_posix()}'")
            lst = Path(tmp) / "list.txt"
            lst.write_text("\n".join(lines))
            out = REC / f"{name}.mp4"
            subprocess.run(
                [FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                 "-vf", "scale=1920:1080:flags=lanczos,fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "16", "-preset", "slow", str(out)],
                check=True,
            )
        print("saved", out.name, f"{frames[-1][0] - frames[0][0]:.1f}s", len(frames), "frames")


def main(only=None):
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
        page = ctx.new_page()
        rec = Recorder(page)

        def go(path, ms=2500):
            page.goto(BASE + path)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(ms)

        def shot(name):
            page.screenshot(path=str(OUT / f"{name}.png"))
            print("saved", name)

        def scroll_to_text(text, offset=110):
            page.evaluate(
                """([t, off]) => {
                  const el = [...document.querySelectorAll('h2,h3,p,span')].find(e => e.textContent.trim() === t);
                  if (el) window.scrollTo({top: el.getBoundingClientRect().top + scrollY - off, behavior: 'instant'});
                }""",
                [text, offset],
            )
            page.wait_for_timeout(1200)

        def smooth_scroll(dy, ms=1600):
            page.evaluate(
                """([dy, ms]) => new Promise(r => {
                  const y0 = scrollY, t0 = performance.now();
                  const f = t => { const k = Math.min(1, (t - t0) / ms); const e = k < .5 ? 2*k*k : 1 - (-2*k + 2)**2 / 2;
                    scrollTo(0, y0 + dy * e); k < 1 ? requestAnimationFrame(f) : r(); };
                  requestAnimationFrame(f);
                })""",
                [dy, ms],
            )

        jobs = {}

        def job(f):
            jobs[f.__name__] = f
            return f

        # ---------- stills ----------
        @job
        def s01_hero():
            go("/")
            shot("s01_hero")
            for i, y in enumerate([1080, 2160, 3240, 4320]):
                page.evaluate(f"window.scrollTo(0, {y})")
                page.wait_for_timeout(1600)
                shot(f"s01_landing_{i + 1}")

        @job
        def s02_answer():
            go("/?a=A0016", 3500)
            page.evaluate("window.scrollTo(0, 260)")
            page.wait_for_timeout(800)
            shot("s02_answer_top")
            scroll_to_text("Rent increases")
            shot("s03_rent")

        @job
        def s04_evidence():
            go("/?a=A0016", 3500)
            scroll_to_text("Rent increases")
            # Statute evidence: the state rent cap that the SF ordinance supersedes.
            page.evaluate(
                """() => {
                  const bs = [...document.querySelectorAll('button')].filter(b => b.textContent.trim().startsWith('View source'));
                  for (const btn of bs) {
                    let el = btn.parentElement;
                    while (el && el.querySelectorAll('button').length < 40) {
                      const n = [...el.querySelectorAll('button')].filter(b => b.textContent.trim().startsWith('View source')).length;
                      if (n > 1) break;
                      if (el.textContent.includes('California Statewide Rent Cap')) { btn.click(); return; }
                      el = el.parentElement;
                    }
                  }
                }"""
            )
            page.wait_for_timeout(2500)
            shot("s04_evidence")

        @job
        def s05_audit():
            go("/?a=A0016", 3500)
            btn = page.get_by_role("button", name="How we got this answer ↓").first
            btn.click()
            page.wait_for_timeout(1500)
            scroll_to_text("Prohibition on Algorithmic Devices to Set Rents", 60)
            shot("s05_audit")

        @job
        def s06_time():
            for name, q in [
                ("s06_time_ca_before", "date=2025-12-31&lens=algorithmic_rent_setting&region=LA"),
                ("s07_time_ca_after", "date=2026-01-02&lens=algorithmic_rent_setting&region=LA"),
                ("s08_time_nj_2027", "date=2027-07-02&lens=algorithmic_rent_setting&region=NJ"),
            ]:
                go(f"/?tab=time&{q}", 5000)
                page.evaluate("window.scrollTo(0, 400)")
                page.wait_for_timeout(1000)
                shot(name)

        @job
        def s09_rights_es():
            go("/?a=A0016&rights=1&lang=es", 3500)
            shot("s09_rights_es")

        @job
        def s10_whatif():
            go("/?a=A0005", 3500)
            page.evaluate("window.scrollTo(0, 260)")
            page.wait_for_timeout(600)
            shot("s10a_unknown")
            page.get_by_role("button", name="What if…").click()
            page.get_by_placeholder("Year built").last.fill("1960")
            page.get_by_role("button", name="Recalculate").click()
            page.wait_for_timeout(3000)
            shot("s10b_whatif_1960")

        @job
        def s11_oakland():
            go("/?a=OAK07", 3500)
            page.evaluate("window.scrollTo(0, 260)")
            page.wait_for_timeout(600)
            shot("s11_oakland_emeryville")

        @job
        def s12_rules():
            go("/?tab=rules", 3500)
            shot("s12_rules")
            page.evaluate("window.scrollTo(0, 700)")
            page.wait_for_timeout(1500)
            shot("s12b_rules_scrolled")

        @job
        def s13_changes():
            go("/?tab=changes", 3500)
            shot("s13_changes")
            page.evaluate("window.scrollTo(0, 650)")
            page.wait_for_timeout(1500)
            shot("s13b_changes_scrolled")

        @job
        def s14_method():
            go("/?tab=audit", 3500)
            shot("s14_method")
            page.evaluate("window.scrollTo(0, 900)")
            page.wait_for_timeout(1500)
            shot("s14b_method_scrolled")

        # ---------- recordings ----------
        @job
        def r1_search():
            go("/", 2500)
            rec.start()
            page.wait_for_timeout(700)
            box = page.get_by_placeholder("Search 500 properties").first
            box.click()
            box.press_sequentially("3515 Fillmore", delay=90)
            page.wait_for_timeout(900)
            page.get_by_role("button", name="3515 FILLMORE ST").first.click()
            page.wait_for_timeout(2200)
            smooth_scroll(260, 900)
            page.wait_for_timeout(1500)
            rec.stop("r1_search")

        @job
        def r2_answer_scroll():
            go("/?a=A0016", 3500)
            page.evaluate("window.scrollTo(0, 260)")
            page.wait_for_timeout(500)
            rec.start()
            page.wait_for_timeout(600)
            target = page.evaluate(
                """() => { const el = [...document.querySelectorAll('h2,h3,p')].find(e => e.textContent.trim() === 'Rent increases');
                  return el.getBoundingClientRect().top - 110; }"""
            )
            smooth_scroll(target, 3200)
            page.wait_for_timeout(2500)
            rec.stop("r2_answer_scroll")

        @job
        def r3_time_ca():
            go("/?tab=time&date=2025-11-20&lens=algorithmic_rent_setting&region=LA", 5000)
            page.evaluate("window.scrollTo(0, 400)")
            page.wait_for_timeout(800)
            rec.start()
            page.wait_for_timeout(500)
            page.get_by_role("button", name="Play").click()
            page.wait_for_timeout(9000)
            rec.stop("r3_time_ca")

        @job
        def r4_time_nj():
            go("/?tab=time&date=2027-03-01&lens=algorithmic_rent_setting&region=NJ", 5000)
            page.evaluate("window.scrollTo(0, 400)")
            page.wait_for_timeout(800)
            rec.start()
            page.wait_for_timeout(500)
            page.get_by_role("button", name="Play").click()
            page.wait_for_timeout(8000)
            rec.stop("r4_time_nj")

        @job
        def r5_whatif():
            go("/?a=A0005", 3500)
            page.evaluate("window.scrollTo(0, 260)")
            page.wait_for_timeout(500)
            rec.start()
            page.wait_for_timeout(800)
            page.get_by_role("button", name="What if…").click()
            page.wait_for_timeout(700)
            f = page.get_by_placeholder("Year built").last
            f.click()
            f.press_sequentially("1960", delay=160)
            page.wait_for_timeout(500)
            page.get_by_role("button", name="Recalculate").click()
            page.wait_for_timeout(3200)
            rec.stop("r5_whatif")

        @job
        def r6_evidence():
            go("/?a=A0016", 3500)
            page.evaluate("window.scrollTo(0, 650)")
            page.wait_for_timeout(500)
            rec.start()
            page.wait_for_timeout(800)
            page.get_by_role("button", name="View source →").first.click()
            page.wait_for_timeout(3500)
            rec.stop("r6_evidence")

        @job
        def r7_landing():
            go("/", 2000)
            rec.start()
            page.wait_for_timeout(1200)
            for _ in range(4):
                smooth_scroll(1080, 1500)
                page.wait_for_timeout(1300)
            rec.stop("r7_landing")

        @job
        def r8_spanish():
            go("/?a=A0016", 3500)
            rec.start()
            page.wait_for_timeout(700)
            page.get_by_role("button", name="Renter summary").click()
            page.wait_for_timeout(1800)
            page.get_by_role("button", name="ES", exact=True).first.click()
            page.wait_for_timeout(3000)
            rec.stop("r8_spanish")

        for name, f in jobs.items():
            if only and name not in only:
                continue
            try:
                f()
            except Exception as e:  # keep going; report the failure
                print("FAILED", name, repr(e)[:400])
        b.close()


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
