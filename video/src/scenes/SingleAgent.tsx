import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, FONT, MONO } from "../theme";
import { SceneTitle, Caption, useEnter, useFade } from "../common";

// One context column growing toward the 200k ceiling.
export const SingleAgent = () => {
  const f = useCurrentFrame();

  // context fill 0..1 over the scene; hits ceiling at frame 430
  const fill = interpolate(f, [90, 430], [0.06, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const hitWall = f > 430;
  const wallFlash = hitWall ? 0.5 + 0.5 * Math.sin(f / 3) : 0;

  const colH = 340; // px height of the context column area
  const colBottom = 610;

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <SceneTitle kicker="Part 2 · The single agent" title="One head: it learns — until the window ends" />

      {/* context column */}
      <div style={{ position: "absolute", left: 150, top: 235, opacity: useFade(30) }}>
        <div style={{ fontFamily: FONT, fontSize: 15, letterSpacing: 2, textTransform: "uppercase", color: C.muted, fontWeight: 600 }}>
          its context
        </div>
      </div>

      {/* ceiling */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: colBottom - colH - 14,
          width: 300,
          borderTop: `3px dashed ${hitWall ? C.bad : C.muted}`,
          opacity: useFade(60),
        }}
      >
        <div style={{ fontFamily: MONO, fontSize: 15, color: hitWall ? C.bad : C.muted, marginTop: 4 }}>
          200k window {hitWall ? "— HARD CLIFF" : ""}
        </div>
      </div>

      {/* the growing bar */}
      <div
        style={{
          position: "absolute",
          left: 170,
          top: colBottom - colH * fill,
          width: 200,
          height: colH * fill,
          background: `linear-gradient(180deg, ${hitWall ? C.bad : C.single} 0%, ${C.singleSoft} 100%)`,
          borderRadius: "10px 10px 0 0",
          boxShadow: hitWall ? `0 0 ${24 * wallFlash}px ${C.bad}` : "none",
          opacity: useFade(60),
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 170,
          top: colBottom + 10,
          width: 200,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 16,
          color: C.single,
          opacity: useFade(60),
        }}
      >
        {hitWall ? "≈187k — died here" : `${Math.round(fill * 200)}k tokens`}
      </div>

      {/* environment box */}
      <div
        style={{
          position: "absolute",
          left: 500,
          top: 300,
          width: 210,
          height: 190,
          background: C.card,
          border: `1px solid ${C.line}`,
          borderRadius: 14,
          padding: 18,
          fontFamily: FONT,
          color: C.ink,
          ...useEnter(80),
        }}
      >
        <div style={{ fontSize: 17, fontWeight: 700, marginBottom: 10 }}>environment</div>
        <div style={{ fontFamily: MONO, fontSize: 15, color: C.muted, lineHeight: 1.9 }}>
          files on disk
          <br />
          tests (oracle) <span style={{ color: C.good }}>✓</span>
          <br />
          re-readable
        </div>
      </div>

      {/* findings, appearing over time */}
      <div style={{ position: "absolute", left: 790, top: 245, width: 400 }}>
        {[
          { at: 110, color: C.good, head: "It learns across tasks", body: "task #1 costs 9 turns… task #30 costs 2. Round 2: 70 turns vs the swarm's 350." },
          { at: 220, color: C.good, head: "Recall doesn't decay", body: "240/240 facts from a 102k context — 100% at every depth (round 5A)." },
          { at: 320, color: C.bad, head: "But one crash = total amnesia", body: "everything not written to disk dies with the context (round 3: +111% under failures)." },
          { at: 440, color: C.bad, head: "And the window is a cliff", body: "at 187k it simply stopped — 8 tasks never seen. Not decay. A wall. (round 5B)" },
        ].map((c, i) => (
          <div
            key={i}
            style={{
              background: C.card,
              border: `1px solid ${C.line}`,
              borderLeft: `4px solid ${c.color}`,
              borderRadius: 10,
              padding: "12px 16px",
              marginBottom: 12,
              ...useEnter(c.at),
            }}
          >
            <div style={{ fontFamily: FONT, fontSize: 18, fontWeight: 700, color: c.color }}>{c.head}</div>
            <div style={{ fontFamily: FONT, fontSize: 15.5, color: C.muted, marginTop: 3, lineHeight: 1.45 }}>{c.body}</div>
          </div>
        ))}
      </div>

      <Caption at={480} text="Cheapest and most accurate — inside one window, on one machine, if nothing crashes." accent={C.single} />
    </AbsoluteFill>
  );
};
