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
    kb(method, [{ at: 0, s: 1.0, px: 960, py: 540 }, { at: 3.2, s: 1.55, px: 900, py: 470 }, { at: 11.4, s: 1.75, px: 700, py: 500 }]),
  ], { at: 5.4, dur: 11.4 });
  p.compose(chip("Pass 1 · every jurisdiction × category, with BM25 retrieval", { x: 140, y: 960 }), { at: 6.0, dur: 3.6 });
  p.compose(chip("Pass 2 · every document, end to end", { x: 140, y: 960, dot: INDIGO }), { at: 9.7, dur: 2.7 });
  p.compose(chip("60 / 60 quotes found verbatim in their source", { x: 140, y: 960, dot: "#30d158" }), { at: 12.5, dur: 3.9 });

  // 3. Verifier + audit trail.
  p.compose(kb(audit, [{ at: 0, s: 1.05, px: 960, py: 600 }, { at: 7.4, s: 1.4, px: 900, py: 860 }]), { at: 16.8, dur: 7.4 });
  p.compose(chip("A second AI pass fact-checks each rule: 59 / 60 confirmed", { x: 140, y: 120, dot: INDIGO }), { at: 17.2, dur: 3.0 });
  p.compose(chip("Every answer lists what we did not verify", { x: 140, y: 120 }), { at: 20.3, dur: 3.6 });

  // 4. Legal city vs mailing city.
  p.compose(kb(oak, [{ at: 0, s: 1.25, px: 720, py: 260 }, { at: 2.6, s: 1.25, px: 720, py: 260 }, { at: 5.0, s: 2.1, px: 690, py: 290 }, { at: 9.0, s: 2.2, px: 690, py: 290 }]), { at: 24.2, dur: 9.0 });
  p.compose(chip("Mailing city: Oakland", { x: 1180, y: 150, dot: "#8e8e93" }), { at: 24.8, dur: 8.0 });
  p.compose(chip("Legal city: Emeryville (Census Geocoder)", { x: 1180, y: 250, dot: TEAL }), { at: 28.4, dur: 4.4 });

  // 5. Deterministic engine: coverage matrix.
  p.compose(kb(rules, [{ at: 0, s: 1.0, px: 960, py: 540 }, { at: 9.1, s: 1.45, px: 960, py: 760 }]), { at: 33.2, dur: 9.1 });
  p.compose(chip("Code stacks state, county and city law", { x: 140, y: 960, dot: INDIGO }), { at: 33.8, dur: 3.6 });
  p.compose(chip("Supersession · effective dates · pending bills", { x: 140, y: 960, dot: TEAL }), { at: 37.6, dur: 4.4 });

  // 6. Self-check: the real terminal run, then the scoreboard.
  p.compose(<media file={term} x={0} y={0} width={W} height={H} fit="cover" />, { at: 42.3, dur: 6.6 });
  p.compose(kb(termStill, [{ at: 0, s: 1.0, px: 960, py: 540 }, { at: 3.4, s: 1.12, px: 700, py: 760 }]), { at: 48.9, dur: 3.45 });
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
  </frame>, { at: 42.3, dur: 10.0 });

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
    p.compose(<rect x={0} y={0} width={W} height={H} fill="#ffffff" animate={[{ property: "opacity", keyframes: [{ at: 0, value: 0 }, { at: 0.12, value: 0.6 }, { at: 0.35, value: 0 }] }]} />, { at: t - 0.12, dur: 0.35 });
  }
  const prev = process.env.PREVIEW;
  if (prev) {
    for (const t of prev.split(",").map(Number)) await p.frame(t, `renders/f_${String(Math.round(t * 10)).padStart(4, "0")}.png`);
  } else {
    await p.render("renders/tech.mp4", { bitrate: 12_000_000 });
  }
};
