export type SummaryResponse = {
  swings: number;
  avg_rating: number | null;
  avg_tempo_ratio: number | null;
  avg_peak_rotational_velocity: number | null;
  clubs: string[];
  ratings: number[];
};

export type RecordsResponse = {
  count: number;
  items: Record<string, string | number | null>[];
};

export type MovementSwingSummary = {
  id: string;
  club: string | null;
  date: string | null;
  rating: number | null;
  sample_count: number;
  duration_seconds: number;
};

export type MovementSwingsResponse = {
  count: number;
  items: MovementSwingSummary[];
};

export type PhaseMarker = {
  type: string;
  time: number;
  confidence?: number;
  source?: string;
};

export type PhaseMetrics = {
  backswing_duration_seconds?: number | null;
  downswing_duration_seconds?: number | null;
  transition_ratio?: number | null;
};

export type MovementDetail = {
  id: string;
  club: string | null;
  date: string | null;
  rating: number | null;
  sample_count: number;
  duration_seconds: number;
  series: {
    times: number[];
    accel_mag: number[];
    gyro_mag: number[];
    pitch: number[];
    roll: number[];
    yaw: number[];
  };
  event_markers: Array<{ type: string; time: number; source?: string }>;
  phase_markers: PhaseMarker[];
  recommendations: string[];
  follow_through: FollowThroughMetrics | null;
  swing_mode?: string;
  fault_flags?: string[];
  phase_metrics?: PhaseMetrics;
  phase_chain_complete?: boolean;
  analysis_version?: string;
};

export type FollowThroughMetrics = {
  window_start?: string | null;
  start_time: number;
  end_time: number;
  roll_deg: number;
  yaw_deg: number;
  pitch_deg: number;
  rotation_deg: number;
  direction_deg: number;
  direction_label: string;
  path: {
    times: number[];
    roll_deg: number[];
    yaw_deg: number[];
    pitch_deg: number[];
  };
};
