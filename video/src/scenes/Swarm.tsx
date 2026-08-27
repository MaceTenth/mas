import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, FONT, MONO } from "../theme";
import { SceneTitle, Caption, useEnter, useFade } from "../common";

const N_CHIPS = 6;
// worker i starts at these local frames; worker 3 gets killed and re-run
const STARTS = [95, 105, 115, 125, 135, 145];
const DUR = 110; // frames a worker takes

export const Swarm = () => {
  const f = useCurrentFrame();

  const workerState = (i: number) => {
    const s = STARTS[i];
    if (f < s) return { phase: "idle", t: 0 };
    const local = f - s;
    if (i === 3) {
      // killed mid-task, then re-dispatched
      if (local < 55) return { phase: "work", t: local / DUR };
      if (local < 85) return { phase: "dead", t: 0 };
      const re = local - 85;
      if (re < DUR) return { phase: "work", t: re / DUR, retry: true };
      return { phase: "done", t: 1, retry: true };
    }
    if (local < DUR) return { phase: "work", t: local / DUR };
    return { phase: "done", t: 1 };
  };

  const doneCount = [0, 1, 2, 3, 4, 5].filter((i) => workerState(i).phase === "done").length;

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <SceneTitle kicker="Part 3 · The swarm" title="Many small heads + a board that never forgets" />

      {/* task board */}
      <div style={{ position: "absolute", left: 90, top: 225, width: 240, ...useEnter(25) }}>
        <div style={{ fontFamily: FONT, fontSize: 15, letterSpacing: 2, textTransform: "uppercase", color: C.muted, fontWeight: 600, marginBottom: 10 }}>
          task board (durable)
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {Array.from({ length: N_CHIPS }, (_, i) => {
            const claimed = i < 6 && f > STARTS[i];
            const done = i < 6 && workerState(i).phase === "done";
            return (
              <div
                key={i}
                style={{
                  fontFamily: MONO,
                  fontSize: 13.5,
                  padding: "7px 9px",
                  borderRadius: 6,
                  background: C.card,
                  border: `1px solid ${done ? C.good : claimed ? C.swarm : C.line}`,
                  color: done ? C.good : claimed ? C.swarm : C.muted,
                }}
              >
                #{i + 1} {done ? "closed ✓" : claimed ? "leased" : "open"}
              </div>
            );
          })}
        </div>
        <div style={{ fontFamily: FONT, fontSize: 14.5, color: C.muted, marginTop: 10, opacity: useFade(300) }}>
          a dead worker's lease expires → task re-opens. Nothing is lost.
        </div>
      </div>

      {/* workers */}
      <div style={{ position: "absolute", left: 420, top: 225, width: 400 }}>
        <div style={{ fontFamily: FONT, fontSize: 15, letterSpacing: 2, textTransform: "uppercase", color: C.muted, fontWeight: 600, marginBottom: 10, ...useEnter(45) }}>
          disposable workers · tiny fresh contexts
        </div>
        {Array.from({ length: 6 }, (_, i) => {
          const st = workerState(i);
          const border = st.phase === "dead" ? C.bad : st.phase === "done" ? C.good : st.phase === "work" ? C.swarm : C.line;
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                background: C.card,
                border: `1px solid ${border}`,
                borderRadius: 9,
                padding: "8px 14px",
                marginBottom: 9,
                opacity: useFade(45 + i * 6),
              }}
            >
              <div style={{ fontFamily: MONO, fontSize: 14.5, color: C.ink, width: 118 }}>
                worker {i + 1}
                {st.retry ? " (retry)" : ""}
              </div>
              <div style={{ flex: 1, height: 10, background: C.line, borderRadius: 5, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${st.t * 100}%`,
                    height: "100%",
                    background: st.phase === "dead" ? C.bad : C.swarm,
                  }}
                />
              </div>
              <div style={{ fontFamily: MONO, fontSize: 15, width: 88, textAlign: "right", color: border }}>
                {st.phase === "dead" ? "KILLED ✕" : st.phase === "done" ? "verified ✓" : st.phase === "work" ? "~11k tok" : "idle"}
              </div>
            </div>
          );
        })}
      </div>

      {/* verification gate + main */}
      <div style={{ position: "absolute", right: 80, top: 250, width: 300, ...useEnter(70) }}>
        <div
          style={{
            background: C.card,
            border: `2px solid ${C.good}`,
            borderRadius: 12,
            padding: "14px 18px",
            fontFamily: FONT,
            marginBottom: 16,
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 700, color: C.good }}>verification gate</div>
          <div style={{ fontSize: 15, color: C.muted, marginTop: 4, lineHeight: 1.45 }}>
            the orchestrator runs the tests itself.
            <br />
            No agent grades its own work.
          </div>
        </div>
        <div
          style={{
            background: C.card,
            border: `1px solid ${C.line}`,
            borderRadius: 12,
            padding: "14px 18px",
            fontFamily: FONT,
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 700, color: C.ink }}>main branch</div>
          <div style={{ fontFamily: MONO, fontSize: 15.5, color: C.good, marginTop: 6 }}>
            {doneCount} / 6 verified merges
          </div>
          <div style={{ fontSize: 15, color: C.muted, marginTop: 4 }}>only verified work lands</div>
        </div>

        <div style={{ marginTop: 18, ...useEnter(360) }}>
          {[
            "2.3× faster under failures",
            "+36% vs +111% crash degradation",
            "escapes the 200k window",
          ].map((t, i) => (
            <div key={i} style={{ fontFamily: FONT, fontSize: 16.5, color: C.swarm, fontWeight: 600, marginBottom: 6 }}>
              ▸ {t}
            </div>
          ))}
        </div>
      </div>

      <Caption at={500} text="The magic isn't the agents. It's the board, the gate, and the lease." accent={C.swarm} />
    </AbsoluteFill>
  );
};
