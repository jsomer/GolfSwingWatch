import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { fetchRecords, fetchSummary } from "./api";
import { MovementExplorer } from "./MovementExplorer";
import type { RecordsResponse, SummaryResponse } from "./types";

const COLORS = ["#1e88e5", "#43a047", "#fb8c00", "#8e24aa", "#ef5350"];

const formatNumber = (value: number | null): string =>
  value === null || Number.isNaN(value) ? "n/a" : value.toFixed(2);

export function App() {
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [records, setRecords] = useState<RecordsResponse | null>(null);
  const [selectedClubs, setSelectedClubs] = useState<string[]>([]);
  const [selectedRatings, setSelectedRatings] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [summaryData, recordsData] = await Promise.all([
          fetchSummary({ clubs: selectedClubs, ratings: selectedRatings }),
          fetchRecords({ clubs: selectedClubs, ratings: selectedRatings }, 250)
        ]);
        if (!cancelled) {
          setSummary(summaryData);
          setRecords(recordsData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [selectedClubs, selectedRatings]);

  const clubSeries = useMemo(() => {
    if (!records?.items) return [];
    const grouped = new Map<string, { club: string; count: number; avgTempo: number; tempoCount: number }>();
    records.items.forEach((item) => {
      const club = String(item.club ?? "Unknown");
      const tempo = typeof item.tempo_ratio === "number" ? item.tempo_ratio : Number(item.tempo_ratio);
      if (!grouped.has(club)) {
        grouped.set(club, { club, count: 0, avgTempo: 0, tempoCount: 0 });
      }
      const entry = grouped.get(club)!;
      entry.count += 1;
      if (!Number.isNaN(tempo)) {
        entry.avgTempo += tempo;
        entry.tempoCount += 1;
      }
    });
    return [...grouped.values()].map((row) => ({
      club: row.club,
      swings: row.count,
      avgTempo: row.tempoCount ? row.avgTempo / row.tempoCount : 0
    }));
  }, [records]);

  const followThroughSeries = useMemo(() => {
    if (!records?.items) return [];
    return records.items
      .map((item) => {
        const rotation = Number(item.follow_through_rotation_deg);
        const roll = Number(item.follow_through_roll_deg);
        const yaw = Number(item.follow_through_yaw_deg);
        if (Number.isNaN(rotation)) return null;
        return {
          label: `${String(item.club ?? "?")} · ${String(item.date ?? "").slice(0, 10)}`,
          rotation,
          roll: Number.isNaN(roll) ? 0 : roll,
          yaw: Number.isNaN(yaw) ? 0 : yaw,
          direction: String(item.follow_through_direction_label ?? "")
        };
      })
      .filter((item): item is NonNullable<typeof item> => item !== null)
      .slice(0, 20);
  }, [records]);

  const avgFollowThroughRotation = useMemo(() => {
    if (!followThroughSeries.length) return null;
    const total = followThroughSeries.reduce((sum, item) => sum + item.rotation, 0);
    return total / followThroughSeries.length;
  }, [followThroughSeries]);

  const tempoTrend = useMemo(() => {
    if (!records?.items) return [];
    const grouped = new Map<string, { date: string; total: number; count: number }>();
    records.items.forEach((item) => {
      const date = String(item.date_only ?? "").slice(0, 10);
      const tempo = typeof item.tempo_ratio === "number" ? item.tempo_ratio : Number(item.tempo_ratio);
      if (!date || Number.isNaN(tempo)) return;
      if (!grouped.has(date)) {
        grouped.set(date, { date, total: 0, count: 0 });
      }
      const entry = grouped.get(date)!;
      entry.total += tempo;
      entry.count += 1;
    });
    return [...grouped.values()]
      .map((row) => ({ date: row.date, tempoRatio: row.total / row.count }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [records]);

  return (
    <main className="page">
      <header className="header">
        <h1>GolfSwingWatch Analysis Dashboard</h1>
        <p>Browser-first analytics UI powered by FastAPI + React.</p>
      </header>

      <section className="filters">
        <div>
          <label>Club Filter</label>
          <select
            multiple
            value={selectedClubs}
            onChange={(event) =>
              setSelectedClubs(Array.from(event.currentTarget.selectedOptions).map((opt) => opt.value))
            }
          >
            {(summary?.clubs ?? []).map((club) => (
              <option key={club} value={club}>
                {club}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Rating Filter</label>
          <select
            multiple
            value={selectedRatings.map(String)}
            onChange={(event) =>
              setSelectedRatings(
                Array.from(event.currentTarget.selectedOptions)
                  .map((opt) => Number(opt.value))
                  .filter((val) => !Number.isNaN(val))
              )
            }
          >
            {(summary?.ratings ?? []).map((rating) => (
              <option key={rating} value={rating}>
                {rating}
              </option>
            ))}
          </select>
        </div>
      </section>

      {error && <p className="error">{error}</p>}
      {loading && <p>Loading...</p>}

      <section className="kpis">
        <article>
          <h2>Swings</h2>
          <strong>{summary?.swings ?? 0}</strong>
        </article>
        <article>
          <h2>Avg Rating</h2>
          <strong>{formatNumber(summary?.avg_rating ?? null)}</strong>
        </article>
        <article>
          <h2>Avg Tempo Ratio</h2>
          <strong>{formatNumber(summary?.avg_tempo_ratio ?? null)}</strong>
        </article>
        <article>
          <h2>Avg Peak Rotation</h2>
          <strong>{formatNumber(summary?.avg_peak_rotational_velocity ?? null)}</strong>
        </article>
        <article>
          <h2>Avg Wrist Return</h2>
          <strong>{formatNumber(avgFollowThroughRotation)}°</strong>
        </article>
      </section>

      <section className="charts charts-three">
        <article>
          <h3>Swings by Club</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={clubSeries}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="club" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="swings">
                {clubSeries.map((_, index) => (
                  <Cell key={`bar-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article>
          <h3>Tempo Trend</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={tempoTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="tempoRatio" stroke="#1e88e5" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </article>

        <article>
          <h3>Wrist Return Rotation</h3>
          <p className="chart-copy">Net wrist rotation from impact through follow-through.</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={followThroughSeries}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" hide />
              <YAxis unit="°" />
              <Tooltip
                formatter={(value: number) => [`${value.toFixed(1)}°`, "Rotation"]}
                labelFormatter={(label) => String(label)}
              />
              <Bar dataKey="rotation" fill="#8e24aa" name="Rotation" />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </section>

      <MovementExplorer />

      <section className="records">
        <h3>Recent Filtered Records ({records?.count ?? 0})</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Club</th>
                <th>Rating</th>
                <th>Tempo</th>
                <th>Wrist Return</th>
                <th>Return Direction</th>
                <th>Peak Rotation</th>
              </tr>
            </thead>
            <tbody>
              {(records?.items ?? []).map((item, idx) => (
                <tr key={`${item.id ?? "row"}-${idx}`}>
                  <td>{String(item.id ?? "")}</td>
                  <td>{String(item.date ?? "")}</td>
                  <td>{String(item.club ?? "")}</td>
                  <td>{String(item.rating ?? "")}</td>
                  <td>{String(item.tempo_ratio ?? "")}</td>
                  <td>
                    {item.follow_through_rotation_deg != null
                      ? `${Number(item.follow_through_rotation_deg).toFixed(1)}°`
                      : ""}
                  </td>
                  <td>{String(item.follow_through_direction_label ?? "")}</td>
                  <td>{String(item.peak_rotational_velocity ?? "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
