type Card = {
  id: string;
  column_id: string;
  title: string;
  priority: "high" | "medium" | "low";
  complexity: "small" | "medium" | "large";
  blocked_since: string | null;
};

const PRIORITY_LABEL: Record<Card["priority"], string> = { high: "High", medium: "Med", low: "Low" };

const ACTIONS: { role: string; label: string; icon: string }[] = [
  { role: "in_progress", label: "In Progress", icon: "▶" },
  { role: "blocked", label: "Blocked", icon: "⏸" },
  { role: "done", label: "Done", icon: "✓" },
];

export function CardItem({
  card,
  role,
  onAdvance,
  onOpen,
}: {
  card: Card;
  role: string;
  onAdvance: (role: string) => void;
  onOpen: () => void;
}) {
  const blockedDays = card.blocked_since
    ? Math.floor((Date.now() - new Date(card.blocked_since).getTime()) / 86_400_000)
    : null;

  return (
    <div className="card" data-role={role} onClick={onOpen} role="button" tabIndex={0}>
      <p className="card-title">{card.title}</p>
      <div className="card-meta">
        <span className={`chip priority-${card.priority}`}>{PRIORITY_LABEL[card.priority]}</span>
        <span className="chip">{card.complexity}</span>
        {blockedDays !== null && <span className="chip chip-warn">blocked {blockedDays}d</span>}
      </div>
      <div className="card-actions">
        {ACTIONS.filter((a) => a.role !== role).map((a) => (
          <button
            key={a.role}
            className={`action-${a.role}`}
            onClick={(e) => {
              e.stopPropagation();
              onAdvance(a.role);
            }}
          >
            <span aria-hidden="true">{a.icon}</span> {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export type { Card };
