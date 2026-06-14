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
  event_markers: Array<{ type: string; time: number }>;
};
