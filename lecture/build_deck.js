const pptxgen = require("pptxgenjs");

const BG = "131719", CARD = "1B2125", CARD2 = "222A2F", INK = "E4E9EC",
  MUT = "93A0A8", LINE = "2A3237", SW = "4593C8", SG = "BA8434",
  GOOD = "6FBF73", BAD = "D9634E";
const H = "Arial", B = "Calibri", M = "Courier New";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5

const base = (kicker, title) => {
  const s = pres.addSlide();
  s.background = { color: BG };
  if (kicker)
    s.addText(kicker.toUpperCase(), { x: 0.6, y: 0.32, w: 12.1, h: 0.3, fontFace: H, fontSize: 11, bold: true, color: MUT, charSpacing: 3, margin: 0 });
  if (title)
    s.addText(title, { x: 0.6, y: 0.6, w: 12.1, h: 0.85, fontFace: H, fontSize: 30, bold: true, color: INK, margin: 0 });
  return s;
};

const card = (s, x, y, w, h, fill = CARD) =>
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: LINE, width: 1 } });

const chip = (s, x, y, color) =>
  s.addShape(pres.ShapeType.roundRect, { x, y, w: 0.18, h: 0.18, rectRadius: 0.04, fill: { color }, line: { type: "none" } });

const stat = (s, x, y, w, num, label, color) => {
  s.addText(num, { x, y, w, h: 0.75, fontFace: M, fontSize: 34, bold: true, color, align: "center", margin: 0 });
  s.addText(label, { x, y: y + 0.72, w, h: 0.6, fontFace: B, fontSize: 12.5, color: MUT, align: "center", margin: 0 });
};

const bullets = (s, x, y, w, h, items, opts = {}) =>
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { code: "2022", indent: 12 }, breakLine: i < items.length - 1, paraSpaceAfter: opts.gap ?? 8 } })),
    { x, y, w, h, fontFace: B, fontSize: opts.size ?? 14.5, color: opts.color ?? INK, valign: "top", margin: 0 });

// ---------- 1 · TITLE ----------
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("One Agent Is Already a Swarm", { x: 0.9, y: 2.35, w: 11.5, h: 1.1, fontFace: H, fontSize: 48, bold: true, color: INK, align: "center", margin: 0 });
  s.addText("Why multi-agent systems are infrastructure, not agent count — a six-round empirical lecture", { x: 1.9, y: 3.55, w: 9.5, h: 0.6, fontFace: B, fontSize: 19, color: SW, align: "center", margin: 0 });
  s.addText("mas  ·  Haiku 4.5  ·  128 verified task lifecycles  ·  total spend $11.30", { x: 2.9, y: 6.5, w: 7.5, h: 0.35, fontFace: M, fontSize: 12, color: MUT, align: "center", margin: 0 });
  s.addNotes("Open with the 77-second Remotion video, then this title. Framing: everything in this talk is measured, not opined. Six benchmark rounds, eleven dollars.");
}

// ---------- 2 · THERE ARE NO AGENTS ----------
{
  const s = base("Part 1 · The illusion", "There are no agents — only stateless calls");
  bullets(s, 0.6, 1.75, 5.9, 4.0, [
    "The model remembers NOTHING between API calls.",
    "A harness keeps a transcript and replays the WHOLE thing into every fresh, memoryless call.",
    "The 'agent' is a narrative the loop performs — continuity is faked by replay.",
    "So one 'agent' on our benchmark = 70 independent model invocations coordinating through a shared document.",
  ], { size: 16, gap: 12 });
  // transcript stack visual
  const bx = 7.3, by = 1.9;
  ["user brief", "assistant: read file", "tool result", "assistant: edit", "…grows forever"].forEach((t, i) => {
    card(s, bx, by + i * 0.62, 2.6, 0.5, CARD);
    s.addText(t, { x: bx + 0.15, y: by + i * 0.62 + 0.06, w: 2.4, h: 0.38, fontFace: M, fontSize: 11.5, color: i % 2 ? SW : INK, margin: 0 });
  });
  s.addShape(pres.ShapeType.line, { x: bx + 2.7, y: by + 1.5, w: 0.9, h: 0, line: { color: SG, width: 3, endArrowType: "triangle", dashType: "dash" } });
  card(s, bx + 3.7, by + 0.9, 1.7, 1.3, CARD2);
  s.addText("LLM", { x: bx + 3.7, y: by + 1.05, w: 1.7, h: 0.5, fontFace: H, fontSize: 22, bold: true, color: INK, align: "center", margin: 0 });
  s.addText("stateless", { x: bx + 3.7, y: by + 1.55, w: 1.7, h: 0.3, fontFace: B, fontSize: 11, color: MUT, align: "center", margin: 0 });
  s.addText("the ENTIRE stack is re-sent, every call", { x: bx, y: by + 3.35, w: 5.4, h: 0.35, fontFace: B, fontSize: 12.5, italic: true, color: SG, margin: 0 });
  s.addNotes("Destroy the noun first. Once the audience accepts that an agent is a loop replaying a transcript into a memoryless model, 'single vs multi' is already dead as a category — it becomes a question about context topology.");
}

