// The design-choices talk — short, to the point. Run: node build_design_talk.js
// Thesis: a multi-agent system is infrastructure; here is each part, why it was chosen, and what it buys.
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
const label = (s, x, y, w, text, color = MUT, size = 10.5) =>
  s.addText(text.toUpperCase(), { x, y, w, h: 0.26, fontFace: H, fontSize: size, bold: true, color, charSpacing: 2, margin: 0 });
const body = (s, x, y, w, h, text, o = {}) =>
  s.addText(text, { x, y, w, h, fontFace: B, fontSize: o.size ?? 12.5, color: o.color ?? INK, valign: o.valign ?? "top", italic: !!o.italic, align: o.align ?? "left", margin: 0 });
const mono = (s, x, y, w, h, text, color = SW, size = 11) =>
  s.addText(text, { x, y, w, h, fontFace: M, fontSize: size, color, valign: "middle", margin: 0 });
const bullets = (s, x, y, w, h, items, o = {}) =>
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { code: "2022", indent: 12 }, breakLine: i < items.length - 1, paraSpaceAfter: o.gap ?? 7 } })),
    { x, y, w, h, fontFace: B, fontSize: o.size ?? 13, color: o.color ?? INK, valign: "top", margin: 0 });
const arrow = (s, x1, y1, x2, y2, color = MUT, width = 2) =>
  s.addShape(pres.ShapeType.line, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
    flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle" },
  });
const footer = (s, text) => body(s, 0.7, 6.55, 12.0, 0.5, text, { italic: true, color: SG, size: 13, align: "center" });

// One "part" page: the decision on the left, the effect on agents on the right, a demo pointer at the bottom.
const partPage = (cfg) => {
  const s = base(cfg.kicker, cfg.title, 27);
  body(s, 0.7, 1.5, 12.0, 0.3, cfg.sub, { italic: true, color: MUT, size: 12 });

  // left: the decision
  card(s, 0.7, 2.0, 5.9, 4.2);
  label(s, 0.9, 2.1, 4.0, "the decision", SG);
  mono(s, 0.9, 2.4, 5.5, 0.4, cfg.chose, cfg.color, 14);
  label(s, 0.9, 2.95, 4.0, "because", MUT);
  bullets(s, 0.9, 3.22, 5.5, 2.0, cfg.because, { size: 12, gap: 6 });
  label(s, 0.9, 5.3, 4.0, "could also be", MUT);
  body(s, 0.9, 5.56, 5.5, 0.55, cfg.alt, { color: MUT, size: 11.5, italic: true });

  // right: what it does for many agents
  card(s, 6.85, 2.0, 5.85, 4.2, CARD2);
  label(s, 7.05, 2.1, 4.5, "what it buys when N agents run", cfg.color);
  bullets(s, 7.05, 2.4, 5.5, 2.75, cfg.buys, { size: 12, gap: 6 });
  label(s, 7.05, 5.2, 4.5, "seen in the demo", GOOD);
  body(s, 7.05, 5.47, 5.5, 0.65, cfg.demo, { size: 11.5, color: INK });

  footer(s, cfg.foot);
  if (cfg.notes) s.addNotes(cfg.notes);
  return s;
};

// =====================================================================
// 0 · Title
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("Boring, durable, already on the machine.", { x: 0.9, y: 2.2, w: 11.5, h: 1.0, fontFace: H, fontSize: 40, bold: true, color: INK, align: "center", margin: 0 });
  s.addText("How we run many coding agents without losing work — and why each part was chosen", { x: 1.2, y: 3.3, w: 10.9, h: 0.6, fontFace: H, fontSize: 20, color: SW, align: "center", margin: 0 });
  s.addText("board · compartments · workers · gate · log — with live demos", { x: 1.2, y: 4.3, w: 10.9, h: 0.4, fontFace: M, fontSize: 13, color: MUT, align: "center", margin: 0 });
  s.addNotes("Short talk. One idea: a multi-agent system is infrastructure, not agent count. Each part here was chosen for being boring, durable and already installed. We show the demos live.");
}

// =====================================================================
// 1 · Motivation — one context hits three walls
// =====================================================================
{
  const s = base("motivation", "One agent is one context. A context hits three walls.", 28);
  const walls = [
    ["◫", "the window", "The inputs do not fit. Read serially, truncate, or forget.", SW],
    ["✕", "the crash", "One process holds all the work. It dies, the work is gone.", BAD],
    ["≡", "the backlog", "Forty independent tasks, one thread. Wall-clock scales with N.", SG],
  ];
  walls.forEach(([icon, name, text, color], i) => {
    const x = 0.7 + i * 4.1;
    card(s, x, 2.0, 3.85, 2.9);
    s.addText(icon, { x, y: 2.15, w: 3.85, h: 0.9, fontFace: H, fontSize: 44, bold: true, color, align: "center", margin: 0 });
    s.addText(name, { x, y: 3.1, w: 3.85, h: 0.4, fontFace: H, fontSize: 18, bold: true, color: INK, align: "center", margin: 0 });
    body(s, x + 0.3, 3.55, 3.25, 1.2, text, { size: 12.5, color: MUT, align: "center" });
  });
  card(s, 0.7, 5.15, 12.0, 1.1, CARD2);
  body(s, 0.95, 5.27, 11.5, 0.9,
    "Users do not want agents. They want work that does not get lost. Every part in this talk exists to get past one of these walls — and to do it with things that were already installed.",
    { size: 14, color: INK, valign: "middle" });
  footer(s, "The model is stateless. The agent is the transcript. So the question is never “how many agents” — it is “what does each call see, and who decides the next one”.");
  s.addNotes("Frame the problem before the parts. A single context window is a single point of failure in three ways. Then the promise: every part that follows removes one of these walls with boring, installed technology.");
}

