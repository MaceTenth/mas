import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, FONT, MONO } from "../theme";
import { SceneTitle, Caption, useEnter, useFade } from "../common";

// 3 simulated calls. Each call: the WHOLE transcript stack flashes and flows
// into a memoryless model; a new block appends to the stack.
const BLOCKS = [
  { label: "user brief", color: C.ink },
  { label: "assistant: read file", color: C.swarm },
  { label: "tool result", color: C.muted },
  { label: "assistant: edit", color: C.swarm },
  { label: "tool result", color: C.muted },
  { label: "assistant: done", color: C.swarm },
];

// call k (0..2) happens between frames CALL_START + k*CALL_LEN
const CALL_START = 105;
const CALL_LEN = 85;

export const Illusion = () => {
  const f = useCurrentFrame();

  const callIdx = Math.min(
    2,
    Math.max(-1, Math.floor((f - CALL_START) / CALL_LEN))
  );
  const callLocal = f - CALL_START - callIdx * CALL_LEN;
  // blocks visible: 2 appear after each completed call, starting with 0
  const completed = callIdx + (callLocal > CALL_LEN - 20 ? 1 : 0);
  const visibleBlocks = Math.min(BLOCKS.length, Math.max(0, (callIdx < 0 ? 0 : callIdx) * 2) + (callIdx >= 0 && callLocal > CALL_LEN - 25 ? 2 : callIdx >= 0 ? 1 : 0) + (callIdx >= 0 ? 1 : 0) - 1);
  const shown = Math.max(callIdx >= 0 ? 1 : 0, Math.min(BLOCKS.length, 2 * Math.max(0, callIdx) + (callLocal > 55 ? 2 : callLocal > 25 ? 1 : 0)));

  // replay flash: whole stack pulses at the start of each call
  const flash =
    callIdx >= 0
      ? interpolate(callLocal, [0, 12, 30], [0, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 0;

  // arrow from stack to model during first half of each call
  const arrowT =
    callIdx >= 0
      ? interpolate(callLocal, [8, 40], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 0;

  const forgetFlash =
    callIdx >= 0
      ? interpolate(callLocal, [58, 66, 80], [0, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 0;

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <SceneTitle kicker="Part 1 · What is an agent, actually?" title="There are no agents — only stateless calls" />

      {/* subtitle */}
      <div
        style={{
          position: "absolute",
          top: 150,
          left: 70,
          fontFamily: FONT,
          fontSize: 21,
          color: C.muted,
          ...useEnter(25),
        }}
      >
        The model remembers <b style={{ color: C.ink }}>nothing</b> between API calls. A harness fakes continuity.
      </div>

      {/* transcript stack */}
      <div style={{ position: "absolute", left: 110, top: 235, width: 330, opacity: useFade(70) }}>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 15,
            letterSpacing: 2,
            textTransform: "uppercase",
            color: C.muted,
            fontWeight: 600,
            marginBottom: 10,
          }}
        >
          the transcript (grows forever)
        </div>
        {BLOCKS.map((b, i) => {
          const on = i < shown;
          return (
            <div
              key={i}
              style={{
                fontFamily: MONO,
                fontSize: 15,
                color: b.color,
                background: C.card,
                border: `1px solid ${flash > 0.05 && on ? C.single : C.line}`,
                boxShadow: flash > 0.05 && on ? `0 0 ${14 * flash}px ${C.single}66` : "none",
                borderRadius: 7,
                padding: "8px 12px",
                marginBottom: 7,
                opacity: on ? 1 : 0.08,
                transition: "none",
              }}
            >
              {b.label}
            </div>
          );
        })}
        <div style={{ fontFamily: FONT, fontSize: 15, color: C.single, fontWeight: 600, opacity: flash }}>
          ↻ the ENTIRE stack is re-sent, every call
        </div>
      </div>

      {/* arrow */}
      <svg style={{ position: "absolute", left: 455, top: 380 }} width={230} height={60}>
        <line
          x1={0}
          y1={30}
          x2={210 * arrowT}
          y2={30}
          stroke={C.single}
          strokeWidth={4}
          strokeDasharray="10 7"
        />
        {arrowT > 0.95 && <polygon points="210,18 230,30 210,42" fill={C.single} />}
      </svg>

      {/* the model */}
      <div
        style={{
          position: "absolute",
          left: 705,
          top: 300,
          width: 230,
          height: 160,
          background: C.card,
          border: `2px solid ${forgetFlash > 0.05 ? C.bad : C.line}`,
          borderRadius: 14,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          opacity: useFade(70),
        }}
      >
        <div style={{ fontFamily: FONT, fontSize: 30, fontWeight: 700, color: C.ink }}>LLM</div>
        <div style={{ fontFamily: FONT, fontSize: 15, color: C.muted, marginTop: 6 }}>stateless</div>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 15,
            color: C.bad,
            fontWeight: 700,
            marginTop: 8,
            opacity: forgetFlash,
          }}
        >
          forgets everything ✕
        </div>
      </div>

      {/* call counter */}
      <div
        style={{
          position: "absolute",
          right: 110,
          top: 250,
          fontFamily: MONO,
          fontSize: 17,
          color: C.muted,
          textAlign: "right",
          opacity: useFade(95),
        }}
      >
        {[0, 1, 2].map((k) => (
          <div key={k} style={{ marginBottom: 8, color: callIdx >= k ? C.good : C.line }}>
            call #{k + 1} {callIdx > k || (callIdx === k && callLocal > 55) ? "✓" : ""}
          </div>
        ))}
      </div>

      <Caption
        at={CALL_START + 3 * CALL_LEN + 5}
        text={'"An agent" = a memoryless model + a loop that replays the whole story into every fresh call.'}
      />
    </AbsoluteFill>
  );
};
