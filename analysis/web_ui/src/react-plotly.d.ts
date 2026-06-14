declare module "react-plotly.js" {
  import type { FC } from "react";
  import type { Config, Data, Layout } from "plotly.js";

  export type PlotParams = {
    data: Data[];
    layout?: Partial<Layout>;
    config?: Partial<Config>;
    style?: React.CSSProperties;
    className?: string;
    useResizeHandler?: boolean;
  };

  const Plot: FC<PlotParams>;
  export default Plot;
}