// ---------- 3 · SAME ENGINE ----------
{
  const s = base("Part 1 · The illusion", "Same engine — the only difference is what each call sees");
  card(s, 0.9, 1.9, 5.5, 3.4);
  chip(s, 1.2, 2.2, SG);
  s.addText("“Single agent”", { x: 1.5, y: 2.08, w: 4, h: 0.4, fontFace: H, fontSize: 18, bold: true, color: SG, margin: 0 });
  stat(s, 1.2, 2.75, 2.4, "70", "calls per job", SG);
  stat(s, 3.7, 2.75, 2.4, "32.6k", "avg input tokens / call", SG);
  s.addText("one growing thread — every call sees everything", { x: 1.2, y: 4.45, w: 4.9, h: 0.6, fontFace: B, fontSize: 13, color: MUT, margin: 0 });
  card(s, 6.9, 1.9, 5.5, 3.4);
  chip(s, 7.2, 2.2, SW);
  s.addText("“Swarm”", { x: 7.5, y: 2.08, w: 4, h: 0.4, fontFace: H, fontSize: 18, bold: true, color: SW, margin: 0 });
  stat(s, 7.2, 2.75, 2.4, "350", "calls per job", SW);
  stat(s, 9.7, 2.75, 2.4, "7.6k", "avg input tokens / call", SW);
  s.addText("forty short threads — each call sees only its brief + artifacts", { x: 7.5, y: 4.45, w: 4.7, h: 0.6, fontFace: B, fontSize: 13, color: MUT, margin: 0 });
  s.addText("Both are swarms of stateless calls. The design choice is context topology + scheduling — the two dials.", { x: 0.9, y: 5.85, w: 11.5, h: 0.5, fontFace: B, fontSize: 16, bold: true, color: INK, align: "center", margin: 0 });
  s.addNotes("These are real logged numbers from round 2. Same model, same prompt, same tools. The billing data makes the architecture difference visible: one long transcript vs forty short ones.");
}

