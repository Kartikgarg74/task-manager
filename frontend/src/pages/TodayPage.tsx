// Sheet 04: done points above, prioritized Up Next below — Blocked cards always
// shown, uncapped, tagged with how many days they've sat there.
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

type DonePoint = { card: string; summary: string; impact: string; resolved: string };
type TomorrowPoint = { card: string; priority: string; blocked_days?: number };
type DigestResponse = {
  provisional: boolean;
  done_points: DonePoint[];
  tomorrow_points: TomorrowPoint[];
  minutes_worked: number;
  efficiency_score: number;
};

export function TodayPage() {
  const { slug = "" } = useParams();
  const { data, isLoading } = useQuery<DigestResponse>({
    queryKey: ["digest", slug],
    queryFn: () => api.getDigest(slug, "today") as Promise<DigestResponse>,
  });

  if (isLoading || !data) return <p className="loading">Loading&hellip;</p>;

  return (
    <div className="today-page">
      <h1>Today {data.provisional && <span className="badge">live — locks in at 23:59</span>}</h1>

      <section>
        <h2>Done today</h2>
        {data.done_points.length === 0 && <p className="empty">Nothing logged yet.</p>}
        <ul className="done-list">
          {data.done_points.map((p, i) => (
            <li key={i}>
              <strong>{p.card}</strong> — {p.summary}
              {p.impact && <em> ({p.impact})</em>}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Up next</h2>
        <ul className="up-next-list">
          {data.tomorrow_points.map((p, i) => (
            <li key={i} className={p.blocked_days !== undefined ? "blocked" : ""}>
              {p.card} <span className="chip">{p.priority}</span>
              {p.blocked_days !== undefined && (
                <span className="chip chip-warn">blocked {p.blocked_days}d — still?</span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
