import { Composition } from "remotion";
import { Main, TOTAL_FRAMES } from "./Main";

export const RemotionRoot = () => (
  <Composition
    id="Main"
    component={Main}
    durationInFrames={TOTAL_FRAMES}
    fps={30}
    width={1280}
    height={720}
  />
);
