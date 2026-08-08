import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type CardUpdate } from "../api/client";
import type { Card } from "./CardItem";

const PRIORITY_LABEL: Record<Card["priority"], string> = { high: "High", medium: "Med", low: "Low" };
const RESOLVED_LABEL: Record<string, string> = { done: "Done", partial: "Partial progress", blocked: "Blocked" };

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

export function CardDetailPanel({
  projectSlug,
  card,
  role,
  onClose,
}: {
  projectSlug: string;
  card: Card;
  role: string;
  onClose: () => void;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const { data: updates, isLoading } = useQuery<CardUpdate[]>({
    queryKey: ["card-updates", projectSlug, card.id],
    queryFn: () => api.getCardUpdates(projectSlug, card.id),
  });

  const blockedDays = card.blocked_since
    ? Math.floor((Date.now() - new Date(card.blocked_since).getTime()) / 86_400_000)
    : null;

  return (
    <div className="card-detail-backdrop" onClick={onClose}>
      <aside className="card-detail-panel" onClick={(e) => e.stopPropagation()} data-role={role}>
        <header className="card-detail-header">
          <span className={`chip status-chip status-${role}`}>{role.replace("_", " ")}</span>
          <button className="card-detail-close" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </header>

        <h2 className="card-detail-title">{card.title}</h2>

        <div className="card-meta">
          <span className={`chip priority-${card.priority}`}>{PRIORITY_LABEL[card.priority]}</span>
          <span className="chip">{card.complexity}</span>
          {blockedDays !== null && <span className="chip chip-warn">blocked {blockedDays}d</span>}
        </div>

        <section className="card-detail-body">
          <h3>Activity</h3>
          {isLoading && <p className="loading">Loading&hellip;</p>}
          {!isLoading && updates?.length === 0 && (
            <p className="empty">Nothing logged on this card yet.</p>
          )}
          {!isLoading && updates && updates.length > 0 && (
            <ul className="update-timeline">
              {updates.map((u) => (
                <li key={u.id} className="update-entry">
                  <div className="update-entry-header">
                    <span className={`chip status-chip status-${u.resolved}`}>
                      {RESOLVED_LABEL[u.resolved] ?? u.resolved}
                    </span>
                    <span className="update-duration">{formatDuration(u.duration_minutes)}</span>
                    <span className="update-when">{formatWhen(u.created_at)}</span>
                  </div>
                  <p className="update-summary">{u.summary}</p>
                  {u.impact && <p className="update-impact">{u.impact}</p>}
                  {u.commit_hash && (
                    <code className={`update-commit ${u.commit_landed ? "landed" : ""}`}>
                      {u.commit_hash} {u.commit_landed ? "· landed" : "· not landed yet"}
                    </code>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </aside>
    </div>
  );
}