// =====================================================================
// 2 · What a MAS is — five boxes, N is a config value
// =====================================================================
{
  const s = base("what a multi-agent system is", "Five boxes. The number of agents is a config value.", 28);
  const boxes = [
    ["BOARD", "durable tasks · atomic claim · leases", SW, 0.7],
    ["COMPARTMENTS", "one isolated copy per attempt", GOOD, 3.1],
    ["WORKERS", "any harness, one contract", INK, 5.5],
    ["GATE", "re-run the check, trust nothing", BAD, 7.9],
    ["LOG + VIEWS", "every change written, every screen a query", SG, 10.3],
  ];
  boxes.forEach(([name, sub, color, x]) => {
    card(s, x, 2.3, 2.3, 1.55, CARD2);
    s.addText(name, { x, y: 2.42, w: 2.3, h: 0.4, fontFace: H, fontSize: 13, bold: true, color, align: "center", margin: 0 });
    body(s, x + 0.1, 2.85, 2.1, 0.9, sub, { size: 11, color: MUT, align: "center" });
  });
  // flow arrows under the boxes
  [[3.0, 3.1], [5.4, 5.5], [7.8, 7.9], [10.2, 10.3]].forEach(([x1, x2]) => arrow(s, x1, 3.07, x2, 3.07, LINE, 1.5));
  body(s, 0.7, 4.15, 12.0, 0.4, "claim → compartment → worker → gate → land (idempotent) → log.  Fail: back off, escalate the model, then park with evidence.", { size: 13, color: INK, align: "center" });

  card(s, 0.7, 4.9, 5.85, 1.3);
  label(s, 0.9, 5.0, 5.5, "the interfaces are the architecture", SG);
  mono(s, 0.9, 5.3, 5.5, 0.8, "claim · lease · verdict · event", SW, 15);
  card(s, 6.85, 4.9, 5.85, 1.3);
  label(s, 7.05, 5.0, 5.5, "the parts are replaceable", SG);
  body(s, 7.05, 5.28, 5.5, 0.85, "So we picked the most boring durable thing already on the machine for each box. One rule: pick parts you can cat.", { size: 12.5, color: INK });
  footer(s, "A single agent is a swarm with N = 1. You never choose whether to build this — only N.");
  s.addNotes("The five boxes, then the loop. Emphasize that the interfaces are what matter; each box's implementation is chosen for being boring and installed. The next six slides are one box each.");
}

// =====================================================================
// HOW IT IS BUILT — six diagram slides
// =====================================================================
const flowBox = (s, x, y, w, h, title, sub, color = INK, fill = CARD2, ev) => {
  card(s, x, y, w, h, fill);
  s.addText(title, { x, y: y + 0.08, w, h: 0.34, fontFace: H, fontSize: 12, bold: true, color, align: "center", margin: 0 });
  if (sub) body(s, x + 0.08, y + 0.42, w - 0.16, h - 0.5, sub, { size: 10, color: MUT, align: "center" });
  if (ev) s.addText(ev, { x: x - 0.2, y: y + h + 0.05, w: w + 0.4, h: 0.26, fontFace: M, fontSize: 8.5, color: SW, align: "center", margin: 0 });
};
const hArrow = (s, x1, x2, y, color = MUT) => arrow(s, x1, y, x2, y, color, 1.75);

// ---- A · from a goal to items
{
  const s = base("how it is built · 1", "From one sentence to rows on the board.", 28);
  body(s, 0.7, 1.5, 12, 0.3, "mas plan is the only place a model shapes the work. Its output is checked like any worker's, then it becomes data.", { italic: true, color: MUT, size: 12 });
  const y = 2.2, h = 1.45, w = 2.2, gap = 0.28;
  const xs = [0.7, 0.7 + (w + gap), 0.7 + 2 * (w + gap), 0.7 + 3 * (w + gap), 0.7 + 4 * (w + gap)];
  flowBox(s, xs[0], y, w, h, "GOAL", "one sentence:\n“Plan a 10-day trip from Israel to Japan…”", SG);
  flowBox(s, xs[1], y, w, h, "PLANNER PROMPT", "fixed template + the goal + a listing of the repo\n“independent, window-sized, each with a check”", INK);
  flowBox(s, xs[2], y, w, h, "MODEL, READ-ONLY", "claude -p in plan mode, tools Read/Grep/Glob, answer forced into a JSON schema", SW);
  flowBox(s, xs[3], y, w, h, "VALIDATE", "drop entries without title/brief/check · slug ids · resolve depends_on · unknown deps dropped", BAD);
  flowBox(s, xs[4], y, w, h, "BOARD", "one row per item + a `planned` event + .mas/last_plan.json (prompt, raw JSON, accepted rows)", GOOD);
  for (let i = 0; i < 4; i++) hArrow(s, xs[i] + w, xs[i + 1], y + h / 2);

  card(s, 0.7, 4.15, 7.4, 2.1);
  label(s, 0.9, 4.25, 6, "what came back for the trip (3 minutes, 7 items)", SG);
  mono(s, 0.9, 4.55, 7.0, 1.6,
    'flights     check: test -f flights.md && grep -qiE "tel aviv|TLV" …\nlodging     check: … grep -qiE "ryokan" … grep -qE "[$][0-9]"\nitinerary   check: for d in 1..10: grep -qiE "day ?$d" itinerary.md\nbudget      check: pytest tests/test_budget.py\n            depends_on: flights, lodging, transport, activities', SW, 10);
  card(s, 8.35, 4.15, 4.35, 2.1, CARD2);
  label(s, 8.55, 4.25, 4, "what an item is", MUT);
  bullets(s, 8.55, 4.55, 4.0, 1.7, [
    "the cut — one window-sized piece",
    "the contract — brief a stranger can pick up cold, merge_paths it may write",
    "the check — a command that exits 0, a JSON shape, or a human",
    "the wiring — depends_on, priority, worker, model",
  ], { size: 11, gap: 4 });
  footer(s, "The plan is evidence, not a conversation: the prompt, the JSON and the accepted rows are all on disk to diff.");
  s.addNotes("Walk the arrow left to right. Stress the two guards: the model is read-only and schema-bound; the validation is code. Show the trip: seven items, checks are shell commands, budget depends on four files. The whole exchange is saved — you can diff what the model proposed against what the board accepted.");
}

