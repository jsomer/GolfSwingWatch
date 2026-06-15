import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Plot from "react-plotly.js";
import type { PlotMouseEvent } from "plotly.js";

type EventMarker = { type: string; time: number };

type WatchFaceVisualizerProps = {
  times: number[];
  pitch: number[];
  roll: number[];
  yaw: number[];
  gyroMag?: number[];
  eventMarkers: EventMarker[];
};

type CalibrationOffsets = {
  pitchDeg: number;
  rollDeg: number;
  yawDeg: number;
};

const MARKER_COLORS: Record<string, string> = {
  address: "#6b7280",
  takeaway: "#43a047",
  top: "#fb8c00",
  downswingStart: "#8e24aa",
  contactGuess: "#ef5350",
  finish: "#1e88e5",
  start: "#43a047",
  impact: "#ef5350",
  followThrough: "#1e88e5"
};

const toDegrees = (radians: number): number => (radians * 180) / Math.PI;
const DEFAULT_CALIBRATION: CalibrationOffsets = {
  pitchDeg: 0,
  rollDeg: 90,
  yawDeg: 0
};
const ADDRESS_LEAD_IN_SECONDS = 0.08;
const TAKEAWAY_GYRO_THRESHOLD = 3.0;

const resolveAddressIndex = (
  times: number[],
  eventMarkers: EventMarker[],
  gyroMag?: number[]
): number => {
  if (times.length === 0) return 0;

  const startMarker = eventMarkers.find(
    (marker) => marker.type === "address" || marker.type === "start"
  );
  if (startMarker) {
    const targetTime = Math.max(0, startMarker.time - ADDRESS_LEAD_IN_SECONDS);
    return times.reduce(
      (best, time, index) =>
        Math.abs(time - targetTime) < Math.abs(times[best] - targetTime) ? index : best,
      0
    );
  }

  if (gyroMag && gyroMag.length === times.length) {
    let addressIdx = 0;
    for (let index = 0; index < gyroMag.length; index += 1) {
      if (gyroMag[index] >= TAKEAWAY_GYRO_THRESHOLD) {
        return Math.max(0, index - 1);
      }
      addressIdx = index;
    }
    return addressIdx;
  }

  return 0;
};

const markerLabel = (type: string): string => {
  const labels: Record<string, string> = {
    address: "Address",
    takeaway: "Takeaway",
    top: "Top",
    downswingStart: "Downswing start",
    contactGuess: "Contact (guess)",
    finish: "Finish",
    followThrough: "Follow-through",
    start: "Start",
    impact: "Impact"
  };
  return labels[type] ?? type.charAt(0).toUpperCase() + type.slice(1);
};

const nearestIndexForTime = (times: number[], targetTime: number): number => {
  if (times.length === 0) return 0;
  return times.reduce(
    (best, time, index) =>
      Math.abs(time - targetTime) < Math.abs(times[best] - targetTime) ? index : best,
    0
  );
};

type CalibrationDialProps = {
  label: string;
  hint: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
};

function CalibrationDial({ label, hint, value, min, max, onChange }: CalibrationDialProps) {
  return (
    <label className="watch-face-dial">
      <span className="watch-face-dial-label">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-label={`${label} face offset`}
      />
      <span className="watch-face-dial-value">{value.toFixed(0)}°</span>
      <span className="watch-face-dial-hint">{hint}</span>
    </label>
  );
}

