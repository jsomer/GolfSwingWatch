import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { fetchMovementDetail, fetchMovementSwings } from "./api";
import type { MovementDetail, MovementSwingSummary } from "./types";
import { WatchFaceVisualizer } from "./WatchFaceVisualizer";

const MARKER_COLORS: Record<string, string> = {
  start: "#43a047",
  impact: "#ef5350",
  followThrough: "#1e88e5"
};

const markerShapes = (markers: MovementDetail["event_markers"], yMax: number) =>
  markers.map((marker) => ({
    type: "line" as const,
    x0: marker.time,
    x1: marker.time,
    y0: 0,
    y1: yMax,
    line: {
      color: MARKER_COLORS[marker.type] ?? "#757575",
      width: 2,
      dash: "dash" as const
    }
  }));

export function MovementExplorer() {
  const [swings, setSwings] = useState<MovementSwingSummary[]>([]);
  const [selectedSwingId, setSelectedSwingId] = useState<string>("");
  const [movement, setMovement] = useState<MovementDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const loadSwings = async () => {
      try {
        const response = await fetchMovementSwings();
        if (cancelled) return;
        setSwings(response.items);
        if (response.items.length > 0) {
          setSelectedSwingId(response.items[0].id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load movement swings");
        }
      }
    };
    void loadSwings();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedSwingId) {
      setMovement(null);
      return;
    }

    let cancelled = false;
    const loadMovement = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchMovementDetail(selectedSwingId);
        if (!cancelled) {
          setMovement(response);
        }
      } catch (err) {
        if (!cancelled) {
          setMovement(null);
          setError(err instanceof Error ? err.message : "Failed to load movement detail");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    void loadMovement();
    return () => {
      cancelled = true;
    };
  }, [selectedSwingId]);

  const accelMax = useMemo(() => {
    if (!movement?.series.accel_mag.length) return 1;
    return Math.max(...movement.series.accel_mag) * 1.1;
  }, [movement]);

  const gyroMax = useMemo(() => {
    if (!movement?.series.gyro_mag.length) return 1;
    return Math.max(...movement.series.gyro_mag) * 1.1;
  }, [movement]);

  const attitudeMax = useMemo(() => {
    if (!movement) return 1;
    const values = [...movement.series.pitch, ...movement.series.roll, ...movement.series.yaw];
    if (!values.length) return 1;
    return Math.max(...values.map(Math.abs)) * 1.2;
  }, [movement]);

  return (
    <section className="movement">
      <h3>Movement Explorer (Plotly)</h3>
      <p className="movement-copy">
        Time-series view of recorded sensor movement for a selected swing.
      </p>

      {swings.length > 0 ? (
        <>
          <label className="movement-picker">
            Swing
            <select value={selectedSwingId} onChange={(event) => setSelectedSwingId(event.target.value)}>
              {swings.map((swing) => (
                <option key={swing.id} value={swing.id}>
                  {swing.club} • {String(swing.date).slice(0, 19)} • {swing.sample_count} samples
                </option>
              ))}
            </select>
          </label>
          <div className="movement-legend" aria-label="Swing event markers">
            <span className="movement-legend-item">
              <span className="movement-legend-swatch start" /> Start
            </span>
            <span className="movement-legend-item">
              <span className="movement-legend-swatch impact" /> Impact
            </span>
            <span className="movement-legend-item">
              <span className="movement-legend-swatch follow" /> Follow-through
            </span>
          </div>
        </>
      ) : (
        <p>No raw swing exports found. Import watch JSON to `data/raw/swings.json`.</p>
      )}

      {error && <p className="error">{error}</p>}
      {loading && <p>Loading movement trace...</p>}

      {movement && movement.sample_count > 0 && (
        <div className="movement-grid">
          <WatchFaceVisualizer
            times={movement.series.times}
            pitch={movement.series.pitch}
            roll={movement.series.roll}
            yaw={movement.series.yaw}
            gyroMag={movement.series.gyro_mag}
            eventMarkers={movement.event_markers}
          />

          <Plot
            data={[
              {
                x: movement.series.times,
                y: movement.series.accel_mag,
                type: "scatter",
                mode: "lines",
                name: "Acceleration"
              }
            ]}
            layout={{
              title: "Acceleration Magnitude",
              xaxis: { title: "Seconds" },
              yaxis: { title: "g" },
              shapes: markerShapes(movement.event_markers, accelMax),
              margin: { t: 40, r: 20, b: 40, l: 50 },
              height: 280
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
          />

          <Plot
            data={[
              {
                x: movement.series.times,
                y: movement.series.gyro_mag,
                type: "scatter",
                mode: "lines",
                name: "Rotation"
              }
            ]}
            layout={{
              title: "Rotational Velocity Magnitude",
              xaxis: { title: "Seconds" },
              yaxis: { title: "rad/s" },
              shapes: markerShapes(movement.event_markers, gyroMax),
              margin: { t: 40, r: 20, b: 40, l: 50 },
              height: 280
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
          />

          <Plot
            data={[
              { x: movement.series.times, y: movement.series.pitch, type: "scatter", mode: "lines", name: "Pitch" },
              { x: movement.series.times, y: movement.series.roll, type: "scatter", mode: "lines", name: "Roll" },
              { x: movement.series.times, y: movement.series.yaw, type: "scatter", mode: "lines", name: "Yaw" }
            ]}
            layout={{
              title: "Watch Orientation",
              xaxis: { title: "Seconds" },
              yaxis: { title: "Radians" },
              shapes: markerShapes(movement.event_markers, attitudeMax),
              margin: { t: 40, r: 20, b: 40, l: 50 },
              height: 280
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
          />
        </div>
      )}
    </section>
  );
}
