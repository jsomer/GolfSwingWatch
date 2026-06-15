export type SummaryResponse = {
  swings: number;
  avg_rating: number | null;
  avg_tempo_ratio: number | null;
  avg_peak_rotational_velocity: number | null;
  clubs: string[];
  ratings: number[];
};

export type PatternSwingBrief = {
  id: string;
  date: string;
  club: string;
  rating: number | null;
  tempo_ratio: number | null;
  fault_flags: string[];
};

export type PatternItem = {
  kind: "fault" | "metric";
  title: string;
  summary: string;
  fault?: string;
  metric?: string;
  low_prevalence?: number;
  high_prevalence?: number;
  low_average?: number;
  high_average?: number;
  delta_ratio?: number;
  affected_swings?: PatternSwingBrief[];
};

export type PatternReport = {
  analysis_version: string;
  swing_count: number;
  low_rated_count: number;
  high_rated_count: number;
  low_rating_threshold: number;
  high_rating_threshold: number;
  practice: {
    practice_count: number;
    full_count: number;
    practice_pct: number | null;
  };
  phase_chain: {
    complete_count: number;
    complete_pct: number | null;
  };
  low_rated_faults: Record<string, number>;
  high_rated_faults: Record<string, number>;
  patterns: PatternItem[];
  markdown: string;
  llm_narrative?: string | null;
  llm_error?: string | null;
  llm_model?: string | null;
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