// ---------- 4 · WHY THE OBSESSION ----------
{
  const s = base("Part 2 · The obsession", "Why is everyone building swarms?");
  const rows = [
    ["The org-chart metaphor", "We called them 'agents', so we scale like hiring. But LLM calls have no identity, no on-the-job learning, no cheap coordination.", SG],
    ["Demo economics", "Forty progress bars go viral; 'idempotent task leasing' does not. The obsession is partly content.", SW],
    ["Vendor incentives", "'Fleet' is a pricing-page word. Agent count is legible to buyers; handoff-verification rate is not.", SW],
    ["Real pain, wrong prescription", "The three walls are real: the window, the crash, the backlog. 'More agents' pattern-matches to microservices — which scaled throughput, never intelligence.", BAD],
  ];
  rows.forEach((r, i) => {
    const y = 1.75 + i * 1.28;
    card(s, 0.7, y, 11.9, 1.12);
    chip(s, 1.0, y + 0.22, r[2]);
    s.addText(r[0], { x: 1.35, y: y + 0.1, w: 3.4, h: 0.9, fontFace: H, fontSize: 16, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(r[1], { x: 4.9, y: y + 0.1, w: 7.4, h: 0.92, fontFace: B, fontSize: 13, color: MUT, valign: "middle", margin: 0 });
  });
  s.addNotes("The fourth reason is the deepest: the pain is real, the prescription is cargo cult. Users never wanted agents — they want work done, unattended, not lost, verified. Every one of those is an infrastructure property.");
}

// ---------- 5 · THE EXPERIMENT ----------
{
  const s = base("Part 3 · The evidence", "The experiment: six rounds, $11.30, nothing self-graded");
  bullets(s, 0.7, 1.8, 6.1, 4.6, [
    "Worker model: Haiku 4.5 everywhere — identical system prompt, tools, repo snapshot in every condition.",
    "Task board: real GitHub Issues (claude-mas-bench / -xl) — workers pull briefs, orchestrator closes issues.",
    "Equal aggregate budgets: 8×14 = one agent's 112 turns; 40×10 = one agent's 400.",
    "Scoring: the orchestrator runs pytest itself. Agent claims are ignored.",
    "Tests immutable; workers isolated in per-task copies; only verified modules merge.",
  ], { size: 14.5, gap: 10 });
  card(s, 7.2, 1.9, 5.3, 4.3, CARD);
  s.addText("The six rounds", { x: 7.5, y: 2.1, w: 4.8, h: 0.4, fontFace: H, fontSize: 16, bold: true, color: INK, margin: 0 });
  bullets(s, 7.5, 2.6, 4.7, 3.5, [
    "R1 — 8 small modules, 42 tests",
    "R2 — 40 modules, 43k lines (context trap)",
    "R3 — 5% per-turn kill rate (chaos)",
    "R4 — topologies: chain, stigmergy",
    "R5 — read-once memory test",
    "R6 — adversarial facts + chaos, no oracle",
  ], { size: 13.5, gap: 7, color: MUT });
  s.addNotes("Emphasize the fairness contract — this is what makes the results defensible. Every number that follows was measured by the orchestrator running the tests, never by agents reporting on themselves.");
}

// ---------- 6 · WALL-CLOCK CHART ----------
{
  const s = base("Part 3 · The evidence", "The swarm's reliable win: the clock");
  card(s, 0.8, 1.8, 8.0, 5.0, CARD);
  s.addChart(pres.ChartType.bar, [
    { name: "Swarm", labels: ["R1 small repo", "R2 43k lines", "R3 under chaos"], values: [27.0, 130.2, 177.5] },
    { name: "Single", labels: ["R1 small repo", "R2 43k lines", "R3 under chaos"], values: [50.4, 190.8, 403.2] },
  ], {
    x: 1.0, y: 2.0, w: 7.6, h: 4.6,
    barDir: "col", chartColors: [SW, SG],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 11, dataLabelFontFace: M,
    showLegend: true, legendPos: "t", legendColor: MUT, legendFontSize: 12,
    catAxisLabelColor: MUT, catAxisLabelFontSize: 12, valAxisLabelColor: MUT, valAxisLabelFontSize: 10,
    valAxisTitle: "wall-clock seconds", showValAxisTitle: true, valAxisTitleColor: MUT, valAxisTitleFontSize: 11,
    valGridLine: { color: LINE, size: 1 }, catGridLine: { style: "none" },
    chartArea: { fill: { color: CARD } }, plotArea: { fill: { color: CARD } },
  });
  stat(s, 9.3, 2.3, 3.2, "1.5–1.9×", "faster on clean runs", SW);
  stat(s, 9.3, 4.0, 3.2, "2.3×", "faster under failures", SW);
  s.addText("ceiling = rate limits,\nnot architecture", { x: 9.3, y: 5.6, w: 3.2, h: 0.7, fontFace: B, fontSize: 12.5, italic: true, color: MUT, align: "center", margin: 0 });
  s.addNotes("Two mechanisms stack: concurrency (wall-clock = critical path, not sum) and smaller contexts serving faster per call (7.6k vs 32.6k avg input). Note the gap WIDENS under chaos.");
}

// ---------- 7 · THE TIE + THE TRAP ----------
{
  const s = base("Part 3 · The evidence", "Accuracy: the swarm never won a clean round");
  card(s, 0.7, 1.8, 5.8, 4.6);
  s.addText("Rounds 1–2: the tie", { x: 1.0, y: 2.0, w: 5.2, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: INK, margin: 0 });
  bullets(s, 1.0, 2.55, 5.2, 3.6, [
    "42/42 and 242/242 for BOTH conditions.",
    "Swarm paid 2.6–3.6× the cost for the tie.",
    "We built a context trap: 43k lines, ~2× the window. It didn't spring.",
  ], { size: 14, gap: 9 });
  card(s, 6.9, 1.8, 5.8, 4.6);
  s.addText("Why: cross-task learning", { x: 7.2, y: 2.0, w: 5.2, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: SG, margin: 0 });
  stat(s, 7.2, 2.6, 2.6, "70", "single-agent turns (learned the bug pattern)", SG);
  stat(s, 9.9, 2.6, 2.6, "350", "swarm turns (40× cold discovery)", SW);
  s.addText("Isolated workers rediscover everything from scratch. One head amortizes discovery across every subtask. Homogeneous breadth compresses.", { x: 7.2, y: 4.6, w: 5.2, h: 1.4, fontFace: B, fontSize: 13.5, color: MUT, margin: 0 });
  s.addNotes("The honest headline: on clean, verifiable work the swarm tied at 3x cost. The trap failure is the interesting part — generated tasks were homogeneous, and the single agent exploited the pattern. Real accuracy gaps need HETEROGENEOUS work.");
}

// ---------- 8 · CHAOS ----------
{
  const s = base("Part 3 · The evidence", "Round 3: give everything a 5% chance of dying, every turn");
  stat(s, 1.2, 2.1, 3.4, "+36%", "swarm completion-time degradation", SW);
  stat(s, 5.0, 2.1, 3.4, "+111%", "single-agent degradation", SG);
  stat(s, 8.8, 2.1, 3.4, "13 vs 5", "kills absorbed (more exposure, less damage)", INK);
  card(s, 0.9, 4.0, 11.5, 2.5);
  bullets(s, 1.2, 4.25, 11.0, 2.1, [
    "A kill destroys context only — disk survives, like a real crash. Orchestrator auto-restarts both sides.",
    "Swarm's unit of loss: ONE issue (≤10 turns). Closed issues stay closed. Siblings never notice.",
    "Single agent's unit of loss: its entire working memory — each replacement re-reads the board, re-runs the suite, re-learns the pattern.",
    "Honest caveat: the single agent survived only because pytest is a free recovery oracle — and because WE provided its restart automation. That automation IS the swarm control plane.",
  ], { size: 13.5, gap: 8 });
  s.addNotes("The caveat is the thesis in miniature: the moment we made the single agent reliable, we had already built the swarm's infrastructure and wrapped it around one worker.");
}

// ---------- 9 · TOPOLOGIES ----------
{
  const s = base("Part 3 · The evidence", "Round 4: how should knowledge move between agents?");
  s.addTable([
    [
      { text: "Topology", options: { bold: true, color: MUT } },
      { text: "Tests", options: { bold: true, color: MUT } },
      { text: "Wall", options: { bold: true, color: MUT } },
      { text: "Turns", options: { bold: true, color: MUT } },
      { text: "Knowledge path", options: { bold: true, color: MUT } },
    ],
    ["Stigmergic swarm (hints board)", "242/242", "90.2s", "391", "shared board, parallel"],
    ["Isolated swarm", "242/242", "130.2s", "350", "none"],
    ["Single agent", "242/242", "190.8s", "70", "one context"],
    [
      { text: "Agent chain (output → input)", options: { color: BAD, bold: true } },
      { text: "236/242", options: { color: BAD, bold: true } },
      { text: "924.4s", options: { color: BAD } },
      { text: "360", options: { color: BAD } },
      { text: "hop-by-hop notes (lossy)", options: { color: BAD } },
    ],
  ], {
    x: 0.8, y: 1.9, w: 11.7, colW: [3.6, 1.5, 1.5, 1.3, 3.8],
    fontFace: B, fontSize: 13.5, color: INK, fill: { color: CARD },
    border: { type: "solid", color: LINE, pt: 0.75 }, rowH: 0.5, valign: "middle", margin: 0.08,
  });
  bullets(s, 0.8, 5.0, 11.7, 1.9, [
    "The chain — the design everyone builds first — was the ONLY architecture to permanently destroy work: one stage died on budget, one declared success while wrong, and nothing ever came back.",
    "Stigmergy worked socially (39 accurate hints, universally read) but not economically: overhead cancelled savings. Pheromones pay only when discovery cost dominates.",
  ], { size: 13.5, gap: 8 });
  s.addNotes("Failure mode of the chain was NOT context bloat — it was unverified handoffs making errors permanent. Data-processing inequality observed live: information through hops can only be lost.");
}

// ---------- 10 · MEMORY ----------
{
  const s = base("Part 3 · The evidence", "Round 5: memory doesn't decay — it falls off a cliff");
  card(s, 0.7, 1.8, 5.8, 4.6);
  s.addText("Inside the window: perfect", { x: 1.0, y: 2.0, w: 5.2, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: GOOD, margin: 0 });
  stat(s, 1.0, 2.6, 5.2, "240/240", "facts recalled from a 102k context — 100% at every depth; randomized control: 240/240 again", GOOD);
  s.addText("No 'lost in the middle'. None.", { x: 1.0, y: 4.7, w: 5.2, h: 0.4, fontFace: B, fontSize: 14, italic: true, color: MUT, align: "center", margin: 0 });
  card(s, 6.9, 1.8, 5.8, 4.6);
  s.addText("At the boundary: a wall", { x: 7.2, y: 2.0, w: 5.2, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: BAD, margin: 0 });
  stat(s, 7.2, 2.6, 5.2, "32/40", "modules covered when 280k of read-once data met a 200k window — died at 187k", BAD);
  s.addText("Every recorded fact was correct. The lost ones were never SEEN.", { x: 7.2, y: 4.7, w: 5.2, h: 0.6, fontFace: B, fontSize: 14, italic: true, color: MUT, align: "center", margin: 0 });
  s.addText("The swarm's memory advantage is not better recall — it is unbounded TOTAL context.", { x: 0.7, y: 6.6, w: 12, h: 0.45, fontFace: B, fontSize: 16, bold: true, color: INK, align: "center", margin: 0 });
  s.addNotes("This kills the folklore. Within the window, recall of structured facts was flawless at every depth. Loss is coverage truncation at a hard boundary — an architecture problem, not a model problem.");
}

// ---------- 11 · THE REVERSAL ----------
{
  const s = base("Part 3 · The evidence", "Round 6: the reversal — no oracle, no swarm advantage");
  stat(s, 1.0, 2.0, 3.6, "0 / 930", "single-agent extraction errors (4 trials, adversarial facts, 95% window depth)", GOOD);
  stat(s, 4.9, 2.0, 3.6, "3–6%", "swarm worker error rate — each faced the decoys cold, once", BAD);
  stat(s, 8.8, 2.0, 3.6, "+10.2", "mean-score gap in the single agent's favor (232.5 vs 222.3, identical chaos)", SG);
  card(s, 0.9, 4.1, 11.5, 2.4);
  bullets(s, 1.2, 4.35, 11.0, 2.0, [
    "Every earlier swarm win leaned on a verification gate (pytest) catching worker mistakes. Extraction has no oracle.",
    "Without verification, swarm accuracy = the product of raw per-worker reliability. A single learning head self-calibrates.",
    "Swarms are weakest exactly where work cannot be verified. The fix when you must fan out: redundancy + majority vote.",
  ], { size: 14, gap: 9 });
  s.addNotes("The most surprising round. Cross-task learning turned out to be an ACCURACY mechanism, not just a cost saver. The literature calls this a 'context effect confound' — our data says it's a real architectural advantage.");
}

// ---------- 12 · THREE WALLS, ONE MOVE ----------
{
  const s = base("Part 4 · The point", "Three walls, one move: take it out of the head");
  s.addTable([
    [
      { text: "The wall", options: { bold: true, color: MUT } },
      { text: "What lived in the head", options: { bold: true, color: MUT } },
      { text: "Where the swarm puts it", options: { bold: true, color: MUT } },
      { text: "Component", options: { bold: true, color: MUT } },
      { text: "Evidence", options: { bold: true, color: MUT } },
    ],
    ["Context window", "the inputs", "artifact store", "decomposer + store", "R5B: 40/40 vs 32/40"],
    ["The crash", "the progress", "task board (verified)", "lease + gate", "R3: +36% vs +111%"],
    ["The backlog", "the plan / what's next", "queue", "scheduler", "R1–3: 1.5–2.3×"],
  ], {
    x: 0.8, y: 2.0, w: 11.7, colW: [2.2, 2.6, 2.7, 2.2, 2.0],
    fontFace: B, fontSize: 14, color: INK, fill: { color: CARD },
    border: { type: "solid", color: LINE, pt: 0.75 }, rowH: 0.62, valign: "middle", margin: 0.08,
  });
  s.addText("The model never changed. The prompts never changed. Every wall fell to plumbing.", { x: 0.8, y: 5.5, w: 11.7, h: 0.5, fontFace: B, fontSize: 17, bold: true, color: SW, align: "center", margin: 0 });
  s.addNotes("The unifying slide. The swarm makes one move in three disguises: it takes something the single agent keeps in its context and hands it to infrastructure.");
}

// ---------- 13 · TWO DIALS ----------
{
  const s = base("Part 4 · The point", "The real design space: two dials");
  const dial = (x, title, l, r, pos) => {
    card(s, x, 2.0, 5.7, 2.9);
    s.addText(title, { x: x + 0.3, y: 2.25, w: 5.1, h: 0.45, fontFace: H, fontSize: 17, bold: true, color: INK, margin: 0 });
    s.addShape(pres.ShapeType.line, { x: x + 0.5, y: 3.45, w: 4.7, h: 0, line: { color: LINE, width: 5 } });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.5 + 4.7 * pos - 0.11, y: 3.34, w: 0.22, h: 0.22, fill: { color: SG }, line: { type: "none" } });
    s.addText(l, { x: x + 0.3, y: 3.7, w: 2.6, h: 0.8, fontFace: B, fontSize: 12, color: MUT, margin: 0 });
    s.addText(r, { x: x + 2.9, y: 3.7, w: 2.5, h: 0.8, fontFace: B, fontSize: 12, color: MUT, align: "right", margin: 0 });
  };
  dial(0.7, "1 · What does each call see?", "everything\n(one shared transcript)", "nothing\n(briefs + artifacts)", 0.62);
  dial(6.9, "2 · Who schedules the next call?", "the model,\nfrom inside its loop", "your code\n(board, leases, retries)", 0.72);
  bullets(s, 0.9, 5.35, 11.6, 1.6, [
    "“Single agent” = dial 1 far left, dial 2 far left.  “Swarm” = both far right.  Chain, stigmergy, compaction — all just settings.",
    "Every finding of the six rounds is a statement about dial 1: learning = total sharing; the cliff = its limit; blast radius = its failure coupling; worker errors = the price of zero sharing.",
  ], { size: 14, gap: 8 });
  s.addNotes("This is the takeaway framework. 'Single vs multi' is a malformed question; these two dials are the real design space, tuned per task.");
}

