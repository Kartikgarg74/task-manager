// Sheet 02/03: device management — rename or revoke without touching any
// historical row that already used a device.
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

type Device = {
  id: string;
  label: string;
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
};

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function DevicesPage() {
  const [label, setLabel] = useState("");
  const [mintedToken, setMintedToken] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: devices } = useQuery<Device[]>({
    queryKey: ["devices"],
    queryFn: () => api.listDevices() as Promise<Device[]>,
  });

  const create = useMutation({
    mutationFn: (label: string) => api.createDevice(label),
    onSuccess: (device) => {
      setMintedToken((device as { token: string }).token);
      queryClient.invalidateQueries({ queryKey: ["devices"] });
    },
  });

  const revoke = useMutation({
    mutationFn: (id: string) => api.revokeDevice(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });

  function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!label.trim()) return;
    create.mutate(label.trim());
    setLabel("");
  }

  return (
    <div className="devices-page">
      <h1>Devices</h1>

      {mintedToken && (
        <div className="token-reveal">
          <p>
            Token for the new device — shown once, put it straight into that device's MCP config:
          </p>
          <code>{mintedToken}</code>
        </div>
      )}

      <ul className="device-list">
        {devices?.map((d) => (
          <li key={d.id}>
            <div className="device-main">
              <span className="device-label">{d.label}</span>
              <span className="device-meta">
                created {formatWhen(d.created_at)}
                {d.revoked_at
                  ? ` · revoked ${formatWhen(d.revoked_at)}`
                  : d.last_seen_at
                    ? ` · last seen ${formatWhen(d.last_seen_at)}`
                    : " · never used yet"}
              </span>
            </div>
            <span className={`chip status-chip status-${d.revoked_at ? "blocked" : d.last_seen_at ? "done" : "backlog"}`}>
              {d.revoked_at ? "revoked" : d.last_seen_at ? "active" : "unused"}
            </span>
            {!d.revoked_at && <button onClick={() => revoke.mutate(d.id)}>Revoke</button>}
          </li>
        ))}
      </ul>

      <form onSubmit={onCreate}>
        <input placeholder="Device label (e.g. phone)" value={label} onChange={(e) => setLabel(e.target.value)} />
        <button type="submit">Add device</button>
      </form>
    </div>
  );
}
