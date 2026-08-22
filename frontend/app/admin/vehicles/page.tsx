"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { Customer, Vehicle } from "@/types";

export default function AdminVehiclesPage() {
  const [rows, setRows] = useState<(Vehicle & { customer_name?: string })[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [vehicles, customers] = await Promise.all([
          api.listVehicles(200),
          api.listCustomers({ limit: 500 }),
        ]);
        if (cancelled) return;
        const byId = new Map<string, Customer>(customers.map((c) => [c.id, c]));
        setRows(
          vehicles.map((v) => ({
            ...v,
            customer_name: byId.get(v.customer_id)?.name,
          })),
        );
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Failed to load vehicles");
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
      <h1 className="font-display text-2xl font-bold">Vehicles</h1>
      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!loading && rows.length === 0 && <p className="text-sm text-muted-foreground">No vehicles yet.</p>}
      <div className="overflow-x-auto rounded-xl border border-border bg-white">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-foam text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left">Customer</th>
              <th className="px-3 py-2 text-left">Vehicle</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Registration</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b last:border-0">
                <td className="px-3 py-2">{row.customer_name ?? row.customer_id.slice(0, 8)}</td>
                <td className="px-3 py-2 font-medium">
                  {row.make} {row.model}
                </td>
                <td className="px-3 py-2 capitalize">{row.vehicle_type}</td>
                <td className="px-3 py-2">{row.registration_number ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
