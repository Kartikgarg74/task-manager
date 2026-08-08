// Sheet 01: the web app's own direct write path to the FastAPI backend —
// no MCP involved, device_id left null server-side (see backend/app/routers/projects.py).

const API_URL = import.meta.env.VITE_API_URL as string;

export type CardUpdate = {
  id: string;
  resolved: string;
  duration_minutes: number;
  summary: string;
  impact: string;
  commit_hash: string | null;
  commit_landed: boolean;
  created_at: string;
  edited_at: string | null;
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeader(): Record<string, string> {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listProjects: () => request<{ slug: string; name: string }[]>("/api/projects"),

  createProject: (name: string) =>
    request<{ slug: string; name: string; created: boolean }>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  getBoard: (slug: string) => request(`/api/projects/${slug}/board`),

  createCard: (slug: string, title: string, priority = "medium") =>
    request(`/api/projects/${slug}/cards`, {
      method: "POST",
      body: JSON.stringify({ title, priority }),
    }),

  moveCard: (slug: string, cardId: string, targetRole: string) =>
    request(`/api/projects/${slug}/cards/${cardId}/move`, {
      method: "PATCH",
      body: JSON.stringify({ target_role: targetRole }),
    }),

  logUpdate: (
    slug: string,
    cardId: string,
    body: { resolved: string; duration_minutes: number; summary: string; impact?: string },
  ) =>
    request(`/api/projects/${slug}/cards/${cardId}/updates`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getCardUpdates: (slug: string, cardId: string) =>
    request<CardUpdate[]>(`/api/projects/${slug}/cards/${cardId}/updates`),

  getDigest: (slug: string, range: "today" | "yesterday" | "week" | "month" = "today") =>
    request(`/api/projects/${slug}/digest?range=${range}`),

  getOverview: (range: "today" | "yesterday" | "week" | "month" = "today") =>
    request(`/api/overview?range=${range}`),

  listDevices: () => request("/api/devices"),
  createDevice: (label: string) =>
    request<{ id: string; label: string; token: string }>("/api/devices", {
      method: "POST",
      body: JSON.stringify({ label }),
    }),
  revokeDevice: (id: string) => request(`/api/devices/${id}`, { method: "DELETE" }),
};

export function wsUrl(slug: string): string {
  return `${API_URL.replace(/^http/, "ws")}/api/projects/${slug}/ws`;
}
