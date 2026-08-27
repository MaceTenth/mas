import { interpolate, useCurrentFrame } from "remotion";
import { C, FONT, MONO } from "./theme";

// fade+rise entry; `at` = local frame the element starts appearing
export const useEnter = (at: number, dur = 15) => {
  const f = useCurrentFrame();
  const t = interpolate(f, [at, at + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return { opacity: t, transform: `translateY(${(1 - t) * 18}px)` };
};

export const useFade = (at: number, dur = 12) => {
  const f = useCurrentFrame();
  return interpolate(f, [at, at + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};

export const SceneTitle = ({
  kicker,
  title,
  at = 0,
}: {
  kicker: string;
  title: string;
  at?: number;
}) => {
  const s = useEnter(at);
  return (
    <div style={{ position: "absolute", top: 44, left: 70, right: 70, ...s }}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 15,
          letterSpacing: 3,
          textTransform: "uppercase",
          color: C.muted,
          fontWeight: 600,
          marginBottom: 8,
        }}
      >
        {kicker}
      </div>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 42,
          fontWeight: 700,
          color: C.ink,
          lineHeight: 1.1,
        }}
      >
        {title}
      </div>
    </div>
  );
};

export const Caption = ({
  text,
  at,
  accent = C.ink,
}: {
  text: string;
  at: number;
  accent?: string;
}) => {
  const s = useEnter(at);
  return (
    <div
      style={{
        position: "absolute",
        bottom: 44,
        left: 70,
        right: 70,
        textAlign: "center",
        fontFamily: FONT,
        fontSize: 25,
        fontWeight: 600,
        color: accent,
        ...s,
      }}
    >
      {text}
    </div>
  );
};

export const Chip = ({
  label,
  color,
  bg,
  style,
}: {
  label: string;
  color: string;
  bg: string;
  style?: React.CSSProperties;
}) => (
  <div
    style={{
      fontFamily: MONO,
      fontSize: 14,
      color,
      background: bg,
      border: `1px solid ${color}55`,
      borderRadius: 6,
      padding: "5px 10px",
      ...style,
    }}
  >
    {label}
  </div>
);