// ---------- 14 · TWO LOCKS ----------
{
  const s = base("Part 4 · The point", "…and two locks that are never optional");
  const lock = (x, title, body, evidence) => {
    card(s, x, 2.0, 5.7, 3.9);
    s.addText(title, { x: x + 0.35, y: 2.3, w: 5.0, h: 0.8, fontFace: H, fontSize: 19, bold: true, color: GOOD, margin: 0 });
    s.addText(body, { x: x + 0.35, y: 3.2, w: 5.0, h: 1.5, fontFace: B, fontSize: 14, color: INK, margin: 0 });
    s.addText(evidence, { x: x + 0.35, y: 4.9, w: 5.0, h: 0.8, fontFace: B, fontSize: 12.5, italic: true, color: MUT, margin: 0 });
  };
  lock(0.7, "Verification gates on every handoff",
    "The orchestrator checks the work itself — tests, schema, build. No agent ever grades its own output. Unverified results never become inputs.",
    "The one round without a gate (the chain) destroyed work. The one task without an oracle (R6) cost the swarm its accuracy.");
  lock(6.9, "State outside every context window",
    "Inputs in the artifact store, progress on the board, plan in the queue. Any agent can die at any time and the system loses at most one lease.",
    "R3: +36% vs +111% degradation. R5B: the only escape from the 200k cliff.");
  s.addNotes("Gates and external state are the two components that did ALL the winning across six rounds. They are the product; agent count is a parameter.");
}

