// Strata - Team video (51.4 s): Víctor Ayrton Soler on camera, captions, product windows, end card.
// His own audio and the music bed are mixed after render.
export default async ({ project }) => {
  const p = await project({ dir: "proj", size: "1920x1080", fps: 30, background: "#000000" });
  const A = async (f) => p.add(f);
  const me = await A("me_fixed.mp4"), backend = await A("c4_engine.jpg"), time = await A("r3_time_ca.mp4");
  const evidence = await A("s04_evidence.jpg"), verify = await A("c3_verify.jpg"), hero = await A("s01_hero.jpg");
  const END = 47.9;

  // Interview framing: subject on the left third, slow push-in.
  p.compose(
    <media file={me} x={0} y={0} width={W} height={H} fit="cover"
      animate={[{ property: "scale", from: 1.2, to: 1.27, duration: END }, { property: "offsetX", from: -360, to: -400, duration: END }, { property: "offsetY", from: -150, to: -175, duration: END }]} />,
    { at: 0, dur: END });

  // Name lower-third.
  p.compose(
    <frame x={110} y={700} width={980} height="hug" layout="column" gap={6} padding={{ top: 22, bottom: 22, left: 30, right: 30 }}
      background="#ffffffee" radius={24} shadow={{ y: 14, blur: 40, color: "#00000040" }}
      motion={{ enter: { from: { x: -40, opacity: 0 }, duration: 0.6, easing: "house" }, exit: { to: { opacity: 0, x: -20 }, duration: 0.4 } }}>
      <text width={920} height={54} fontFamily={FONT} fontWeight={700} fontSize={44} letterSpacing={-1.2} color={INK}>Víctor Ayrton Soler</text>
      <text width={920} height={36} fontFamily={FONT} fontWeight={500} fontSize={28} color={MUTED}>Computer Science · Tecnológico de Monterrey, Campus Puebla</text>
    </frame>,
    { at: 0.8, dur: 6.4 });

  // Product windows on the right, while he talks about them.
  const side = (file, d, extra = {}) => (
    <media file={file} x={1150} y={230} width={690} height={388} fit="cover" radius={20} shadow={{ y: 22, blur: 60, color: "#00000066" }} {...extra}
      animate={[{ property: "opacity", keyframes: [{ at: 0, value: 0 }, { at: 0.4, value: 1 }, { at: d - 0.35, value: 1 }, { at: d, value: 0 }] },
        { property: "offsetY", keyframes: [{ at: 0, value: 24 }, { at: 0.55, value: 0, easing: "house" }, { at: d, value: 0 }] }]} />
  );
  p.compose(side(backend, 4.6), { at: 9.0, dur: 4.6 });
  p.compose(side(time, 7.4, { trimStart: 0.4 }), { at: 20.6, dur: 7.4 });
  p.compose(side(evidence, 5.6), { at: 30.0, dur: 5.6 });
  p.compose(side(verify, 2.6), { at: 35.6, dur: 2.6 });
  p.compose(side(hero, 6.0), { at: 38.8, dur: 6.0 });

  // English captions, timed to his words.
  const CAPS = [
    [0.0, 2.44, "Hi, I'm Víctor Ayrton Soler,"],
    [2.46, 4.8, "and I'm in my 5th semester of Computer Science"],
    [4.8, 7.46, "at Tecnológico de Monterrey, Campus Puebla, in Mexico."],
    [7.98, 10.36, "I like building the parts of software people don't usually see,"],
    [10.44, 13.14, "such as backends, APIs, and the systems behind them."],
    [13.54, 15.48, "Lately, I've been quite interested in AI"],
    [15.48, 18.22, "and how to use it in real products without trusting it blindly."],
    [18.68, 20.28, "And that's why I chose this challenge."],
    [20.76, 22.84, "Technically, it's kinda hard, because the law changes"],
    [22.84, 24.76, "by state, by city and by date."],
    [24.9, 26.66, "And it matters, because renters and landlords"],
    [26.66, 28.04, "make real decisions with it."],
    [28.04, 29.7, "I worked on this project solo."],
    [30.0, 33.38, "The hardest part was making sure that AI never made anything up."],
    [33.84, 35.86, "So every rule quotes the law, word for word,"],
    [35.96, 38.2, "and my code checks the quote against the source."],
    [38.86, 41.74, "For me, this weekend was a chance to bring backend, AI"],
    [42.0, 44.66, "and full-stack work together in one single project."],
    [45.24, 47.86, "So thank you for watching, and please enjoy Strata."],
  ];
  for (const [a, b, txt] of CAPS) {
    const w = Math.min(1700, Math.ceil(txt.length * 21) + 60);
    p.compose(
      <frame x={(W - w) / 2} y={940} width={w} height={74} layout="row" align="center" justify="center" background="#000000b3" radius={16}>
        <text width={w - 40} height={52} align="center" fontFamily={FONT} fontWeight={600} fontSize={38} color="#ffffff">{txt}</text>
      </frame>,
      { at: a, dur: b - a - 0.02 });
  }

  // End card.
  p.compose([
    <rect x={0} y={0} width={W} height={H} fill={{ kind: "radial", stops: [{ offset: 0, color: "#ffffff" }, { offset: 1, color: "#e8e8ed" }] }}
      animate={[{ property: "opacity", from: 0, to: 1, duration: 0.4 }]} />,
    ...mark({ x: 880, y: 250, size: 160, at: 0.2 }),
    <text x={0} y={450} width={W} align="center" fontFamily={FONT} fontWeight={700} fontSize={96} letterSpacing={-3.5} color={INK}
      motion={{ by: "character", from: { opacity: 0, y: 24 }, at: 0.6, duration: 0.45, overlap: 0.8, easing: "house" }}>Strata</text>,
    <text x={0} y={590} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={34} color={MUTED}
      motion={{ by: "line", from: { opacity: 0, y: 10 }, at: 1.1, duration: 0.5 }}>Built solo by Víctor Ayrton Soler · Hack-Nation 7</text>,
    <text x={0} y={660} width={W} align="center" fontFamily={FONT} fontWeight={600} fontSize={30} color={ACCENT}
      motion={{ by: "line", from: { opacity: 0 }, at: 1.5, duration: 0.5 }}>strata-jet-tau.vercel.app</text>,
  ], { at: END, dur: 3.5 });

  const prev = process.env.PREVIEW;
  if (prev) {
    for (const t of prev.split(",").map(Number)) await p.frame(t, `renders/f_${String(Math.round(t * 10)).padStart(4, "0")}.png`);
  } else {
    await p.render("renders/team.mp4", { bitrate: 12_000_000 });
  }
};
