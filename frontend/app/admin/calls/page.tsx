"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { CallLog } from "@/types";

export default function AdminCallsPage() {
  const [rows, setRows] = useState<CallLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.adminCallLogs({ limit: 100 });
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Failed to load call logs");
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
      <h1 className="font-display text-2xl font-bold">Calls</h1>
      <p className="text-sm text-muted-foreground">CallLog rows from VAPI / Uplift / Fake providers.</p>
      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!loading && rows.length === 0 && <p className="text-sm text-muted-foreground">No calls logged yet.</p>}
      <div className="overflow-x-auto rounded-xl border border-border bg-white">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-foam text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left">Call ID</th>
              <th className="px-3 py-2 text-left">Phone</th>
              <th className="px-3 py-2 text-left">Provider</th>
              <th className="px-3 py-2 text-left">Outcome</th>
              <th className="px-3 py-2 text-left">Duration</th>
              <th className="px-3 py-2 text-left">Booking</th>
              <th className="px-3 py-2 text-left">Started</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b last:border-0">
                <td className="px-3 py-2 font-mono text-xs">{row.call_id.slice(0, 14)}…</td>
                <td className="px-3 py-2">{row.phone ?? "—"}</td>
                <td className="px-3 py-2 uppercase">{row.provider ?? "—"}</td>
                <td className="px-3 py-2">{row.outcome}</td>
                <td className="px-3 py-2">
                  {row.duration_seconds != null ? `${row.duration_seconds}s` : "—"}
                </td>
                <td className="px-3 py-2 font-mono text-xs">
                  {row.booking_id ? `${row.booking_id.slice(0, 8)}…` : "—"}
                </td>
                <td className="px-3 py-2">{new Date(row.started_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
