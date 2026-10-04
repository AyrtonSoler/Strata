// Shared Strata motion kit for the Higgsedit scripts (inlined into each edit).
const W = 1920, H = 1080, CX = 960, CY = 540;
const INK = "#1d1d1f", MUTED = "#6e6e73", ACCENT = "#0071e3", TEAL = "#0a9e8f", INDIGO = "#5856d6";
const FONT = "Inter";

// Ken Burns on a full-screen still: keys [{at, s, px, py}] put screen point (px,py) of the
// 1920x1080 picture at the centre with scale s (scale origin is the top-left corner).
const kb = (file, keys, extra = {}) => {
  const k = (prop, f) => ({ property: prop, keyframes: keys.map((q) => ({ at: q.at, value: f(q), easing: q.e || "smooth" })) });
  return (
    <media file={file} x={0} y={0} width={W} height={H} fit="cover" {...extra}
      animate={[k("scale", (q) => q.s), k("offsetX", (q) => (q.s === 1 && q.px === undefined ? 0 : CX - q.s * q.px)), k("offsetY", (q) => (q.s === 1 && q.py === undefined ? 0 : CY - q.s * q.py))]} />
  );
};

const fadeIO = (dur, fin = 0.35, fout = 0.35) => ({
  property: "opacity",
  keyframes: [{ at: 0, value: 0 }, { at: fin, value: 1 }, { at: dur - fout, value: 1 }, { at: dur, value: 0 }],
});

// A frosted pill caption with an optional coloured dot.
const chip = (label, { x, y, dot = ACCENT, size = 30, dur }) => (
  <frame x={x} y={y} width="hug" height="hug" layout="row" align="center" gap={14}
    padding={{ top: 16, bottom: 16, left: 24, right: 28 }} background="#ffffffee" radius={999}
    shadow={{ y: 12, blur: 40, color: "#00000026" }}
    motion={{ enter: { from: { y: 18, opacity: 0, scale: 0.96 }, duration: 0.5, easing: "house" }, exit: { to: { opacity: 0, y: -8 }, duration: 0.3 } }}>
    <rect width={14} height={14} radius={7} fill={dot} />
    <text fontFamily={FONT} fontWeight={600} fontSize={size} color={INK}>{label}</text>
  </frame>
);

// Big kinetic headline, word by word.
const headline = (content, { y = 420, size = 120, color = "#ffffff", at = 0 }) => (
  <text x={0} y={y} width={W} align="center" fontFamily={FONT} fontWeight={700} fontSize={size} letterSpacing={-size * 0.035} color={color}
    motion={{ by: "word", from: { opacity: 0, y: 40 }, at, duration: 0.7, overlap: 0.55, easing: "house" }}>{content}</text>
);