// ---- B · one item's life
{
  const s = base("how it is built · 2", "One item's life: the loop the orchestrator runs.", 28);
  body(s, 0.7, 1.5, 12, 0.3, "Plain code, no model in the loop. Every box writes an event before the next one starts.", { italic: true, color: MUT, size: 12 });
  const y = 2.1, h = 1.3, w = 1.55, gap = 0.2;
  const names = [["CLAIM", "atomic · one owner · lease + heartbeat", SW, "claimed"], ["COMPARTMENT", "a git worktree for this attempt", GOOD, "compartment"],
    ["PROMPT", "built from the row: frame + brief + check", INK, "dispatched"], ["WORKER", "any harness · runs · exits", INK, "activity…\nworker_finished"],
    ["GATE", "re-run the check in the worktree", BAD, "gate\nverified | rejected"], ["LAND", "copy merge_paths · commit", GOOD, "merged"], ["DONE", "row closed · lesson appended", GOOD, "done · lesson"]];
  names.forEach(([t, sub, c, ev], i) => flowBox(s, 0.7 + i * (w + gap), y, w, h, t, sub, c, CARD2, ev));
  for (let i = 0; i < 6; i++) hArrow(s, 0.7 + i * (w + gap) + w, 0.7 + (i + 1) * (w + gap), y + h / 2);
  // fail branch
  const gx = 0.7 + 4 * (w + gap) + w / 2;
  arrow(s, gx, y + h + 0.4, gx, 4.55, BAD, 1.75);
  card(s, 3.6, 4.6, 5.9, 0.95, CARD);
  s.addText("rejected → requeued with backoff → next model tier → third failure: PARKED with the evidence", { x: 3.75, y: 4.68, w: 5.6, h: 0.35, fontFace: H, fontSize: 11.5, bold: true, color: BAD, margin: 0 });
  mono(s, 3.75, 5.03, 5.6, 0.45, "failed · requeued · dispatched (escalated_from) · … · parked", SW, 9.5);
  card(s, 9.75, 4.6, 2.95, 0.95, CARD);
  s.addText("a human fixes the contract", { x: 9.9, y: 4.68, w: 2.7, h: 0.35, fontFace: H, fontSize: 11.5, bold: true, color: SG, margin: 0 });
  mono(s, 9.9, 5.03, 2.7, 0.45, "mas edit · mas unpark · mas run", SW, 9.5);
  hArrow(s, 9.5, 9.75, 5.07, SG);
  card(s, 0.7, 5.75, 12.0, 0.65, CARD2);
  body(s, 0.9, 5.85, 11.6, 0.5, "Crash at any box: the row keeps the truth. The lease expires, the item reopens, the next run continues. Ctrl-C hands leases back with the attempt refunded.", { size: 12, color: INK, valign: "middle" });
  footer(s, "Seven boxes, one row each. The events under the boxes are the journal you can read back with mas events.");
  s.addNotes("This is the orchestrator's whole job. Name the event under each box — that is what mas watch shows and what the walkthrough document lists. Then the red branch: rejection, backoff, escalation, park. Then the human path: edit the contract, unpark, run. Close with the crash sentence.");
}

