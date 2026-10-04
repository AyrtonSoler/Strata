// Shared Strata motion kit for the Higgsedit scripts (inlined into each edit).
const W = 1920, H = 1080, CX = 960, CY = 540;
const INK = "#1d1d1f", MUTED = "#6e6e73", ACCENT = "#0071e3", TEAL = "#0a9e8f", INDIGO = "#5856d6";
const FONT = "Inter";

// Ken Burns on a full-screen still: keys [{at, s, px, py}] put screen point (px,py) of the
// 1920x1080 picture at the centre with scale s (scale origin is the top-left corner).
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const kb = (file, keys, extra = {}) => {
  const k = (prop, f) => ({ property: prop, keyframes: keys.map((q) => ({ at: q.at, value: f(q), easing: q.e || "smooth" })) });
  return (
    <media file={file} x={0} y={0} width={W} height={H} fit="cover" {...extra}
      animate={[k("scale", (q) => q.s), k("offsetX", (q) => clamp(CX - q.s * q.px, W - q.s * W, 0)), k("offsetY", (q) => clamp(CY - q.s * q.py, H - q.s * H, 0))]} />
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
    <text width={Math.ceil(label.length * size * 0.56)} height={Math.ceil(size * 1.25)} fontFamily={FONT} fontWeight={600} fontSize={size} color={INK}>{label}</text>
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
