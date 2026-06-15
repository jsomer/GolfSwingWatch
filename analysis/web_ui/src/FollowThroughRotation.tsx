import { useMemo } from "react";
import Plot from "react-plotly.js";
import type { FollowThroughMetrics } from "./types";

type FollowThroughRotationProps = {
  metrics: FollowThroughMetrics;
};

export function FollowThroughRotation({ metrics }: FollowThroughRotationProps) {
  const path = metrics.path;

  const pathMax = useMemo(() => {
    if (!path) return 10;
    const values = [...path.roll_deg, ...path.yaw_deg, ...path.pitch_deg].map(Math.abs);
    return Math.max(10, ...values) * 1.15;
  }, [path]);

  return (
    <div className="follow-through-panel">
      <div className="follow-through-summary">
        <div>
          <span className="follow-through-label">Wrist Return Rotation</span>
          <strong className="follow-through-value">{metrics.rotation_deg.toFixed(1)}°</strong>
        </div>
        <p className="follow-through-direction">{metrics.direction_label}</p>
        <div className="follow-through-components">
          <span>Roll {metrics.roll_deg >= 0 ? "+" : "−"} {Math.abs(metrics.roll_deg).toFixed(1)}°</span>
          <span>Yaw {metrics.yaw_deg >= 0 ? "+" : "−"} {Math.abs(metrics.yaw_deg).toFixed(1)}°</span>
          <span>Pitch {metrics.pitch_deg >= 0 ? "+" : "−"} {Math.abs(metrics.pitch_deg).toFixed(1)}°</span>
        </div>
      </div>

      <div className="follow-through-charts">
        <Plot
          data={[
            {
              type: "scatterpolar",
              r: [0, metrics.rotation_deg],
              theta: [metrics.direction_deg, metrics.direction_deg],
              mode: "lines+markers",
              line: { color: "#1e88e5", width: 4 },
              marker: { size: [0, 12], color: ["#1e88e5", "#ef5350"] },
              hoverinfo: "skip",
              showlegend: false
            },
            {
              type: "scatterpolar",
              r: [metrics.rotation_deg],
              theta: [metrics.direction_deg],
              mode: "markers",
              marker: { size: 14, color: "#ef5350", line: { color: "#ffffff", width: 2 } },
              name: "Net rotation",
              hovertemplate: "Rotation: %{r:.1f}°<br>Direction: %{theta:.0f}°<extra></extra>"
            }
          ]}
          layout={{
            title: "Return Direction Compass",
            polar: {
              radialaxis: {
                angle: 90,
                tickfont: { size: 10 },
                gridcolor: "#e5e7eb"
              },
              angularaxis: {
                direction: "clockwise",
                rotation: 90,
                tickmode: "array",
                tickvals: [0, 90, 180, 270],
                ticktext: ["Roll +", "Yaw +", "Roll −", "Yaw −"],
                gridcolor: "#e5e7eb"
              },
              bgcolor: "#f8fafc"
            },
            margin: { t: 48, r: 24, b: 24, l: 24 },
            height: 320,
            paper_bgcolor: "#ffffff",
            annotations: [
              {
                text: "Roll/Yaw plane · arrow shows net wrist path from impact",
                xref: "paper",
                yref: "paper",
                x: 0.5,
                y: -0.04,
                showarrow: false,
                font: { size: 11, color: "#6b7280" }
              }
            ]
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />

        {path && path.times.length > 1 && (
          <>
            <Plot
              data={[
                {
                  x: path.roll_deg,
                  y: path.yaw_deg,
                  type: "scatter",
                  mode: "lines+markers",
                  line: { color: "#1e88e5", width: 2 },
                  marker: { size: 5, color: "#1e88e5" },
                  name: "Return path"
                },
                {
                  x: [0],
                  y: [0],
                  type: "scatter",
                  mode: "markers",
                  marker: { size: 10, color: "#43a047", symbol: "circle" },
                  name: "Impact"
                },
                {
                  x: [path.roll_deg[path.roll_deg.length - 1]],
                  y: [path.yaw_deg[path.yaw_deg.length - 1]],
                  type: "scatter",
                  mode: "markers",
                  marker: { size: 10, color: "#ef5350", symbol: "diamond" },
                  name: "Finish"
                }
              ]}
              layout={{
                title: "Wrist Return Path (Roll vs Yaw)",
                xaxis: { title: "Roll change (°)", range: [-pathMax, pathMax], zeroline: true, zerolinecolor: "#d1d5db" },
                yaxis: { title: "Yaw change (°)", range: [-pathMax, pathMax], zeroline: true, zerolinecolor: "#d1d5db", scaleanchor: "x", scaleratio: 1 },
                margin: { t: 48, r: 20, b: 48, l: 56 },
                height: 320,
                showlegend: true,
                legend: { orientation: "h", y: -0.18 }
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
            />

            <Plot
              data={[
                { x: path.times, y: path.roll_deg, type: "scatter", mode: "lines", name: "Roll", line: { color: "#1e88e5" } },
                { x: path.times, y: path.yaw_deg, type: "scatter", mode: "lines", name: "Yaw", line: { color: "#43a047" } },
                { x: path.times, y: path.pitch_deg, type: "scatter", mode: "lines", name: "Pitch", line: { color: "#fb8c00" } }
              ]}
              layout={{
                title: "Follow-Through Rotation Over Time",
                xaxis: { title: "Seconds after impact" },
                yaxis: { title: "Cumulative rotation (°)" },
                margin: { t: 48, r: 20, b: 48, l: 56 },
                height: 280,
                legend: { orientation: "h", y: -0.22 }
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
            />
          </>
        )}
      </div>
    </div>
  );
}