// ---- C · the worker is a black box
{
  const s = base("how it is built · 3", "A worker is a black box.", 28);
  body(s, 0.7, 1.5, 12, 0.3, "A prompt and a directory go in; changed files come out. We never take the worker's answer — we take its directory. Its reply is logged and never trusted.", { italic: true, color: MUT, size: 12 });
  // inputs
  card(s, 0.7, 2.2, 3.2, 1.0, CARD2); s.addText("PROMPT", { x: 0.7, y: 2.28, w: 3.2, h: 0.3, fontFace: H, fontSize: 12, bold: true, color: SG, align: "center", margin: 0 });
  body(s, 0.85, 2.6, 2.9, 0.55, "built from the row: frame + title + brief + “verified by: <check>”", { size: 10, color: MUT, align: "center" });
  card(s, 0.7, 3.45, 3.2, 1.0, CARD2); s.addText("A DIRECTORY", { x: 0.7, y: 3.53, w: 3.2, h: 0.3, fontFace: H, fontSize: 12, bold: true, color: GOOD, align: "center", margin: 0 });
  body(s, 0.85, 3.85, 2.9, 0.55, "its own git worktree of main — edit anything, nothing leaks", { size: 10, color: MUT, align: "center" });
  // the box
  card(s, 4.7, 2.2, 3.9, 2.25, CARD);
  s.addText("ANY HARNESS", { x: 4.7, y: 2.45, w: 3.9, h: 0.5, fontFace: H, fontSize: 20, bold: true, color: INK, align: "center", margin: 0 });
  mono(s, 4.85, 3.05, 3.6, 0.9, "claude -p · codex exec\nGemini / Anthropic / OpenAI loop\nany CLI from config", SW, 11);
  body(s, 4.85, 3.95, 3.6, 0.4, "runs · uses its own tools · exits", { size: 10.5, color: MUT, align: "center" });
  hArrow(s, 3.9, 4.7, 2.7, SG); hArrow(s, 3.9, 4.7, 3.95, GOOD);
  // outputs
  card(s, 9.4, 2.2, 3.3, 1.0, CARD2); s.addText("CHANGED FILES", { x: 9.4, y: 2.28, w: 3.3, h: 0.3, fontFace: H, fontSize: 12, bold: true, color: GOOD, align: "center", margin: 0 });
  body(s, 9.55, 2.6, 3.0, 0.55, "the only result that counts — gated, then merge_paths land", { size: 10, color: MUT, align: "center" });
  card(s, 9.4, 3.45, 3.3, 1.0, CARD2); s.addText("ITS REPLY", { x: 9.4, y: 3.53, w: 3.3, h: 0.3, fontFace: H, fontSize: 12, bold: true, color: MUT, align: "center", margin: 0 });
  body(s, 9.55, 3.85, 3.0, 0.55, "“all tests pass” → logged as a claim in worker_finished; never decides anything", { size: 10, color: MUT, align: "center" });
  hArrow(s, 8.6, 9.4, 2.7, GOOD); hArrow(s, 8.6, 9.4, 3.95, LINE);
  // requirements + frame
  card(s, 0.7, 4.75, 5.9, 1.55);
  label(s, 0.9, 4.85, 5, "a harness qualifies if it", SG);
  bullets(s, 0.9, 5.12, 5.5, 1.15, ["runs non-interactively", "accepts a prompt", "works in a directory you give it", "exits"], { size: 11.5, gap: 2 });
  card(s, 6.85, 4.75, 5.85, 1.55, CARD2);
  label(s, 7.05, 4.85, 5, "the only “how to answer” we give", MUT);
  mono(s, 7.05, 5.12, 5.5, 1.15, "You own exactly ONE task, in an isolated working copy.\nDo not touch anything outside your task's scope.\nYour work will be verified by running: <check>\nRun that yourself; do not report success unless it passes.", SW, 9.5);
  footer(s, "Advice for the model's benefit, not a protocol we depend on. Structure is forced only when the deliverable is a file with a shape.");
  s.addNotes("The pluggability slide. Two arrows in, two out — and one of the outputs is crossed out in spirit: the reply is logged, never trusted. Read the four requirements. The prompt frame is the only instruction on how to answer, and the gate does not depend on it being followed.");
}

// ---- D · four harnesses, one slot
{
  const s = base("how it is built · 4", "Four harnesses, one slot, one result shape.", 28);
  const cols = [
    ["Claude Code", 'claude -p "<prompt>" --output-format stream-json --max-turns N --permission-mode acceptEdits --allowedTools …', "tool calls stream live · final result: cost, turns, usage · its check command is auto-allowed", SW],
    ["Codex", "codex exec --sandbox workspace-write -C <worktree> --output-last-message f --json --ephemeral", "JSONL events → activity + tokens · last-message file → summary", SG],
    ["API loop", "our 60-line harness: read_file · grep · edit_file · write_file · run_check · done(summary)", "Anthropic, Gemini or OpenAI models · protected paths refused · ends on done() or the turn budget", GOOD],
    ["Any CLI", 'config: {"cmd": ["mybot", "--prompt", "{prompt}", …], "summary": "stdout_tail"}', "placeholders {prompt} {cwd} {model} · stdout tail is the summary · exit code is the claim", INK],
  ];
  cols.forEach(([name, launch, read, color], i) => {
    const x = 0.7 + i * 3.05;
    card(s, x, 1.95, 2.85, 2.75, CARD2);
    s.addText(name, { x, y: 2.03, w: 2.85, h: 0.34, fontFace: H, fontSize: 13, bold: true, color, align: "center", margin: 0 });
    label(s, x + 0.15, 2.42, 2.6, "launch", MUT, 8.5);
    mono(s, x + 0.15, 2.66, 2.55, 0.95, launch, SW, 8.5);
    label(s, x + 0.15, 3.62, 2.6, "what we read back", MUT, 8.5);
    body(s, x + 0.15, 3.86, 2.55, 0.8, read, { size: 9.5, color: INK });
    arrow(s, x + 1.425, 4.7, x + 1.425, 5.05, color, 1.5);
  });
  card(s, 0.7, 5.1, 12.0, 0.75, CARD);
  mono(s, 0.9, 5.15, 11.6, 0.65, "WorkerResult(ok = CLAIM, summary, turns, cost_usd, tokens, seconds) → event worker_finished → the gate runs the check anyway", INK, 10);
  footer(s, "ok is what the worker believes. The verdict is what the check says. Adding a harness is one config block, not a code change.");
  s.addNotes("Four columns, one funnel. The point is the bottom line: every harness collapses to the same small record, and that record's ok field is a claim we log and ignore. Mention timeouts: when we kill a worker at its budget, whatever it left on disk is still gated — partial work can land.");
}

