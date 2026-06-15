import { useCallback, useEffect, useState } from "react";
import { fetchPatterns } from "./api";
import type { PatternReport } from "./types";

type PatternInspectorProps = {
  selectedClubs: string[];
  selectedRatings: number[];
};

export function PatternInspector({ selectedClubs, selectedRatings }: PatternInspectorProps) {
  const [report, setReport] = useState<PatternReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [llmLoading, setLlmLoading] = useState(false);

  const loadReport = useCallback(
    async (withLlm: boolean) => {
      if (withLlm) {
        setLlmLoading(true);
      } else {
        setLoading(true);
      }
      setError(null);
      try {
        const response = await fetchPatterns(
          {
            clubs: selectedClubs,
            ratings: selectedRatings
          },
          { llm: withLlm }
        );
        setReport((current) =>
          withLlm
            ? {
                ...response,
                patterns: current?.patterns ?? response.patterns,
                markdown: current?.markdown ?? response.markdown
              }
            : response
        );
        if (withLlm && response.llm_error) {
          setError(response.llm_error);
        }
      } catch (err) {
        if (!withLlm) {
          setReport(null);
        }
        setError(err instanceof Error ? err.message : "Failed to load pattern report");
      } finally {
        if (withLlm) {
          setLlmLoading(false);
        } else {
          setLoading(false);
        }
      }
    },
    [selectedClubs, selectedRatings]
  );

  useEffect(() => {
    void loadReport(false);
  }, [loadReport]);

  return (
    <section className="pattern-inspector">
      <div className="pattern-header">
        <div>
          <h3>Pattern Inspector</h3>
          <p className="movement-copy">
            Compares low-rated vs high-rated swings using fault flags and phase metrics. Optional
            AI summary cites the computed stats below — not generic tips.
          </p>
        </div>
        <button
          type="button"
          className="pattern-llm-button"
          disabled={loading || llmLoading || !report}
          onClick={() => void loadReport(true)}
        >
          {llmLoading ? "Generating AI summary..." : "Generate AI summary"}
        </button>
      </div>

      {loading && <p>Analyzing swing cohorts...</p>}
      {error && <p className="error">{error}</p>}

      {report && (
        <>
          <div className="pattern-stats">
            <span>{report.swing_count} swings</span>
            <span>{report.low_rated_count} low-rated</span>
            <span>{report.high_rated_count} high-rated</span>
            {report.practice.practice_pct != null && (
              <span>{Math.round(report.practice.practice_pct * 100)}% practice mode</span>
            )}
          </div>

          {report.llm_narrative && (
            <div className="pattern-llm-narrative">
              <h4>AI Summary{report.llm_model ? ` (${report.llm_model})` : ""}</h4>
              {report.llm_narrative.split("\n").map((paragraph) =>
                paragraph.trim() ? <p key={paragraph.slice(0, 40)}>{paragraph}</p> : null
              )}
            </div>
          )}

          {report.patterns.length === 0 ? (
            <p className="pattern-empty">
              No strong cohort patterns in the current filter. Record more swings with varied
              ratings, or add flaw tags on iPhone.
            </p>
          ) : (
            <ol className="pattern-list">
              {report.patterns.map((pattern) => (
                <li key={`${pattern.kind}-${pattern.title}`}>
                  <strong>{pattern.title}</strong>
                  <p>{pattern.summary}</p>
                  {pattern.affected_swings && pattern.affected_swings.length > 0 && (
                    <ul>
                      {pattern.affected_swings.slice(0, 5).map((swing) => (
                        <li key={swing.id}>
                          {swing.club} · {String(swing.date).slice(0, 10)} · rating{" "}
                          {swing.rating ?? "?"}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}
