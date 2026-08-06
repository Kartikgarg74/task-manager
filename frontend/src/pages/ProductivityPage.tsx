// Sheet 05: today's score is live/provisional; week/month read the locked
// digests history and chart one point per day.
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

type TodayShape = {
  minutes_worked: number;
  efficiency_score: number;
  device_breakdown: { device: string; minutes: number }[];
};
type HistoryShape = {
  days: { date: string; minutes_worked: number; efficiency_score: number }[];
  total_minutes: number;
};

export function ProductivityPage() {
  const { slug = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const range = (params.get("range") as "today" | "week" | "month") || "today";

  const { data, isLoading } = useQuery({
    queryKey: ["productivity", slug, range],
    queryFn: () => api.getDigest(slug, range),
  });

  if (isLoading || !data) return <p className="loading">Loading&hellip;</p>;

  return (
    <div className="productivity-page">
      <h1>Productivity</h1>
      <div className="range-toggle">
        {(["today", "week", "month"] as const).map((r) => (
          <button key={r} className={r === range ? "active" : ""} onClick={() => setParams({ range: r })}>
            {r}
          </button>
        ))}
      </div>

      {range === "today" ? (
        <TodayView data={data as TodayShape} />
      ) : (
        <HistoryView data={data as HistoryShape} />
      )}
    </div>
  );
}

function TodayView({ data }: { data: TodayShape }) {
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
      <h2>By device</h2>
      <ul className="device-breakdown">
        {data.device_breakdown.map((d) => (
          <li key={d.device}>
            {d.device} — {d.minutes} min
          </li>
        ))}
      </ul>
    </>
  );
}

function HistoryView({ data }: { data: HistoryShape }) {
  return (
    <>
      <p className="stat-value">{data.total_minutes} minutes total</p>
      <table className="history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Minutes</th>
            <th>Efficiency</th>
          </tr>
        </thead>
        <tbody>
          {data.days.map((d) => (
            <tr key={d.date}>
              <td>{d.date}</td>
              <td>{d.minutes_worked}</td>
              <td>{d.efficiency_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