// ---- E · the gate decides, with the trip example
{
  const s = base("how it is built · 5", "The gate decides — never the reply.", 28);
  body(s, 0.7, 1.5, 12, 0.3, "The check is a shell command the worker was told about. The orchestrator runs it again, in the worker's own worktree.", { italic: true, color: MUT, size: 12 });
  flowBox(s, 0.7, 2.15, 2.3, 1.2, "WORKER EXITS", "claims ok — or claims failure — or was killed at its time budget", MUT);
  hArrow(s, 3.0, 3.45, 2.75);
  flowBox(s, 3.45, 2.15, 2.5, 1.2, "RUN THE CHECK", "cmd: exit 0? · schema: shape ok? · human: park for approval", BAD);
  // pass
  arrow(s, 5.95, 2.5, 6.5, 2.5, GOOD, 1.75);
  flowBox(s, 6.5, 2.05, 2.7, 0.9, "PASS → LAND", "copy only merge_paths · commit · done · lesson", GOOD);
  // fail
  arrow(s, 5.95, 3.05, 6.5, 3.05, BAD, 1.75);
  flowBox(s, 6.5, 3.05, 2.7, 0.9, "FAIL → RETRY", "backoff · stronger model · 3rd time: parked with evidence", BAD);
  card(s, 9.5, 2.05, 3.2, 1.9, CARD2);
  label(s, 9.65, 2.13, 3, "the trip run, item budget", SG);
  mono(s, 9.65, 2.4, 2.95, 1.5, "rejected ×3\n  python: command not found\nparked (evidence kept)\nmas edit --check …python3…\nmas unpark · mas run\nverified · landed 2 files", SW, 9.5);
  card(s, 0.7, 4.3, 5.9, 1.95);
  label(s, 0.9, 4.4, 5, "what the gate makes possible", GOOD);
  bullets(s, 0.9, 4.68, 5.5, 1.5, [
    "A worker that lies changes nothing.",
    "A worker killed at its budget still gets gated — partial work can land.",
    "Cheap and untrusted models become usable: trust comes from the check.",
    "Every verdict carries its output: the evidence when an item parks.",
  ], { size: 11.5, gap: 3 });
  card(s, 6.85, 4.3, 5.85, 1.95, CARD2);
  label(s, 7.05, 4.4, 5, "and what it cannot do", BAD);
  bullets(s, 7.05, 4.68, 5.5, 1.5, [
    "Judge quality with no oracle — that is a human, or a vote across independent workers.",
    "Notice a wrong check. Six correct implementations were once rejected by one bad assertion; the trip's budget was rejected by a missing `python`.",
    "So: derive checks from data and name the exact interpreter.",
  ], { size: 11.5, gap: 3 });
  footer(s, "Words are voted, actions are gated. Never trust the worker; make the check something you can run.");
  s.addNotes("The most important mechanism. Walk the fork: pass lands only the declared files; fail retries up the model tiers and parks with evidence. Then the trip example on the right — a real failure from the walkthrough document, fixed by a human command that is itself an event. Left: what the gate buys. Right: its limits, honestly.");
}

// ---- F · what this gives us
{
  const s = base("how it is built · 6", "What this construction gives us.", 28);
  const cards = [
    ["The vendor is config", "Claude, Codex, Gemini or a shell script on the same board, chosen per item; escalation tiers per kind.", SW],
    ["Cheap where checked", "Haiku or Flash for gated work at cents per item; a stronger model only where judgement is needed, or on the retry.", GOOD],
    ["Failure is bounded", "Lease expiry, backoff, escalation, breaker, evidence — per item. One bad worker never costs the run.", BAD],
    ["Nothing is lost", "State is rows; work is files in worktrees; landing is a commit. Kill it, restart it, watch it from elsewhere.", SG],
    ["Cost and time per item", "Every attempt records tokens, dollars, seconds and turns — the comparison tables come free.", INK],
    ["One contract to extend", "Four requirements to plug in a new harness; one config block, no code, same gate.", MUT],
  ];
  cards.forEach(([h, t, c], i) => {
    const x = 0.7 + (i % 3) * 4.05, y = 2.0 + Math.floor(i / 3) * 2.05;
    card(s, x, y, 3.85, 1.85, i % 2 ? CARD : CARD2);
    chip(s, x + 0.2, y + 0.22, c);
    s.addText(h, { x: x + 0.5, y: y + 0.12, w: 3.2, h: 0.36, fontFace: H, fontSize: 13.5, bold: true, color: INK, margin: 0 });
    body(s, x + 0.2, y + 0.6, 3.5, 1.15, t, { size: 11.5, color: MUT });
  });
  footer(s, "Agents are the demo; the environment is the product. Build the board, the gate and the log — then N is a number in your config.");
  s.addNotes("The payoff slide before the parts. Six cards, each one traceable to a mechanism from the previous five slides. Then move into the per-part decisions.");
}

