// The lecture deck — built page by page. Run: node build_lecture.js
const pptxgen = require("pptxgenjs");

const BG = "131719", CARD = "1B2125", CARD2 = "222A2F", INK = "E4E9EC",
  MUT = "93A0A8", LINE = "2A3237", SW = "4593C8", SG = "BA8434",
  GOOD = "6FBF73", BAD = "D9634E";
const H = "Arial", B = "Calibri", M = "Courier New";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5

// ---------- helpers ----------
const base = (kicker, title, titleSize = 30) => {
  const s = pres.addSlide();
  s.background = { color: BG };
  if (kicker)
    s.addText(kicker.toUpperCase(), { x: 0.6, y: 0.32, w: 12.1, h: 0.3, fontFace: H, fontSize: 11, bold: true, color: MUT, charSpacing: 3, margin: 0 });
  if (title)
    s.addText(title, { x: 0.6, y: 0.6, w: 12.1, h: 0.85, fontFace: H, fontSize: titleSize, bold: true, color: INK, margin: 0 });
  return s;
};
const card = (s, x, y, w, h, fill = CARD) =>
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: LINE, width: 1 } });
const chip = (s, x, y, color) =>
  s.addShape(pres.ShapeType.roundRect, { x, y, w: 0.18, h: 0.18, rectRadius: 0.04, fill: { color }, line: { type: "none" } });
const bullets = (s, x, y, w, h, items, o = {}) =>
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { code: "2022", indent: 12 }, breakLine: i < items.length - 1, paraSpaceAfter: o.gap ?? 8 } })),
    { x, y, w, h, fontFace: B, fontSize: o.size ?? 14.5, color: o.color ?? INK, valign: "top", margin: 0 });

// =====================================================================
// PAGE 0 · Title
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("One Agent Is Already a Swarm", { x: 0.9, y: 2.3, w: 11.5, h: 1.1, fontFace: H, fontSize: 48, bold: true, color: INK, align: "center", margin: 0 });
  s.addText("Why multi-agent systems are infrastructure, not agent count", { x: 1.9, y: 3.5, w: 9.5, h: 0.6, fontFace: B, fontSize: 20, color: SW, align: "center", margin: 0 });
  s.addText("Part 0  why complex systems collapse   ·   Part 1  what an agent actually is   ·   Part 2  why swarms   ·   Part 3  the environment", { x: 0.9, y: 6.4, w: 11.5, h: 0.35, fontFace: B, fontSize: 12, color: MUT, align: "center", margin: 0 });
  s.addNotes("Title. Say the subtitle out loud and let it be the promise of the talk: by the end, 'how many agents' should feel like the wrong question.");
}

// =====================================================================
// PAGE 1 · Section hook — "Every complex system is dying."
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("PART 0 · WHY COMPLEX SYSTEMS COLLAPSE", { x: 0.7, y: 0.5, w: 8, h: 0.3, fontFace: H, fontSize: 11, bold: true, color: MUT, charSpacing: 3, margin: 0 });

  s.addText("Every complex system is dying.", { x: 0.7, y: 2.3, w: 5.9, h: 1.7, fontFace: H, fontSize: 44, bold: true, color: INK, valign: "middle", margin: 0 });
  s.addText("Four laws describe how. None of them cares about your intentions.", { x: 0.7, y: 4.15, w: 5.6, h: 0.9, fontFace: B, fontSize: 18, color: MUT, margin: 0 });

  // complexity curve vs the ceiling of what a team can hold
  const pts = 24;
  const complexity = Array.from({ length: pts }, (_, i) => Math.round(1000 * Math.exp(i / 6.2) / Math.exp((pts - 1) / 6.2)) / 1000);
  const ceiling = Array.from({ length: pts }, () => 0.42);
  const labels = Array.from({ length: pts }, (_, i) => `${i}`);
  s.addChart(pres.ChartType.line, [
    { name: "complexity", labels, values: complexity },
    { name: "what a team can hold", labels, values: ceiling },
  ], {
    x: 6.9, y: 1.4, w: 5.9, h: 4.6,
    chartColors: [SG, MUT],
    lineSize: 3, lineSmooth: true, lineDataSymbol: "none",
    showLegend: false, showTitle: false,
    catAxisHidden: true, valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" },
    valAxisMinVal: 0, valAxisMaxVal: 1.05,
    chartArea: { fill: { color: BG } }, plotArea: { fill: { color: BG } },
  });
  s.addText("complexity", { x: 11.1, y: 1.45, w: 1.7, h: 0.3, fontFace: B, fontSize: 13, italic: true, color: SG, align: "right", margin: 0 });
  s.addText("what a team can hold", { x: 7.0, y: 3.62, w: 2.6, h: 0.3, fontFace: B, fontSize: 13, italic: true, color: MUT, margin: 0 });
  s.addText("time →", { x: 11.6, y: 6.0, w: 1.2, h: 0.3, fontFace: B, fontSize: 12, color: MUT, align: "right", margin: 0 });

  s.addNotes("Open the section with silence after this line. Then: 'This is not a metaphor and not a warning about bad engineers. Four laws — one from physics, one from empirical software research, one from systems theory, one from economics — describe why every system we build heads this way. Let me give you all four in five minutes, because the rest of this talk is what happens when you ignore them with AI agents.'");
}

// =====================================================================
// PAGE 2 · Law 1 — Software Entropy
// =====================================================================
{
  const s = base("Part 0 · Law 1 of 4 — Software Entropy",
    "Disorder is the default state. Order costs continuous energy.", 28);

  bullets(s, 0.7, 1.85, 5.3, 3.6, [
    "Borrowed straight from the second law of thermodynamics: left alone, every system drifts toward disorder.",
    "In software the leaks are familiar — a feature under deadline, a quick fix, \"we'll clean it later.\" Each adds a little disorder. Nothing removes it unless someone deliberately spends energy: refactoring.",
    "The end state has a name: the Big Ball of Mud — \"haphazardly structured, sprawling, sloppy, duct-tape-and-baling-wire\" (Foote & Yoder, 1997). The most common architecture in the world, and the only one nobody chose.",
  ], { size: 14.5, gap: 12 });
  s.addText("Keep this shape in mind. A context window rots the same way — we'll measure exactly where.",
    { x: 0.7, y: 5.75, w: 5.3, h: 0.7, fontFace: B, fontSize: 13.5, italic: true, color: SG, margin: 0 });

  // --- visual: tidy modules → tangle ---
  const seg = (x1, y1, x2, y2, color, width = 1.25) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipV: (x1 < x2) !== (y1 < y2), line: { color, width },
    });
  const mod = (x, y, color) => {
    s.addShape(pres.ShapeType.roundRect, { x, y, w: 0.5, h: 0.34, rectRadius: 0.05, fill: { color: CARD2 }, line: { color, width: 1.25 } });
  };
  const panel = (x, label) => {
    card(s, x, 2.0, 2.6, 3.5, CARD);
    s.addText(label, { x: x + 0.15, y: 2.08, w: 2.4, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  };

  // day 1: 3x3 grid, orthogonal neighbor links
  panel(6.55, "DAY 1");
  const g = (c, r) => [6.55 + 0.32 + c * 0.82, 2.55 + r * 0.95]; // top-left of module (c,r)
  const gc = (c, r) => { const [x, y] = g(c, r); return [x + 0.25, y + 0.17]; }; // center
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    if (c < 2) { const [x1, y1] = gc(c, r); const [x2, y2] = gc(c + 1, r); seg(x1 + 0.25, y1, x2 - 0.25, y2, MUT); }
    if (r < 2) { const [x1, y1] = gc(c, r); const [x2, y2] = gc(c, r + 1); seg(x1, y1 + 0.17, x2, y2 - 0.17, MUT); }
  }
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) { const [x, y] = g(c, r); mod(x, y, INK); }

  // arrow between panels
  s.addShape(pres.ShapeType.line, { x: 9.3, y: 3.7, w: 0.75, h: 0, line: { color: SG, width: 2.5, endArrowType: "triangle" } });
  s.addText("features\n+ deadlines\n− refactoring", { x: 9.15, y: 3.9, w: 1.05, h: 0.75, fontFace: B, fontSize: 10, color: SG, align: "center", margin: 0 });

  // year 3: jittered modules, many crossing links
  panel(10.2, "YEAR 3");
  const jit = [[0.02, 0.18], [-0.12, -0.08], [0.15, 0.22], [0.2, -0.1], [-0.05, 0.3], [-0.18, 0.05], [0.12, -0.15], [-0.1, 0.25], [0.05, -0.05]];
  const pos = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const [jx, jy] = jit[r * 3 + c];
    pos.push([10.2 + 0.28 + c * 0.78 + jx, 2.55 + r * 0.95 + jy]);
  }
  const links = [[0, 4], [0, 8], [1, 6], [1, 7], [2, 3], [2, 4], [3, 8], [4, 6], [5, 0], [5, 7], [6, 2], [7, 3], [8, 1], [4, 1], [0, 2], [6, 8]];
  links.forEach(([a, b], i) => {
    const [ax, ay] = pos[a]; const [bx, by] = pos[b];
    seg(ax + 0.25, ay + 0.17, bx + 0.25, by + 0.17, BAD, i % 3 === 0 ? 1.75 : 1);
  });
  pos.forEach(([x, y]) => mod(x, y, SG));

  s.addText("Big Ball of Mud", { x: 10.2, y: 5.58, w: 2.6, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: BAD, align: "center", margin: 0 });

  s.addNotes("Law 1 is physics borrowed. The point to land: entropy is not a failure of skill — it's the default direction of every system, and order only exists where someone keeps paying for it. Pause on 'the only architecture nobody chose': every Big Ball of Mud was built by people who intended something else. Plant the seed: a growing context window is a growing system; it accumulates the same disorder. We'll come back to this with numbers.");
}

