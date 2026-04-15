// Override broken @types for react-magnifier (PureComponent types incompatible with @types/react 18)
declare module "react-magnifier" {
  import { ComponentType, CSSProperties } from "react";

  interface MagnifierProps {
    src: string;
    zoomImgSrc?: string;
    zoomFactor?: number;
    mgWidth?: number;
    mgHeight?: number;
    mgBorderWidth?: number;
    mgShape?: "circle" | "square";
    mgShowOverflow?: boolean;
    mgMouseOffsetX?: number;
    mgMouseOffsetY?: number;
    mgTouchOffsetX?: number;
    mgTouchOffsetY?: number;
    width?: string | number;
    height?: string | number;
    className?: string;
    style?: CSSProperties;
  }

  const Magnifier: ComponentType<MagnifierProps>;
  export default Magnifier;
}