// =====================================================================
// 3 · Board = SQLite
// =====================================================================
partPage({
  kicker: "part 1 · the board", title: "The board: one SQLite file, WAL mode.", color: SW,
  sub: "Every task, its owner, its lease, its attempts and its verdict — in a file you can copy.",
  chose: "sqlite3  ·  .mas/board.db  ·  BEGIN IMMEDIATE",
  because: [
    "One transaction is one atomic claim: exactly one worker wins an item, even with eight pulling at once.",
    "WAL: readers never block writers, so the live view and other processes read while workers write.",
    "Zero servers. cp board.db is a full backup; sqlite3 board.db is the debugger.",
    "A restart reads the file and continues — the orchestrator holds no state of its own.",
  ],
  alt: "GitHub Issues · Postgres · Redis Streams · DynamoDB — anything persistent with an atomic claim",
  buys: [
    "No two agents ever own the same task (the claim), and no dead agent blocks a task forever (the lease expires, heartbeats renew it while alive).",
    "Retries with backoff and model escalation are rows, not memory. Three failures park the item with the evidence attached.",
    "Kill the orchestrator mid-run and start it again: leases expire, work resumes from the file. Ctrl-C hands leases back with the attempt refunded.",
  ],
  demo: "Demo 1: SIGKILL the run, rerun, 8/8 lands. Demo 6: a dead lease, a crash and a timeout injected on purpose — all recovered from the same file, $0.",
  foot: "Issues have no atomic claim and rate-limit you. A file with a transaction does. So SQLite schedules; Issues mirror.",
  notes: "The board is where correctness lives: the claim, the lease, the breaker. Stress that it is a file — cp is a backup, sqlite3 is the debugger — and that the orchestrator is stateless because of it. Bugs this caught in development: heartbeat longer than lease, exhausted item re-queued past its limit.",
});

// =====================================================================
// 4 · Human mirror = GitHub Issues
// =====================================================================
partPage({
  kicker: "part 2 · the human mirror", title: "GitHub Issues: where people see it happen.", color: SG,
  sub: "One issue per item, one comment per step, closed with the verdict. Never a scheduler.",
  chose: "gh issue create / comment / close",
  because: [
    "It is where humans already file work — items can be imported from issues (check: and merge_paths: lines in the body).",
    "A comment thread is a free evidence log: dispatched → gate passed → landed, commit sha included.",
    "Close-with-verdict is a status everyone already understands; no dashboard to build.",
    "The gh CLI means no SDK, no tokens in code.",
  ],
  alt: "Linear · Jira · a Slack channel — anything humans watch",
  buys: [
    "The audience (or the team) watches the swarm work in a place they know, while the board keeps the locks.",
    "Two problems stay separate: not stepping on the same task (board) and not stepping on the same files (worktrees). Issues solve neither — they show.",
    "Why not schedule with Issues? No compare-and-swap: two agents can both read “open” and both start. Plus rate limits. Fine for one scheduler, unsafe for many.",
  ],
  demo: "mas run --github owner/repo: every item becomes an issue; the audience opens the repo and watches issues close with verdicts as workers land.",
  foot: "Mirror what humans need to see. Lock with something transactional.",
  notes: "Be precise about the split: Issues are intake and visibility. The exactly-one-owner guarantee comes from SQLite. Mention the one race we hit: an item was claimed before its issue number was recorded — fixed by creating the issue before the item becomes claimable.",
});

// =====================================================================
// 5 · Compartments = git worktrees
// =====================================================================
partPage({
  kicker: "part 3 · compartments and the store", title: "Compartments: a git worktree per attempt.", color: GOOD,
  sub: "Every attempt edits its own checkout. Only gate-verified files land on main, idempotently.",
  chose: "git worktree add -b mas/<item>-a<attempt>",
  because: [
    "Isolation for free: one directory and one branch per attempt, sharing one object store. Nothing to install.",
    "Landing = copy the verified files listed in merge_paths, then commit. Land twice: nothing changes.",
    "The history is the audit trail: one commit per verified item, with the item id in the message.",
    "A crashed or rejected attempt is a directory to delete.",
  ],
  alt: "containers · plain repo copies · object-store prefixes",
  buys: [
    "Eight agents edit in parallel and never collide; a stale worker from a lost lease can never share a path with the attempt that replaced it.",
    "merge_paths is the contract's blast radius: a doer may only land its own file; a single agent may land exports/ but never tests/ or fixtures/.",
    "Partial work survives a deadline: whatever is on disk is gated and landed, the rest is discarded — not merged half-way.",
  ],
  demo: "Demo 2: Claude and Codex land alternating commits on one main with zero conflicts. Demo 6: a stale compartment and a fresh one coexist; only the verified one lands.",
  foot: "Worktrees give bulkheads and an audit trail with one command you already have.",
  notes: "Explain worktrees for people who only know branches: same repo, another working directory, another branch, shared objects. Then the two rules: per attempt, not per item (a real bug), and merge_paths as the blast radius.",
});

// =====================================================================
// 6 · Workers = harnesses behind one contract
// =====================================================================
partPage({
  kicker: "part 4 · the workers", title: "Workers: any harness, one contract.", color: INK,
  sub: "claude -p · codex exec · the Gemini or Anthropic API · any headless CLI described in config.",
  chose: "run(prompt, cwd) → whatever changed in cwd",
  because: [
    "Someone else maintains the harness: tools, permissions, sandbox, streaming.",
    "The contract is tiny: a prompt in, a directory to work in, exit. Nothing else is read — the gate decides.",
    "A worker's “done” is a claim, never a verdict. So the harness can be anything, including a shell script.",
    "The vendor becomes config: models per kind, escalation tiers, worker_pref per item.",
  ],
  alt: "the raw API loop (we ship one) · Hermes · Gemini CLI · OpenCode · aider — mas harnesses add <name>",
  buys: [
    "Mixed fleets on one board: Claude and Codex on the same repo; cheap models where the check is real, strong models where judgement is needed.",
    "Escalation on retry: the first attempt on the cheap tier, the retry on the strong one — automatically.",
    "Cheap is fast: Gemini 2.5 Flash fixed a module in ~9 s for half a cent, gate-verified. Eight of them landed 27 of 32 parsers in four minutes.",
  ],
  demo: "Demo 2: --workers claude,codex. Demo 3/4: eight reviewers across two harnesses. mas harnesses add gemini → one more kind in the fleet.",
  foot: "The environment never integrates with a harness. It gives it a directory and checks the result.",
  notes: "The pluggability point. Show the contract line. Name the four requirements: non-interactive, takes a prompt, works in a directory, exits. Then the payoff: mixed fleets and cheap models, because trust comes from the gate, not the model.",
});

