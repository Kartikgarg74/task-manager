// Sheet 06: same query the 9:30 AM email uses, rendered as a page. Minutes sum
// honestly across projects. Combined efficiency is computed once over every
// project's pooled updates (see backend/app/services/productivity.py) rather
// than averaged from each project's own score, which distorts the number.
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

type Overview = {
  total_minutes: number;
  combined_efficiency_score: number;
  projects: { project: string; minutes_worked?: number; efficiency_score?: number }[];
};

const RANGES = [
  { key: "today", label: "Today" },
  { key: "yesterday", label: "Yesterday" },
  { key: "week", label: "7 days" },
  { key: "month", label: "1 month" },
] as const;
type RangeKey = (typeof RANGES)[number]["key"];

export function OverviewPage() {
  const [params, setParams] = useSearchParams();
  const range = (params.get("range") as RangeKey) || "today";

  const { data, isLoading } = useQuery<Overview>({
    queryKey: ["overview", range],
    queryFn: () => api.getOverview(range) as Promise<Overview>,
  });

  return (
    <div className="overview-page">
      <h1>Overview</h1>
      <p className="page-subtitle">Combined across every project.</p>

      <div className="range-toggle">
        {RANGES.map((r) => (
          <button key={r.key} className={r.key === range ? "active" : ""} onClick={() => setParams({ range: r.key })}>
            {r.label}
          </button>
        ))}
      </div>

      {!isLoading && data && (
        <div className="stat-row">
          <div className="stat">
            <span className="stat-value">{data.total_minutes}</span>
            <span className="stat-label">minutes, every project</span>
          </div>
          <div className="stat">
            <span className="stat-value">{data.combined_efficiency_score}</span>
            <span className="stat-label">combined efficiency</span>
          </div>
        </div>
      )}

      <h2>By project</h2>
      <ul className="project-list">
        {data?.projects.map((p) => (
          <li key={p.project}>
            <Link to={`/projects/${p.project}`}>{p.project}</Link>
            {p.minutes_worked !== undefined && (
              <span className="chip">
                {p.minutes_worked}m &middot; eff {p.efficiency_score}
              </span>
            )}
          </li>
        ))}
        {data?.projects.length === 0 && <p className="empty">No projects yet — create one from the sidebar.</p>}
      </ul>
    </div>
  );
}
