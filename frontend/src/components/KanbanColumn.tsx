import { CardItem, type Card } from "./CardItem";

export function KanbanColumn({
  name,
  cards,
  onAdvance,
}: {
  name: string;
  cards: Card[];
  onAdvance: (cardId: string, targetRole: string) => void;
}) {
  return (
    <div className="column">
      <h3>
        {name} <span className="column-count">{cards.length}</span>
      </h3>
      <div className="column-body">
        {cards.map((card) => (
          <CardItem key={card.id} card={card} onAdvance={(role) => onAdvance(card.id, role)} />
        ))}
        {cards.length === 0 && <p className="empty">Nothing here</p>}
      </div>
    </div>
  );
}
