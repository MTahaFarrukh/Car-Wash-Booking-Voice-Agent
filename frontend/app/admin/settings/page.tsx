"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { AdminStatus, DbHealthResponse } from "@/types";

function StatusRow({
  title,
  connected,
  detail,
}: {
  title: string;
  connected: boolean;
  detail?: string | null;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-border bg-white px-4 py-3">
      <div>
        <p className="font-semibold text-ink">{title}</p>
        {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
      </div>
      <span
        className={
          connected
            ? "rounded-md bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-900"
            : "rounded-md bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-900"
        }
      >
        {connected ? "Connected" : "Not connected"}
      </span>
    </div>
  );
}

export default function AdminSettingsPage() {
  const [status, setStatus] = useState<AdminStatus | null>(null);
  const [db, setDb] = useState<DbHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, d] = await Promise.all([api.adminStatus(), api.healthDb()]);
        if (cancelled) return;
        setStatus(s);
        setDb(d);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Failed to load status");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl font-bold">Settings</h1>
      <p className="text-sm text-muted-foreground">
        Connection status only. API keys and secrets are never shown in the browser.
      </p>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!status && !error && <p className="text-sm text-muted-foreground">Loading…</p>}
      {status && (
        <div className="max-w-xl space-y-3">
          <StatusRow
            title="Database"
            connected={status.database.connected || db?.database === "connected"}
            detail={status.database.detail}
          />
          <StatusRow title={status.gemini.name} connected={status.gemini.connected} detail={status.gemini.detail} />
          <StatusRow
            title="WhatsApp"
            connected={status.whatsapp.connected}
            detail={status.whatsapp.detail}
          />
          <StatusRow
            title="Voice Provider"
            connected={status.voice.connected}
            detail={status.voice.detail?.toUpperCase()}
          />
          <p className="text-xs text-muted-foreground">Environment: {status.environment}</p>
        </div>
      )}
    </div>
  );
}
