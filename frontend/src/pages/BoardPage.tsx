import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useBoardSocket } from "../hooks/useBoardSocket";
import { KanbanColumn } from "../components/KanbanColumn";
import type { Card } from "../components/CardItem";

type Board = {
  project: { slug: string; name: string } | null;
  columns: { id: string; name: string; role: string; position: number }[];
  cards: Card[];
};

export function BoardPage() {
  const { slug = "" } = useParams();
  const queryClient = useQueryClient();
  const [newTitle, setNewTitle] = useState("");
  useBoardSocket(slug);

  const { data: board, isLoading } = useQuery<Board>({
    queryKey: ["board", slug],
    queryFn: () => api.getBoard(slug) as Promise<Board>,
  });

  const createCard = useMutation({
    mutationFn: (title: string) => api.createCard(slug, title),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["board", slug] }),
  });

  const moveCard = useMutation({
    mutationFn: ({ cardId, targetRole }: { cardId: string; targetRole: string }) =>
      api.moveCard(slug, cardId, targetRole),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["board", slug] }),
  });

  function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    createCard.mutate(newTitle.trim());
    setNewTitle("");
  }

  if (isLoading || !board?.project) return <p className="loading">Loading&hellip;</p>;

  return (
    <div className="board-page">
      <header className="board-header">
        <h1>{board.project.name}</h1>
        <form onSubmit={onCreate}>
          <input
            placeholder="New card title&hellip;"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
          <button type="submit">Add card</button>
        </form>
      </header>

      <div className="board-columns">
        {board.columns.map((col) => (
          <KanbanColumn
            key={col.id}
            name={col.name}
            cards={board.cards.filter((c) => c.column_id === col.id)}
            onAdvance={(cardId, targetRole) => moveCard.mutate({ cardId, targetRole })}
          />
        ))}
      </div>
    </div>
  );
}