// ---------- 15 · DECISION TABLE ----------
{
  const s = base("Part 4 · The point", "The decision table");
  s.addTable([
    [
      { text: "Your task looks like…", options: { bold: true, color: MUT } },
      { text: "Use", options: { bold: true, color: MUT } },
      { text: "Evidence", options: { bold: true, color: MUT } },
    ],
    ["Fits one window · verifiable · similar structure", { text: "Single agent", options: { color: SG, bold: true } }, "tie at 2.6–3.6× less cost (R1–2)"],
    ["No oracle · repeated structure", { text: "Single agent, bounded batches", options: { color: SG, bold: true } }, "0 vs 3–6% errors (R6)"],
    ["Deadline-bound", { text: "Swarm", options: { color: SW, bold: true } }, "1.5–2.3× faster (R1–3)"],
    ["Input exceeds the window", { text: "Swarm — shard it", options: { color: SW, bold: true } }, "40/40 vs 32/40 (R5B)"],
    ["Long horizon, crashes expected", { text: "Swarm + durable board", options: { color: SW, bold: true } }, "+36% vs +111% (R3)"],
    ["Sequential dependent stages", { text: "Gated pipeline — never a raw chain", options: { color: BAD, bold: true } }, "chain destroyed work (R4)"],
    ["High stakes, no oracle", { text: "N agents + majority vote", options: { color: SW, bold: true } }, "consequence of R6"],
  ], {
    x: 0.8, y: 1.85, w: 11.7, colW: [4.9, 3.6, 3.2],
    fontFace: B, fontSize: 13, color: INK, fill: { color: CARD },
    border: { type: "solid", color: LINE, pt: 0.75 }, rowH: 0.52, valign: "middle", margin: 0.07,
  });
  s.addNotes("The handout slide. Default to single; raise N at the clock, the window, and failure. Every row cites a measured round.");
}

