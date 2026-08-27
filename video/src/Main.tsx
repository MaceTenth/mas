import { AbsoluteFill, Series, useCurrentFrame, interpolate } from "remotion";
import { C, FONT } from "./theme";
import { Illusion } from "./scenes/Illusion";
import { SingleAgent } from "./scenes/SingleAgent";
import { Swarm } from "./scenes/Swarm";
import { Dials } from "./scenes/Dials";

const OPEN = 105;
const S1 = 450; // illusion
const S2 = 560; // single agent
const S3 = 590; // swarm
const S4 = 620; // dials + end card
export const TOTAL_FRAMES = OPEN + S1 + S2 + S3 + S4; // 2325 ≈ 77.5s

const Opening = () => {
  const f = useCurrentFrame();
  const o1 = interpolate(f, [5, 25], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const o2 = interpolate(f, [40, 60], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: C.bg, alignItems: "center", justifyContent: "center", textAlign: "center" }}>
      <div>
        <div style={{ fontFamily: FONT, fontSize: 54, fontWeight: 700, color: C.ink, opacity: o1 }}>
          Agents, Swarms &amp; the Two Dials
        </div>
        <div style={{ fontFamily: FONT, fontSize: 24, color: C.muted, marginTop: 20, opacity: o2 }}>
          what a six-round benchmark taught us about multi-agent systems
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const Main = () => (
  <Series>
    <Series.Sequence durationInFrames={OPEN}>
      <Opening />
    </Series.Sequence>
    <Series.Sequence durationInFrames={S1}>
      <Illusion />
    </Series.Sequence>
    <Series.Sequence durationInFrames={S2}>
      <SingleAgent />
    </Series.Sequence>
    <Series.Sequence durationInFrames={S3}>
      <Swarm />
    </Series.Sequence>
    <Series.Sequence durationInFrames={S4}>
      <Dials />
    </Series.Sequence>
  </Series>
);