// =====================================================================
// 7 · Gate = the check command
// =====================================================================
partPage({
  kicker: "part 5 · the gate", title: "The gate: the check is re-run by code, never by the worker.", color: BAD,
  sub: "cmd: a test command · schema: a JSON shape · human: park for a person. Exit 0 or nothing lands.",
  chose: "cmd:python -m pytest tests/test_x.py -q",
  because: [
    "A verdict the worker cannot argue with — the same command it was told to run, run again in its compartment.",
    "It is what makes cheap and untrusted workers usable at all: trust comes from the check, not the model.",
    "Structure can be gated when truth cannot: schema checks for votes, tests for code, a human for the irreversible.",
    "Every verdict is an event with the output attached — the evidence when an item parks.",
  ],
  alt: "linters · builds · golden files · a reference implementation · a human (awaiting_human)",
  buys: [
    "Workers claimed success and were wrong, several times, across the demos. Nothing unverified ever landed.",
    "It also caught our own mistake: in one experiment a planner wrote a wrong test, and six correct implementations were rejected by it. The gate is only as good as the check — so derive checks from data, not from a model's prose.",
    "Words are voted, actions are gated: reviews are sampled across independent agents; code is verified.",
  ],
  demo: "Every demo: ✅ VERIFIED / ❌ REJECTED lines in the log. Demo 6: a worker that confidently writes the wrong answer is rejected by the gate, then by a schema check.",
  foot: "Never trust the worker. Make the check something you can run, and make it come from data.",
  notes: "The most important slide. Two lessons: the gate is the product, and the contract can be wrong. Tell the demo-5 story briefly: one wrong assertion, six correct attempts rejected, 40 minutes lost — and the reviewer who wrote the test never suspected it.",
});

// =====================================================================
// 8 · Log + views = the same SQLite, append-only
// =====================================================================
partPage({
  kicker: "part 6 · the log and the views", title: "The log: every state change is a write; every screen is a query.", color: SG,
  sub: "Append-only events in the same file. The live dashboard, mas watch and the recovery report are all views over it.",
  chose: "INSERT INTO events (ts, item_id, kind, data)",
  because: [
    "Claimed, dispatched, each tool call, gate verdict, landed, requeued, parked, lease expired — one row each, never edited.",
    "Views are rebuilt from the log: the live terminal UI (8 fps), mas watch from another process, the dashboard, the recovery report.",
    "Debugging is a SELECT. Evidence for a parked item is its own event history.",
    "The same file as the board — one thing to copy, one thing to inspect.",
  ],
  alt: "Kafka · a log file · OpenTelemetry",
  buys: [
    "You can see the whole system from the logs: configuration, board writes, worker activity, gate verdicts, retries, escalations, breaker trips.",
    "Lessons from finished items are appended and shown to later workers — stigmergy through the log, not through chat.",
    "Post-mortems are cheap: demo 6 derives its entire recovery report — 18 patterns proven — from the event rows.",
  ],
  demo: "mas run shows the live view; mas watch in a second terminal shows the same board. Demo 6 ends with result/recovery.md derived from 193 ordered events.",
  foot: "The log is the truth. Screens are for reading it.",
  notes: "Tool 9 in practice. Point at the live view during the demo and say: nothing here is a second source of truth; it is a query over the events. Mention lessons as the one channel agents 'talk' through — a row, not a conversation.",
});

// =====================================================================
// 9 · Use cases — when it pays, and when it does not
// =====================================================================
{
  const s = base("use cases", "When it pays — and when one agent is simply better.", 28);
  const pay = [
    ["A backlog of independent, verifiable jobs", "Fix 8 modules, write 32 parsers, migrate 40 files. N workers, wall-clock ÷ N, each lands as it passes.", "demo 1 · demo 2"],
    ["Many eyes on one question", "Eight independent reviewers, no shared context, then one adjudicator for precision. Words are voted.", "demo 3 · demo 4"],
    ["Runs that must survive failure", "Dead leases, crashes, timeouts, false success — bounded, retried, escalated, parked with evidence.", "demo 6"],
  ];
  pay.forEach(([h, t, d], i) => {
    const y = 2.0 + i * 1.22;
    card(s, 0.7, y, 6.3, 1.1);
    chip(s, 0.95, y + 0.2, GOOD);
    s.addText(h, { x: 1.25, y: y + 0.1, w: 5.6, h: 0.32, fontFace: H, fontSize: 13.5, bold: true, color: INK, margin: 0 });
    body(s, 1.25, y + 0.44, 4.4, 0.6, t, { size: 11.5, color: MUT });
    mono(s, 5.55, y + 0.5, 1.35, 0.4, d, GOOD, 10);
  });
  card(s, 7.3, 2.0, 5.4, 3.54, CARD2);
  chip(s, 7.55, 2.2, BAD);
  s.addText("When not: the work fits one window", { x: 7.85, y: 2.1, w: 4.7, h: 0.32, fontFace: H, fontSize: 13.5, bold: true, color: INK, margin: 0 });
  body(s, 7.55, 2.55, 4.95, 1.3,
    "Same spec, a small library. One strong agent: 44/44 in 6 min for $1.69. Planner + doers + review loop: 42/44 in 64 min for $9.82. Splitting bought nothing and the planner's one wrong test cost 40 minutes.",
    { size: 11.5, color: INK });
  label(s, 7.55, 3.95, 4.5, "rule of thumb", SG);
  body(s, 7.55, 4.22, 4.95, 1.25,
    "Decompose only when the work breaks a wall. Keep one head when there is a pattern to amortize and it fits — it is cheaper and often more accurate. Either way, build the environment: it is the same five boxes at N = 1.",
    { size: 11.5, color: MUT });
  footer(s, "The team wins at the three walls. Everywhere else it pays for coordination it does not need.");
  s.addNotes("Be honest here; it is what makes the rest credible. Three shapes that pay, one that does not, with the numbers from our own experiment. The rule of thumb is the takeaway.");
}

