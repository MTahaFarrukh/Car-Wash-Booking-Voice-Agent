"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { WhatsAppActivity } from "@/types";

export default function AdminWhatsAppPage() {
  const [rows, setRows] = useState<WhatsAppActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.adminWhatsAppActivity(100);
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Failed to load WhatsApp activity");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl font-bold">WhatsApp</h1>
      <p className="text-sm text-muted-foreground">
        Processed reply log from the Baileys bridge (no secrets shown).
      </p>
      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!loading && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">No WhatsApp activity stored yet.</p>
      )}
      <div className="space-y-3">
        {rows.map((row) => (
          <article key={row.id} className="rounded-xl border border-border bg-white p-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>From {row.sender_id}</span>
              <span>{new Date(row.created_at).toLocaleString()}</span>
            </div>
            <p className="mt-2 whitespace-pre-wrap text-ink">{row.response_message}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
