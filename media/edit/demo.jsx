// Strata - Demo video (58.5 s). Narration blocks are placed at 0.3 / 15.2 / 24.2 / 34.6 s and muxed after render.
export default async ({ project }) => {
  const p = await project({ dir: "proj", size: "1920x1080", fps: 30, background: "#000000" });
  const A = async (f) => p.add(f);
  const building = await A("v0_slow.mp4"), letter = await A("v1_letter.mp4"), book = await A("key3.png"), aerial = await A("v3_slow.mp4");
  const search = await A("r1_search.mp4"), answer = await A("s02_answer_top.jpg"), rent = await A("s03_rent.jpg"), evidence = await A("s04_evidence.jpg");
  const time = await A("r3_time_ca.mp4"), unknown = await A("s10a_unknown.jpg"), whatif = await A("r5_whatif.mp4"), spanish = await A("s09_rights_es.jpg");

  const vignette = (o = 0.55) => <rect x={0} y={0} width={W} height={H} fill={{ kind: "linear", angle: 90, stops: [{ offset: 0, color: "#000000", opacity: 0 }, { offset: 0.55, color: "#000000", opacity: 0.05 }, { offset: 1, color: "#000000", opacity: o }] }} />;
  const layerWord = (word, color, i, t) => (
    <frame x={560 + i * 290} y={850} width={260} height={84} layout="row" align="center" gap={16}
      motion={{ enter: { from: { y: 30, opacity: 0 }, duration: 0.5, easing: "house" } }} at={t}>
      <rect width={22} height={22} radius={11} fill={color} />
      <text width={210} height={84} fontFamily={FONT} fontWeight={700} fontSize={64} letterSpacing={-2} color="#ffffff">{word}</text>
    </frame>
  );

  // 1. Hook: law settles onto a building (Kling, slowed to 7 s).
  p.compose([
    <media file={building} x={0} y={0} width={W} height={H} fit="cover" animate={[{ property: "scale", from: 1.0, to: 1.08, duration: 7 }, { property: "offsetX", from: 0, to: -77, duration: 7 }, { property: "offsetY", from: 0, to: -20, duration: 7 }]} />,
    vignette(0.75),
    <text x={0} y={720} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={52} letterSpacing={-1} color="#ffffff"
      motion={{ by: "word", from: { opacity: 0, y: 20 }, at: 0.4, duration: 0.6, overlap: 0.6, easing: "house" }}>Every apartment sits under layers of law.</text>,
    <frame x={0} y={0} width={W} height={H} layout="none">
      {layerWord("State", INDIGO, 0, 4.2)}
      {layerWord("County", "#8e8e93", 1, 5.2)}
      {layerWord("City", TEAL, 2, 6.0)}
    </frame>,
  ], { at: 0, dur: 7.0 });

  // 2. The renter's question.
  p.compose([
    <media file={letter} x={0} y={0} width={W} height={H} fit="cover" trimStart={0.3} animate={[{ property: "scale", from: 1.0, to: 1.05, duration: 4.4 }, { property: "offsetX", from: 0, to: -48, duration: 4.4 }, { property: "offsetY", from: 0, to: -27, duration: 4.4 }]} />,
    vignette(0.7),
    headline("Is that even legal?", { y: 820, size: 96, at: 2.2 }),
  ], { at: 7.0, dur: 4.4 });
  p.compose([
    kb(book, [{ at: 0, s: 1.0, px: 960, py: 540 }, { at: 3.6, s: 1.18, px: 1250, py: 560 }]),
    vignette(0.7),
    <text x={0} y={860} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={54} letterSpacing={-1} color="#ffffff"
      motion={{ by: "word", from: { opacity: 0, y: 16 }, at: 0.3, duration: 0.5, overlap: 0.6 }}>Today, that means reading statutes by hand.</text>,
  ], { at: 11.4, dur: 3.6 });

  // 3. Meet Strata.
  p.compose([
    <rect x={0} y={0} width={W} height={H} fill={{ kind: "radial", stops: [{ offset: 0, color: "#ffffff" }, { offset: 1, color: "#e8e8ed" }] }} />,
    ...mark({ x: 870, y: 300, size: 180, at: 0.05 }),
    <text x={0} y={520} width={W} align="center" fontFamily={FONT} fontWeight={700} fontSize={120} letterSpacing={-4.5} color={INK}
      motion={{ by: "character", from: { opacity: 0, y: 26 }, at: 0.5, duration: 0.45, overlap: 0.8, easing: "house" }}>Strata</text>,
  ], { at: 15.0, dur: 1.8 });

  // 4. Type an address: the real app.
  p.compose(<media file={search} x={0} y={0} width={W} height={H} fit="cover" animate={[{ property: "scale", from: 1.0, to: 1.06, duration: 5.9 }, { property: "offsetX", from: 0, to: -58, duration: 5.9 }]} />, { at: 16.8, dur: 5.9 });
  p.compose(chip("Census Geocoder finds the legal city", { x: 1180, y: 960, dot: TEAL }), { at: 18.6, dur: 3.9 });
  p.compose(kb(answer, [{ at: 0, s: 1.25, px: 900, py: 330 }, { at: 1.5, s: 1.45, px: 1150, py: 320 }]), { at: 22.7, dur: 1.5 });

  // 5. The rent answer: local ordinance applies, state cap superseded.
  p.compose(kb(rent, [{ at: 0, s: 1.0, px: 960, py: 540 }, { at: 1.6, s: 1.5, px: 950, py: 240 }, { at: 3.6, s: 1.5, px: 950, py: 240 }, { at: 5.2, s: 1.5, px: 950, py: 540 }, { at: 6.8, s: 1.55, px: 960, py: 540 }]), { at: 24.2, dur: 6.8 });
  p.compose(chip("San Francisco Rent Ordinance · Applies", { x: 140, y: 960, dot: "#30d158" }), { at: 26.0, dur: 2.6 });
  p.compose(chip("California statewide cap · Superseded", { x: 140, y: 960, dot: "#8e8e93" }), { at: 28.7, dur: 2.1 });

  // 6. Evidence: the exact passage.
  p.compose(kb(evidence, [{ at: 0, s: 1.05, px: 960, py: 560 }, { at: 3.6, s: 1.6, px: 980, py: 590 }]), { at: 31.0, dur: 3.6 });
  p.compose(chip("The statute itself, passage highlighted", { x: 140, y: 960, dot: "#ffcc00" }), { at: 31.6, dur: 2.8 });

  // 7. Time Machine: California switches on, building by building.
  p.compose(<media file={time} x={0} y={0} width={W} height={H} fit="cover"
    animate={[{ property: "scale", from: 1.25, to: 1.4, duration: 9.6 }, { property: "offsetX", from: CX - 1.25 * 790, to: CX - 1.4 * 790, duration: 9.6 }, { property: "offsetY", from: CY - 1.25 * 560, to: CY - 1.4 * 560, duration: 9.6 }]} />, { at: 34.6, dur: 9.6 });
  p.compose(chip("Jan 1, 2026 · California's algorithmic-pricing ban takes effect", { x: 140, y: 960, dot: "#30d158" }), { at: 37.0, dur: 7.0 });

  // 8. Unknown, and the fact that would decide it.
  p.compose(kb(unknown, [{ at: 0, s: 1.15, px: 1000, py: 340 }, { at: 1.7, s: 1.3, px: 1000, py: 360 }]), { at: 44.2, dur: 1.9 });
  p.compose(chip("Year built not in public records: Unknown", { x: 140, y: 960, dot: "#ff9f0a" }), { at: 44.4, dur: 1.6 });
  p.compose(kb(whatif, [{ at: 0, s: 1.15, px: 1000, py: 360 }, { at: 3.6, s: 1.15, px: 1000, py: 360 }]), { at: 46.1, dur: 3.6 });
  p.compose(chip("What if it was built in 1960? Recalculated by code", { x: 140, y: 960, dot: ACCENT }), { at: 46.6, dur: 2.9 });

  // 9. English or Spanish.
  p.compose(kb(spanish, [{ at: 0, s: 1.1, px: 960, py: 520 }, { at: 2.5, s: 1.3, px: 960, py: 500 }]), { at: 49.7, dur: 2.5 });

  // 10. Tagline over the city, then the URL.
  p.compose([
    <media file={aerial} x={0} y={0} width={W} height={H} fit="cover" animate={[{ property: "scale", from: 1.0, to: 1.06, duration: 6.3 }, { property: "offsetX", from: 0, to: -58, duration: 6.3 }, { property: "offsetY", from: 0, to: -32, duration: 6.3 }]} />,
    <rect x={0} y={0} width={W} height={H} fill="#000000" opacity={0.45} />,
    <rect x={880} y={150} width={160} height={160} radius={38} fill="#ffffff" shadow={{ y: 20, blur: 60, color: "#00000066" }}
      animate={[{ property: "opacity", from: 0, to: 1, duration: 0.4 }]} />,
    ...mark({ x: 900, y: 165, size: 120, at: 0.15 }),
    <text x={0} y={350} width={W} align="center" fontFamily={FONT} fontWeight={700} fontSize={104} letterSpacing={-4} color="#ffffff"
      motion={{ by: "character", from: { opacity: 0, y: 24 }, at: 0.2, duration: 0.45, overlap: 0.8, easing: "house" }}>Strata</text>,
    <text x={0} y={520} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={64} letterSpacing={-1.5} color="#ffffff"
      motion={{ by: "word", from: { opacity: 0, y: 22 }, at: 1.25, duration: 0.5, overlap: 0.25, easing: "house" }}>Every rule. Every address. Every date.</text>,
    <text x={0} y={680} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={36} color="#5ee6d6"
      motion={{ by: "line", from: { opacity: 0, y: 10 }, at: 4.0, duration: 0.6 }}>strata-jet-tau.vercel.app</text>,
  ], { at: 52.2, dur: 6.3 });

  for (const t of [7.0, 11.4, 16.8, 24.2, 31.0, 34.6, 44.2, 49.7, 52.2]) {
    p.compose(<rect x={0} y={0} width={W} height={H} fill="#000000" animate={[{ property: "opacity", keyframes: [{ at: 0, value: 0 }, { at: 0.1, value: 0.35 }, { at: 0.3, value: 0 }] }]} />, { at: t - 0.1, dur: 0.3 });
  }
  const prev = process.env.PREVIEW;
  if (prev) {
    for (const t of prev.split(",").map(Number)) await p.frame(t, `renders/f_${String(Math.round(t * 10)).padStart(4, "0")}.png`);
  } else {
    await p.render("renders/demo.mp4", { bitrate: 12_000_000 });
  }
};
