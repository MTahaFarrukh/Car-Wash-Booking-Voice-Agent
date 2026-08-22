"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { Service } from "@/types";

export default function AdminServicesPage() {
  const [rows, setRows] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.listServices(false);
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Failed to load services");
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
      <h1 className="font-display text-2xl font-bold">Services</h1>
      <p className="text-sm text-muted-foreground">Live catalog from the database — not hardcoded.</p>
      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!loading && rows.length === 0 && <p className="text-sm text-muted-foreground">No services found.</p>}
      <div className="grid gap-3 md:grid-cols-2">
        {rows.map((service) => (
          <div key={service.id} className="rounded-xl border border-border bg-white p-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="font-display text-lg font-bold">{service.name}</h2>
              <span className="text-xs uppercase text-muted-foreground">
                {service.active ? "Active" : "Inactive"}
              </span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{service.description}</p>
            <p className="mt-3 text-sm">
              {service.duration_minutes} min · {String(service.price)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
