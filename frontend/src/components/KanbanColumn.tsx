import { CardItem, type Card } from "./CardItem";

export function KanbanColumn({
  name,
  role,
  cards,
  onAdvance,
  onOpen,
}: {
  name: string;
  role: string;
  cards: Card[];
  onAdvance: (cardId: string, targetRole: string) => void;
  onOpen: (cardId: string) => void;
}) {
  return (
    <div className="column">
      <h3>
        {name} <span className="column-count">{cards.length}</span>
      </h3>
      <div className="column-body">
        {cards.map((card) => (
          <CardItem
            key={card.id}
            card={card}
            role={role}
            onAdvance={(targetRole) => onAdvance(card.id, targetRole)}
            onOpen={() => onOpen(card.id)}
          />
        ))}
        {cards.length === 0 && <p className="empty">Nothing here</p>}
      </div>
    </div>
  );
}