// ---------- 16 · RESEARCH ----------
{
  const s = base("Part 4 · The point", "The literature landed in the same place");
  const rc = (x, title, body) => {
    card(s, x, 2.0, 3.85, 3.6);
    s.addText(title, { x: x + 0.25, y: 2.25, w: 3.35, h: 0.85, fontFace: H, fontSize: 15.5, bold: true, color: SW, margin: 0 });
    s.addText(body, { x: x + 0.25, y: 3.2, w: 3.35, h: 2.2, fontFace: B, fontSize: 12.5, color: INK, margin: 0 });
  };
  rc(0.65, "Berkeley MAST (NeurIPS ’25)", "1,600+ traces, 14 failure modes. MAS failures are DESIGN failures — specification, misalignment, missing verification — not model weakness.");
  rc(4.75, "“Illusion of Multi-Agent Advantage” (’26)", "At equal compute, automatic MAS frameworks lose to one agent + self-consistency at up to 10× the cost. Debate gains ≈ majority voting.");
  rc(8.85, "Anthropic’s own system (’25)", "+90.2% on breadth research — but ~80% of the variance is token usage at 15× cost. Parallelism = spending tokens faster, not thinking better.");
  s.addText("Our $11 benchmark independently replicated all three. The frontier is orchestration design — not agent count.", { x: 0.8, y: 6.0, w: 11.7, h: 0.5, fontFace: B, fontSize: 16, bold: true, color: INK, align: "center", margin: 0 });
  s.addNotes("You're not contrarian — you're current. Cite: arXiv 2503.13657 (MAST), arXiv 2606.13003 (Illusion), Anthropic engineering blog (multi-agent research system).");
}

