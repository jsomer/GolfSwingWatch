import { useEffect, useMemo, useRef, useState } from "react";

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

  const startMarker = eventMarkers.find((marker) => marker.type === "start");
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
  if (type === "followThrough") return "Follow-through";
  return type.charAt(0).toUpperCase() + type.slice(1);
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

    let index = playbackStartIndex.current;
    let lastTick = performance.now();
    let raf = 0;

    const step = (now: number) => {
      const elapsedSeconds = (now - lastTick) / 1000;
      lastTick = now;
      const currentTime = times[index] ?? 0;
      const targetTime = currentTime + elapsedSeconds;

      while (index < maxIndex && (times[index + 1] ?? 0) <= targetTime) {
        index += 1;
      }

      if (index >= maxIndex) {
        setPlaying(false);
        setFrameIndex(maxIndex);
        return;
      }

      setFrameIndex(index);
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

  const updateCalibration = (axis: keyof CalibrationOffsets, value: number) => {
    setCalibration((current) => ({ ...current, [axis]: value }));
  };

  return (
    <article className="watch-face-panel">
      <h4>Watch Position</h4>
      <p className="movement-copy">
        Scrub to a moment where you know how the watch face is oriented (address is a good choice),
        set that as the baseline, then adjust the dials until the model matches. The face updates live
        as you move through the swing.
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
        <input
          type="range"
          min={0}
          max={maxIndex}
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