export function WatchFaceVisualizer({
  times,
  pitch,
  roll,
  yaw,
  gyroMag,
  eventMarkers
}: WatchFaceVisualizerProps) {
  const addressIndex = useMemo(
    () => resolveAddressIndex(times, eventMarkers, gyroMag),
    [times, eventMarkers, gyroMag]
  );

  const [frameIndex, setFrameIndex] = useState(addressIndex);
  const [referenceIndex, setReferenceIndex] = useState(addressIndex);
  const [calibration, setCalibration] = useState<CalibrationOffsets>(DEFAULT_CALIBRATION);
  const [playing, setPlaying] = useState(false);
  const playbackStartIndex = useRef(0);

  const maxIndex = Math.max(times.length - 1, 0);

  useEffect(() => {
    setReferenceIndex(addressIndex);
    setCalibration(DEFAULT_CALIBRATION);
    setFrameIndex(addressIndex);
    setPlaying(false);
  }, [times, pitch, roll, yaw, addressIndex]);

  useEffect(() => {
    if (!playing || times.length < 2) return;

    const startWall = performance.now();
    const startSampleTime = times[playbackStartIndex.current] ?? 0;
    let raf = 0;

    const step = (now: number) => {
      const elapsedSeconds = (now - startWall) / 1000;
      const targetTime = startSampleTime + elapsedSeconds;
      const endTime = times[maxIndex] ?? 0;

      if (targetTime >= endTime) {
        setPlaying(false);
        setFrameIndex(maxIndex);
        return;
      }

      setFrameIndex(nearestIndexForTime(times, targetTime));
      raf = requestAnimationFrame(step);
    };

    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [playing, times, maxIndex]);

  const currentPitch = pitch[frameIndex] ?? 0;
  const currentRoll = roll[frameIndex] ?? 0;
  const currentYaw = yaw[frameIndex] ?? 0;
  const currentTime = times[frameIndex] ?? 0;

  const referencePitch = pitch[referenceIndex] ?? 0;
  const referenceRoll = roll[referenceIndex] ?? 0;
  const referenceYaw = yaw[referenceIndex] ?? 0;
  const referenceTime = times[referenceIndex] ?? 0;

  const deltaPitch = currentPitch - referencePitch;
  const deltaRoll = currentRoll - referenceRoll;
  const deltaYaw = currentYaw - referenceYaw;

  const deltaPitchSeries = useMemo(
    () => pitch.map((value) => toDegrees(value - referencePitch)),
    [pitch, referencePitch]
  );
  const deltaRollSeries = useMemo(
    () => roll.map((value) => toDegrees(value - referenceRoll)),
    [roll, referenceRoll]
  );
  const deltaYawSeries = useMemo(
    () => yaw.map((value) => toDegrees(value - referenceYaw)),
    [yaw, referenceYaw]
  );

  const displayPitchDeg = toDegrees(deltaPitch) + calibration.pitchDeg;
  const displayRollDeg = toDegrees(deltaRoll) + calibration.rollDeg;
  const displayYawDeg = toDegrees(deltaYaw) + calibration.yawDeg;

  const atReferenceFrame = frameIndex === referenceIndex;

  const nearestMarker = useMemo(() => {
    return eventMarkers.reduce<EventMarker | null>((closest, marker) => {
      if (!closest) return marker;
      const closestDelta = Math.abs(closest.time - currentTime);
      const markerDelta = Math.abs(marker.time - currentTime);
      return markerDelta < closestDelta ? marker : closest;
    }, null);
  }, [eventMarkers, currentTime]);

  const showMarkerHint =
    nearestMarker !== null && Math.abs(nearestMarker.time - currentTime) < 0.05;

  const timelineYRange = useMemo(() => {
    const values = [...deltaPitchSeries, ...deltaRollSeries, ...deltaYawSeries];
    if (!values.length) return [-10, 10];
    const maxAbs = Math.max(10, ...values.map(Math.abs));
    return [-maxAbs * 1.15, maxAbs * 1.15];
  }, [deltaPitchSeries, deltaRollSeries, deltaYawSeries]);

  const pitchYRange = useMemo(() => {
    if (!deltaPitchSeries.length) return [-10, 10];
    const maxAbs = Math.max(10, ...deltaPitchSeries.map(Math.abs));
    return [-maxAbs * 1.15, maxAbs * 1.15];
  }, [deltaPitchSeries]);

  const timelineShapes = useMemo(
    () => [
      ...eventMarkers.map((marker) => ({
        type: "line" as const,
        x0: marker.time,
        x1: marker.time,
        y0: timelineYRange[0],
        y1: timelineYRange[1],
        line: {
          color: MARKER_COLORS[marker.type] ?? "#757575",
          width: 1.5,
          dash: "dash" as const
        }
      })),
      {
        type: "line" as const,
        x0: currentTime,
        x1: currentTime,
        y0: timelineYRange[0],
        y1: timelineYRange[1],
        line: { color: "#111827", width: 3 }
      }
    ],
    [eventMarkers, currentTime, timelineYRange]
  );

  const pitchShapes = useMemo(
    () => [
      {
        type: "line" as const,
        x0: times[0] ?? 0,
        x1: times[maxIndex] ?? 0,
        y0: 0,
        y1: 0,
        line: { color: "#9ca3af", width: 1, dash: "dot" as const }
      },
      ...eventMarkers.map((marker) => ({
        type: "line" as const,
        x0: marker.time,
        x1: marker.time,
        y0: pitchYRange[0],
        y1: pitchYRange[1],
        line: {
          color: MARKER_COLORS[marker.type] ?? "#757575",
          width: 1.5,
          dash: "dash" as const
        }
      })),
      {
        type: "line" as const,
        x0: currentTime,
        x1: currentTime,
        y0: pitchYRange[0],
        y1: pitchYRange[1],
        line: { color: "#111827", width: 3 }
      }
    ],
    [eventMarkers, currentTime, pitchYRange, times, maxIndex]
  );

  const seekToTime = useCallback(
    (targetTime: number) => {
      setPlaying(false);
      setFrameIndex(nearestIndexForTime(times, targetTime));
    },
    [times]
  );

  const handleTimelineClick = useCallback(
    (event: Readonly<PlotMouseEvent>) => {
      const point = event.points?.[0];
      if (point?.x === undefined) return;
      seekToTime(Number(point.x));
    },
    [seekToTime]
  );

  const plotScrubProps = {
    onClick: handleTimelineClick
  };

  const updateCalibration = (axis: keyof CalibrationOffsets, value: number) => {
    setCalibration((current) => ({ ...current, [axis]: value }));
  };

  return (
    <article className="watch-face-panel">
      <h4>Watch Position</h4>
      <p className="movement-copy">
        Scrub the timeline or click a chart to move through the swing. The vertical line marks the
        current frame shown on the 3D watch model.
      </p>

      <div className="watch-face-stage">
        <div className="watch-face-perspective">
          <div
            className="watch-face-body"
            style={{
              transform: `rotateY(${displayRollDeg}deg) rotateX(${displayPitchDeg}deg) rotateZ(${displayYawDeg}deg)`
            }}
          >
            <svg viewBox="0 0 200 240" className="watch-face-svg" aria-hidden="true">
              <rect x="24" y="8" width="152" height="224" rx="36" fill="#2b2b2e" />
              <rect x="176" y="98" width="10" height="44" rx="3" fill="#55565a" />
              <rect x="36" y="24" width="128" height="192" rx="28" fill="#0b0b0d" stroke="#3a3a3c" strokeWidth="2" />
              <circle cx="100" cy="56" r="5" fill="#ff6b4a" />
              <line x1="100" y1="120" x2="100" y2="72" stroke="#8ab4ff" strokeWidth="4" strokeLinecap="round" />
              <circle cx="100" cy="120" r="6" fill="#43a047" />
              <text x="100" y="196" textAnchor="middle" fill="#8e8e93" fontSize="12" fontFamily="Inter, sans-serif">
                12
              </text>
            </svg>
          </div>
        </div>

        <div className="watch-face-readout">
          <div>
            <span className="watch-face-label">Time</span>
            <strong>{currentTime.toFixed(2)}s</strong>
          </div>
          <div>
            <span className="watch-face-label">Baseline</span>
            <strong>{referenceTime.toFixed(2)}s</strong>
          </div>
          <div>
            <span className="watch-face-label">Pitch Δ</span>
            <strong>{toDegrees(deltaPitch).toFixed(1)}°</strong>
          </div>
          <div>
            <span className="watch-face-label">Roll Δ</span>
            <strong>{toDegrees(deltaRoll).toFixed(1)}°</strong>
          </div>
          <div>
            <span className="watch-face-label">Yaw Δ</span>
            <strong>{toDegrees(deltaYaw).toFixed(1)}°</strong>
          </div>
          <div>
            <span className="watch-face-label">At baseline</span>
            <strong>{atReferenceFrame ? "Yes" : "No"}</strong>
          </div>
        </div>
      </div>

      {times.length >= 2 ? (
        <div className="watch-face-timeline-charts">
          <Plot
            data={[
              {
                x: times,
                y: deltaPitchSeries,
                type: "scatter",
                mode: "lines",
                name: "Pitch Δ",
                line: { color: "#fb8c00", width: 2 }
              },
              {
                x: times,
                y: deltaRollSeries,
                type: "scatter",
                mode: "lines",
                name: "Roll Δ",
                line: { color: "#1e88e5", width: 2 }
              },
              {
                x: times,
                y: deltaYawSeries,
                type: "scatter",
                mode: "lines",
                name: "Yaw Δ",
                line: { color: "#8e24aa", width: 2 }
              }
            ]}
            layout={{
              title: "Watch Position Timeline",
              xaxis: { title: "Seconds" },
              yaxis: { title: "Degrees from baseline", range: timelineYRange },
              shapes: timelineShapes,
              margin: { t: 48, r: 20, b: 48, l: 56 },
              height: 260,
              legend: { orientation: "h", y: -0.25 },
              hovermode: "x unified"
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
            {...plotScrubProps}
          />

          <Plot
            data={[
              {
                x: times,
                y: deltaPitchSeries,
                type: "scatter",
                mode: "lines",
                name: "Wrist flexion",
                line: { color: "#fb8c00", width: 3 },
                fill: "tozeroy",
                fillcolor: "rgba(251, 140, 0, 0.12)"
              }
            ]}
            layout={{
              title: "Wrist Up / Down (Pitch)",
              xaxis: { title: "Seconds" },
              yaxis: {
                title: "Degrees from baseline",
                range: pitchYRange,
                zeroline: true,
                zerolinecolor: "#9ca3af"
              },
              shapes: pitchShapes,
              annotations: [
                {
                  x: 0.01,
                  y: 0.98,
                  xref: "paper",
                  yref: "paper",
                  text: "↑ face tilts up · ↓ face tilts down",
                  showarrow: false,
                  font: { size: 11, color: "#6b7280" },
                  xanchor: "left",
                  yanchor: "top"
                }
              ],
              margin: { t: 48, r: 20, b: 48, l: 56 },
              height: 260,
              showlegend: false,
              hovermode: "x"
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
            {...plotScrubProps}
          />
        </div>
      ) : (
        <p className="watch-face-timeline-empty">Not enough samples to render the position timeline.</p>
      )}

      <section className="watch-face-calibration-panel">
        <h5>Face angle calibration</h5>
        <p className="watch-face-calibration-copy">
          At the baseline moment, sensor deltas are zero — only the dial offsets move the face. Away
          from baseline, sensor motion and dial offsets combine.
        </p>
        <div className="watch-face-dials">
          <CalibrationDial
            label="Pitch offset"
            hint="Tips the face toward or away from you"
            value={calibration.pitchDeg}
            min={-180}
            max={180}
            onChange={(value) => updateCalibration("pitchDeg", value)}
          />
          <CalibrationDial
            label="Roll offset"
            hint="Tilts the face left or right on your wrist"
            value={calibration.rollDeg}
            min={-180}
            max={180}
            onChange={(value) => updateCalibration("rollDeg", value)}
          />
          <CalibrationDial
            label="Yaw offset"
            hint="Spins the face clockwise around the screen normal"
            value={calibration.yawDeg}
            min={-180}
            max={180}
            onChange={(value) => updateCalibration("yawDeg", value)}
          />
        </div>
      </section>

      {showMarkerHint && nearestMarker && (
        <p className="watch-face-marker-hint">
          Near event: <strong>{markerLabel(nearestMarker.type)}</strong> at{" "}
          {nearestMarker.time.toFixed(2)}s
        </p>
      )}

      <div className="watch-face-controls">
        <div className="watch-face-timeline-labels">
          <span>{(times[0] ?? 0).toFixed(2)}s</span>
          <strong>{currentTime.toFixed(2)}s</strong>
          <span>{(times[maxIndex] ?? 0).toFixed(2)}s</span>
        </div>
        <input
          type="range"
          min={0}
          max={maxIndex}
          step={1}
          value={frameIndex}
          onChange={(event) => {
            setPlaying(false);
            setFrameIndex(Number(event.target.value));
          }}
          aria-label="Swing playback position"
        />
        <div className="watch-face-buttons">
          <button
            type="button"
            onClick={() => {
              playbackStartIndex.current = frameIndex;
              setPlaying((value) => !value);
            }}
            disabled={times.length < 2}
          >
            {playing ? "Pause" : "Play"}
          </button>
          <button type="button" onClick={() => setReferenceIndex(frameIndex)}>
            Set baseline here
          </button>
          <button
            type="button"
            onClick={() => {
              setPlaying(false);
              setFrameIndex(referenceIndex);
            }}
          >
            Go to baseline
          </button>
          <button
            type="button"
            onClick={() => {
              setReferenceIndex(addressIndex);
              setCalibration(DEFAULT_CALIBRATION);
              setPlaying(false);
              setFrameIndex(addressIndex);
            }}
          >
            Reset all
          </button>
        </div>
      </div>
    </article>
  );
}
