import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, FONT, MONO } from "../theme";
import { SceneTitle, Caption, useEnter, useFade } from "../common";

const END = 420; // end card start (local frame)

// an arc gauge with a needle sweeping between two labeled poles
const Dial = ({
  title,
  left,
  right,
  sweepAt,
  x,
}: {
  title: string;
  left: string;
  right: string;
  sweepAt: number;
  x: number;
}) => {
  const f = useCurrentFrame();
  const t = interpolate(
    f,
    [sweepAt, sweepAt + 45, sweepAt + 90, sweepAt + 125],
    [-80, 80, -30, 45],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const cx = 170;
  const cy = 165;
  const r = 130;
  return (
    <div style={{ position: "absolute", left: x, top: 250, width: 340, ...useEnter(sweepAt - 20) }}>
      <svg width={340} height={190}>
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={C.line}
          strokeWidth={12}
          strokeLinecap="round"
        />
        <g transform={`rotate(${t}, ${cx}, ${cy})`}>
          <line x1={cx} y1={cy} x2={cx} y2={cy - r + 22} stroke={C.single} strokeWidth={6} strokeLinecap="round" />
        </g>
        <circle cx={cx} cy={cy} r={10} fill={C.single} />
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: -18 }}>
        <div style={{ fontFamily: FONT, fontSize: 14.5, color: C.muted, width: 130 }}>{left}</div>
        <div style={{ fontFamily: FONT, fontSize: 14.5, color: C.muted, width: 130, textAlign: "right" }}>{right}</div>
      </div>
      <div style={{ fontFamily: FONT, fontSize: 19, fontWeight: 700, color: C.ink, textAlign: "center", marginTop: 14 }}>
        {title}
      </div>
    </div>
  );
};

const Lock = ({ at, text }: { at: number; text: string }) => (
  <div
    style={{
      fontFamily: FONT,
      fontSize: 19,
      fontWeight: 700,
      color: C.good,
      background: C.card,
      border: `2px solid ${C.good}`,
      borderRadius: 12,
      padding: "14px 26px",
      ...useEnter(at),
    }}
  >
    🔒 {text}
  </div>
);

const Body = () => (
  <>
    <SceneTitle kicker="Part 4 · The point" title="MAS is not more agents. It's two dials — and two locks." />
    <Dial
      title="Dial 1 — what does each call see?"
      left="everything (one shared transcript)"
      right="nothing (briefs + artifacts)"
      sweepAt={70}
      x={170}
    />
    <Dial
      title="Dial 2 — who schedules the next call?"
      left="the model, from inside its loop"
      right="your code (board, leases, retries)"
      sweepAt={120}
      x={760}
    />
    <div style={{ position: "absolute", left: 0, right: 0, top: 520, display: "flex", justifyContent: "center", gap: 26 }}>
      <Lock at={250} text="verification gates on every handoff" />
      <Lock at={285} text="state that lives outside every context window" />
    </div>
    <Caption at={330} text="Every setting of these dials is 'multi-agent'. The dials — not the agent count — are the design." />
  </>
);

const EndCard = () => {
  const o = useFade(END + 5);
  const line2 = useEnter(END + 40);
  const foot = useEnter(END + 90);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center" }}>
      <div style={{ opacity: o, maxWidth: 900 }}>
        <div style={{ fontFamily: FONT, fontSize: 46, fontWeight: 700, color: C.ink, lineHeight: 1.25 }}>
          A single agent is a swarm with <span style={{ color: C.single }}>N = 1</span>.
        </div>
        <div style={{ fontFamily: FONT, fontSize: 30, fontWeight: 600, color: C.swarm, marginTop: 26, ...line2 }}>
          You never choose whether to build the MAS —<br />
          only N.
        </div>
        <div style={{ fontFamily: MONO, fontSize: 16, color: C.muted, marginTop: 48, ...foot }}>
          claude_mas · six-round benchmark · Haiku 4.5 · $11.30
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const Dials = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {f < END ? <Body /> : <EndCard />}
    </AbsoluteFill>
  );
};