// =====================================================================
// 10 · The demos — what each one proves
// =====================================================================
{
  const s = base("the demos", "Six runs, each proving a part.", 28);
  const rows = [
    ["1", "one fleet", "4 Claude workers fix 8 buggy modules; Ctrl-C mid-run, run again", "board · leases · resume", "mas demo run 1"],
    ["2", "mixed fleet", "Claude and Codex on the same repo, 4 items each, one main", "workers · compartments", "mas demo run 2"],
    ["3", "debate or vote", "8 reviewers vote on a PR with a planted bug; one adjudicator; a script tallies", "gate on structure · bulkheads", "mas demo run 3"],
    ["4", "many eyes", "8 reviewers, 4 planted bugs in 5 files; recall of one vs the union", "independent views", "mas demo run 4"],
    ["5", "advice as context", "a small model alone vs with a private-context adviser vs a strong model alone", "what each call sees", "mas demo run 5"],
    ["6", "recovery lab", "faults injected on cue: dead lease, false success, crash, timeout — $0, ~20 s", "every reliability tool", "mas demo run 6"],
  ];
  const cols = [[0.7, 0.5], [1.25, 1.8], [3.1, 5.4], [8.55, 2.4], [11.0, 1.7]];
  ["#", "demo", "what happens", "proves", "command"].forEach((h, i) => label(s, cols[i][0], 1.7, cols[i][1], h, MUT, 9.5));
  rows.forEach(([n, name, what, proves, cmd], i) => {
    const y = 2.02 + i * 0.68;
    card(s, 0.7, y, 12.0, 0.6, i % 2 ? CARD : CARD2);
    s.addText(n, { x: cols[0][0] + 0.1, y: y + 0.12, w: 0.4, h: 0.36, fontFace: H, fontSize: 14, bold: true, color: SW, margin: 0 });
    s.addText(name, { x: cols[1][0], y: y + 0.12, w: cols[1][1], h: 0.36, fontFace: H, fontSize: 12, bold: true, color: INK, margin: 0 });
    body(s, cols[2][0], y + 0.1, cols[2][1], 0.45, what, { size: 10.5, color: INK, valign: "middle" });
    body(s, cols[3][0], y + 0.1, cols[3][1], 0.45, proves, { size: 10.5, color: GOOD, valign: "middle" });
    mono(s, cols[4][0], y + 0.1, cols[4][1], 0.45, cmd, SW, 10);
  });
  footer(s, "Every demo runs from one command. Nothing in them is special: they only call the board API you can call from the CLI.");
  s.addNotes("Run the demos live from here. Demo 6 first if time is short — it is deterministic, free and twenty seconds. Then demo 1 with Ctrl-C and resume. Demo 2 for the mixed fleet.");
}

// =====================================================================
// 11 · Findings
// =====================================================================
{
  const s = base("what we learned", "Five findings from running it.", 28);
  const f = [
    ["The gate is the product.", "Workers claimed success and were wrong, repeatedly. Nothing unverified landed."],
    ["Decomposition has a price.", "A one-window task pays it and collects nothing: 6 min and $1.69 alone vs 64 min and $9.82 as a team."],
    ["The contract can be wrong, and the loop cannot see it.", "One bad test assertion rejected six correct implementations. Derive checks from data, never from a model's prose."],
    ["Independent views add recall; the adjudicator adds precision.", "Every reviewer found the planted bugs; half of them found a real one nobody planted."],
    ["Reliability comes from the environment.", "Leases, breakers, per-attempt compartments and idempotent landing each caught a real bug during development."],
  ];
  f.forEach(([h, t], i) => {
    const y = 1.85 + i * 0.9;
    card(s, 0.7, y, 12.0, 0.8);
    chip(s, 0.95, y + 0.16, [BAD, SG, BAD, GOOD, SW][i]);
    s.addText(h, { x: 1.25, y: y + 0.07, w: 11.2, h: 0.32, fontFace: H, fontSize: 14, bold: true, color: INK, margin: 0 });
    body(s, 1.25, y + 0.4, 11.2, 0.36, t, { size: 11.5, color: MUT });
  });
  footer(s, "Build the board, the gate and the log. Then N is a number in your config.");
  s.addNotes("Close on the five findings. If asked 'so should I build a swarm?': build the environment always; raise N at the clock, the window and failure.");
}

pres.writeFile({ fileName: require("path").join(__dirname, "design-talk.pptx") }).then(() => console.log("written"));
