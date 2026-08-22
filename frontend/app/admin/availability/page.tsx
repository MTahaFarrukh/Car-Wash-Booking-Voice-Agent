"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { AvailabilityResult, Service } from "@/types";
import { Button } from "@/components/ui/button";

export default function AdminAvailabilityPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [serviceId, setServiceId] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [requested, setRequested] = useState("");
  const [result, setResult] = useState<AvailabilityResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void api.listServices(true).then(setServices).catch(() => setServices([]));
  }, []);

  async function check() {
    if (!serviceId || !date) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await api.getAvailability(date, serviceId, requested || undefined));
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.detail : "Availability check failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl font-bold">Availability</h1>
      <p className="text-sm text-muted-foreground">Uses GET /api/availability — same engine as bookings.</p>
      <div className="flex flex-wrap gap-2">
        <select
          value={serviceId}
          onChange={(e) => setServiceId(e.target.value)}
          className="rounded-lg border border-input px-3 py-2 text-sm"
        >
          <option value="">Select service</option>
          {services.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-lg border border-input px-3 py-2 text-sm"
        />
        <input
          type="time"
          value={requested}
          onChange={(e) => setRequested(e.target.value)}
          className="rounded-lg border border-input px-3 py-2 text-sm"
        />
        <Button disabled={!serviceId || loading} onClick={() => void check()}>
          {loading ? "Checking…" : "Check"}
        </Button>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {result && (
        <div className="rounded-xl border border-border bg-white p-4 text-sm">
          <p>
            <strong>Available:</strong> {result.available ? "Yes" : "No"}
          </p>
          {result.message && <p className="mt-1 text-muted-foreground">{result.message}</p>}
          <p className="mt-3 font-semibold">Slots / alternatives</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(result.alternatives ?? []).map((slot) => (
              <span key={slot} className="rounded-md bg-foam px-2 py-1">
                {String(slot).slice(0, 5)}
              </span>
            ))}
            {(result.alternatives ?? []).length === 0 && (
              <span className="text-muted-foreground">None returned</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
