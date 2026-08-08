// Sheet 04: done points above, prioritized Up Next below — Blocked cards always
// shown, uncapped, tagged with how many days they've sat there. "Up next" only
// makes sense for the live "today" view — history ranges show what got done.
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

type DonePoint = { card: string; summary: string; impact: string; resolved: string };
type TomorrowPoint = { card: string; priority: string; blocked_days?: number };

type DayShape = {
  provisional: boolean;
  date: string;
  done_points: DonePoint[];
  tomorrow_points: TomorrowPoint[];
  minutes_worked: number;
  efficiency_score: number;
};
type HistoryShape = {
  total_minutes: number;
  days: { date: string; minutes_worked: number; efficiency_score: number; done_points: DonePoint[] }[];
};

const RANGES = [
  { key: "today", label: "Today" },
  { key: "yesterday", label: "Yesterday" },
  { key: "week", label: "7 days" },
  { key: "month", label: "1 month" },
] as const;
type RangeKey = (typeof RANGES)[number]["key"];

function formatDay(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

export function TodayPage() {
  const { slug = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const range = (params.get("range") as RangeKey) || "today";
  const isSingleDay = range === "today" || range === "yesterday";

  const { data, isLoading } = useQuery<DayShape | HistoryShape>({
    queryKey: ["digest", slug, range],
    queryFn: () => api.getDigest(slug, range) as Promise<DayShape | HistoryShape>,
  });

  return (
    <div className="today-page">
      <div className="page-heading">
        <h1>Activity</h1>
        {isSingleDay && (data as DayShape)?.provisional && (
          <span className="badge">live — locks in at 23:59</span>
        )}
      </div>

      <div className="range-toggle">
        {RANGES.map((r) => (
          <button key={r.key} className={r.key === range ? "active" : ""} onClick={() => setParams({ range: r.key })}>
            {r.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="loading">Loading&hellip;</p>}

      {!isLoading && isSingleDay && <SingleDayView data={data as DayShape} />}
      {!isLoading && !isSingleDay && <HistoryView data={data as HistoryShape} />}
    </div>
  );
}

function DoneList({ points }: { points: DonePoint[] }) {
  if (points.length === 0) return <p className="empty">Nothing logged.</p>;
  return (
    <ul className="done-list">
      {points.map((p, i) => (
        <li key={i}>
          <div className="done-item-main">
            <strong>{p.card}</strong>
            <p>{p.summary}</p>
          </div>
          {p.impact && <em className="done-item-impact">{p.impact}</em>}
        </li>
      ))}
    </ul>
  );
}

function SingleDayView({ data }: { data: DayShape }) {
  return (
    <>
      <div className="stat-row">
        <div className="stat">
          <span className="stat-value">{data.minutes_worked}</span>
          <span className="stat-label">minutes worked</span>
        </div>
        <div className="stat">
          <span className="stat-value">{data.efficiency_score}</span>
          <span className="stat-label">efficiency</span>
        </div>
      </div>

      <section>
        <h2>Done</h2>
        <DoneList points={data.done_points} />
      </section>

      {data.tomorrow_points.length > 0 && (
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
      )}
    </>
  );
}

function HistoryView({ data }: { data: HistoryShape }) {
  const activeDays = data.days.filter((d) => d.done_points.length > 0);

  return (
    <>
      <div className="stat-row">
        <div className="stat">
          <span className="stat-value">{data.total_minutes}</span>
          <span className="stat-label">minutes worked</span>
        </div>
      </div>

      {activeDays.length === 0 && <p className="empty">Nothing logged in this period yet.</p>}

      {activeDays.map((d) => (
        <section key={d.date}>
          <h2>
            {formatDay(d.date)} <span className="chip">{d.minutes_worked}m · eff {d.efficiency_score}</span>
          </h2>
          <DoneList points={d.done_points} />
        </section>
      ))}
    </>
  );
}