// ---------- 17 · HARNESS ARCHITECTURE ----------
{
  const s = base("Part 5 · How the harness is built", "~1,600 lines of Python. Five boxes. That's the whole MAS.");
  const box = (x, y, w, h, title, sub, color = INK) => {
    card(s, x, y, w, h, CARD2);
    s.addText(title, { x: x + 0.12, y: y + 0.08, w: w - 0.24, h: 0.35, fontFace: H, fontSize: 14, bold: true, color, margin: 0 });
    s.addText(sub, { x: x + 0.12, y: y + 0.45, w: w - 0.24, h: h - 0.55, fontFace: B, fontSize: 10.5, color: MUT, margin: 0 });
  };
  const arrow = (x, y, w, h) => s.addShape(pres.ShapeType.line, { x, y, w, h, line: { color: MUT, width: 2.25, endArrowType: "triangle" } });
  box(0.7, 2.0, 3.1, 1.5, "ORCHESTRATOR", "plain Python. decompose → dispatch → verify → merge. Retries, leases, budgets. The only place control flow lives.", SW);
  box(4.7, 1.7, 3.4, 1.2, "TASK BOARD", "GitHub Issues. open = todo, assignee = lease, close = verified done. Survives everything.");
  box(4.7, 3.3, 3.4, 1.2, "WORKERS ×N", "stateless tool loops (or claude -p). Fresh context per task, isolated copy, hard turn budget. Disposable.");
  box(9.2, 1.7, 3.4, 1.2, "VERIFICATION GATE", "orchestrator runs pytest itself. Reject → retry/escalate. Never trust exit text.", GOOD);
  box(9.2, 3.3, 3.4, 1.2, "STORE", "git worktrees + artifacts. Immutable results; merge = copy verified module to main.");
  arrow(3.8, 2.4, 0.85, -0.3); // orch -> board
  arrow(3.8, 2.9, 0.85, 0.9);  // orch -> workers
  arrow(8.15, 3.9, 1.0, 0);    // workers -> store
  arrow(8.15, 3.5, 1.0, -1.2); // workers -> gate
  arrow(9.2, 2.1, -0.55, 0);   // gate -> board (close)
  bullets(s, 0.7, 5.2, 11.9, 1.7, [
    "Worker (worker2.py, ~250 lines): Messages API loop — tools (grep, paged read, surgical edit, run_tests, done), prompt caching, 429 retries, context-overflow catch, chaos hook.",
    "Orchestrator (~150 lines/round): fetch issues → fresh copy per task → ThreadPool(12) → score() with pytest → merge verified file → gh issue close. Chaos = kill + re-dispatch on the surviving tree.",
  ], { size: 12.5, gap: 7 });
  s.addNotes("Walk the diagram left to right. Emphasize: the workers are the LEAST interesting box — we swapped them for claude -p in one function and nothing else changed.");
}