// =====================================================================
// PAGE 3 · Law 2 — Lehman's Second Law
// =====================================================================
{
  const s = base("Part 0 · Law 2 of 4 — Lehman's Laws of Software Evolution",
    "“Complexity increases — unless work is done to maintain or reduce it.”", 28);
  s.addText("— Meir M. Lehman, Laws of Software Evolution (1974–1980), from two decades of watching IBM’s OS/360 grow",
    { x: 0.7, y: 1.5, w: 8.5, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  bullets(s, 0.7, 2.0, 5.6, 3.5, [
    "These are laws of EVOLVING systems — software embedded in a changing world. Not a warning about bad engineers; a description of what living systems do.",
    "Law I — Continuing Change: a system must keep adapting, or it becomes progressively less useful.",
    "Law II — Increasing Complexity: as it adapts, its complexity grows — unless work is done to maintain or reduce it.",
    "Together they form the trap: you must change; change breeds complexity; and complexity is only ever held back, never solved. The whole law lives in one clause — “unless work is done.”",
  ], { size: 14, gap: 10 });
  s.addText("Remember that clause. In agent systems the “work done” has a name — verification gates and state kept outside the model. Infrastructure is Lehman’s counter-force.",
    { x: 0.7, y: 5.75, w: 5.6, h: 0.85, fontFace: B, fontSize: 13.5, italic: true, color: SG, margin: 0 });

  // --- visual: tug of war on a complexity gauge ---
  s.addText("COMPLEXITY", { x: 8.95, y: 2.0, w: 1.6, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, align: "center", margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: 9.55, y: 2.35, w: 0.4, h: 3.4, rectRadius: 0.2, fill: { color: CARD2 }, line: { color: LINE, width: 1 } });
  s.addText("high", { x: 10.0, y: 2.35, w: 0.6, h: 0.25, fontFace: B, fontSize: 10.5, color: MUT, margin: 0 });
  s.addText("low", { x: 10.0, y: 5.5, w: 0.6, h: 0.25, fontFace: B, fontSize: 10.5, color: MUT, margin: 0 });
  // current level marker
  s.addShape(pres.ShapeType.roundRect, { x: 9.43, y: 3.55, w: 0.64, h: 0.16, rectRadius: 0.06, fill: { color: SG }, line: { type: "none" } });

  // Law I pushes up (left)
  s.addShape(pres.ShapeType.upArrow, { x: 7.85, y: 2.55, w: 0.95, h: 1.55, fill: { color: BAD }, line: { type: "none" } });
  s.addText("Law I · continuing change", { x: 6.7, y: 4.25, w: 2.55, h: 0.35, fontFace: H, fontSize: 13, bold: true, color: BAD, align: "center", margin: 0 });
  s.addText("pushes up. Always. Whether you plan for it or not.", { x: 6.7, y: 4.6, w: 2.55, h: 0.6, fontFace: B, fontSize: 12, color: MUT, align: "center", margin: 0 });

  // deliberate work pushes down (right)
  s.addShape(pres.ShapeType.downArrow, { x: 10.85, y: 3.85, w: 0.95, h: 1.55, fill: { color: GOOD }, line: { type: "none" } });
  s.addText("deliberate work", { x: 10.25, y: 2.55, w: 2.35, h: 0.35, fontFace: H, fontSize: 13, bold: true, color: GOOD, align: "center", margin: 0 });
  s.addText("refactoring · architecture · verification. Pushes down — only while someone pays for it.", { x: 10.25, y: 2.9, w: 2.35, h: 0.85, fontFace: B, fontSize: 12, color: MUT, align: "center", margin: 0 });

  s.addText("The gap between the two arrows is your trajectory.", { x: 6.7, y: 6.0, w: 6.0, h: 0.35, fontFace: B, fontSize: 13.5, italic: true, color: INK, align: "center", margin: 0 });

  s.addNotes("Lehman studied OS/360 for two decades and wrote down what he saw as laws, not advice. Two things to land: (1) 'evolving' — this applies to any system that must keep changing to stay useful, which is every system anyone in this room runs; (2) the clause 'unless work is done' — complexity is a budget line, not a one-time fix. Ask the room: who has a standing line item for REDUCING complexity? That silence is Law II. Then the seed: in agent systems, the counter-force is infrastructure — gates and external state. We'll show what it buys.");
}

// =====================================================================
// PAGE 4 · Law 3 — Gall's Law
// =====================================================================
{
  const s = base("Part 0 · Law 3 of 4 — Gall's Law",
    "“A complex system that works has invariably evolved from a simple system that worked.”", 26);
  s.addText("— John Gall, Systemantics: How Systems Work and Especially How They Fail (1975)",
    { x: 0.7, y: 1.5, w: 8.5, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  bullets(s, 0.7, 2.0, 5.6, 3.6, [
    "The second half is the sharp edge: “A complex system designed from scratch never works and cannot be made to work. You have to start over, beginning with a working simple system.”",
    "This is the only one of the four that is an instruction, not a diagnosis: start with the simplest thing that works, and grow it under real load. Never architect complexity up front.",
    "Why it holds: complexity designed from scratch encodes guesses about problems you haven’t met yet. Complexity grown encodes solutions to problems you actually had. Only the second kind pays rent.",
    "The discipline it demands: every intermediate stage must itself work. A system that is “almost working” at every step is not evolving — it is accumulating.",
  ], { size: 14, gap: 10 });
  s.addText("This is the whole case for “one agent first — raise N only at a boundary.” It is also the epitaph of the 40-agent chain we’ll meet later: designed complex, from scratch, and the only architecture in our data that destroyed work.",
    { x: 0.7, y: 5.7, w: 5.6, h: 0.95, fontFace: B, fontSize: 13, italic: true, color: SG, margin: 0 });

  // --- visual: two paths ---
  const seg = (x1, y1, x2, y2, color, width = 2.25, dash) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipV: (x1 < x2) !== (y1 < y2), line: { color, width, ...(dash ? { dashType: dash } : {}) },
    });
  card(s, 6.8, 1.95, 5.95, 4.4, CARD);
  s.addText("complexity ↑", { x: 6.95, y: 2.05, w: 1.6, h: 0.28, fontFace: B, fontSize: 10.5, color: MUT, margin: 0 });
  s.addText("time →", { x: 11.6, y: 5.98, w: 1.0, h: 0.28, fontFace: B, fontSize: 10.5, color: MUT, align: "right", margin: 0 });

  // path A: designed complex from scratch — straight, steep, dashed, ends in ✕
  seg(7.35, 5.55, 9.3, 2.55, BAD, 2.25, "dash");
  s.addText("✕", { x: 9.12, y: 2.22, w: 0.4, h: 0.4, fontFace: H, fontSize: 20, bold: true, color: BAD, align: "center", margin: 0 });
  s.addText("designed complex, from scratch\n— never works", { x: 6.95, y: 2.4, w: 2.15, h: 0.55, fontFace: B, fontSize: 11, color: BAD, align: "right", margin: 0 });

  // path B: staircase — each step works
  const steps = [[7.35, 8.55, 5.55, "simple ✓"], [8.55, 9.75, 4.75, "working ✓"], [9.75, 10.95, 3.95, "grown ✓"], [10.95, 12.45, 3.15, "complex — and works ✓"]];
  steps.forEach(([x1, x2, y, label], i) => {
    seg(x1, y, x2, y, GOOD, 3);
    if (i < steps.length - 1) seg(x2, y, x2, steps[i + 1][2], GOOD, 3);
    s.addText(label, { x: x1 + (i === 0 ? 0.45 : 0), y: y - 0.34, w: x2 - x1 + 0.3, h: 0.3, fontFace: B, fontSize: 11, bold: true, color: GOOD, margin: 0 });
  });
  s.addText("grown from a working simple system — every step works", { x: 7.35, y: 5.68, w: 4.0, h: 0.3, fontFace: B, fontSize: 11, italic: true, color: GOOD, margin: 0 });

  s.addNotes("Gall was a pediatrician who wrote a half-satirical book about systems in 1975; this law survived because every engineer recognizes it from experience. Land the shift in register: the first two laws describe; this one INSTRUCTS. Simplest working thing, then grow under load. Then the connection: 'designed complex from scratch' is exactly how most multi-agent systems get built — org chart first, roles first, forty agents on day one. Preview the punchline: the one architecture in our benchmark that permanently lost work was the most ambitious one, designed rather than grown.");
}

// =====================================================================
// PAGE 5 · Law 4 — Technical Bankruptcy
// =====================================================================
{
  const s = base("Part 0 · Law 4 of 4 — Technical Bankruptcy",
    "Debt is fine. Interest is what kills you.", 30);
  s.addText("— the metaphor is Ward Cunningham’s (1992); “bankruptcy” is what the industry calls the day the interest exceeds the payroll",
    { x: 0.7, y: 1.5, w: 9.5, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  bullets(s, 0.7, 2.0, 5.6, 3.6, [
    "Every shortcut is a loan: the feature now, the payment later. Cunningham’s point was never “don’t borrow” — a team that never takes shortcuts dies of caution. The point is that debt carries interest.",
    "Entropy is the interest rate. Each shortcut makes the next change slower — and the payments grow whether or not you keep borrowing. (Laws 1 and 2, priced.)",
    "Bankruptcy is the day a trivial change costs more than the team can pay. “The system is too fragile to touch.” The only move left is the rewrite.",
    "And the rewrite restarts the same curve. Most rewrites faithfully rebuild the original Big Ball of Mud in a newer language — because the process that generated the debt never changed.",
  ], { size: 14, gap: 10 });
  s.addText("In agent systems the loan is an unverified handoff — one agent’s output taken on faith by the next. The interest compounds per hop. Later we watch a chain go bankrupt in 40 stages.",
    { x: 0.7, y: 5.7, w: 5.6, h: 0.95, fontFace: B, fontSize: 13, italic: true, color: SG, margin: 0 });

  // --- visual: compounding cost, the cliff of the rewrite, and the curve starting again ---
  const N1 = 16, N2 = 8;
  const rise1 = Array.from({ length: N1 }, (_, i) => Math.round(1000 * Math.exp(i / 4.6) / Math.exp((N1 - 1) / 4.6)) / 1000);
  const rise2 = Array.from({ length: N2 }, (_, i) => Math.round(1000 * 0.06 * Math.exp(i / 2.9)) / 1000);
  const cost = [...rise1, ...rise2];
  const payroll = cost.map(() => 0.55);
  const labels = cost.map((_, i) => `${i}`);
  s.addChart(pres.ChartType.line, [
    { name: "cost of the next change", labels, values: cost },
    { name: "what the team can pay", labels, values: payroll },
  ], {
    x: 6.9, y: 1.9, w: 5.9, h: 4.3,
    chartColors: [SG, MUT], lineSize: 3, lineSmooth: false, lineDataSymbol: "none",
    showLegend: false, showTitle: false, catAxisHidden: true, valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" },
    valAxisMinVal: 0, valAxisMaxVal: 1.05,
    chartArea: { fill: { color: BG } }, plotArea: { fill: { color: BG } },
  });
  s.addText("cost of the next change", { x: 7.9, y: 2.35, w: 2.2, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "right", margin: 0 });
  s.addText("what the team can pay", { x: 7.0, y: 3.55, w: 2.4, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });
  s.addText("bankruptcy", { x: 8.35, y: 4.45, w: 1.15, h: 0.3, fontFace: H, fontSize: 12.5, bold: true, color: BAD, align: "right", margin: 0 });
  s.addText("the rewrite ↓", { x: 10.85, y: 2.05, w: 1.3, h: 0.3, fontFace: H, fontSize: 12.5, bold: true, color: BAD, margin: 0 });
  s.addText("…and it starts again", { x: 11.0, y: 3.05, w: 1.75, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "right", margin: 0 });
  s.addText("time →", { x: 11.7, y: 6.15, w: 1.1, h: 0.28, fontFace: B, fontSize: 10.5, color: MUT, align: "right", margin: 0 });

  s.addNotes("Cunningham coined 'technical debt' in 1992 to explain to a finance-minded boss why shipping fast now would slow them later. Two things to land: (1) borrowing is legitimate — the sin is ignoring the interest; (2) the rewrite is not a fix, it's a bankruptcy filing, and without changing the process it reproduces the same curve. Point at the second rise on the chart. Then the bridge to agents: every unverified handoff is a loan taken on faith, and the interest compounds per hop — that's the chain we'll watch fail. This is also why the field's multi-agent frameworks keep getting rewritten: MAST's 14 failure modes read like a bankruptcy report.");
}

// =====================================================================
// PAGE 6 · Part 1 — What is an agent? (anatomy)
// =====================================================================
{
  const s = base("Part 1 · What is an agent?",
    "An agent is a loop: a model, a set of tools, and a transcript.", 30);

  bullets(s, 0.7, 1.85, 5.5, 3.9, [
    "The model is a function. Text in, text out. It is stateless — it remembers nothing between calls.",
    "The tools are functions the model may ASK for: read a file, edit it, run the tests, search. The model never executes anything. It emits a request; the harness runs it and hands back the result.",
    "The loop is the harness: call the model → if it asked for a tool, run it and append the result → call the model again. Repeat until it says “done” or the budget runs out.",
    "The transcript is the growing record of everything so far — the brief, every request, every result. It is re-sent IN FULL on every turn. It is the agent’s memory. Nothing else is.",
  ], { size: 14, gap: 11 });
  s.addText("Hold onto that last sentence. Everything in Part 2 follows from it.",
    { x: 0.7, y: 5.95, w: 5.5, h: 0.5, fontFace: B, fontSize: 13.5, italic: true, color: SG, margin: 0 });

  // --- visual: the loop ---
  const arrow = (x1, y1, x2, y2, color = MUT, begin = false) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipV: y2 < y1, flipH: false,
      line: { color, width: 2, ...(begin ? { beginArrowType: "triangle" } : { endArrowType: "triangle" }) },
    });
  const box = (x, y, w, h, title, sub, color = INK) => {
    card(s, x, y, w, h, CARD2);
    s.addText(title, { x: x + 0.1, y: y + 0.08, w: w - 0.2, h: 0.32, fontFace: H, fontSize: 12.5, bold: true, color, align: "center", margin: 0 });
    if (sub) s.addText(sub, { x: x + 0.1, y: y + 0.42, w: w - 0.2, h: h - 0.5, fontFace: B, fontSize: 10.5, color: MUT, align: "center", margin: 0 });
  };

  // transcript (tall, grows)
  card(s, 7.0, 2.3, 1.75, 3.3, CARD);
  s.addText("TRANSCRIPT", { x: 7.0, y: 2.38, w: 1.75, h: 0.3, fontFace: H, fontSize: 11, bold: true, color: INK, charSpacing: 2, align: "center", margin: 0 });
  ["brief", "request: read", "result", "request: edit", "result", "…"].forEach((t, i) => {
    s.addShape(pres.ShapeType.roundRect, { x: 7.15, y: 2.78 + i * 0.42, w: 1.45, h: 0.32, rectRadius: 0.05, fill: { color: CARD2 }, line: { color: LINE, width: 1 } });
    s.addText(t, { x: 7.15, y: 2.78 + i * 0.42, w: 1.45, h: 0.32, fontFace: M, fontSize: 9.5, color: t.startsWith("request") ? SW : t === "…" ? MUT : INK, align: "center", valign: "middle", margin: 0 });
  });
  s.addText("grows every turn", { x: 6.9, y: 5.65, w: 1.95, h: 0.28, fontFace: B, fontSize: 10.5, italic: true, color: MUT, align: "center", margin: 0 });

  // model + tools
  box(9.45, 3.35, 1.6, 1.15, "MODEL", "text in → text out\nstateless");
  box(11.3, 3.35, 1.45, 1.15, "TOOLS", "read · edit\nrun tests · search");

  // arrows: transcript → model (replayed in full)
  arrow(8.75, 3.92, 9.45, 3.92, SG);
  s.addText("replayed\nin full", { x: 8.62, y: 3.15, w: 0.95, h: 0.7, fontFace: B, fontSize: 10, italic: true, color: SG, align: "center", margin: 0 });
  // model → tools (request)
  arrow(11.05, 3.75, 11.3, 3.75, SW);
  s.addText("request", { x: 10.75, y: 3.05, w: 0.9, h: 0.28, fontFace: B, fontSize: 10, color: SW, align: "center", margin: 0 });
  // tools → transcript (result appended): down, then left with arrow at the left end
  arrow(12.0, 4.5, 12.0, 5.25, MUT);
  s.addShape(pres.ShapeType.line, { x: 8.75, y: 5.25, w: 3.25, h: 0.001, line: { color: MUT, width: 2, beginArrowType: "triangle" } });
  s.addText("result appended to the transcript", { x: 8.9, y: 5.32, w: 3.0, h: 0.28, fontFace: B, fontSize: 10, italic: true, color: MUT, align: "center", margin: 0 });
  // model → done
  arrow(10.25, 3.35, 10.25, 2.55, GOOD);
  s.addText("“done” → answer", { x: 9.55, y: 2.2, w: 1.5, h: 0.3, fontFace: B, fontSize: 10.5, bold: true, color: GOOD, align: "center", margin: 0 });
  s.addText("one turn = one trip around the loop", { x: 8.9, y: 6.0, w: 3.9, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: INK, align: "center", margin: 0 });

  s.addNotes("Demystify before anything else. Four parts, and only one of them is intelligent. The model is a pure function — emphasize 'stateless' with a pause; most of the room believes the model 'remembers' the conversation. The tools are requests, not actions: the model writes 'please run the tests', the harness runs them. The loop is just a while-loop. And the transcript — say this slowly — is re-sent in full every turn. It is the only memory there is. Next slide draws the consequence.");
}

// =====================================================================
// PAGE 6b · Part 1 — Same model, same code: only the context changed
// =====================================================================
{
  const s = base("Part 1 · What is an agent? — an example",
    "Same model. Same code. Only the context changed.", 30);
  s.addText("Ask a model if code is correct and it reads it the way you read code on paper: it can only guess. Put the result of RUNNING the code into its context, and it can verify, diagnose, and fix.",
    { x: 0.7, y: 1.5, w: 11.9, h: 0.5, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  const arrow = (x1, y1, x2, y2, color = MUT) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width: 2, endArrowType: "triangle" },
    });
  const code = (x, y, w, h, lines, color = INK) => {
    s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.05, fill: { color: BG }, line: { color: LINE, width: 1 } });
    s.addText(lines.map((t, i) => ({ text: t, options: { breakLine: i < lines.length - 1 } })),
      { x: x + 0.12, y: y + 0.07, w: w - 0.24, h: h - 0.14, fontFace: M, fontSize: 10, color, valign: "top", margin: 0 });
  };
  const modelBox = (x, y, color) => {
    card(s, x, y, 1.15, 0.7, CARD2);
    s.addText("MODEL", { x, y: y + 0.09, w: 1.15, h: 0.28, fontFace: H, fontSize: 11.5, bold: true, color, align: "center", margin: 0 });
    s.addText("same weights", { x, y: y + 0.38, w: 1.15, h: 0.25, fontFace: B, fontSize: 9, color: MUT, align: "center", margin: 0 });
  };
  const bubble = (x, y, w, h, text, color) => {
    s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.1, fill: { color: CARD2 }, line: { color, width: 1.5 } });
    s.addText(text, { x: x + 0.15, y: y + 0.08, w: w - 0.3, h: h - 0.16, fontFace: B, fontSize: 11, color: INK, valign: "middle", margin: 0 });
  };
  const snippet = ["def median(xs):", "    xs.sort()", "    return xs[len(xs) // 2]"];

  // ---- CALL 1: the code as text
  card(s, 0.7, 2.15, 5.85, 4.1, CARD);
  s.addText("CALL 1 · THE CODE, AS TEXT", { x: 0.9, y: 2.25, w: 4.0, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  s.addText("a model", { x: 4.6, y: 2.25, w: 1.75, h: 0.28, fontFace: B, fontSize: 10.5, italic: true, color: MUT, align: "right", margin: 0 });
  s.addText("context", { x: 0.9, y: 2.62, w: 1.0, h: 0.25, fontFace: H, fontSize: 8.5, bold: true, color: SG, charSpacing: 1, margin: 0 });
  code(0.9, 2.9, 2.75, 0.95, snippet);
  code(0.9, 3.95, 2.75, 0.5, ["“Is this correct?”"], MUT);
  arrow(3.65, 3.9, 4.15, 3.9, SG);
  modelBox(4.15, 3.55, MUT);
  arrow(4.72, 4.25, 4.72, 4.6, MUT);
  bubble(1.1, 4.65, 5.2, 0.8, "“Looks correct — it sorts the list and returns the middle element.”  ✓", MUT);
  s.addText("A guess. Plausible, confident, unverifiable — and wrong. It has no way to check. It never had.",
    { x: 0.9, y: 5.6, w: 5.5, h: 0.55, fontFace: B, fontSize: 11.5, italic: true, color: BAD, margin: 0 });

  // ---- CALL 2: the code + a tool result
  card(s, 6.8, 2.15, 5.85, 4.1, CARD);
  s.addText("CALL 2 · THE CODE + ITS OUTPUT WHEN RUN", { x: 7.0, y: 2.25, w: 4.4, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: GOOD, charSpacing: 2, margin: 0 });
  s.addText("a coding agent", { x: 10.9, y: 2.25, w: 1.55, h: 0.28, fontFace: B, fontSize: 10.5, italic: true, color: GOOD, align: "right", margin: 0 });
  s.addText("context", { x: 7.0, y: 2.62, w: 1.0, h: 0.25, fontFace: H, fontSize: 8.5, bold: true, color: SG, charSpacing: 1, margin: 0 });
  code(7.0, 2.9, 2.75, 0.95, snippet);
  code(7.0, 3.95, 2.75, 0.85, [">>> median([1, 2, 3, 4])", "3", "# expected 2.5"], SW);
  s.addText("TOOL RESULT · the harness ran it", { x: 7.0, y: 4.84, w: 2.75, h: 0.22, fontFace: H, fontSize: 8.5, bold: true, color: SW, charSpacing: 1, margin: 0 });
  arrow(9.75, 3.9, 10.25, 3.9, SG);
  modelBox(10.25, 3.55, GOOD);
  arrow(10.82, 4.25, 10.82, 5.05, GOOD);
  bubble(7.2, 5.1, 5.25, 0.8, "“Wrong for even length — it returns the upper middle. Fix: average the two middle values. Also sort a copy: xs.sort() mutates the caller’s list.”", GOOD);
  s.addText("Now it can verify, diagnose, fix — and ask to run it again.",
    { x: 7.0, y: 5.95, w: 5.5, h: 0.28, fontFace: B, fontSize: 11.5, italic: true, color: GOOD, margin: 0 });

  s.addText("The tool did not make the model smarter. It put evidence into the context. Model + tools + the context those tools produce = an agent.",
    { x: 0.7, y: 6.45, w: 12.0, h: 0.5, fontFace: B, fontSize: 13.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("The cheapest demo of the whole thesis. Left: paste code, ask 'is this correct?'. The model answers with confidence — and it's a guess; it has the same information you'd have reading it on paper. Right: identical model, identical code, plus one thing — the output of actually running it, which the harness put into the context. Now it verifies, diagnoses, proposes a fix, and can ask to run again. Nothing about the model changed. Say it plainly: a 'coding agent' is a model whose context contains the results of tools. That is why the transcript is the agent (next slide) — and why what each call gets to see is the real design question (Part 2).");
}

// =====================================================================
// PAGE 7 · Part 1 — The reveal: the agent is the transcript
// =====================================================================
{
  const s = base("Part 1 · What is an agent? — the reveal",
    "There are no agents — only stateless calls.", 30);
  s.addText("What we call an “agent” is a story the loop tells a memoryless model. Which means the story can be told to any model.",
    { x: 0.7, y: 1.5, w: 10.5, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  const cons = [
    [GOOD, "The agent is the transcript, not the process.", "Hand the same transcript to a fresh call — any call, any machine — and the same agent continues, mid-thought. It doesn’t know it died."],
    [BAD, "Lose the transcript and the agent is gone.", "Even if the process is alive. A model with an empty context is not an agent that forgot — it is no agent at all."],
    [SG, "So whoever holds the context holds the agent.", "Keep it outside the process and the agent can be resurrected anywhere, by any copy of the model. Copy it twice and you have two."],
  ];
  cons.forEach(([c, head, body], i) => {
    const y = 2.0 + i * 1.28;
    card(s, 0.7, y, 5.6, 1.12);
    chip(s, 0.95, y + 0.2, c);
    s.addText(head, { x: 1.25, y: y + 0.1, w: 4.9, h: 0.35, fontFace: H, fontSize: 14, bold: true, color: INK, margin: 0 });
    s.addText(body, { x: 1.25, y: y + 0.47, w: 4.9, h: 0.62, fontFace: B, fontSize: 12, color: MUT, margin: 0 });
  });
  s.addText("There was never a “one” to begin with. Once you see that, the question is no longer how many agents you have — it is what each call gets to see. That is Part 2.",
    { x: 0.7, y: 5.95, w: 5.6, h: 0.9, fontFace: B, fontSize: 13, italic: true, color: SG, margin: 0 });

  // --- visual: regeneration ---
  const arrow = (x1, y1, x2, y2, color = MUT) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipV: y2 < y1, line: { color, width: 2, endArrowType: "triangle" },
    });
  const modelBox = (x, y, title, sub, color, dead = false) => {
    card(s, x, y, 1.6, 1.05, CARD2);
    s.addText(title, { x, y: y + 0.1, w: 1.6, h: 0.32, fontFace: H, fontSize: 12.5, bold: true, color, align: "center", margin: 0 });
    s.addText(sub, { x: x + 0.05, y: y + 0.45, w: 1.5, h: 0.55, fontFace: B, fontSize: 10.5, color: MUT, align: "center", margin: 0 });
    if (dead) s.addText("✕", { x: x + 1.1, y: y - 0.2, w: 0.5, h: 0.5, fontFace: H, fontSize: 24, bold: true, color: BAD, align: "center", margin: 0 });
  };

  // the transcript, kept outside
  card(s, 6.95, 2.15, 1.75, 3.2, CARD);
  s.addText("TRANSCRIPT", { x: 6.95, y: 2.23, w: 1.75, h: 0.3, fontFace: H, fontSize: 11, bold: true, color: INK, charSpacing: 2, align: "center", margin: 0 });
  ["brief", "request: read", "result", "request: edit", "result", "turn 41 …"].forEach((t, i) => {
    s.addShape(pres.ShapeType.roundRect, { x: 7.1, y: 2.63 + i * 0.42, w: 1.45, h: 0.32, rectRadius: 0.05, fill: { color: CARD2 }, line: { color: LINE, width: 1 } });
    s.addText(t, { x: 7.1, y: 2.63 + i * 0.42, w: 1.45, h: 0.32, fontFace: M, fontSize: 9.5, color: t.startsWith("request") ? SW : INK, align: "center", valign: "middle", margin: 0 });
  });
  s.addText("stored outside\nany process", { x: 6.85, y: 5.4, w: 1.95, h: 0.5, fontFace: B, fontSize: 10.5, italic: true, color: MUT, align: "center", margin: 0 });

  // scenario A: process 1 dies at turn 41
  modelBox(9.6, 2.25, "MODEL · call #41", "the process that\nran turns 1–41", MUT, true);
  arrow(8.7, 2.9, 9.6, 2.9, LINE);
  s.addText("process dies", { x: 9.6, y: 3.35, w: 1.6, h: 0.28, fontFace: B, fontSize: 10.5, italic: true, color: BAD, align: "center", margin: 0 });

  // scenario B: same transcript → fresh process → turn 42
  modelBox(9.6, 4.2, "MODEL · call #42", "a fresh process,\nanother machine", GOOD);
  arrow(8.7, 4.72, 9.6, 4.72, GOOD);
  s.addText("same transcript", { x: 8.55, y: 4.35, w: 1.2, h: 0.3, fontFace: B, fontSize: 10, italic: true, color: GOOD, align: "center", margin: 0 });
  arrow(11.2, 4.72, 11.75, 4.72, GOOD);
  card(s, 11.75, 4.3, 1.0, 0.85, CARD2);
  s.addText("turn 42", { x: 11.75, y: 4.38, w: 1.0, h: 0.3, fontFace: M, fontSize: 11, bold: true, color: GOOD, align: "center", margin: 0 });
  s.addText("as if nothing\nhappened", { x: 11.75, y: 4.66, w: 1.0, h: 0.45, fontFace: B, fontSize: 9.5, color: MUT, align: "center", margin: 0 });

  s.addText("Same agent. Different process. Nothing was lost — because nothing lived in the process.", { x: 6.9, y: 6.0, w: 5.9, h: 0.5, fontFace: B, fontSize: 12.5, italic: true, color: INK, align: "center", margin: 0 });

  s.addNotes("Deliver the title slowly. Then the turn: because the model is stateless, the 'agent' is entirely contained in the transcript — so it can be REGENERATED. Walk the diagram: the process running call 41 dies. Hand the very same transcript to a fresh process on another machine, and call 42 happens as if nothing occurred. The agent never noticed its own death. Then the mirror image: keep the process, lose the transcript — no agent. Land the conclusion: whoever holds the context holds the agent. Store it outside, resurrect it anywhere, copy it and there are two. Then cue the clip on the next slide.");
}

// =====================================================================
// PAGE 8 · Interlude — "There is no spoon."
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("PART 1 · INTERLUDE", { x: 0.7, y: 0.5, w: 8, h: 0.3, fontFace: H, fontSize: 11, bold: true, color: MUT, charSpacing: 3, margin: 0 });

  // video frame (16:9) — insert the clip here via Insert → Video → Online Video
  const fx = 2.67, fy = 1.05, fw = 8.0, fh = 4.5;
  s.addShape(pres.ShapeType.roundRect, { x: fx, y: fy, w: fw, h: fh, rectRadius: 0.1, fill: { color: "0B0E10" }, line: { color: LINE, width: 1.5 } });
  s.addShape(pres.ShapeType.ellipse, { x: fx + fw / 2 - 0.55, y: fy + fh / 2 - 0.55, w: 1.1, h: 1.1, fill: { color: CARD2 }, line: { color: INK, width: 2 } });
  s.addShape(pres.ShapeType.triangle, { x: fx + fw / 2 - 0.2, y: fy + fh / 2 - 0.28, w: 0.5, h: 0.56, rotate: 90, fill: { color: INK }, line: { type: "none" } });
  s.addText("The Matrix (1999) — the spoon boy scene", { x: fx, y: fy + fh - 0.5, w: fw, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, align: "center", margin: 0 });
  s.addText([{ text: "▶ find the clip", options: { hyperlink: { url: "https://www.youtube.com/results?search_query=the+matrix+there+is+no+spoon+scene" }, color: SW } }],
    { x: fx, y: fy + 0.2, w: fw, h: 0.3, fontFace: B, fontSize: 11, align: "center", margin: 0 });

  // the echo
  s.addText("“There is no spoon.”", { x: 0.9, y: 5.85, w: 5.6, h: 0.6, fontFace: H, fontSize: 24, italic: true, color: INK, align: "right", margin: 0 });
  s.addText("— The Matrix, 1999", { x: 0.9, y: 6.45, w: 5.6, h: 0.3, fontFace: B, fontSize: 12, color: MUT, align: "right", margin: 0 });
  s.addShape(pres.ShapeType.line, { x: 6.66, y: 5.9, w: 0.001, h: 0.85, line: { color: LINE, width: 1.5 } });
  s.addText("There is no agent.", { x: 6.85, y: 5.85, w: 5.6, h: 0.6, fontFace: H, fontSize: 24, bold: true, color: SG, margin: 0 });
  s.addText("— only the context that regenerates it", { x: 6.85, y: 6.45, w: 5.6, h: 0.3, fontFace: B, fontSize: 12, color: MUT, margin: 0 });

  s.addNotes("TO EMBED THE CLIP: in PowerPoint, select this slide → Insert → Video → Online Video → paste the YouTube URL of the spoon-boy scene; size it to the dark frame. (Embedding via YouTube is the legitimate route — don't ship a downloaded copy of the film.) Play ~60 seconds. Then, in your words: the boy's point is that the spoon isn't the thing — the mind is; bend the mind and the spoon follows. Our version: the agent isn't the thing — the context is. Bend the context, and the agent follows. Hold the beat, then move to Part 2.");
}

// =====================================================================
// PAGE 10 · Part 2 — Why swarms? The obsession (meme slot)
// =====================================================================
{
  const s = base("Part 2 · Why swarms? — the obsession",
    "Why is everyone building swarms?", 30);

  // meme slot — replace with your image (Insert → Pictures), keep this frame's size
  s.addShape(pres.ShapeType.roundRect, { x: 0.7, y: 1.75, w: 4.7, h: 4.15, rectRadius: 0.1, fill: { color: "0B0E10" }, line: { color: MUT, width: 1.5, dashType: "dash" } });
  s.addText("MEME GOES HERE", { x: 0.7, y: 3.45, w: 4.7, h: 0.4, fontFace: H, fontSize: 14, bold: true, color: MUT, charSpacing: 3, align: "center", margin: 0 });
  s.addText("Insert → Pictures, then size to this frame", { x: 0.7, y: 3.9, w: 4.7, h: 0.3, fontFace: B, fontSize: 10.5, italic: true, color: LINE, align: "center", margin: 0 });

  // four reasons
  const reasons = [
    [SG, "The org-chart metaphor", "We called them “agents,” so we scale like hiring. But calls have no identity, no on-the-job learning, no cheap coordination. People aren’t designing systems — they’re drawing org charts."],
    [SW, "Demo economics", "Forty progress bars advancing in parallel go viral. “Idempotent task leasing” does not. Part of the obsession is content."],
    [SW, "Vendor incentives", "“Fleet” is a pricing-page word. Agent count is legible to buyers and boards; handoff-verification rate is not — even though it’s the number that predicts success."],
    [BAD, "Real pain, wrong prescription", "The pains are real — the window, the crash, the backlog. “More agents” pattern-matches to microservices, which scaled throughput, never intelligence."],
  ];
  reasons.forEach(([c, head, body], i) => {
    const y = 1.75 + i * 1.07;
    card(s, 5.75, y, 7.0, 0.97);
    chip(s, 5.98, y + 0.16, c);
    s.addText(head, { x: 6.28, y: y + 0.07, w: 6.3, h: 0.32, fontFace: H, fontSize: 13.5, bold: true, color: c === BAD ? BAD : INK, margin: 0 });
    s.addText(body, { x: 6.28, y: y + 0.4, w: 6.3, h: 0.55, fontFace: B, fontSize: 11.5, color: MUT, margin: 0 });
  });

  s.addText("Three of these four reasons are about us, not about systems. The fourth is the one worth taking seriously — because the pain behind it is real. Next page.",
    { x: 0.7, y: 6.1, w: 12.0, h: 0.6, fontFace: B, fontSize: 13.5, italic: true, color: SG, margin: 0 });

  s.addNotes("Let the meme get its laugh, then go sober: 'here is the autopsy.' Four reasons. The first three are sociology — metaphor, content, sales — and it's worth saying out loud that most swarm architectures are org charts with API keys. The fourth is different in kind: the pain is genuine. Slow down on it. Microservices is the tell — we all remember scaling a service by splitting it, and we forget that it scaled THROUGHPUT, never how smart the service was. Hand off: 'so let's take the fourth reason seriously.'");
}

// =====================================================================
// PAGE 11 · Part 2 — Is it necessary? What users want
// =====================================================================
{
  const s = base("Part 2 · Why swarms? — is it actually necessary?",
    "Nobody wants agents. They want work that doesn’t get lost.", 30);

  // left: what users say → what that actually is
  s.addText("WHAT USERS SAY", { x: 0.7, y: 1.8, w: 3.0, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  s.addText("WHAT THAT ACTUALLY IS", { x: 4.05, y: 1.8, w: 2.4, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  const rows = [
    ["“Just get it done — I’ll check in the morning.”", "unattended operation: a scheduler"],
    ["“Don’t lose my work when something breaks.”", "durable state outside any process"],
    ["“I need to be able to trust the result.”", "verification gates"],
    ["“Clear the backlog faster than I can alone.”", "a queue + parallel workers"],
    ["“…and don’t surprise me on cost.”", "budgets and leases"],
  ];
  rows.forEach(([say, is], i) => {
    const y = 2.2 + i * 0.74;
    s.addShape(pres.ShapeType.line, { x: 0.7, y: y - 0.08, w: 5.75, h: 0.001, line: { color: LINE, width: 0.75 } });
    s.addText(say, { x: 0.7, y, w: 3.0, h: 0.6, fontFace: B, fontSize: 12.5, italic: true, color: INK, valign: "middle", margin: 0 });
    s.addText("→", { x: 3.7, y, w: 0.3, h: 0.6, fontFace: B, fontSize: 13, color: MUT, align: "center", valign: "middle", margin: 0 });
    s.addText(is, { x: 4.05, y, w: 2.4, h: 0.6, fontFace: B, fontSize: 12.5, bold: true, color: SW, valign: "middle", margin: 0 });
  });
  s.addText("Every item in the right column is a property of infrastructure. None is a property of agent count.",
    { x: 0.7, y: 5.95, w: 5.75, h: 0.6, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  // right: the three walls a single context hits — the legitimate motivation
  s.addText("THE THREE WALLS A SINGLE CONTEXT HITS", { x: 6.85, y: 1.8, w: 5.9, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  const walls = [
    [SG, "The window", "The task’s inputs don’t fit in one context. Not a slow fade — a hard edge.", "needs: somewhere outside the context to keep the inputs"],
    [BAD, "The crash", "Everything in flight dies with the transcript. The longer the horizon, the more certain the loss.", "needs: somewhere outside the context to keep the progress"],
    [SW, "The backlog", "One thread. One human watching it. Everything serialized behind both.", "needs: a queue, and more than one worker"],
  ];
  // memorable glyphs, drawn as shapes: bar hitting a ceiling · lightning · a stacked queue
  const glyph = (i, x, y, c) => {
    if (i === 0) {
      s.addShape(pres.ShapeType.line, { x, y, w: 0.6, h: 0.001, line: { color: c, width: 2, dashType: "dash" } });
      s.addShape(pres.ShapeType.roundRect, { x: x + 0.2, y: y + 0.1, w: 0.2, h: 0.62, rectRadius: 0.04, fill: { color: c }, line: { type: "none" } });
    } else if (i === 1) {
      s.addShape(pres.ShapeType.lightningBolt, { x: x + 0.05, y: y - 0.02, w: 0.5, h: 0.76, fill: { color: c }, line: { type: "none" } });
    } else {
      [0, 0.24, 0.48].forEach((dy, k) => s.addShape(pres.ShapeType.roundRect, { x: x + (k === 1 ? 0.06 : 0), y: y + 0.08 + dy, w: 0.6 - (k === 1 ? 0.12 : 0), h: 0.16, rectRadius: 0.04, fill: { color: c }, line: { type: "none" } }));
    }
  };
  walls.forEach(([c, head, body, need], i) => {
    const y = 2.2 + i * 1.28;
    card(s, 6.85, y, 5.9, 1.15);
    glyph(i, 7.05, y + 0.2, c);
    s.addText(head, { x: 7.85, y: y + 0.08, w: 4.8, h: 0.32, fontFace: H, fontSize: 14, bold: true, color: INK, margin: 0 });
    s.addText(body, { x: 7.85, y: y + 0.42, w: 4.8, h: 0.4, fontFace: B, fontSize: 11.5, color: MUT, margin: 0 });
    s.addText(need, { x: 7.85, y: y + 0.8, w: 4.8, h: 0.3, fontFace: B, fontSize: 11.5, bold: true, color: c, margin: 0 });
  });

  s.addText("Three real needs — and every one of them is about where state lives, not how many agents you run. Hold that thought.",
    { x: 6.85, y: 6.05, w: 5.9, h: 0.6, fontFace: B, fontSize: 13, italic: true, color: SG, margin: 0 });

  s.addNotes("Left side first: translate what users actually ask for into what it technically is. Read a row or two aloud — 'check in the morning' is a scheduler; 'don't lose my work' is durable state. Land the line under the table: every one is an infrastructure property, none is agent count. Then the right side: the fourth reason from the previous page, taken seriously. Three walls a single context genuinely hits — the window, the crash, the backlog — and under each, what it actually NEEDS. Notice the pattern out loud: 'outside the context', 'outside the context', 'a queue'. The audience should already be able to guess the next slide's answer.");
}

// =====================================================================
// PAGE 12 · Part 2 — Why do we insist they talk?
// =====================================================================
{
  const s = base("Part 2 · Why swarms? — why do we insist they talk?",
    "We made them talk like us. But an agent is its context — and context is finite.", 27);
  s.addText("Chat is how humans coordinate, so it is the first thing we built. Every message an agent reads is context it spends; every message it passes on is a summary.",
    { x: 0.7, y: 1.58, w: 11.8, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  // line from (x1,y1) to (x2,y2): flipH when going left, flipV when going up
  const seg = (x1, y1, x2, y2, color, width = 1.75, both = false) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1,
      line: { color, width, endArrowType: "triangle", ...(both ? { beginArrowType: "triangle" } : {}) },
    });
  const agent = (x, y, label, color = INK) => {
    card(s, x, y, 0.95, 0.6, CARD2);
    s.addText(label, { x, y, w: 0.95, h: 0.6, fontFace: H, fontSize: 11.5, bold: true, color, align: "center", valign: "middle", margin: 0 });
  };

  // ---------- left: human-style coordination — agents talk ----------
  card(s, 0.7, 1.95, 5.75, 3.95, CARD);
  s.addText("HUMAN-STYLE COORDINATION · AGENTS TALK", { x: 0.9, y: 2.05, w: 5.4, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: BAD, charSpacing: 2, margin: 0 });
  const notes = ["“threshold must be inclusive — use >= in quote_total”", "“the threshold thing was fixed”", "“some fix was applied”", "“done ✓”"];
  const xs = [0.95, 2.35, 3.75, 5.15];
  xs.forEach((x, i) => {
    s.addShape(pres.ShapeType.roundRect, { x: x - 0.1, y: 2.5, w: 1.2, h: 0.95, rectRadius: 0.08, fill: { color: BG }, line: { color: i === 3 ? GOOD : LINE, width: 1 } });
    s.addText(notes[i], { x: x - 0.05, y: 2.55, w: 1.1, h: 0.85, fontFace: B, fontSize: i === 3 ? 12 : 9.5, italic: i !== 3, bold: i === 3, color: i === 3 ? GOOD : i === 0 ? INK : MUT, align: "center", valign: "middle", margin: 0 });
    agent(x, 3.7, `agent ${i + 1}`);
    if (i < 3) seg(x + 0.95, 4.0, xs[i + 1], 4.0, MUT, 1.75);
  });
  s.addText("it wasn’t.", { x: 5.05, y: 4.35, w: 1.15, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: BAD, align: "center", margin: 0 });
  s.addText("each message is a lossy summary  ·  every participant must hold the whole conversation  ·  the conversation grows, the context does not",
    { x: 0.9, y: 5.05, w: 5.4, h: 0.75, fontFace: B, fontSize: 11, color: MUT, align: "center", margin: 0 });

  // ---------- right: agents share state, not messages ----------
  card(s, 6.85, 1.95, 5.9, 3.95, CARD);
  s.addText("THE ALTERNATIVE · AGENTS SHARE STATE", { x: 7.05, y: 2.05, w: 5.5, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: GOOD, charSpacing: 2, margin: 0 });
  card(s, 9.05, 3.05, 1.55, 1.1, CARD2);
  s.addText("BOARD", { x: 9.05, y: 3.13, w: 1.55, h: 0.3, fontFace: H, fontSize: 11.5, bold: true, color: INK, charSpacing: 2, align: "center", margin: 0 });
  s.addText("task #7\nopen → leased\n→ verified ✓", { x: 9.05, y: 3.43, w: 1.55, h: 0.7, fontFace: M, fontSize: 9, color: GOOD, align: "center", margin: 0 });
  const corners = [[7.15, 2.4], [11.55, 2.4], [7.15, 4.4], [11.55, 4.4]];
  corners.forEach(([x, y], i) => {
    agent(x, y, `agent ${i + 1}`);
    const ax = x < 9 ? x + 0.95 : x, ay = y + 0.3;          // agent edge facing the board
    const bx = x < 9 ? 9.05 : 10.6, by = y < 3.5 ? 3.2 : 4.0; // board corner facing the agent
    seg(ax, ay, bx, by, GOOD, 1.75, true);
  });
  s.addText("read · write — never each other", { x: 8.85, y: 4.2, w: 1.95, h: 0.3, fontFace: B, fontSize: 9.5, italic: true, color: MUT, align: "center", margin: 0 });
  s.addText("one small, exact state  ·  nothing to summarize  ·  nothing lost in transit  ·  no transcript grows with the group",
    { x: 7.05, y: 5.15, w: 5.5, h: 0.65, fontFace: B, fontSize: 11, color: MUT, align: "center", margin: 0 });

  s.addText("We copied the one coordination style a finite, stateless context cannot afford. The research says the same — next.",
    { x: 0.9, y: 6.1, w: 11.7, h: 0.6, fontFace: B, fontSize: 15, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("Keep it tight; the diagram does the work. The point of this slide is a single causal chain: we coordinate by talking, so we made agents talk — but an agent IS its context (Part 1), and context is finite. So every message costs the very thing the agent is made of, and every hand-off is a summary that can only lose information. Read the bubbles left to right and watch the fix shrink into a confident 'done' that wasn't. Right side: the alternative is not better messages — it's no messages: a small exact shared state that never grows with the group. Then hand off: the literature has measured this failure, several times.");
}

// =====================================================================
// PAGE 13 · Part 2 — The research: agent communication fails
// =====================================================================
{
  const s = base("Part 2 · Why swarms? — what the research found",
    "Five groups. Five methods. One conclusion: the more agents talk, the worse they do.", 26);

  const papers = [
    [SG, "Don’t Build Multi-Agents", "Cognition (Walden Yan) · 2025", "https://cognition.ai/blog/dont-build-multi-agents",
      "Hand-offs lose context; parallel agents make conflicting implicit decisions. Their rule: share the full context, never a summary — and if you can’t, don’t split the work."],
    [BAD, "Why Do Multi-Agent LLM Systems Fail? (MAST)", "Cemri et al., UC Berkeley · NeurIPS 2025", "https://arxiv.org/abs/2503.13657",
      "1,600+ traces, 14 failure modes. A whole family is inter-agent misalignment: information withheld, input ignored, reasoning–action mismatch. Failures of communication, not of models."],
    [SW, "The Illusion of Multi-Agent Advantage", "equal-compute audits · 2026", "https://arxiv.org/abs/2606.13003",
      "At equal compute, automatic multi-agent frameworks lose to one agent with self-consistency — at up to 10× the cost. Information passed through hops can only be lost (data-processing inequality)."],
    [SW, "Debate or Vote", "multi-agent debate studies · 2025", "https://arxiv.org/abs/2508.17536",
      "Agents arguing does not improve expected correctness — debate is a martingale. Majority voting over independent answers explains the gains. Talking adds nothing that counting didn’t."],
    [GOOD, "AI agents can coordinate beyond human scale", "De Marzo, Castellano, Garcia · Science Advances 2026", "https://www.science.org/doi/10.1126/sciadv.aea6091",
      "Coordination by reading everyone’s messages hits a hard ceiling — an “AI Dunbar number” — because the message list grows with the group while the context does not."],
  ];
  papers.forEach(([c, title, venue, url, finding], i) => {
    const y = 1.72 + i * 0.94;
    card(s, 0.7, y, 12.0, 0.84);
    chip(s, 0.93, y + 0.16, c);
    s.addText([{ text: title, options: { hyperlink: { url }, color: SW } }],
      { x: 1.22, y: y + 0.07, w: 3.9, h: 0.5, fontFace: H, fontSize: 12, bold: true, valign: "top", margin: 0 });
    s.addText(venue, { x: 1.22, y: y + 0.55, w: 3.9, h: 0.26, fontFace: B, fontSize: 10, color: MUT, margin: 0 });
    s.addText(finding, { x: 5.25, y: y + 0.07, w: 7.25, h: 0.72, fontFace: B, fontSize: 11.5, color: INK, valign: "middle", margin: 0 });
  });

  s.addText("Not one of these groups set out to prove it. All five found it. So — not conversation. An environment.",
    { x: 0.7, y: 6.5, w: 12.0, h: 0.45, fontFace: B, fontSize: 14.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("Don't read the cards — pick two and tell them as stories. Cognition: a company that sells an autonomous engineer published 'don't build multi-agents', because their own hand-offs kept losing the plot. Berkeley: sixteen hundred traces, and the failures cluster around agents not telling each other things, ignoring each other, or saying one thing and doing another — a communication taxonomy. Then the physics one: coordination by reading everyone's messages caps out, because the message list grows with the group and the context doesn't — the same finiteness from Part 1, measured. Titles are links; the audience can pull any of them up. Close: five independent groups, five methods, one conclusion — and none of them was trying to find it. Then turn the page: not conversation. An environment.");
}

// =====================================================================
// TRANSITION PAGE · Part 3 opener — the environment
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("PART 3 · THE ENVIRONMENT", { x: 0.7, y: 0.5, w: 8, h: 0.3, fontFace: H, fontSize: 11, bold: true, color: MUT, charSpacing: 3, margin: 0 });

  // two questions, two answers
  const qa = (x, q, a, color) => {
    card(s, x, 1.5, 5.75, 2.55, CARD);
    s.addText(q, { x: x + 0.35, y: 1.75, w: 5.05, h: 0.9, fontFace: B, fontSize: 18, color: MUT, margin: 0 });
    s.addText(a, { x: x + 0.35, y: 2.75, w: 5.05, h: 1.0, fontFace: H, fontSize: 40, bold: true, color, margin: 0 });
  };
  qa(0.7, "What turns a stateless model\ninto an agent?", "Context.", SG);
  qa(6.9, "What turns agents into\na multi-agent system?", "The environment.", SW);

  s.addText("That is why we began with architecture. A multi-agent system is not more agents — it is the infrastructure the calls live in: where their context is kept, who hands them work, what checks their output, what survives when they die. Build that environment right and the system works. Build it wrong and no number of agents will save it.",
    { x: 0.9, y: 4.35, w: 11.5, h: 1.2, fontFace: B, fontSize: 16, color: INK, margin: 0 });

  s.addShape(pres.ShapeType.line, { x: 0.9, y: 5.8, w: 11.5, h: 0.001, line: { color: LINE, width: 1 } });
  s.addText("So before we build one: how do we tame complex systems today — and which of those patterns become an environment for agents?",
    { x: 0.9, y: 5.95, w: 11.5, h: 0.8, fontFace: B, fontSize: 17, italic: true, color: SG, margin: 0 });

  s.addNotes("Two questions, two one-word answers; let each land. Then the pivot that justifies Part 0: we spent five minutes on the laws of complex systems because a MAS IS a complex system — the agents are the least interesting part. The environment decides everything: where context lives, who dispatches, what verifies, what survives a crash. Then the hand-off: we already know how to tame complex systems — forty years of distributed-systems patterns. The next section maps them onto agents, one family at a time.");
}

// =====================================================================
// PAGE 14 · Part 3 — You can have a MAS: the right motivation, the right architecture (the toolbox)
// =====================================================================
{
  const s = base("Part 3 · The environment — the toolbox",
    "You can have a multi-agent system — with the right motivation and the right architecture.", 26);
  s.addText("We already know how to tame complex systems. Forty years of distributed-systems patterns are the toolbox. Here is what we borrow.",
    { x: 0.7, y: 1.58, w: 11.8, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  // --- the right motivation: one of the three walls ---
  card(s, 0.7, 1.98, 12.0, 0.72, CARD);
  s.addText("THE RIGHT MOTIVATION", { x: 0.9, y: 2.2, w: 2.3, h: 0.3, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, valign: "middle", margin: 0 });
  const mini = (i, x, y, c) => {
    if (i === 0) {
      s.addShape(pres.ShapeType.line, { x, y, w: 0.34, h: 0.001, line: { color: c, width: 1.5, dashType: "dash" } });
      s.addShape(pres.ShapeType.roundRect, { x: x + 0.11, y: y + 0.07, w: 0.12, h: 0.32, rectRadius: 0.03, fill: { color: c }, line: { type: "none" } });
    } else if (i === 1) {
      s.addShape(pres.ShapeType.lightningBolt, { x: x + 0.02, y: y - 0.02, w: 0.3, h: 0.44, fill: { color: c }, line: { type: "none" } });
    } else {
      [0, 0.14, 0.28].forEach((dy, k) => s.addShape(pres.ShapeType.roundRect, { x: x + (k === 1 ? 0.04 : 0), y: y + 0.03 + dy, w: 0.34 - (k === 1 ? 0.08 : 0), h: 0.09, rectRadius: 0.02, fill: { color: c }, line: { type: "none" } }));
    }
  };
  [["the window", SG], ["the crash", BAD], ["the backlog", SW]].forEach(([t, c], i) => {
    const x = 3.4 + i * 1.9;
    mini(i, x, 2.15, c);
    s.addText(t, { x: x + 0.45, y: 2.2, w: 1.4, h: 0.3, fontFace: B, fontSize: 12.5, bold: true, color: INK, valign: "middle", margin: 0 });
  });
  s.addText("build one when you hit a wall — not before", { x: 9.0, y: 2.2, w: 3.55, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: SG, align: "right", valign: "middle", margin: 0 });

  // --- the right architecture: four drawers of the toolbox ---
  s.addText("THE RIGHT ARCHITECTURE — WHAT WE BORROW", { x: 0.7, y: 2.85, w: 8, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  const drawers = [
    [SG, "DECOMPOSE", "answers Entropy", ["bounded contexts (DDD)", "bulkheads · isolation", "small, verifiable units"], "one task = one context = one worktree. A failure can’t leak."],
    [SW, "DECOUPLE", "answers Lehman", ["queues & event streams", "pull, not push", "idempotent consumers"], "the task board. Workers pull work — and never talk to each other."],
    [BAD, "SURVIVE", "answers Bankruptcy", ["timeouts & budgets", "retries with backoff", "circuit breakers · leases · supervisors"], "turn budgets, re-dispatch, let it crash. Loss is bounded to one task."],
    [GOOD, "VERIFY & OBSERVE", "answers Gall", ["health checks · contracts", "event sourcing + views", "logs · metrics · audit"], "the gate runs the tests. Immutable artifacts. Every close carries a verdict."],
  ];
  drawers.forEach(([c, name, law, tools, agents], i) => {
    const x = 0.7 + i * 3.05;
    card(s, x, 3.2, 2.9, 2.85);
    chip(s, x + 0.2, 3.38, c);
    s.addText(name, { x: x + 0.48, y: 3.28, w: 2.3, h: 0.32, fontFace: H, fontSize: 13, bold: true, color: c, charSpacing: 1, margin: 0 });
    s.addText(law, { x: x + 0.2, y: 3.62, w: 2.5, h: 0.26, fontFace: B, fontSize: 10.5, italic: true, color: MUT, margin: 0 });
    s.addText(tools.map((t, k) => ({ text: t, options: { bullet: { code: "2022", indent: 10 }, breakLine: k < tools.length - 1, paraSpaceAfter: 3 } })),
      { x: x + 0.2, y: 3.95, w: 2.55, h: 1.0, fontFace: B, fontSize: 11.5, color: INK, valign: "top", margin: 0 });
    s.addShape(pres.ShapeType.line, { x: x + 0.2, y: 5.0, w: 2.5, h: 0.001, line: { color: LINE, width: 0.75 } });
    s.addText(agents, { x: x + 0.2, y: 5.08, w: 2.55, h: 0.9, fontFace: B, fontSize: 11, color: MUT, margin: 0 });
  });

  s.addText("Nothing here is new. A swarm is distributed-systems engineering with stateless calls as the workers. One tool per slide — next.",
    { x: 0.7, y: 6.25, w: 12.0, h: 0.6, fontFace: B, fontSize: 14, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("The turn from critique to construction. Say it plainly: yes, you can have a MAS — but two conditions. Motivation: you hit one of the three walls (point at the glyphs — the room knows them by now). Architecture: the environment, built from tools you already trust. Walk the four drawers fast, each tied to its law from Part 0: decomposition bounds entropy; decoupling lets you change without coupling (Lehman); survival patterns bound the interest (bankruptcy); verification is Gall's 'every stage must work'. Land the closing line hard: none of this is new. Every pattern people are rediscovering with agents was written down between 1995 and 2015. We just translate the vocabulary — and that's the next nine slides.");
}

// =====================================================================
// PAGE 15 · Tool 1 — Bounded contexts
// =====================================================================
{
  const s = base("Part 3 · Tool 1 of 9 — Bounded contexts (Domain-Driven Design)",
    "Split by what crosses the boundary — not by who does it.", 27);
  s.addText("— Eric Evans, Domain-Driven Design (2003): each context keeps its own internal model; between contexts crosses only a small, explicit, agreed language.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  bullets(s, 0.7, 1.95, 5.5, 3.7, [
    "The pattern: a system is cut into bounded contexts. Internals never leak. What crosses a boundary is a contract — small, typed, agreed in advance.",
    "Why it exists: entropy. Shared internals couple everything to everything; a contract lets each part change — or rot — without infecting the rest.",
    "For agents: each subagent is a bounded context, and its transcript is the internal model. What crosses is the contract — a yes/no, a price, three lines of background, a list of sources. Never the transcript.",
    "The final agent receives a curated context assembled from contracts: N large contexts collapsed into one small one. One hop. Typed. The opposite of the relay.",
    "Rule of thumb: design the answer format before the agent. If the contract doesn’t fit on one line, the boundary is in the wrong place.",
  ], { size: 13, gap: 8 });
  s.addText("The contract is also where errors hide — a wrong “yes” is invisible downstream. Boundaries need verification. Tool 8.",
    { x: 0.7, y: 5.85, w: 5.5, h: 0.75, fontFace: B, fontSize: 12.5, italic: true, color: SG, margin: 0 });

  // --- diagram: fan-out into big contexts, fan-in through contracts, one agent acts ---
  const seg = (x1, y1, x2, y2, color, width = 1.5) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle" },
    });
  const subs = [
    ["subagent 1", "reads 40 pages\nof docs", 0.95, "yes"],
    ["subagent 2", "queries 3 pricing\nAPIs", 0.85, "$1,240"],
    ["subagent 3", "reads the ticket\nhistory", 1.05, "3-line\nbackground"],
    ["subagent 4", "scans the repo", 0.88, "5 sources"],
  ];
  subs.forEach(([name, work, h, ans], i) => {
    const x = 6.75 + i * 1.5;
    card(s, x, 1.95, 1.3, 0.42, CARD2);
    s.addText(name, { x, y: 1.95, w: 1.3, h: 0.42, fontFace: H, fontSize: 10.5, bold: true, color: INK, align: "center", valign: "middle", margin: 0 });
    // its big private context
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.1, y: 2.45, w: 1.1, h, rectRadius: 0.06, fill: { color: CARD }, line: { color: MUT, width: 1, dashType: "dash" } });
    s.addText(work, { x: x + 0.1, y: 2.45, w: 1.1, h, fontFace: B, fontSize: 9.5, color: MUT, align: "center", valign: "middle", margin: 0 });
    // the contract that crosses
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.15, y: 3.95, w: 1.0, h: 0.46, rectRadius: 0.06, fill: { color: BG }, line: { color: GOOD, width: 1.5 } });
    s.addText(ans, { x: x + 0.15, y: 3.95, w: 1.0, h: 0.46, fontFace: M, fontSize: 9.5, bold: true, color: GOOD, align: "center", valign: "middle", margin: 0 });
    seg(x + 0.65, 3.8, x + 0.65, 3.95, GOOD, 1.25);
    seg(x + 0.65, 4.41, 9.75, 4.85, GOOD, 1.25);
  });
  s.addText("private contexts — stay behind the boundary", { x: 6.75, y: 3.62, w: 5.85, h: 0.22, fontFace: B, fontSize: 9.5, italic: true, color: MUT, align: "center", margin: 0 });

  card(s, 7.9, 4.85, 3.7, 0.7, CARD2);
  s.addText("CURATED CONTEXT  ·  ~600 tokens", { x: 7.9, y: 4.9, w: 3.7, h: 0.3, fontFace: H, fontSize: 10.5, bold: true, color: INK, charSpacing: 1, align: "center", margin: 0 });
  s.addText("yes · $1,240 · background · 5 sources", { x: 7.9, y: 5.2, w: 3.7, h: 0.3, fontFace: M, fontSize: 9.5, color: GOOD, align: "center", margin: 0 });
  seg(9.75, 5.55, 9.75, 5.85, SG, 2);
  card(s, 7.9, 5.85, 3.7, 0.6, CARD2);
  s.addText("ONE AGENT — does the work", { x: 7.9, y: 5.85, w: 3.7, h: 0.6, fontFace: H, fontSize: 12.5, bold: true, color: SG, align: "center", valign: "middle", margin: 0 });
  s.addText("N big contexts → 1 small one. One hop. Facts, not summaries of summaries.", { x: 6.7, y: 6.55, w: 6.0, h: 0.3, fontFace: B, fontSize: 11, italic: true, color: INK, align: "center", margin: 0 });

  s.addNotes("Use the audience's own intuition: this is how a good research team briefs a decision-maker. Four subagents each burn a large private context — forty pages of docs, three APIs, the ticket history, the repo — and each returns ONE typed thing: yes, a price, three lines, five links. Nothing else crosses. The decision-maker gets six hundred tokens of curated facts and acts. Contrast with page 12: that was N hops of shrinking summaries; this is one hop of typed contracts. Then the DDD framing: boundary first, agent second — write the contract in one line or move the boundary. And the caveat that sets up tool 8: a compact answer hides its own errors; the boundary is exactly where you verify.");
}

// =====================================================================
// PAGE 16 · Tool 2 — Bulkheads / isolation
// =====================================================================
{
  const s = base("Part 3 · Tool 2 of 9 — Bulkheads (isolation)",
    "Run together, fail alone: one sealed compartment per task.", 28);
  s.addText("— from ship design; in software, Michael Nygard, Release It! (2007): partition resources so a failure in one compartment cannot flood the rest.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  bullets(s, 0.7, 1.95, 5.5, 3.75, [
    "The pattern: a hull cut into sealed compartments — one breach floods one compartment, never the ship. Separate pools, processes, containers: resources that fail alone.",
    "Why it exists: shared mutable state is the medium failure travels through. A bounded context (tool 1) draws the logical line; a bulkhead makes it physical — nothing crosses by accident.",
    "For agents: each parallel task gets its own compartment — its own working copy, its own fresh context, its own budget — and shares nothing mutable. Ten run at once; one crashing, looping, or going wrong cannot touch the other nine.",
    "What belongs here — work that is independent by nature: ten agents running ten configurations; five agents attacking one question with different prompts, then a vote (independence is what makes the vote valid); forty modules, one each.",
    "The test: can you write a compartment’s inputs and its one output without mentioning any other compartment? Yes → run them in parallel. No → it’s a pipeline. Different tool.",
  ], { size: 12, gap: 6 });
  s.addText("The price of isolation is duplication: every compartment pays its own setup and rediscovers what its neighbours know. You buy safety and parallelism with tokens.",
    { x: 0.7, y: 6.05, w: 5.5, h: 0.7, fontFace: B, fontSize: 12, italic: true, color: SG, margin: 0 });

  // --- diagram: the hull ---
  const hx = 6.75, hy = 2.1, hw = 5.9, hh = 2.45, n = 5, cw = hw / n;
  card(s, hx, hy, hw, hh, CARD);
  s.addText("THE HULL · SHARE NOTHING THAT CAN BE DAMAGED", { x: hx, y: hy - 0.32, w: hw, h: 0.26, fontFace: H, fontSize: 10, bold: true, color: MUT, charSpacing: 2, align: "center", margin: 0 });
  const labels = ["config A", "config B", "config C", "config D", "config E"];
  const flooded = 2;
  for (let k = 0; k < n; k++) {
    const x = hx + k * cw;
    if (k > 0) s.addShape(pres.ShapeType.line, { x, y: hy, w: 0.001, h: hh, line: { color: INK, width: 2.25 } });
    if (k === flooded)
      s.addShape(pres.ShapeType.rect, { x: x + 0.02, y: hy + 0.02, w: cw - 0.04, h: hh - 0.04, fill: { color: BAD, transparency: 72 }, line: { type: "none" } });
    s.addText(`compartment ${k + 1}`, { x, y: hy + 0.1, w: cw, h: 0.26, fontFace: B, fontSize: 9.5, color: MUT, align: "center", margin: 0 });
    card(s, x + 0.17, hy + 0.55, cw - 0.34, 0.55, CARD2);
    s.addText(k === flooded ? "✕" : "agent", { x: x + 0.17, y: hy + 0.55, w: cw - 0.34, h: 0.55, fontFace: H, fontSize: k === flooded ? 18 : 11, bold: true, color: k === flooded ? BAD : INK, align: "center", valign: "middle", margin: 0 });
    s.addText(labels[k], { x, y: hy + 1.25, w: cw, h: 0.26, fontFace: M, fontSize: 9.5, color: k === flooded ? BAD : INK, align: "center", margin: 0 });
    s.addText(k === flooded ? "looped · crashed\nflooded — alone" : "own copy\nown context\nown budget", { x: x + 0.05, y: hy + 1.55, w: cw - 0.1, h: 0.85, fontFace: B, fontSize: 9, color: k === flooded ? BAD : MUT, align: "center", margin: 0 });
  }
  // outputs
  for (let k = 0; k < n; k++) {
    const x = hx + k * cw;
    const ok = k !== flooded;
    s.addShape(pres.ShapeType.line, { x: x + cw / 2, y: hy + hh, w: 0.001, h: 0.3, line: { color: ok ? GOOD : BAD, width: 1.5, endArrowType: "triangle", ...(ok ? {} : { dashType: "dash" }) } });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.2, y: hy + hh + 0.35, w: cw - 0.4, h: 0.4, rectRadius: 0.06, fill: { color: BG }, line: { color: ok ? GOOD : BAD, width: 1.5 } });
    s.addText(ok ? "result ✓" : "none", { x: x + 0.2, y: hy + hh + 0.35, w: cw - 0.4, h: 0.4, fontFace: M, fontSize: 9.5, bold: true, color: ok ? GOOD : BAD, align: "center", valign: "middle", margin: 0 });
  }
  card(s, hx + 0.9, hy + hh + 1.0, hw - 1.8, 0.62, CARD2);
  s.addText("compare · vote · pick the best", { x: hx + 0.9, y: hy + hh + 1.03, w: hw - 1.8, h: 0.32, fontFace: H, fontSize: 12, bold: true, color: INK, align: "center", margin: 0 });
  s.addText("independence is what makes the comparison valid", { x: hx + 0.9, y: hy + hh + 1.33, w: hw - 1.8, h: 0.26, fontFace: B, fontSize: 9.5, italic: true, color: MUT, align: "center", margin: 0 });
  s.addText("One compartment floods. Four results arrive. The ship sails.", { x: hx, y: 6.42, w: hw, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: INK, align: "center", margin: 0 });

  s.addNotes("Two examples the room will recognize: a parameter sweep — ten agents, ten configurations, ten independent measurements; and self-consistency — five agents, same question, different prompts, then vote. In both, independence isn't a nice-to-have: shared state would CORRELATE their errors, and correlated answers can't be compared or voted on. Point at the flooded compartment: it looped, it crashed, whatever — the other four don't know and don't care. Then the test for whether work belongs here: write a compartment's inputs and its single output without naming another compartment. If you can't, it's a pipeline, and the next tools apply. Finish on the price: isolation costs duplication — each compartment rediscovers what its neighbours know. You buy safety and parallelism with tokens; sometimes that's the right trade, sometimes it isn't.");
}

// =====================================================================
// PAGE 17 · Tool 3 — Queues & pull-based consumers (the board)
// =====================================================================
{
  const s = base("Part 3 · Tool 3 of 9 — Queues & competing consumers (the board)",
    "Put the work on a board. Let the workers come and take it.", 28);
  s.addText("— Competing Consumers, Hohpe & Woolf, Enterprise Integration Patterns (2003): N consumers pull from one queue; every message reaches exactly one of them.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  bullets(s, 0.7, 1.95, 5.5, 3.95, [
    "The pattern: producers put items on a queue; free consumers take the next one. Exactly one consumer per item. No dispatcher decides who does what — the free worker is the one who takes it.",
    "Why it exists: Lehman. Add, remove, or rewrite consumers without touching producers or each other. The queue absorbs bursts, its depth is your backpressure signal, and pull balances load by itself.",
    "For agents: the board IS the queue. An item = a brief + the check that proves it done. A worker pulls one item, works in its own compartment (tool 2), submits. The item closes only when verified. Nobody assigns. Nobody talks. Adding a worker adds throughput.",
    "A task you can run tomorrow — “migrate 60 endpoints off the deprecated auth middleware”: a script writes 60 items (path · file · its tests · the recipe). Eight workers pull. Each migrates one endpoint, runs its tests, submits; the orchestrator re-runs them and closes the item. A worker dies → its lease expires → the item reappears for the next one (tool 4).",
    "Rule of thumb: an item must be pullable cold — the brief plus the check must be enough for a worker that knows nothing else.",
  ], { size: 12, gap: 6 });
  s.addText("The queue coordinates work, not knowledge: it doesn’t carry what worker 3 learned. That stays in its compartment — unless you build a place for it (tool 9).",
    { x: 0.7, y: 6.05, w: 5.5, h: 0.7, fontFace: B, fontSize: 12, italic: true, color: SG, margin: 0 });

  // --- diagram ---
  const seg = (x1, y1, x2, y2, color, width = 1.5, dash) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle", ...(dash ? { dashType: "dash" } : {}) },
    });
  // producer
  card(s, 6.75, 2.15, 1.65, 0.85, CARD2);
  s.addText("PRODUCER", { x: 6.75, y: 2.2, w: 1.65, h: 0.3, fontFace: H, fontSize: 10.5, bold: true, color: INK, charSpacing: 1, align: "center", margin: 0 });
  s.addText("a script or a planner\nwrites 60 items", { x: 6.75, y: 2.48, w: 1.65, h: 0.5, fontFace: B, fontSize: 9.5, color: MUT, align: "center", margin: 0 });
  seg(8.4, 2.57, 8.75, 2.57, MUT);
  // the board
  card(s, 8.75, 1.95, 3.95, 1.3, CARD);
  s.addText("THE BOARD · one item per endpoint", { x: 8.75, y: 2.0, w: 3.95, h: 0.28, fontFace: H, fontSize: 10, bold: true, color: INK, charSpacing: 1, align: "center", margin: 0 });
  const items = ["01 ✓", "02 ✓", "03 ✓", "04 ✓", "05 ⟳", "06 ⟳", "07 ⟳", "08 ⟳", "09", "10", "11", "…60"];
  items.forEach((t, k) => {
    const col = k % 6, row = Math.floor(k / 6);
    const x = 8.9 + col * 0.63, y = 2.35 + row * 0.38;
    const st = t.includes("✓") ? GOOD : t.includes("⟳") ? SW : MUT;
    s.addShape(pres.ShapeType.roundRect, { x, y, w: 0.58, h: 0.3, rectRadius: 0.05, fill: { color: CARD2 }, line: { color: st, width: 1 } });
    s.addText(t, { x, y, w: 0.58, h: 0.3, fontFace: M, fontSize: 8.5, color: st, align: "center", valign: "middle", margin: 0 });
  });
  s.addText("✓ verified · ⟳ leased · open", { x: 8.75, y: 3.12, w: 3.95, h: 0.2, fontFace: B, fontSize: 8.5, italic: true, color: MUT, align: "center", margin: 0 });

  // workers pulling
  const wx = [7.05, 8.5, 9.95, 11.4];
  wx.forEach((x, i) => {
    const dead = i === 3;
    card(s, x, 4.15, 1.15, 0.6, CARD2);
    s.addText(dead ? "✕" : `worker ${i + 1}`, { x, y: 4.15, w: 1.15, h: 0.6, fontFace: H, fontSize: dead ? 16 : 10.5, bold: true, color: dead ? BAD : INK, align: "center", valign: "middle", margin: 0 });
    seg(x + 0.575, 4.15, x + 0.575, 3.3, dead ? BAD : SW, 1.5, dead);
    s.addText(dead ? "lease expires\n→ item reopens" : `pulls #0${5 + i}`, { x: x - 0.15, y: 4.8, w: 1.45, h: 0.42, fontFace: B, fontSize: 9, italic: true, color: dead ? BAD : MUT, align: "center", margin: 0 });
  });
  s.addText("pull", { x: 8.95, y: 3.55, w: 0.6, h: 0.22, fontFace: B, fontSize: 9, italic: true, color: SW, align: "center", margin: 0 });
  // outcome strip
  card(s, 6.75, 5.35, 5.95, 0.55, CARD2);
  s.addText("each: migrate one endpoint · run its tests · submit  →  orchestrator re-runs the tests  →  item closed ✓", { x: 6.75, y: 5.35, w: 5.95, h: 0.55, fontFace: B, fontSize: 10, color: INK, align: "center", valign: "middle", margin: 0 });
  s.addText("60 endpoints  ·  8 lanes  ·  0 conversations  ·  human-readable, always", { x: 6.75, y: 6.0, w: 5.95, h: 0.3, fontFace: M, fontSize: 9, color: GOOD, align: "center", margin: 0 });
  s.addText("Nobody assigns. Nobody talks. The free worker takes the next item.", { x: 6.75, y: 6.42, w: 5.95, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: INK, align: "center", margin: 0 });

  s.addNotes("Give them the concrete task and make it boring on purpose: sixty endpoints to migrate off a deprecated middleware. A script writes sixty items — path, file, the tests that must pass, a link to the recipe. Eight workers start and PULL: whoever is free takes the next one. Nobody assigns; there is no manager agent deciding who does what. Point out the three properties that fall out for free: load balances itself (the free worker takes the next item), the queue depth tells you how far behind you are, and a human can open the board at any moment and read the truth. Then worker 4: it died. Its lease expires, the item reappears, someone else takes it — that's tool 4. Close on the rule: every item must be pullable cold — brief plus check, sufficient for a worker that knows nothing else. If you can't write that, the item isn't ready for the board.");
}

// =====================================================================
// PAGE 18 · Tool 4 — Idempotency & leases (diagram-first)
// =====================================================================
{
  const s = base("Part 3 · Tool 4 of 9 — Idempotency & leases",
    "The same task will run twice. Make sure that’s harmless.", 28);
  s.addText("The problem: leases re-open a task when its worker goes quiet — so a slow worker and its replacement can both finish it. Twice must equal once.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

  const arrow = (x1, y1, x2, y2, color, width = 1.75, dash) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle", ...(dash ? { dashType: "dash" } : {}) },
    });

  // the task
  card(s, 0.7, 1.95, 12.0, 0.6, CARD);
  s.addText("THE TASK", { x: 0.9, y: 1.95, w: 1.3, h: 0.6, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, valign: "middle", margin: 0 });
  s.addText("Bill 500 customers for June: charge the card, email the receipt. One item per customer. Eight workers pull.", { x: 2.2, y: 1.95, w: 10.3, h: 0.6, fontFace: B, fontSize: 13.5, color: INK, valign: "middle", margin: 0 });

  // what happens to item #23 (Dana)
  const steps = [
    ["worker A pulls #23", "Dana · June", SW],
    ["A stalls mid-way", "lease expires → #23 reopens", SG],
    ["worker B pulls #23", "bills Dana · verified ✓", GOOD],
    ["A wakes up", "…and bills Dana again?", BAD],
  ];
  steps.forEach(([h, sub, c], i) => {
    const x = 0.7 + i * 3.1;
    card(s, x, 2.8, 2.7, 0.85, CARD2);
    s.addText(h, { x: x + 0.15, y: 2.86, w: 2.4, h: 0.32, fontFace: H, fontSize: 12, bold: true, color: c, margin: 0 });
    s.addText(sub, { x: x + 0.15, y: 3.2, w: 2.4, h: 0.4, fontFace: B, fontSize: 11, color: INK, margin: 0 });
    if (i < 3) arrow(x + 2.7, 3.22, x + 3.1, 3.22, MUT);
  });

  // two outcomes
  const outcome = (x, color, head, rule, chips, verdict) => {
    card(s, x, 3.95, 5.85, 2.35, CARD);
    s.addText(head, { x: x + 0.25, y: 4.05, w: 5.4, h: 0.3, fontFace: H, fontSize: 11, bold: true, color, charSpacing: 1, margin: 0 });
    s.addText(rule, { x: x + 0.25, y: 4.37, w: 5.4, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: INK, margin: 0 });
    s.addText("Dana’s account:", { x: x + 0.25, y: 4.85, w: 1.6, h: 0.3, fontFace: B, fontSize: 11, color: MUT, valign: "middle", margin: 0 });
    chips.forEach(([t, cc], k) => {
      s.addShape(pres.ShapeType.roundRect, { x: x + 1.85 + k * 1.05, y: 4.85, w: 0.95, h: 0.34, rectRadius: 0.06, fill: { color: BG }, line: { color: cc, width: 1.5 } });
      s.addText(t, { x: x + 1.85 + k * 1.05, y: 4.85, w: 0.95, h: 0.34, fontFace: M, fontSize: 9.5, bold: true, color: cc, align: "center", valign: "middle", margin: 0 });
    });
    s.addText(verdict, { x: x + 0.25, y: 5.4, w: 5.4, h: 0.75, fontFace: B, fontSize: 12, color, margin: 0 });
  };
  outcome(0.7, BAD, "WITHOUT IDEMPOTENCY · the task is an action",
    "“charge $49 and send the receipt”",
    [["$49", BAD], ["$49", BAD], ["receipt", BAD], ["receipt", BAD]],
    "Charged twice. Two receipts. A refund, an apology, a support ticket — for every customer whose worker was slow.");
  outcome(6.85, GOOD, "WITH IDEMPOTENCY · the task is a state",
    "“Dana is billed for June” — key: (customer, month). Check, then act.",
    [["$49", GOOD], ["receipt", GOOD]],
    "A’s second run checks the key: June already billed → nothing to do. Twice = once. The replacement was free.");

  s.addText("Write every task as a state to reach, keyed by what makes it unique — and check before you act. (“Done” as an inspectable state is exactly what verification, tool 8, needs.)",
    { x: 0.7, y: 6.5, w: 12.0, h: 0.55, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("Tell it as a story. Five hundred customers to bill; eight workers pulling one customer each. Item #23 is Dana. Worker A pulls it, charges the card... and stalls — a slow payment API, a hung process, whatever. Its lease expires; the board re-opens #23; worker B pulls it and bills Dana. Then A wakes up and finishes what it started. This is not a corner case — leases exist precisely to make it happen, because the alternative is losing Dana entirely when A dies. So the only question is what A's second run does. Left: the task was an ACTION — charge and send — so Dana is charged twice and gets two receipts. Right: the task was a STATE — 'Dana is billed for June', keyed by customer and month — so A checks the key, finds June billed, and stops. Same crash, same lease, same two workers; the only difference is how the task was written. That's idempotency, and it's the same thing payment providers make you do with an idempotency key on every charge.");
}

// =====================================================================
// PAGE 19 · Tool 5 — Timeouts, retries & backoff
// =====================================================================
{
  const s = base("Part 3 · Tool 5 of 9 — Timeouts, retries & backoff",
    "Leases catch dead workers. Timeouts catch stuck ones.", 28);
  s.addText("The problem: stuck isn’t dead — a looping agent keeps heartbeating, so its lease never expires. And forty simultaneous retries are a self-inflicted outage.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  // the task
  card(s, 0.7, 1.98, 12.0, 0.6, CARD);
  s.addText("THE TASK", { x: 0.9, y: 1.98, w: 1.3, h: 0.6, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, valign: "middle", margin: 0 });
  s.addText("The 60-endpoint migration again. Each worker runs its endpoint’s tests on a shared build server. At 10:00, forty workers hit it at once — it starts answering “too busy.”", { x: 2.2, y: 1.98, w: 10.3, h: 0.6, fontFace: B, fontSize: 12.5, color: INK, valign: "middle", margin: 0 });

  const panel = (x, color, head, bars, chartNote, story, stuck, verdict) => {
    card(s, x, 2.8, 5.85, 3.5, CARD);
    s.addText(head, { x: x + 0.25, y: 2.9, w: 5.4, h: 0.28, fontFace: H, fontSize: 11, bold: true, color, charSpacing: 1, margin: 0 });
    s.addText("retries hitting the server, per second", { x: x + 0.25, y: 3.2, w: 2.7, h: 0.22, fontFace: B, fontSize: 9, italic: true, color: MUT, margin: 0 });
    s.addChart(pres.ChartType.bar, [{ name: "retries", labels: bars.map((_, i) => `${i}s`), values: bars }], {
      x: x + 0.2, y: 3.4, w: 2.8, h: 1.25, barDir: "col", chartColors: [color], barGapWidthPct: 35,
      showLegend: false, showTitle: false, showValue: false,
      catAxisHidden: true, valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
      valAxisMinVal: 0, valAxisMaxVal: 45,
      chartArea: { fill: { color: CARD } }, plotArea: { fill: { color: CARD } },
    });
    s.addText(chartNote, { x: x + 0.25, y: 4.62, w: 2.7, h: 0.24, fontFace: M, fontSize: 9, color, align: "center", margin: 0 });
    s.addText(story, { x: x + 3.15, y: 3.25, w: 2.5, h: 1.6, fontFace: B, fontSize: 10.5, color: INK, margin: 0 });
    // the stuck worker
    card(s, x + 0.25, 4.98, 5.35, 0.72, CARD2);
    s.addText(stuck, { x: x + 0.4, y: 4.98, w: 5.05, h: 0.72, fontFace: B, fontSize: 10, color: INK, valign: "middle", margin: 0 });
    s.addText(verdict, { x: x + 0.25, y: 5.8, w: 5.35, h: 0.4, fontFace: B, fontSize: 11, bold: true, color, align: "center", valign: "middle", margin: 0 });
  };
  panel(0.7, BAD, "NO TIMEOUT · INSTANT RETRY",
    [40, 40, 40, 40, 40, 40, 40, 40], "40 · 40 · 40 · 40 … the stampede",
    "10:00:00 — forty workers → “too busy.”\n10:00:01 — forty retries → “too busy.”\nForever. The server never gets one quiet second to recover. The swarm is now the outage.",
    "worker 7 · turn 12… 13… 14… re-reading auth.py. Alive, heartbeating, lease renewed. Nobody will ever notice.",
    "server never recovers · tokens burn · one lane stuck forever");
  panel(6.85, GOOD, "BUDGET PER ATTEMPT · BACKOFF + JITTER",
    [40, 21, 11, 6, 3, 1, 1, 0], "40 · 21 · 11 · 6 · 3 · 1 … breathes",
    "10:00:00 — forty workers → “too busy.”\nEach waits 2s, 4s, 8s… plus a random slice. Retries fan out; the server breathes; stragglers trickle in.\nAll sixty done by 10:01.",
    "worker 7 · 10-turn budget → attempt ends. Retry #2: stronger model + note “attempt 1 ran out re-reading auth.py” → done ✓ in 6 turns.",
    "all 60 finish in a minute · stuck → failed → retried · attempts are counted");

  s.addText("Every attempt has a budget. Every retry is spaced, randomized, and different from the last — stronger model, more budget, a note. Attempts are counted; tool 6 decides when to stop.",
    { x: 0.7, y: 6.5, w: 12.0, h: 0.55, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("Two failures that are not crashes. First: forty workers hit the build server together and it says 'too busy'. Left chart — instant retry: forty, forty, forty, every second, forever; the server never recovers because the swarm itself is now the load. This is the most common way a swarm hurts itself. Right chart — exponential backoff with jitter: 2s, 4s, 8s plus a random slice; the retries fan out, the server breathes, everyone finishes within a minute. Second failure: worker 7 is alive, heartbeating, renewing its lease — and re-reading the same file for the fourteenth time. Leases can't see this; only a budget per attempt can. Ten turns and the attempt ENDS; the retry gets a stronger model and a note about what went wrong — because retrying a deterministic failure identically fails identically. Land the title: leases handle workers that die; timeouts handle workers that don't. And the hand-off: attempts are counted — tool 6 says when to stop counting.");
}

// =====================================================================
// PAGE 20 · Tool 6 — Circuit breaker
// =====================================================================
{
  const s = base("Part 3 · Tool 6 of 9 — Circuit breaker (Nygard, Release It!, 2007)",
    "When a task keeps failing, stop trying. Flag it. Move on.", 28);
  s.addText("The problem: retries assume the failure is temporary. Some aren’t — the spec is wrong, the dependency is dead. Infinite retries burn budget and hide a real defect.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  // the task
  card(s, 0.7, 1.98, 12.0, 0.6, CARD);
  s.addText("THE TASK", { x: 0.9, y: 1.98, w: 1.3, h: 0.6, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, valign: "middle", margin: 0 });
  s.addText("Endpoint #41 in the migration. Its tests can never pass — one test still asserts the OLD behaviour. Every worker that pulls #41 fails. Every single one.", { x: 2.2, y: 1.98, w: 10.3, h: 0.6, fontFace: B, fontSize: 12.5, color: INK, valign: "middle", margin: 0 });

  // the state machine
  const arrow = (x1, y1, x2, y2, color, width = 2, head = true) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, ...(head ? { endArrowType: "triangle" } : {}) },
    });
  const state = (x, color, name, lines) => {
    card(s, x, 2.9, 2.7, 1.3, CARD2);
    s.addText(name, { x, y: 2.98, w: 2.7, h: 0.32, fontFace: H, fontSize: 13, bold: true, color, charSpacing: 2, align: "center", margin: 0 });
    s.addText(lines, { x: x + 0.15, y: 3.3, w: 2.4, h: 0.85, fontFace: B, fontSize: 10, color: INK, align: "center", margin: 0 });
  };
  state(0.9, GOOD, "CLOSED", "attempts flow.\nfailures are counted:\n#41 fails · fails · fails");
  state(5.35, BAD, "OPEN", "stop. no more attempts on #41.\nparked + flagged “needs a human”\nwith the failure log attached");
  state(9.8, SG, "HALF-OPEN", "one probe attempt.\npasses → closed\nfails → open again");
  arrow(3.6, 3.55, 5.35, 3.55, MUT);
  s.addText("3 failures in a row", { x: 3.6, y: 3.2, w: 1.75, h: 0.28, fontFace: B, fontSize: 10, italic: true, color: BAD, align: "center", margin: 0 });
  arrow(8.05, 3.55, 9.8, 3.55, MUT);
  s.addText("cooldown, or a human fixed something", { x: 7.95, y: 3.2, w: 1.95, h: 0.28, fontFace: B, fontSize: 9.5, italic: true, color: SG, align: "center", margin: 0 });
  // half-open → closed: long return arrow above the boxes
  arrow(11.15, 2.9, 11.15, 2.68, GOOD, 2, false);
  arrow(11.15, 2.68, 2.25, 2.68, GOOD, 2, false);
  arrow(2.25, 2.68, 2.25, 2.9, GOOD, 2, true);
  s.addText("probe passes → closed", { x: 5.0, y: 2.66, w: 3.4, h: 0.24, fontFace: B, fontSize: 9.5, italic: true, color: GOOD, align: "center", margin: 0 });
  // half-open → open: return arrow below
  arrow(11.15, 4.2, 11.15, 4.48, BAD, 2, false);
  arrow(11.15, 4.48, 6.7, 4.48, BAD, 2, false);
  arrow(6.7, 4.48, 6.7, 4.2, BAD, 2, true);
  s.addText("probe fails → open again", { x: 7.3, y: 4.5, w: 3.4, h: 0.24, fontFace: B, fontSize: 9.5, italic: true, color: BAD, align: "center", margin: 0 });

  // outcomes
  const outcome = (x, color, head, body, verdict) => {
    card(s, x, 4.9, 5.85, 1.45, CARD);
    s.addText(head, { x: x + 0.25, y: 4.98, w: 5.4, h: 0.28, fontFace: H, fontSize: 11, bold: true, color, charSpacing: 1, margin: 0 });
    s.addText(body, { x: x + 0.25, y: 5.28, w: 5.4, h: 0.68, fontFace: B, fontSize: 10.5, color: INK, margin: 0 });
    s.addText(verdict, { x: x + 0.25, y: 5.98, w: 5.4, h: 0.3, fontFace: B, fontSize: 11, bold: true, color, margin: 0 });
  };
  outcome(0.7, BAD, "WITHOUT A BREAKER",
    "#41 fails → retried → fails → retried… Forty attempts across eight workers. The wrong test is never noticed because every attempt looks like a fresh try. The other items wait while lanes cycle on #41.",
    "budget burned · defect hidden · queue starved");
  outcome(6.85, GOOD, "WITH A BREAKER",
    "Three failures → open. #41 is parked with its evidence: three attempt logs all ending in the same assertion. A human reads them in thirty seconds, fixes the test, closes the breaker. Meanwhile the other 59 endpoints finished.",
    "infinite loop → a ticket with evidence · lanes freed · 59/60 done");

  s.addText("A breaker turns an infinite loop into a ticket — and it is the piece the relay on page 12 lacked: a stage that keeps failing must stop, not hand a confident “done” downstream.",
    { x: 0.7, y: 6.5, w: 12.0, h: 0.55, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("Story: endpoint #41 cannot pass — one of its tests still asserts the old behaviour. So every worker that pulls it fails, and retries (tool 5) make the problem WORSE: each retry looks like a fresh attempt, nobody notices the pattern, forty attempts burn budget while the other items starve. The breaker is the counter that retries lack. Walk the state machine: CLOSED, attempts flow and failures are counted; three in a row and it OPENS — no more attempts, the item is parked and flagged with its evidence attached; then HALF-OPEN — one probe, after a cooldown or after a human changed something; pass → closed, fail → open again. For agents, what counts as a failure: verification failed, budget exhausted, or the same error signature repeating. And notice the human's role: they are the half-open probe, and because the parked item carries three attempt logs, their decision takes thirty seconds. Close on the relay: a stage that keeps failing must STOP. It must never pass a confident 'done' to the next agent.");
}

// =====================================================================
// PAGE 21 · Tool 7 — Supervisor trees ("let it crash")
// =====================================================================
{
  const s = base("Part 3 · Tool 7 of 9 — Supervisor trees (Erlang/OTP, Ericsson, 1986–)",
    "Let it crash. Something above it restarts it — from durable state.", 27);
  s.addText("The problem: workers die in ways no lease or timeout describes — OOM-killed, host rebooted, key revoked. Someone must notice and restart. And restart FROM something.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  card(s, 0.7, 1.98, 12.0, 0.6, CARD);
  s.addText("THE TASK", { x: 0.9, y: 1.98, w: 1.3, h: 0.6, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, valign: "middle", margin: 0 });
  s.addText("The migration, 2:00 AM. The host running workers 3–6 reboots. Four half-finished endpoints — and the orchestrator was on that host too.", { x: 2.2, y: 1.98, w: 10.3, h: 0.6, fontFace: B, fontSize: 12.5, color: INK, valign: "middle", margin: 0 });

  const arrow = (x1, y1, x2, y2, color, width = 1.5, dash) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle", ...(dash ? { dashType: "dash" } : {}) },
    });

  // --- the tree ---
  card(s, 2.45, 2.85, 3.3, 0.55, CARD2);
  s.addText("ROOT SUPERVISOR", { x: 2.45, y: 2.87, w: 3.3, h: 0.3, fontFace: H, fontSize: 11, bold: true, color: GOOD, charSpacing: 1, align: "center", margin: 0 });
  s.addText("systemd · k8s · cron — too simple to fail", { x: 2.45, y: 3.13, w: 3.3, h: 0.24, fontFace: B, fontSize: 9, color: MUT, align: "center", margin: 0 });
  arrow(4.1, 3.4, 4.1, 3.62, MUT);
  card(s, 2.45, 3.62, 3.3, 0.6, CARD2);
  s.addText("ORCHESTRATOR · supervises the workers", { x: 2.45, y: 3.64, w: 3.3, h: 0.3, fontFace: H, fontSize: 10.5, bold: true, color: INK, align: "center", margin: 0 });
  s.addText("✕ died with the host  →  restarted by root ✓", { x: 2.45, y: 3.92, w: 3.3, h: 0.26, fontFace: B, fontSize: 9, color: SG, align: "center", margin: 0 });
  const wx = [0.75, 1.98, 3.21, 4.44, 5.67, 6.9];
  wx.forEach((x, i) => {
    const dead = i >= 2;
    arrow(4.1, 4.22, x + 0.5, 4.6, dead ? BAD : MUT, 1.25, dead);
    card(s, x, 4.6, 1.0, 0.5, CARD2);
    s.addText(dead ? "✕" : `worker ${i + 1}`, { x, y: 4.6, w: 1.0, h: 0.5, fontFace: H, fontSize: dead ? 15 : 10, bold: true, color: dead ? BAD : INK, align: "center", valign: "middle", margin: 0 });
    s.addText(dead ? `worker ${i + 1}` : "alive", { x, y: 5.12, w: 1.0, h: 0.22, fontFace: B, fontSize: 8.5, color: dead ? BAD : GOOD, align: "center", margin: 0 });
  });
  s.addShape(pres.ShapeType.roundRect, { x: 3.1, y: 4.5, w: 4.95, h: 0.95, rectRadius: 0.08, fill: { type: "none" }, line: { color: BAD, width: 1.25, dashType: "dash" } });
  s.addText("host B rebooted", { x: 6.2, y: 5.42, w: 1.85, h: 0.22, fontFace: B, fontSize: 9, italic: true, color: BAD, align: "right", margin: 0 });
  s.addText("one-for-one: restart only the dead child (independent tasks)  ·  one-for-all: restart every sibling (shared state)", { x: 0.7, y: 5.68, w: 7.6, h: 0.24, fontFace: B, fontSize: 9, italic: true, color: MUT, margin: 0 });

  // --- right: durable state + what happens ---
  card(s, 8.55, 2.85, 4.15, 0.95, CARD);
  s.addText("DURABLE STATE · the board + the store", { x: 8.7, y: 2.92, w: 3.9, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: INK, charSpacing: 1, margin: 0 });
  s.addText("Every level restarts from here — never from memory. The tree holds no state worth saving.", { x: 8.7, y: 3.2, w: 3.9, h: 0.55, fontFace: B, fontSize: 10, color: MUT, margin: 0 });
  arrow(8.55, 3.3, 5.75, 3.85, GOOD, 1.5);
  s.addText("restarts from", { x: 6.6, y: 3.35, w: 1.5, h: 0.22, fontFace: B, fontSize: 9, italic: true, color: GOOD, align: "center", margin: 0 });

  card(s, 8.55, 3.95, 4.15, 1.95, CARD);
  s.addText("2:00:00 AM — WHAT ACTUALLY HAPPENS", { x: 8.7, y: 4.02, w: 3.9, h: 0.28, fontFace: H, fontSize: 10.5, bold: true, color: GOOD, charSpacing: 1, margin: 0 });
  s.addText([
    { text: "① root notices the orchestrator is gone. Restarts it. 5 seconds.", options: { breakLine: true, paraSpaceAfter: 4 } },
    { text: "② the new orchestrator reads the board: four leases expired → four items back to open.", options: { breakLine: true, paraSpaceAfter: 4 } },
    { text: "③ it spawns fresh workers; they pull the four items and start over.", options: { breakLine: true, paraSpaceAfter: 4 } },
    { text: "Lost: four in-flight attempts. Kept: 56 verified endpoints. Nobody was paged.", options: { bold: true, color: GOOD } },
  ], { x: 8.7, y: 4.32, w: 3.9, h: 1.55, fontFace: B, fontSize: 10, color: INK, valign: "top", margin: 0 });

  // outcomes
  card(s, 0.7, 5.98, 5.85, 0.62, CARD);
  s.addText("WITHOUT: the run silently stops at 2:00 AM. You find out at 9:00. Four leases held by ghosts; nothing else moves.", { x: 0.9, y: 5.98, w: 5.5, h: 0.62, fontFace: B, fontSize: 10.5, color: BAD, valign: "middle", margin: 0 });
  card(s, 6.85, 5.98, 5.85, 0.62, CARD);
  s.addText("WITH: the tree restarts the orchestrator, the orchestrator restarts the workers, the workers restart the work — all from the board.", { x: 7.05, y: 5.98, w: 5.5, h: 0.62, fontFace: B, fontSize: 10.5, color: GOOD, valign: "middle", margin: 0 });

  s.addText("Reliability doesn’t live in the worker. It lives one level up, in something too simple to fail — and in state nothing can forget. The supervisor never understands the work; it only knows alive, dead, and where to restart from.",
    { x: 0.7, y: 6.72, w: 12.0, h: 0.55, fontFace: B, fontSize: 12, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("Erlang was built at Ericsson to run telephone switches with nine nines of uptime, and its central idea sounds reckless: let it crash. Don't defend against every error inside a process — put a supervisor above it whose only job is to notice death and restart from a known-good state. Supervisors die too, so you stack them: a tree. Walk the scene: 2 AM, host B reboots, taking workers 3–6 AND the orchestrator. Root — systemd, Kubernetes, a cron job, something too simple to fail — restarts the orchestrator in seconds. The orchestrator holds no memory; it reads the board: four leases expired, four items reopened; it spawns workers, they pull, they start over. Lost: four in-flight attempts. Kept: fifty-six verified endpoints. Two rules for agents: the supervisor must be simpler than what it supervises — never put an LLM in the supervisor loop; and the tree holds no state — everything restarts from the board and the store. Strategies: one-for-one for independent tasks (tool 2 made them independent), one-for-all only when siblings share state.");
}

// =====================================================================
// PAGE 22 · Tool 8 — Health checks & contracts: the verification gate
// =====================================================================
{
  const s = base("Part 3 · Tool 8 of 9 — Health checks & contracts (the verification gate)",
    "Never ask a worker if it’s done. Check.", 28);
  s.addText("The problem: a worker’s “done ✓” is a claim, not a fact — and in a conversation the claim travels exactly as fast as the truth. Every tool so far has pointed here.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  card(s, 0.7, 1.98, 12.0, 0.6, CARD);
  s.addText("THE TASK", { x: 0.9, y: 1.98, w: 1.3, h: 0.6, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, valign: "middle", margin: 0 });
  s.addText("Endpoint #17. The worker submits “migrated, tests pass ✓.” It’s wrong — it ran the old test file. And #18 is waiting to build on #17.", { x: 2.2, y: 1.98, w: 10.3, h: 0.6, fontFace: B, fontSize: 12.5, color: INK, valign: "middle", margin: 0 });

  const arrow = (x1, y1, x2, y2, color, width = 1.75) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle" },
    });

  // --- the gate ---
  card(s, 0.75, 3.35, 1.3, 0.65, CARD2);
  s.addText("worker", { x: 0.75, y: 3.35, w: 1.3, h: 0.65, fontFace: H, fontSize: 11, bold: true, color: INK, align: "center", valign: "middle", margin: 0 });
  arrow(2.05, 3.67, 2.45, 3.67, MUT);
  card(s, 2.45, 3.25, 1.95, 0.85, CARD2);
  s.addText("SUBMITTED", { x: 2.45, y: 3.3, w: 1.95, h: 0.28, fontFace: H, fontSize: 10, bold: true, color: MUT, charSpacing: 1, align: "center", margin: 0 });
  s.addText("#17 · “done ✓”\na claim", { x: 2.45, y: 3.56, w: 1.95, h: 0.5, fontFace: B, fontSize: 10.5, color: INK, align: "center", margin: 0 });
  arrow(4.4, 3.67, 4.8, 3.67, MUT);
  s.addShape(pres.ShapeType.roundRect, { x: 4.8, y: 2.95, w: 2.1, h: 1.45, rectRadius: 0.1, fill: { color: CARD2 }, line: { color: GOOD, width: 2.25 } });
  s.addText("THE GATE", { x: 4.8, y: 3.02, w: 2.1, h: 0.3, fontFace: H, fontSize: 12, bold: true, color: GOOD, charSpacing: 2, align: "center", margin: 0 });
  s.addText("the orchestrator runs the\ncontract ITSELF:\ntests · schema · build\npolicy · budget", { x: 4.8, y: 3.32, w: 2.1, h: 1.05, fontFace: B, fontSize: 9.5, color: INK, align: "center", margin: 0 });
  // pass
  arrow(6.9, 3.35, 7.35, 3.05, GOOD);
  s.addText("pass", { x: 6.85, y: 2.85, w: 0.6, h: 0.22, fontFace: B, fontSize: 9.5, italic: true, color: GOOD, align: "center", margin: 0 });
  card(s, 7.35, 2.75, 1.05, 0.7, CARD2);
  s.addText("CLOSED ✓\nmerged", { x: 7.35, y: 2.75, w: 1.05, h: 0.7, fontFace: H, fontSize: 9.5, bold: true, color: GOOD, align: "center", valign: "middle", margin: 0 });
  // fail
  arrow(6.9, 4.0, 7.35, 4.3, BAD);
  s.addText("fail", { x: 6.85, y: 4.32, w: 0.6, h: 0.22, fontFace: B, fontSize: 9.5, italic: true, color: BAD, align: "center", margin: 0 });
  card(s, 7.35, 3.95, 1.05, 0.75, CARD2);
  s.addText("REJECTED\n→ open, verdict\nattached", { x: 7.35, y: 3.95, w: 1.05, h: 0.75, fontFace: H, fontSize: 8.5, bold: true, color: BAD, align: "center", valign: "middle", margin: 0 });
  s.addText("nothing downstream ever sees an unverified result", { x: 0.7, y: 4.55, w: 7.75, h: 0.24, fontFace: B, fontSize: 10, italic: true, color: INK, align: "center", margin: 0 });

  // --- four rules ---
  card(s, 8.6, 2.75, 4.1, 2.05, CARD);
  s.addText("FOUR RULES", { x: 8.75, y: 2.82, w: 3.8, h: 0.26, fontFace: H, fontSize: 10.5, bold: true, color: GOOD, charSpacing: 2, margin: 0 });
  s.addText([
    { text: "① The worker never grades itself. A separate process runs the check.", options: { breakLine: true, paraSpaceAfter: 3 } },
    { text: "② The contract is written before the work (tool 1) and is an inspectable state (tool 4).", options: { breakLine: true, paraSpaceAfter: 3 } },
    { text: "③ Unverified output is never an input. Ever.", options: { breakLine: true, paraSpaceAfter: 3 } },
    { text: "④ No oracle? Gate the actions, sample the words, vote across independent workers, escalate the irreversible to a human.", options: {} },
  ], { x: 8.75, y: 3.1, w: 3.8, h: 1.65, fontFace: B, fontSize: 9.5, color: INK, valign: "top", margin: 0 });

  // outcomes
  const outcome = (x, color, head, body) => {
    card(s, x, 4.95, 5.85, 1.3, CARD);
    s.addText(head, { x: x + 0.25, y: 5.02, w: 5.4, h: 0.28, fontFace: H, fontSize: 11, bold: true, color, charSpacing: 1, margin: 0 });
    s.addText(body, { x: x + 0.25, y: 5.32, w: 5.4, h: 0.88, fontFace: B, fontSize: 10.5, color: INK, margin: 0 });
  };
  outcome(0.7, BAD, "WITHOUT THE GATE",
    "#17 closes on the worker’s word. #18 starts building on it. Two hours later #18 fails for reasons nobody can see. A human finds the wrong test file at 4 PM. Both are redone. That is the relay from page 12, one hop at a time.");
  outcome(6.85, GOOD, "WITH THE GATE",
    "The orchestrator runs the real test file: red. #17 is rejected in four seconds with “test_auth_v2 was not run” attached. The retry passes. #17 closes on evidence; #18 starts on solid ground. Nothing downstream ever saw the claim.");

  s.addText("Every swarm success in this talk goes through this box. A single agent survives without it because a human is the gate. Remove the human, and the gate is not optional.",
    { x: 0.7, y: 6.45, w: 12.0, h: 0.55, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("This is the keystone; slides 1, 4 and 6 all pointed here. The idea is as old as load balancers: never trust a component's self-report — probe it. Story: the worker on #17 says tests pass; it ran the wrong test file. Without a gate that claim becomes truth, #18 builds on it, and the failure surfaces two hours later where nobody can explain it — the relay, one hop at a time. With a gate, the orchestrator runs the real tests itself and rejects the claim in four seconds with the reason attached. Four rules: the worker never grades itself; the contract is written before the work and is an inspectable state; unverified output is never an input; and when there is no oracle — writing, judgment calls — you gate the actions, sample the words, vote across independent workers, and escalate anything irreversible to a human. Then the honest closing: the single agent gets away without this because a human is watching — the human IS the gate. The moment you remove the human, this box becomes the most important thing in the system.");
}

// =====================================================================
// PAGE 23 · Tool 9 — Event sourcing & materialized views (+ observability)
// =====================================================================
{
  const s = base("Part 3 · Tool 9 of 9 — Event sourcing & materialized views (+ observability)",
    "Never rewrite history. Keep the log; serve each reader a view.", 28);
  s.addText("The problem: overwrite state and the past is gone; read all of it and the context is gone. One idea fixes both — an append-only log, and views sized for their readers.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: MUT, margin: 0 });

  card(s, 0.7, 1.98, 12.0, 0.6, CARD);
  s.addText("THE TASK", { x: 0.9, y: 1.98, w: 1.3, h: 0.6, fontFace: H, fontSize: 10.5, bold: true, color: MUT, charSpacing: 2, valign: "middle", margin: 0 });
  s.addText("The support system. Dana’s thread is 300 messages long. A worker pulls “ticket #4812 has a new message.” It cannot read 300 messages — and it must never rewrite one.", { x: 2.2, y: 1.98, w: 10.3, h: 0.6, fontFace: B, fontSize: 12.5, color: INK, valign: "middle", margin: 0 });

  const arrow = (x1, y1, x2, y2, color, width = 1.5, head = true) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, ...(head ? { endArrowType: "triangle" } : {}) },
    });

  // --- the log ---
  card(s, 0.7, 2.85, 2.55, 2.35, CARD);
  s.addText("THE LOG · append-only", { x: 0.7, y: 2.92, w: 2.55, h: 0.26, fontFace: H, fontSize: 10, bold: true, color: INK, charSpacing: 1, align: "center", margin: 0 });
  ["msg #1 · Dana", "reply #1", "refund #77 issued", "msg #2 · Dana", "…", "msg #300 · Dana"].forEach((t, i) => {
    const y = 3.22 + i * 0.31;
    s.addShape(pres.ShapeType.roundRect, { x: 0.85, y, w: 2.25, h: 0.26, rectRadius: 0.04, fill: { color: CARD2 }, line: { color: LINE, width: 1 } });
    s.addText(t, { x: 0.85, y, w: 2.25, h: 0.26, fontFace: M, fontSize: 8.5, color: t.includes("refund") ? SG : INK, align: "center", valign: "middle", margin: 0 });
  });
  s.addText("nothing edited · nothing deleted · the truth", { x: 0.7, y: 5.22, w: 2.55, h: 0.22, fontFace: B, fontSize: 8.5, italic: true, color: MUT, align: "center", margin: 0 });

  // --- the views (materialized from the log, one per reader) ---
  const views = [
    [3.75, 2.85, GOOD, "CASE STATE · for the worker", "~400 tokens, rebuilt from the log: open questions · promises made · actions taken · tone. This is what the worker loads — not 300 messages."],
    [8.35, 2.85, SW, "BOARD STATUS · for the scheduler", "one line per ticket: open · leased · closed. The queue from tool 3 is itself a view over this log."],
    [3.75, 4.05, INK, "DASHBOARD · for humans", "counts, SLA breaches, cost per ticket, error rate, who’s stuck. Observability is just another view."],
    [8.35, 4.05, SG, "LESSONS · for the next worker", "short, curated findings earlier workers appended. The answer to “knowledge stays in the compartment” — read at start, three lines, not a transcript."],
  ];
  views.forEach(([x, y, c, head, body]) => {
    card(s, x, y, 4.35, 1.05, CARD);
    s.addText(head, { x: x + 0.15, y: y + 0.07, w: 4.05, h: 0.26, fontFace: H, fontSize: 10.5, bold: true, color: c, charSpacing: 1, margin: 0 });
    s.addText(body, { x: x + 0.15, y: y + 0.34, w: 4.05, h: 0.7, fontFace: B, fontSize: 9.5, color: INK, margin: 0 });
    if (x < 8) arrow(3.25, 4.05, x, y + 0.5, MUT, 1.25);      // left column: straight from the log
  });
  // right column: routed around the left-column cards
  arrow(3.25, 2.95, 3.25, 2.76, MUT, 1.25, false); arrow(3.25, 2.76, 10.5, 2.76, MUT, 1.25, false); arrow(10.5, 2.76, 10.5, 2.85, MUT, 1.25);
  arrow(3.25, 5.15, 3.25, 5.24, MUT, 1.25, false); arrow(3.25, 5.24, 10.5, 5.24, MUT, 1.25, false); arrow(10.5, 5.24, 10.5, 5.1, MUT, 1.25);
  s.addText("views can be stale or wrong — the log cannot. Rebuild any view, any time, from the log.", { x: 3.75, y: 5.3, w: 8.95, h: 0.22, fontFace: B, fontSize: 10, italic: true, color: INK, align: "center", margin: 0 });

  // outcomes
  const outcome = (x, color, head, body) => {
    card(s, x, 5.58, 5.85, 0.88, CARD);
    s.addText(head, { x: x + 0.25, y: 5.62, w: 5.4, h: 0.26, fontFace: H, fontSize: 10.5, bold: true, color, charSpacing: 1, margin: 0 });
    s.addText(body, { x: x + 0.25, y: 5.86, w: 5.4, h: 0.58, fontFace: B, fontSize: 10, color: INK, margin: 0 });
  };
  outcome(0.7, BAD, "WITHOUT", "The worker loads 300 messages: 60k tokens gone before it reads Dana’s question. Or someone “cleans up” the thread — and the refund record vanishes with it.");
  outcome(6.85, GOOD, "WITH", "The worker loads a 400-token case state. The full log stays intact for audit. The dashboard shows cost per ticket. The next worker reads three lessons, not a transcript.");

  s.addText("The log is the truth; views are for reading. Nobody reads the truth directly — that is how a thousand agents share one history without any of them holding it.",
    { x: 0.7, y: 6.62, w: 12.0, h: 0.5, fontFace: B, fontSize: 11.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("Last tool, and it closes two loops. First, the mechanics: event sourcing — you never update state in place; you append what happened, and everything anyone reads is a VIEW rebuilt from that log. Git works this way; so does a ticket's history; so does a bank ledger. Dana's thread is 300 messages; the worker doesn't read them. It reads a 400-token case state — open questions, promises, actions, tone — rebuilt from the log. The scheduler reads a one-line status. Humans read a dashboard: observability is just another view. And the fourth view answers the caveat from tools 2 and 3 — 'knowledge stays in the compartment': a LESSONS view, short curated findings earlier workers appended, read at the start of every task. Three lines, not a transcript. Then the property that makes it safe: views can be stale or wrong; the log cannot. Rebuild any view from the log at any time. Close on the sentence that ties the tool to Part 1: the window is finite, so nobody reads the truth directly — everyone reads a view built for them. That is how a thousand agents share one history without any one of them holding it.");
}

// =====================================================================
// PAGE 24 · The environment, assembled — nine tools, five boxes, built once
// =====================================================================
{
  const s = base("Part 3 · The environment, assembled",
    "Nine tools, five boxes, built once. The task decides the rest.", 28);
  s.addText("Mechanisms are generic and dormant until needed — a lease that never expires costs nothing. What changes per task: the cut, the contract, the check, the view.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: MUT, margin: 0 });

  const arrow = (x1, y1, x2, y2, color, width = 1.5, both = false) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle", ...(both ? { beginArrowType: "triangle" } : {}) },
    });
  const box = (x, y, w, h, title, tools, body, color = INK) => {
    card(s, x, y, w, h, CARD2);
    s.addText(title, { x: x + 0.12, y: y + 0.08, w: w - 0.24, h: 0.3, fontFace: H, fontSize: 11.5, bold: true, color, margin: 0 });
    s.addText(tools, { x: x + 0.12, y: y + 0.36, w: w - 0.24, h: 0.24, fontFace: M, fontSize: 9, color: SG, margin: 0 });
    s.addText(body, { x: x + 0.12, y: y + 0.6, w: w - 0.24, h: h - 0.65, fontFace: B, fontSize: 9.5, color: MUT, margin: 0 });
  };

  // --- the five boxes ---
  box(0.75, 2.05, 2.35, 1.35, "ORCHESTRATOR", "tools 5 · 6 · 7", "budgets per attempt, the breaker, restart-from-the-board. Plain code. No LLM in this loop.", SW);
  box(3.7, 2.05, 2.2, 1.35, "THE BOARD", "tools 3 · 4 · 9", "the queue, the leases, the status view. Durable. Human-readable. The truth about work.");
  box(3.7, 3.85, 2.2, 1.35, "WORKERS × N", "tools 1 · 2", "bounded contexts in bulkheads: one brief, one compartment, one fresh context. Disposable.");
  box(6.5, 2.05, 1.85, 1.35, "THE GATE", "tools 8 · 4", "runs the contract itself; idempotent merge by item id. Nothing unverified gets past.", GOOD);
  box(6.5, 3.85, 1.85, 1.35, "LOG + VIEWS", "tools 9 · 1", "append-only artifacts; case state, lessons, dashboard rebuilt per reader.");
  arrow(3.1, 2.6, 3.7, 2.6, MUT);                        // orchestrator → board
  arrow(3.1, 3.1, 3.7, 4.3, MUT);                        // orchestrator → workers (spawn / supervise)
  arrow(4.8, 3.4, 4.8, 3.85, SW, 1.5, true);             // board ↔ workers (pull / lease)
  arrow(5.9, 4.2, 6.5, 3.0, GOOD);                       // workers → gate (submit)
  arrow(7.42, 3.4, 7.42, 3.85, GOOD);                    // gate → log (verified artifact)
  arrow(6.5, 2.35, 5.9, 2.35, GOOD);                     // gate → board (close ✓)
  arrow(6.5, 4.85, 5.9, 4.85, MUT);                      // views → workers (case state, lessons)
  s.addText("close ✓", { x: 5.85, y: 2.08, w: 0.7, h: 0.22, fontFace: B, fontSize: 8.5, italic: true, color: GOOD, align: "center", margin: 0 });
  s.addText("pull · lease", { x: 4.9, y: 3.5, w: 1.0, h: 0.22, fontFace: B, fontSize: 8.5, italic: true, color: SW, margin: 0 });
  s.addText("submit", { x: 5.95, y: 3.5, w: 0.7, h: 0.22, fontFace: B, fontSize: 8.5, italic: true, color: GOOD, margin: 0 });
  s.addText("views in", { x: 5.85, y: 4.9, w: 0.7, h: 0.22, fontFace: B, fontSize: 8.5, italic: true, color: MUT, align: "center", margin: 0 });
  s.addText("This is the whole multi-agent system. The agents are the least interesting box.", { x: 0.7, y: 5.4, w: 7.65, h: 0.3, fontFace: B, fontSize: 11, italic: true, color: INK, align: "center", margin: 0 });

  // --- what the task decides ---
  card(s, 8.65, 2.05, 4.05, 3.65, CARD);
  s.addText("WHAT THE TASK DECIDES", { x: 8.8, y: 2.12, w: 3.8, h: 0.26, fontFace: H, fontSize: 10.5, bold: true, color: SG, charSpacing: 2, margin: 0 });
  [["THE CUT", "tool 1", "into what independent, window-sized pieces? (if none are independent → a pipeline of gates, not a swarm)"],
   ["THE CONTRACT", "tools 1 · 4", "what crosses the boundary: a yes/no, a price, a state — never a transcript"],
   ["THE CHECK", "tool 8", "what proves it done: tests · schema · policy · a vote · a human — the oracle sets how far you can trust the swarm"],
   ["THE VIEW", "tool 9", "what each reader loads: 400 tokens of case state, one status line, three lessons"]].forEach(([h, t, b], i) => {
    const y = 2.45 + i * 0.8;
    s.addText(h, { x: 8.8, y, w: 1.3, h: 0.26, fontFace: H, fontSize: 10.5, bold: true, color: INK, margin: 0 });
    s.addText(t, { x: 8.8, y: y + 0.26, w: 1.3, h: 0.22, fontFace: M, fontSize: 8.5, color: SG, margin: 0 });
    s.addText(b, { x: 10.15, y, w: 2.45, h: 0.75, fontFace: B, fontSize: 9.5, color: MUT, margin: 0 });
  });

  s.addText("Build the nine once. Design four things per task. The environment behaves according to the task — because the task is what flows through it. Build the kitchen once; the recipe decides which burners are lit.",
    { x: 0.7, y: 5.95, w: 12.0, h: 0.75, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("The payoff slide of Part 3. Point at each box and read its tool numbers — the nine tools collapse into five pieces of infrastructure, and the agents are the least interesting one. Then the question the room is thinking: do I really need all nine? The honest answer is that most of them are mechanisms with near-zero idle cost — a lease that never expires, a breaker that never trips, a supervisor that never has to restart anything. You build them once and they sleep until the task's shape wakes them. What you actually design per task is four things: the cut (into what independent pieces — and if there are none, you're building a gated pipeline, not a swarm), the contract (what crosses the boundary), the check (what proves it done — and the oracle you have decides how far you can trust the swarm), and the view (what each reader loads). Kitchen analogy: you don't build a new kitchen per dish. The recipe decides which burners are lit.");
}

// =====================================================================
// PAGE 24b · Part 3 — Design choices: why these parts
// =====================================================================
{
  const s = base("Part 3 · The environment — design choices",
    "Why these parts? Boring, durable, already on the machine.", 27);
  s.addText("The interfaces are the architecture — claim · lease · verdict · event. The parts behind them are replaceable, so we picked the ones with nothing to install and nothing to run.",
    { x: 0.7, y: 1.5, w: 12.0, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  const cols = [[0.7, 1.5], [2.3, 2.15], [4.55, 5.05], [9.7, 2.95]];
  ["BOX", "WE CHOSE", "BECAUSE", "COULD ALSO BE"].forEach((h, i) =>
    s.addText(h, { x: cols[i][0], y: 1.92, w: cols[i][1], h: 0.25, fontFace: H, fontSize: 9.5, bold: true, color: MUT, charSpacing: 2, margin: 0 }));
  s.addShape(pres.ShapeType.line, { x: 0.7, y: 2.2, w: 11.95, h: 0.001, line: { color: LINE, width: 1 } });

  const rows = [
    [SW, "Board", "SQLite — one file, WAL mode", "One transaction is one atomic claim (BEGIN IMMEDIATE). Readers never block writers, so the live view is just a query. cp board.db backs up the entire system.", "GitHub Issues · Postgres · Redis Streams · DynamoDB — anything persistent with an atomic claim"],
    [SG, "Human mirror", "GitHub Issues", "Where humans already file work. A comment thread is a free evidence log; close-with-verdict is a status everyone reads; the gh CLI means no SDK. But no atomic claim and rate limits — so it mirrors, it does not schedule.", "Linear · Jira · a Slack channel"],
    [GOOD, "Compartments + store", "git worktrees → main", "Isolation for free: one directory and one branch per attempt. Landing = copy the verified files and commit; the history is the audit trail; a crashed attempt is just a directory to delete.", "containers · repo copies · object-store prefixes"],
    [INK, "Workers", "claude -p · codex exec", "Someone else maintains the harness: tools, permissions, sandbox, streaming. One contract — prompt in, result out — so the vendor and N are config, not code.", "the raw API loop (we ship one) · any CLI agent"],
    [BAD, "Gate", "the item’s test command", "A verdict the worker cannot argue with: the same command it was told to run, re-run by code. Exit 0 or nothing lands.", "schema check · linter · a human (awaiting_human)"],
    [MUT, "Log + views", "the same SQLite, append-only events", "Every state change is a write; every screen is a query. mas watch is a SELECT in a loop, from any process, on any machine that can read the file.", "Kafka · a log file · OpenTelemetry"],
  ];
  const y0 = 2.3, rh = 0.66, gap = 0.06;
  rows.forEach(([c, box, chose, why, alt], i) => {
    const y = y0 + i * (rh + gap);
    card(s, 0.7, y, 11.95, rh, i % 2 ? CARD : CARD2);
    chip(s, 0.85, y + 0.14, c);
    s.addText(box, { x: 1.12, y: y + 0.06, w: 1.15, h: rh - 0.12, fontFace: H, fontSize: 11, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(chose, { x: cols[1][0], y: y + 0.06, w: cols[1][1], h: rh - 0.12, fontFace: M, fontSize: 9.5, bold: true, color: c === INK || c === MUT ? SW : c, valign: "middle", margin: 0 });
    s.addText(why, { x: cols[2][0], y: y + 0.05, w: cols[2][1], h: rh - 0.1, fontFace: B, fontSize: 9.5, color: INK, valign: "middle", margin: 0 });
    s.addText(alt, { x: cols[3][0], y: y + 0.05, w: cols[3][1], h: rh - 0.1, fontFace: B, fontSize: 9, italic: true, color: MUT, valign: "middle", margin: 0 });
  });

  s.addText("Rule of thumb: pick parts you can cat. If one command shows you the whole state, you can debug it, back it up, and hand it to the next process.",
    { x: 0.7, y: 6.72, w: 12.0, h: 0.45, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("Why these parts and not a message broker or a database server. Start with the principle: the interfaces are the architecture — claim, lease, verdict, event — the parts are replaceable. Then the board: we began on GitHub Issues, because a swarm working in public issues is the most convincing demo there is — humans see the work, the comments are the evidence, close-with-verdict needs no dashboard. But Issues cannot give you an atomic claim and they rate-limit you, so in the environment they mirror while SQLite schedules: one file, one transaction per claim, readers never blocked (that is what makes the live view free), and 'cp' is a backup. Worktrees give isolation and an audit trail with nothing to install. The CLIs give you a maintained harness and make the vendor a config value. The gate is the one part you never delegate. Close on the rule of thumb: if you can cat it, you can debug it.");
}

// =====================================================================
// PAGES 25–27 · Three cases through the whole toolbox
// =====================================================================
const casePage = (cfg) => {
  const s = base(cfg.kicker, cfg.title, 27);
  s.addText(cfg.task, { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: MUT, margin: 0 });

  // left: through the five boxes
  s.addText("THROUGH THE FIVE BOXES", { x: 0.7, y: 1.95, w: 7.2, h: 0.24, fontFace: H, fontSize: 10, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  const boxes = [["ORCHESTRATOR", SW], ["THE BOARD", INK], ["WORKERS × N", INK], ["THE GATE", GOOD], ["LOG + VIEWS", INK]];
  boxes.forEach(([name, c], i) => {
    const y = 2.25 + i * 0.76;
    card(s, 0.7, y, 7.2, 0.68, CARD);
    s.addText(name, { x: 0.85, y, w: 1.55, h: 0.68, fontFace: H, fontSize: 10, bold: true, color: c, valign: "middle", margin: 0 });
    s.addText(cfg.rows[i], { x: 2.45, y, w: 5.35, h: 0.68, fontFace: B, fontSize: 10, color: INK, valign: "middle", margin: 0 });
  });

  // right: which walls + the four decisions
  card(s, 8.15, 1.95, 4.55, 1.55, CARD);
  s.addText("WHICH WALLS IT HITS", { x: 8.3, y: 2.02, w: 4.3, h: 0.24, fontFace: H, fontSize: 10, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  [["the backlog", SW], ["the crash", BAD], ["the window", SG]].forEach(([w, c], i) => {
    const y = 2.3 + i * 0.38;
    s.addText("✓", { x: 8.3, y, w: 0.3, h: 0.34, fontFace: H, fontSize: 12, bold: true, color: c, valign: "middle", margin: 0 });
    s.addText(w, { x: 8.6, y, w: 1.15, h: 0.34, fontFace: H, fontSize: 10, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(cfg.walls[i], { x: 9.75, y, w: 2.85, h: 0.34, fontFace: B, fontSize: 9, color: MUT, valign: "middle", margin: 0 });
  });
  card(s, 8.15, 3.65, 4.55, 2.4, CARD);
  s.addText("THE FOUR DECISIONS", { x: 8.3, y: 3.72, w: 4.3, h: 0.24, fontFace: H, fontSize: 10, bold: true, color: MUT, charSpacing: 2, margin: 0 });
  [["the cut", cfg.cut], ["the contract", cfg.contract], ["the check", cfg.check], ["the view", cfg.view]].forEach(([k, v], i) => {
    const y = 4.0 + i * 0.4;
    s.addText(k, { x: 8.3, y, w: 1.25, h: 0.38, fontFace: H, fontSize: 9.5, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(v, { x: 9.55, y, w: 3.05, h: 0.38, fontFace: B, fontSize: 9, color: MUT, valign: "middle", margin: 0 });
  });
  s.addText(cfg.oracle, { x: 8.3, y: 5.62, w: 4.3, h: 0.4, fontFace: B, fontSize: 9.5, bold: true, color: cfg.oracleColor, valign: "middle", margin: 0 });

  // bottom: result + source
  s.addText(cfg.result, { x: 0.7, y: 6.2, w: 12.0, h: 0.55, fontFace: B, fontSize: 12.5, italic: true, color: SG, align: "center", margin: 0 });
  if (cfg.sources) s.addText(cfg.sources, { x: 0.7, y: 6.78, w: 12.0, h: 0.26, fontFace: B, fontSize: 9.5, align: "center", margin: 0 });
  s.addNotes(cfg.notes);
};

casePage({
  kicker: "Part 3 · Case 1 of 3 — customer support",
  title: "Case 1 · 500 conversations, zero persistent agents",
  task: "A support desk: 500 open conversations, bursty inbound, refunds and plan changes allowed, 24/7. There is no “Dana’s agent.” There is Dana’s thread — and whoever is free.",
  rows: [
    "sizes the pool to inbound volume (20 workers at 3 AM, 200 at noon); a budget per reply; a breaker on tickets that bounce three times; restarts from the board",
    "one item per inbound message — “ticket #4812 has a new message” — leased by whoever is free; ordered by SLA, not by arrival",
    "pull one message, load the 400-token case state (never the 300-message thread), reply, write state back, die. The next message may go to anyone",
    "actions are keyed states — “refund #77 issued,” “plan = Basic from July” — policy-checked (refund cap, no deletions); the irreversible goes to a human; replies sampled for QA",
    "the thread is the log; case state and lessons are views rebuilt from it; the dashboard shows SLA, cost per ticket, escalations",
  ],
  walls: ["bursty inbound that one thread can’t clear", "threads live for weeks; workers don’t have to", "300-message threads never enter a context — views do"],
  cut: "per inbound message", contract: "a reply + actions as keyed states", check: "policy on actions · sampled QA on words · a human on the irreversible", view: "case state ~400 tokens · lessons · dashboard",
  oracle: "ORACLE: SOFT — there is no unit test for a good reply. So gate the actions hard, sample the words, and put a human behind every irreversible door.", oracleColor: SG,
  result: "Threads are state, workers are throughput. A wrong reply costs an apology; a wrong action is impossible. This is how contact centres already run — a ticket queue and whoever is free.",
  notes: "Run the toolbox on the product everyone recognizes. The key move: there is no 'Dana's agent'. Dana's thread is the log; the worker that answers her at 3 AM regenerates the agent from a 400-token case state and dies. Actions are keyed states so a retried worker can't refund twice; the refund cap and the 'no deletions' rule are the gate; anything irreversible escalates. Be honest about the oracle: a good reply has no test, so this case leans on gating actions rather than words — that is a design choice forced by the oracle, and it is the right one.",
});

casePage({
  kicker: "Part 3 · Case 2 of 3 — code migration at scale (Google, 2025)",
  title: "Case 2 · Migrating a monorepo: thousands of files, one gate",
  task: "Google ran 39 internal migrations in twelve months — e.g. 32-bit → 64-bit IDs across Ads — with LLM-generated edits, verified by build and tests, reviewed by humans.",
  rows: [
    "static analysis finds every location to change and makes one unit per file or call-site cluster; retries a failed unit with the compiler’s error attached; parks units that won’t converge",
    "the list of migration units and their state — pending → edited → verified → reviewed → committed. Thousands of rows; readable by any engineer",
    "one unit each, in its own checkout: rewrite this file to the new type or API. No knowledge of the other thousand files — and no need for it",
    "compile + the existing tests + lints, run by the pipeline: a red build is a rejection with the error attached. Then a human reviews the diff — reviews, doesn’t redo",
    "every edit is a diff in version control (append-only); the dashboard is a view: % done, % accepted, hours saved",
  ],
  walls: ["thousands of files — years of manual work", "multi-week runs; any unit can be redone", "no context holds a monorepo — units are file-sized"],
  cut: "one file or call-site cluster", contract: "a diff that compiles and passes the existing tests", check: "build + tests (a real oracle) → human review", view: "unit status · the diff · the dashboard",
  oracle: "ORACLE: TESTS — hard enough to trust at scale. Humans review the verified diff; they never redo the work.", oracleColor: GOOD,
  result: "74% of code changes LLM-generated · ~50% of total migration time saved · 39 migrations in a year. The gate is what made the numbers safe to trust.",
  sources: [{ text: "Ziftci et al., “Migrating Code At Scale With LLMs At Google” (2025)", options: { hyperlink: { url: "https://arxiv.org/abs/2504.09691" }, color: SW } }, { text: "   ·   ", options: { color: MUT } }, { text: "Nikolov et al., “How is Google using AI for internal code migrations?” (2025)", options: { hyperlink: { url: "https://arxiv.org/abs/2501.06972" }, color: SW } }],
  notes: "This is our 60-endpoint migration at ten-thousand-times scale, and it is published. Google's pipeline is our five boxes with different names: analysis creates the units (the cut), each unit is edited in isolation (bulkheads), the build and tests are the gate, version control is the log, a dashboard is the view. Note what humans do: they review verified diffs — they don't redo work, and they aren't the gate. Results: about three quarters of the changes LLM-generated, roughly half the total time saved, thirty-nine migrations in a year. The lesson to land: those numbers are trustworthy BECAUSE a compiler and a test suite stood between the model and the codebase.",
});

casePage({
  kicker: "Part 3 · Case 3 of 3 — unit tests at scale (Meta TestGen-LLM, 2024)",
  title: "Case 3 · Tests for thousands of classes: three filters, zero faith",
  task: "TestGen-LLM: an LLM proposes extra unit tests per class; each must build, pass reliably, and raise coverage — or it is discarded. Engineers see only survivors.",
  rows: [
    "walks the codebase, one unit per class; sends each candidate through three filters in order; keeps only survivors; a budget per class; nothing is ever shown that didn’t pass all three",
    "the list of classes to improve — pending → proposed → filtered → offered to an engineer → accepted. Thousands of rows, no dependencies between them",
    "one class each: read the existing test file, propose new test cases for it. No knowledge of the other classes needed — and none available",
    "three automatic filters: does it build? does it pass — run repeatedly, to catch flaky tests? does it raise coverage? Fail any one → discarded, silently. Then an engineer reviews the survivor",
    "surviving tests land as diffs in version control; the dashboard is a view: build rate, pass rate, coverage gained, acceptance rate per product",
  ],
  walls: ["thousands of under-tested classes nobody has time for", "any class can be redone; order never matters", "one class fits a context — the codebase never does"],
  cut: "one class · one test file", contract: "a test that builds, passes repeatedly, and adds coverage", check: "build → repeated pass → coverage delta (automatic)", view: "only survivors reach an engineer · the dashboard",
  oracle: "ORACLE: HARD — build, pass, and coverage are machine-checkable. The filters ARE the design: hallucinated tests never reach a human.", oracleColor: GOOD,
  result: "75% of generated tests built · 57% passed reliably · 25% raised coverage · 73% of surviving recommendations accepted by Meta engineers for production. The gate turned a hallucination-prone generator into a tool people trust.",
  sources: [{ text: "Alshahwan et al., “Automated Unit Test Improvement using Large Language Models at Meta” (FSE 2024)", options: { hyperlink: { url: "https://arxiv.org/abs/2402.09171" }, color: SW } }],
  notes: "The most useful case for a room of engineers: everyone has classes nobody tested. Meta's design is our toolbox with the gate turned up to maximum. One class per worker — the cut is trivial and the units are independent. The contract is strict: a test that builds, passes on repeated runs (that's how they catch flaky tests), and measurably raises coverage. Three filters in order; fail any one and the candidate is dropped silently — engineers only ever see survivors. Read the funnel aloud: 75% built, 57% passed reliably, 25% raised coverage — so three quarters of what the model produced never reached a human — and of what did, 73% was accepted into production. That is the whole thesis in numbers: the model is fallible, the filters are not, and the environment decides what counts. Same shape as Google's migration, same shape as the support desk — the oracle just keeps getting harder, and the swarm gets trusted with more.",
});

// =====================================================================
// PAGE 28 · The two dials — the real design space
// =====================================================================
{
  const s = base("Part 4 · The takeaway", "The real design space is two dials — not a head count.", 28);
  s.addText("Every architecture in this talk is a setting of these two dials. “Single agent” and “swarm” are just the corners.",
    { x: 0.7, y: 1.5, w: 11.8, h: 0.3, fontFace: B, fontSize: 12, italic: true, color: MUT, margin: 0 });

  const arrow = (x1, y1, x2, y2, color, width = 1.75, dash) =>
    s.addShape(pres.ShapeType.line, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle", ...(dash ? { dashType: "dash" } : {}) },
    });
  const dot = (x, y, color, label, lx, ly, lw, align = "left") => {
    s.addShape(pres.ShapeType.ellipse, { x: x - 0.11, y: y - 0.11, w: 0.22, h: 0.22, fill: { color }, line: { type: "none" } });
    s.addText(label, { x: lx, y: ly, w: lw, h: 0.5, fontFace: B, fontSize: 9.5, color: INK, align, margin: 0 });
  };

  // the plane
  card(s, 0.7, 2.0, 7.25, 4.05, CARD);
  arrow(1.35, 5.55, 7.6, 5.55, MUT, 2);                  // dial 1 (x)
  arrow(1.35, 5.55, 1.35, 2.35, MUT, 2);                 // dial 2 (y)
  s.addText("DIAL 1 · what does each call see?", { x: 3.2, y: 5.62, w: 3.2, h: 0.24, fontFace: H, fontSize: 9.5, bold: true, color: MUT, charSpacing: 1, align: "center", margin: 0 });
  s.addText("everything — one shared transcript", { x: 1.4, y: 5.62, w: 2.2, h: 0.24, fontFace: B, fontSize: 9, italic: true, color: SG, margin: 0 });
  s.addText("a view — brief + state", { x: 5.9, y: 5.62, w: 1.75, h: 0.24, fontFace: B, fontSize: 9, italic: true, color: SW, align: "right", margin: 0 });
  s.addText("DIAL 2 · who decides the next call?", { x: 1.45, y: 2.1, w: 3.4, h: 0.24, fontFace: H, fontSize: 9.5, bold: true, color: MUT, charSpacing: 1, margin: 0 });
  s.addText("↑ your code — board · leases · gate", { x: 1.45, y: 2.34, w: 3.0, h: 0.24, fontFace: B, fontSize: 9, italic: true, color: SW, margin: 0 });
  s.addText("↓ the model, from inside its loop", { x: 1.45, y: 5.28, w: 3.0, h: 0.24, fontFace: B, fontSize: 9, italic: true, color: SG, margin: 0 });

  // positions
  dot(1.9, 5.0, SG, "single agent — sees everything, schedules itself", 2.1, 4.86, 1.75);
  dot(4.2, 5.0, MUT, "compaction — an agent reading a summary of itself", 4.4, 4.86, 2.1);
  dot(3.2, 4.1, BAD, "the relay — each agent sees a summary; the previous agent decides. Loses work.", 3.4, 3.9, 2.35);
  dot(6.85, 4.55, SG, "fan-out → one agent (tool 1): workers see briefs; a lead model schedules", 4.55, 4.28, 2.15, "right");
  dot(6.85, 2.75, SW, "the swarm — and all three cases: sees a view, code decides", 4.3, 2.48, 2.4, "right");
  arrow(5.85, 3.6, 6.6, 3.0, GOOD, 1.75, true);
  s.addText("the nine tools move you here", { x: 3.7, y: 3.42, w: 2.15, h: 0.24, fontFace: B, fontSize: 9, italic: true, color: GOOD, align: "right", margin: 0 });

  // how to read it
  card(s, 8.2, 2.0, 4.5, 4.05, CARD);
  s.addText("HOW TO SET THE DIALS", { x: 8.35, y: 2.08, w: 4.2, h: 0.26, fontFace: H, fontSize: 10.5, bold: true, color: SG, charSpacing: 2, margin: 0 });
  s.addText([
    { text: "Dial 1 — turn toward “a view” when the work exceeds one window or must run in parallel. Leave it at “everything” when there is a pattern to amortize and it fits: one head that sees it all is cheaper and often more accurate.", options: { breakLine: true, paraSpaceAfter: 6 } },
    { text: "Dial 2 — turn toward “your code” the moment nobody is watching. In a chat, the human is the scheduler and the gate. Remove the human, and code must take both jobs — leases, retries, verification.", options: { breakLine: true, paraSpaceAfter: 6 } },
    { text: "The relay is the trap: dial 1 half-turned (summaries), dial 2 not turned at all (an agent decides). It is the only setting in this talk that destroys work.", options: { breakLine: true, paraSpaceAfter: 6 } },
    { text: "Nine tools, one direction: they are how you turn both dials without losing the truth — state moves out of the context, scheduling moves into code.", options: { bold: true, color: GOOD } },
  ], { x: 8.35, y: 2.38, w: 4.2, h: 3.6, fontFace: B, fontSize: 10, color: INK, valign: "top", margin: 0 });

  s.addText("There was never a choice between one agent and many. Only: what does each call see, and who decides the next one.",
    { x: 0.7, y: 6.3, w: 12.0, h: 0.5, fontFace: B, fontSize: 13, italic: true, color: SG, align: "center", margin: 0 });

  s.addNotes("The framework to take home. Two dials: what each call sees (everything → a view) and who decides the next call (the model → your code). Place the talk's architectures on the plane: the single agent bottom-left; compaction a little to its right — an agent reading a summary of itself; the relay in the middle-bottom, the one setting that destroyed work; fan-out-to-one-agent on the right but low, because a lead model still schedules; the swarm and all three cases top-right. The nine tools are the arrow: they move you toward top-right without losing the truth — state out of the context, scheduling into code. Then the two rules for setting the dials, and the honest one about dial 1: leave it at 'everything' when the work fits and has a pattern — one head is cheaper, and often more accurate.");
}

// =====================================================================
// PAGE 29 · Close
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("A single agent is a swarm with N = 1.", { x: 1.0, y: 2.2, w: 11.3, h: 0.95, fontFace: H, fontSize: 40, bold: true, color: INK, align: "center", margin: 0 });
  s.addText("You never choose whether to build the MAS — only N.", { x: 1.0, y: 3.25, w: 11.3, h: 0.7, fontFace: H, fontSize: 26, bold: true, color: SW, align: "center", margin: 0 });
  s.addText("Users don’t want agents. They want work that doesn’t get lost.\nAgents are the demo; the environment is the product. Build the board, the gate, and the log — then N is a number in your config.",
    { x: 1.9, y: 4.35, w: 9.5, h: 1.1, fontFace: B, fontSize: 16, color: MUT, align: "center", margin: 0 });
  s.addText("four laws  ·  no agents, only context  ·  the environment  ·  nine tools  ·  three cases  ·  two dials", { x: 0.9, y: 6.45, w: 11.5, h: 0.35, fontFace: M, fontSize: 11.5, color: MUT, align: "center", margin: 0 });
  s.addNotes("End on the two lines and stop talking. Expected questions: 'so should I never build a swarm?' — build the environment always; raise N at the clock, the window, and failure. 'What about tasks with no oracle?' — gate the actions, sample the words, vote across independent workers, escalate the irreversible. 'Isn't this just distributed systems?' — yes. That is the point.");
}

pres.writeFile({ fileName: "/Users/shimonmoyal/claude_mas/lecture/lecture.pptx" }).then(() => console.log("written"));
