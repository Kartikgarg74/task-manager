type Card = {
  id: string;
  column_id: string;
  title: string;
  priority: "high" | "medium" | "low";
  complexity: "small" | "medium" | "large";
  blocked_since: string | null;
};

const PRIORITY_LABEL: Record<Card["priority"], string> = { high: "High", medium: "Med", low: "Low" };

export function CardItem({ card, onAdvance }: { card: Card; onAdvance: (role: string) => void }) {
  const blockedDays = card.blocked_since
    ? Math.floor((Date.now() - new Date(card.blocked_since).getTime()) / 86_400_000)
    : null;

  return (
    <div className="card">
      <p className="card-title">{card.title}</p>
      <div className="card-meta">
        <span className={`chip priority-${card.priority}`}>{PRIORITY_LABEL[card.priority]}</span>
        <span className="chip">{card.complexity}</span>
        {blockedDays !== null && <span className="chip chip-warn">blocked {blockedDays}d</span>}
      </div>
      <div className="card-actions">
        <button onClick={() => onAdvance("in_progress")}>&rarr; In Progress</button>
        <button onClick={() => onAdvance("blocked")}>&rarr; Blocked</button>
        <button onClick={() => onAdvance("done")}>&rarr; Done</button>
      </div>
    </div>
  );
}

export type { Card };
