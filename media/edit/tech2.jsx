// Strata - Tech video v3 (59.8 s): the stack, the pipeline with real code, lookup time, the self-check.
// Narration (sped up 1.1x) is muxed after render: blocks at 0.3 / 12.0 / 39.6 / 49.7 s.
export default async ({ project }) => {
  const p = await project({ dir: "proj", size: "1920x1080", fps: 30, background: "#f5f5f7" });
  const A = async (f) => p.add(f);
  const grid = await A("v2_grid.mp4"), hero = await A("s01_hero.jpg"), evidence = await A("s04_evidence.jpg");
  const bm25 = await A("c2_bm25.jpg"), llm = await A("c1_llm.jpg"), method = await A("s14_method.jpg"), verify = await A("c3_verify.jpg");
  const audit = await A("s05_audit.jpg"), search = await A("r1_search.mp4"), oak = await A("s11_oakland_emeryville.jpg"), engine = await A("c4_engine.jpg");
  const term = await A("r9_selfcheck.mp4");

  const fadeKeys = (d, a = 0.35) => [{ at: 0, value: 0 }, { at: a, value: 1 }, { at: d - 0.25, value: 1 }, { at: d, value: 0 }];
  const label = (txt, { x, y, w, size = 22, weight = 600, color = INK, align = "center" }) => (
    <text x={x} y={y} width={w} height={Math.ceil(size * 1.3)} align={align} fontFamily={FONT} fontWeight={weight} fontSize={size} color={color}>{txt}</text>
  );
  // A content window under the pipeline bar.
  const win = (file, d, extra = {}) => (
    <media file={file} x={240} y={236} width={1440} height={810} fit="cover" radius={22} shadow={{ y: 24, blur: 60, color: "#00000033" }} {...extra}
      animate={[{ property: "opacity", keyframes: fadeKeys(d) }, { property: "offsetY", keyframes: [{ at: 0, value: 30 }, { at: 0.5, value: 0, easing: "house" }, { at: d, value: 0 }] }]} />
  );
  // Horizontal pipeline of pills; each pill lights up during its [start, end) window (scene-local seconds).
  const bar = (nodes, { y, w, gap, dur }) => {
    const x0 = (W - (nodes.length * w + (nodes.length - 1) * gap)) / 2;
    const out = [];
    nodes.forEach(([txt, t0, t1], i) => {
      const x = x0 + i * (w + gap);
      const enter = 0.08 * i;
      const off = Math.min(Math.max(t0 + 0.3, t1), dur - 0.3);
      const lit = [{ at: 0, value: 0, easing: "hold" }, { at: t0, value: 0 }, { at: t0 + 0.25, value: 1, easing: "hold" }, { at: off, value: 1 }, { at: off + 0.25, value: 0 }];
      const shown = [{ at: 0, value: 0 }, { at: enter + 0.3, value: 1 }, { at: dur, value: 1 }];
      out.push(<rect x={x} y={y} width={w} height={64} radius={32} fill="#ffffff" strokeColor="#d2d2d7" strokeWidth={1.5} animate={[{ property: "opacity", keyframes: shown }]} />);
      out.push(<rect x={x} y={y} width={w} height={64} radius={32} fill={INK} animate={[{ property: "opacity", keyframes: lit }]} />);
      if (t1 < dur - 0.6) {
        out.push(<rect x={x} y={y} width={w} height={64} radius={32} fill={TEAL}
          animate={[{ property: "opacity", keyframes: [{ at: 0, value: 0, easing: "hold" }, { at: t1 + 0.2, value: 0 }, { at: t1 + 0.45, value: 0.16 }] }]} />);
      }
      out.push(<text x={x} y={y + 18} width={w} height={30} align="center" fontFamily={FONT} fontWeight={600} fontSize={22} color={MUTED} animate={[{ property: "opacity", keyframes: shown }]}>{txt}</text>);
      out.push(<text x={x} y={y + 18} width={w} height={30} align="center" fontFamily={FONT} fontWeight={600} fontSize={22} color="#ffffff" animate={[{ property: "opacity", keyframes: lit }]}>{txt}</text>);
      if (i < nodes.length - 1) {
        out.push(<rect x={x + w + 6} y={y + 31} width={gap - 12} height={2} fill="#c7c7cc"
          animate={[{ property: "opacity", keyframes: [{ at: 0, value: 0 }, { at: enter + 0.4, value: 1 }, { at: dur, value: 1 }] }]} />);
      }
    });
    return out;
  };

  // 1. Hook (0 - 2.3): "How Strata is built."
  p.compose([
    <media file={grid} x={0} y={0} width={W} height={H} fit="cover" animate={[{ property: "scale", from: 1.0, to: 1.04, duration: 2.3 }]} />,
    <rect x={0} y={0} width={W} height={H} fill="#000000" opacity={0.45} />,
    headline("How Strata is built.", { y: 440, size: 140, at: 0.2 }),
  ], { at: 0, dur: 2.3 });

  // 2. The stack (2.3 - 11.9), as strata cards, beside the real product.
  const layer = (name, items, color, i, t) => (
    <frame x={110} y={190 + i * 150} width={1000} height={124} layout="row" align="center" gap={26} padding={{ left: 0, right: 30 }}
      background="#ffffff" radius={26} shadow={{ y: 10, blur: 30, color: "#0000001a" }} at={t}
      motion={{ enter: { from: { x: -40, opacity: 0 }, duration: 0.55, easing: "house" } }}>
      <rect width={14} height={124} radius={7} fill={color} />
      <text width={200} height={46} fontFamily={FONT} fontWeight={700} fontSize={36} letterSpacing={-1} color={INK}>{name}</text>
      <text width={720} height={36} fontFamily={FONT} fontWeight={500} fontSize={27} color={MUTED}>{items}</text>
    </frame>
  );
  p.compose([
    <text x={110} y={92} width={900} height={60} fontFamily={FONT} fontWeight={700} fontSize={50} letterSpacing={-1.5} color={INK}
      motion={{ by: "word", from: { opacity: 0, y: 14 }, at: 0, duration: 0.5, overlap: 0.5 }}>The stack</text>,
    <frame x={0} y={0} width={W} height={H} layout="none">
      {layer("Frontend", "React 19 · TypeScript · Vite · Tailwind · Leaflet", TEAL, 0, 0.1)}
      {layer("Backend", "Python 3.12 · FastAPI · uv", INDIGO, 1, 5.0)}
      {layer("AI", "Anthropic SDK · Claude Sonnet 5 · JSON schema", "#1d1d1f", 2, 5.9)}
      {layer("Data", "RealPage corpus · Census Geocoder · parcel records", "#8e8e93", 3, 6.6)}
      {layer("Deploy", "Vercel · static site + Python function", ACCENT, 4, 7.8)}
    </frame>,
    <media file={hero} x={1160} y={330} width={660} height={371} fit="cover" radius={18} shadow={{ y: 20, blur: 50, color: "#00000033" }}
      animate={[{ property: "opacity", keyframes: [{ at: 0, value: 0 }, { at: 0.6, value: 1 }, { at: 9.6, value: 1 }] }, { property: "offsetY", keyframes: [{ at: 0, value: 30 }, { at: 0.8, value: 0, easing: "house" }, { at: 9.6, value: -12 }] }]} />,
    label("The live product", { x: 1160, y: 724, w: 660, size: 24, weight: 600, color: MUTED }),
  ], { at: 2.3, dur: 9.6 });

  // 3. Build time: the extraction pipeline (11.9 - 39.4), each step with its real code or screen.
  const S = 11.9;
  p.compose(bar([
    ["87 legal documents", 0.1, 4.1], ["BM25 retrieval", 4.1, 7.5], ["Claude Sonnet 5", 7.5, 14.9],
    ["Per-document pass", 14.9, 18.4], ["Quote check", 18.4, 22.7], ["Merge + verify", 22.7, 27.5],
  ], { y: 120, w: 255, gap: 38, dur: 27.5 }).concat([
    label("BUILD TIME · AI READS", { x: 0, y: 64, w: W, size: 20, weight: 700, color: TEAL }),
  ]), { at: S, dur: 27.5 });
  const steps = [[evidence, 0.0, 4.1], [bm25, 4.1, 3.4], [llm, 7.5, 7.4], [method, 14.9, 3.5], [verify, 18.4, 4.3], [audit, 22.7, 4.8]];
  for (const [f, t, d] of steps) p.compose(win(f, d), { at: S + t, dur: d });

  // 4. Lookup time (39.4 - 49.4): no model, just the geocoder and plain code.
  const L = 39.4;
  p.compose(bar([
    ["Address", 0.1, 3.4], ["Census Geocoder", 3.4, 6.1], ["Coverage engine", 6.1, 10.0], ["Answer + source", 9.4, 10.0],
  ], { y: 120, w: 360, gap: 46, dur: 10.0 }).concat([
    label("LOOKUP TIME · CODE DECIDES · NO AI", { x: 0, y: 64, w: W, size: 20, weight: 700, color: INDIGO }),
  ]), { at: L, dur: 10.0 });
  p.compose(win(search, 3.4, { trimStart: 1.0 }), { at: L, dur: 3.4 });
  p.compose(win(oak, 2.7), { at: L + 3.4, dur: 2.7 });
  p.compose(win(engine, 3.9), { at: L + 6.1, dur: 3.9 });

  // 5. Reproducible: the real self-check run and the numbers.
  const stat = (n, txt, i, t) => (
    <frame x={250 + i * 485} y={790} width={440} height="hug" layout="column" gap={6} padding={{ top: 24, bottom: 24, left: 30, right: 30 }}
      background="#ffffff" radius={28} shadow={{ y: 18, blur: 50, color: "#00000040" }} at={t}
      motion={{ enter: { from: { y: 40, opacity: 0, scale: 0.94 }, duration: 0.55, easing: "house" } }}>
      <text fontFamily={FONT} fontWeight={700} fontSize={72} letterSpacing={-2.5} color={INK}>{n}</text>
      <text fontFamily={FONT} fontWeight={500} fontSize={26} color={MUTED}>{txt}</text>
    </frame>
  );
  p.compose([
    <media file={term} x={0} y={0} width={W} height={H} fit="cover" />,
    <frame x={0} y={0} width={W} height={H} layout="none">
      {stat("287", "model calls, all cached", 0, 2.2)}
      {stat("~$10", "total model cost", 1, 4.0)}
      {stat("21 / 21", "known answers pass", 2, 5.3)}
    </frame>,
  ], { at: 49.4, dur: 6.9 });

  // 6. End card.
  p.compose([
    <rect x={0} y={0} width={W} height={H} fill={{ kind: "radial", stops: [{ offset: 0, color: "#ffffff" }, { offset: 1, color: "#e8e8ed" }] }} />,
    ...mark({ x: 880, y: 220, size: 160, at: 0.05 }),
    <text x={0} y={420} width={W} align="center" fontFamily={FONT} fontWeight={700} fontSize={104} letterSpacing={-4} color={INK}
      motion={{ by: "character", from: { opacity: 0, y: 26 }, at: 0.5, duration: 0.45, overlap: 0.8, easing: "house" }}>Strata</text>,
    <text x={0} y={570} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={36} color={MUTED}
      motion={{ by: "line", from: { opacity: 0, y: 12 }, at: 1.1, duration: 0.5 }}>React · FastAPI · Claude Sonnet 5 · Vercel</text>,
    <text x={0} y={650} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={32} color={ACCENT}
      motion={{ by: "line", from: { opacity: 0 }, at: 1.5, duration: 0.5 }}>github.com/AyrtonSoler/Strata</text>,
  ], { at: 56.3, dur: 3.5 });

  const prev = process.env.PREVIEW;
  if (prev) {
    for (const t of prev.split(",").map(Number)) await p.frame(t, `renders/f_${String(Math.round(t * 10)).padStart(4, "0")}.png`);
  } else {
    await p.render("renders/tech.mp4", { bitrate: 12_000_000 });
  }
};
