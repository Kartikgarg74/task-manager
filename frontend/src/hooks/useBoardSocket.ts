// Sheet 01: the realtime replacement for Supabase's client-side subscription —
// any write, from any source (MCP or this same web app), shows up here.
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { wsUrl } from "../api/client";

export function useBoardSocket(slug: string) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const ws = new WebSocket(wsUrl(slug));
    ws.onmessage = () => {
      // Any board-changing event invalidates the board query — simplest correct
      // thing; a bigger board could diff message.type instead of refetching whole.
      queryClient.invalidateQueries({ queryKey: ["board", slug] });
    };
    return () => ws.close();
  }, [slug, queryClient]);
}