// ---------- 18 · THE WORKER ----------
{
  const s = base("Part 5 · How the harness is built", "The worker: a tool loop you can read in one sitting");
  card(s, 0.7, 1.8, 6.4, 4.9, CARD2);
  s.addText(
    "while turns < budget:\n" +
    "  resp = api.call(system, TOOLS,\n" +
    "                  messages)      # cached\n" +
    "  for tool_use in resp:\n" +
    "    out = dispatch(tool_use)     # grep /\n" +
    "          read / edit / pytest / done\n" +
    "    messages.append(result(out))\n" +
    "  if done: break\n" +
    "  if rng() < chaos_rate: die()   # R3/R6\n\n" +
    "return {turns, usage, killed,\n" +
    "        context_exhausted}",
    { x: 1.0, y: 2.05, w: 5.9, h: 4.4, fontFace: M, fontSize: 13, color: INK, valign: "top", margin: 0 });
  bullets(s, 7.5, 1.9, 5.1, 4.8, [
    "Same class for every condition — single vs swarm differ ONLY in brief + budget.",
    "Tool outputs hard-capped (400-line reads, 3k-char test output): the budget is enforced by infrastructure, not by asking nicely.",
    "Writes to tests/ rejected. Guardrails are code.",
    "Prompt caching on the growing thread: ~90% input cost reduction.",
    "Swap-in: replace this class with subprocess claude -p / codex exec — proven, 1 function.",
  ], { size: 13.5, gap: 9 });
  s.addNotes("Point at the chaos line — one line of code gave us the entire resilience research program. The worker is deliberately boring; boring workers are replaceable workers.");
}

// ---------- 19 · CLI SWAP ----------
{
  const s = base("Part 5 · How the harness is built", "Production: the harness IS the worker binary");
  card(s, 0.7, 1.8, 6.4, 3.2, CARD2);
  s.addText(
    "subprocess.run([\"claude\", \"-p\", brief,\n" +
    "  \"--model\", \"claude-haiku-4-5\",\n" +
    "  \"--output-format\", \"json\",\n" +
    "  \"--max-turns\", \"14\",\n" +
    "  \"--permission-mode\", \"acceptEdits\",\n" +
    "  \"--allowedTools\",\n" +
    "  \"Read,Edit,Grep,Bash(pytest:*)\"],\n" +
    "  cwd=worktree)",
    { x: 1.0, y: 2.05, w: 5.9, h: 2.8, fontFace: M, fontSize: 13.5, color: INK, valign: "top", margin: 0 });
  s.addText("Live demo result: 6 turns, 36.9s, $0.10 — verified 5/5 by the orchestrator. Codex: same slot via codex exec.", { x: 1.0, y: 5.2, w: 5.9, h: 0.8, fontFace: B, fontSize: 13, italic: true, color: GOOD, margin: 0 });
  s.addText("The 5 pieces you still own", { x: 7.5, y: 1.9, w: 5.1, h: 0.4, fontFace: H, fontSize: 16, bold: true, color: INK, margin: 0 });
  bullets(s, 7.5, 2.4, 5.1, 4.3, [
    "Decomposer — issue → window-sized task DAG",
    "Verification gate — YOU run the tests",
    "Leases, timeouts, retries — crash absorption",
    "Merge policy — what lands on main, and when",
    "Budgets & permissions — cost + security policy per worker",
  ], { size: 14, gap: 10 });
  s.addNotes("The harness replaced the WORKER, not the control plane. Auth for cloud: ANTHROPIC_API_KEY, or claude setup-token for subscription, or Bedrock/Vertex env vars. ~300-400 lines of glue total.");
}

// ---------- 20 · CLOSE ----------
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("A single agent is a swarm with N = 1.", { x: 1.2, y: 2.5, w: 10.9, h: 0.9, fontFace: H, fontSize: 40, bold: true, color: INK, align: "center", margin: 0 });
  s.addText("You never choose whether to build the MAS — only N.", { x: 1.2, y: 3.6, w: 10.9, h: 0.7, fontFace: H, fontSize: 26, bold: true, color: SW, align: "center", margin: 0 });
  s.addText("Users don't want agents. They want work that doesn't get lost.\nAgents are the demo; infrastructure is the product. Build the board, the gate, and the lease.", { x: 1.9, y: 4.7, w: 9.5, h: 1.0, fontFace: B, fontSize: 16, color: MUT, align: "center", margin: 0 });
  s.addText("full report + data: mas benchmark artifact  ·  six rounds  ·  $11.30", { x: 2.9, y: 6.5, w: 7.5, h: 0.35, fontFace: M, fontSize: 11.5, color: MUT, align: "center", margin: 0 });
  s.addNotes("End here. Q&A prompts to expect: 'what about heterogeneous tasks?' (untested, round 7 candidate — SWE-bench-style real bugs) and 'majority voting?' (untested cell of the consensus table).");
}

pres.writeFile({ fileName: require("path").join(__dirname, "one-agent-is-a-swarm.pptx") }).then(() => console.log("written"));