// The Strata mark as native paths: three isometric slabs that drop in, then the address dot.
const SLABS = [[12.4, "#3a3a3c", "#1d1d1f", "#000000"], [6.2, "#7d7bf0", "#4a48c4", "#3b39a8"], [0, "#22c3b2", "#08897c", "#06705f"]];
const mark = ({ x, y, size, at = 0 }) => {
  const k = size / 32;
  const P = (pts) => "M" + pts.map(([a, b]) => `${(a * k).toFixed(1)} ${(b * k).toFixed(1)}`).join(" L") + " Z";
  const nodes = [];
  SLABS.forEach(([dy, top, left, right], i) => {
    const t0 = at + i * 0.22;
    const anim = [
      { property: "offsetY", keyframes: [{ at: 0, value: -size * 0.55, easing: "hold" }, { at: t0, value: -size * 0.55, easing: [0.2, 1.4, 0.4, 1] }, { at: t0 + 0.7, value: 0 }] },
      { property: "opacity", keyframes: [{ at: 0, value: 0, easing: "hold" }, { at: t0, value: 0 }, { at: t0 + 0.25, value: 1 }] },
    ];
    const faces = [
      [left, [[4, 10 + dy], [16, 16 + dy], [16, 18.6 + dy], [4, 12.6 + dy]]],
      [right, [[28, 10 + dy], [16, 16 + dy], [16, 18.6 + dy], [28, 12.6 + dy]]],
      [top, [[16, 4 + dy], [28, 10 + dy], [16, 16 + dy], [4, 10 + dy]]],
    ];
    faces.forEach(([c, pts]) => nodes.push(<path x={x} y={y} width={size} height={size} d={P(pts)} fill={c} stroke={{ width: 1.2 * k, color: c, cap: "round" }} animate={anim} />));
  });
  const r = 2.2 * k, t1 = at + 2 * 0.22 + 0.55;
  nodes.push(<rect x={x + 16 * k - r} y={y + 10 * k - r} width={2 * r} height={2 * r} radius={r} fill="#ffffff"
    animate={[{ property: "opacity", keyframes: [{ at: 0, value: 0, easing: "hold" }, { at: t1, value: 0 }, { at: t1 + 0.3, value: 1 }] }]} />);
  return nodes;
};
// Strata - Tech video (59.5 s). Narration is muxed after render.
export default async ({ project }) => {
  const p = await project({ dir: "proj", size: "1920x1080", fps: 30, background: "#f5f5f7" });
  const A = async (f) => p.add(f);
  const grid = await A("v2_grid.mp4"), method = await A("s14_method.jpg"), audit = await A("s05_audit.jpg");
  const oak = await A("s11_oakland_emeryville.jpg"), rules = await A("s12_rules.jpg"), term = await A("r9_selfcheck.mp4");
  const termStill = await A("s15_selfcheck.jpg");

  // 1. Hook: legal text resolving into rule cells (Kling), "AI reads. Code decides."
  p.compose([
    <media file={grid} x={0} y={0} width={W} height={H} fit="cover" animate={[{ property: "scale", from: 1.0, to: 1.06, duration: 5.4 }, { property: "offsetX", from: 0, to: -57, duration: 5.4 }, { property: "offsetY", from: 0, to: -32, duration: 5.4 }]} />,
    <rect x={0} y={0} width={W} height={H} fill={{ kind: "radial", stops: [{ offset: 0, color: "#000000", opacity: 0.55 }, { offset: 1, color: "#000000", opacity: 0.15 }] }} />,
    headline("AI reads.", { y: 330, size: 150, at: 0.5 }),
    headline("Code decides.", { y: 520, size: 150, at: 2.3, color: "#5ee6d6" }),
  ], { at: 0, dur: 5.4 });

  // 2. Method: two extraction passes, every quote checked.
  p.compose([
    kb(method, [{ at: 0, s: 1.0, px: 960, py: 540 }, { at: 3.2, s: 1.55, px: 900, py: 470 }, { at: 11.4, s: 1.75, px: 700, py: 500 }],
  ], { at: 5.4, dur: 11.4 });
  p.compose(chip("Pass 1 · every jurisdiction × category, with BM25 retrieval", { x: 140, y: 860 }), { at: 6.0, dur: 3.6 });
  p.compose(chip("Pass 2 · every document, end to end", { x: 140, y: 860, dot: INDIGO }), { at: 9.7, dur: 2.7 });
  p.compose(chip("60 / 60 quotes found verbatim in their source", { x: 140, y: 860, dot: "#30d158" }), { at: 12.5, dur: 4.2 });

  // 3. Verifier + audit trail.
  p.compose(kb(audit, [{ at: 0, s: 1.05, px: 960, py: 600 }, { at: 7.4, s: 1.4, px: 900, py: 860 }]), { at: 16.8, dur: 7.4 });
  p.compose(chip("A second AI pass fact-checks each rule: 59 / 60 confirmed", { x: 140, y: 120, dot: INDIGO }), { at: 17.2, dur: 3.0 });
  p.compose(chip("Every answer lists what we did not verify", { x: 140, y: 120 }), { at: 20.3, dur: 3.8 });

  // 4. Legal city vs mailing city.
  p.compose(kb(oak, [{ at: 0, s: 1.25, px: 720, py: 260 }, { at: 2.6, s: 1.25, px: 720, py: 260 }, { at: 5.0, s: 2.1, px: 690, py: 290 }, { at: 9.0, s: 2.2, px: 690, py: 290 }]), { at: 24.2, dur: 9.0 });
  p.compose(chip("Mailing city: Oakland", { x: 1180, y: 150, dot: "#8e8e93" }), { at: 24.8, dur: 8.2 });
  p.compose(chip("Legal city: Emeryville (Census Geocoder)", { x: 1180, y: 250, dot: TEAL }), { at: 28.4, dur: 4.6 });

  // 5. Deterministic engine: coverage matrix.
  p.compose(kb(rules, [{ at: 0, s: 1.0, px: 960, py: 540 }, { at: 9.1, s: 1.45, px: 960, py: 760 }]), { at: 33.2, dur: 9.1 });
  p.compose(chip("Code stacks state → county → city", { x: 140, y: 120, dot: INDIGO }), { at: 33.8, dur: 3.6 });
  p.compose(chip("Supersession · effective dates · pending bills", { x: 140, y: 120, dot: TEAL }), { at: 37.6, dur: 4.6 });

  // 6. Self-check: the real terminal run, then the scoreboard.
  p.compose(<media file={term} x={0} y={0} width={W} height={H} fit="cover" />, { at: 42.3, dur: 6.6 });
  p.compose(kb(termStill, [{ at: 0, s: 1.0, px: 960, py: 540 }, { at: 3.6, s: 1.12, px: 700, py: 760 }]), { at: 48.9, dur: 3.6 });
  const stat = (n, label, i, t) => (
    <frame x={170 + i * 405} y={770} width={370} height="hug" layout="column" gap={6} padding={{ top: 26, bottom: 26, left: 30, right: 30 }}
      background="#ffffff" radius={28} shadow={{ y: 18, blur: 50, color: "#00000040" }}
      motion={{ enter: { from: { y: 40, opacity: 0, scale: 0.94 }, duration: 0.55, easing: "house" } }} at={t} >
      <text fontFamily={FONT} fontWeight={700} fontSize={76} letterSpacing={-2.5} color={INK}>{n}</text>
      <text fontFamily={FONT} fontWeight={500} fontSize={26} color={MUTED}>{label}</text>
    </frame>
  );
  p.compose(<frame x={0} y={0} width={W} height={H} layout="none">
    {stat("500", "addresses resolved", 0, 0.4)}
    {stat("60", "schema-valid rules", 1, 2.2)}
    {stat("5 / 5", "change cases pass", 2, 4.3)}
    {stat("21 / 21", "known answers", 3, 6.2)}
  </frame>, { at: 42.3, dur: 10.2 });

  // 7. End card: the mark drops in, then the name.
  p.compose([
    <rect x={0} y={0} width={W} height={H} fill={{ kind: "radial", stops: [{ offset: 0, color: "#ffffff" }, { offset: 1, color: "#e8e8ed" }] }} />,
    ...mark({ x: 850, y: 250, size: 220, at: 0.2 }),
    <text x={0} y={500} width={W} align="center" fontFamily={FONT} fontWeight={700} fontSize={110} letterSpacing={-4} color={INK}
      motion={{ by: "character", from: { opacity: 0, y: 30 }, at: 1.1, duration: 0.5, overlap: 0.8, easing: "house" }}>Strata</text>,
    <text x={0} y={650} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={44} color={MUTED}
      motion={{ by: "word", from: { opacity: 0, y: 16 }, at: 1.9, duration: 0.5, overlap: 0.5 }}>AI reads. Code decides.</text>,
    <text x={0} y={800} width={W} align="center" fontFamily={FONT} fontWeight={500} fontSize={30} color={MUTED}
      motion={{ by: "line", from: { opacity: 0 }, at: 2.8, duration: 0.6 }}>287 model calls · about $10 · fully reproducible</text>,
    <text x={0} y={852} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={30} color={ACCENT}
      motion={{ by: "line", from: { opacity: 0 }, at: 3.2, duration: 0.6 }}>github.com/AyrtonSoler/hack-nation-7</text>,
  ], { at: 52.5, dur: 7.0 });

  // Quick fades between scenes.
  for (const t of [5.4, 16.8, 24.2, 33.2, 42.3, 52.5]) {
    p.compose(<rect x={0} y={0} width={W} height={H} fill="#ffffff" animate={[{ property: "opacity", keyframes: [{ at: 0, value: 0 }, { at: 0.12, value: 0.85 }, { at: 0.35, value: 0 }] }]} />, { at: t - 0.12, dur: 0.35 });
  }
  const prev = process.env.PREVIEW;
  if (prev) {
    for (const t of prev.split(",").map(Number)) await p.frame(t, `renders/f_${String(t).replace(".", "_")}.png`);
  } else {
    await p.render("renders/tech.mp4", { bitrate: 12_000_000 });
  }
};
