"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useAdminNotifications } from "@/lib/admin-notifications";
import type { BookingListItem, BookingSource, BookingStatus } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function SourceBadge({ source }: { source: BookingSource }) {
  const label = source === "dashboard" ? "Web" : source === "voice" ? "Voice" : "WhatsApp";
  const variant = source === "voice" ? "voice" : source === "whatsapp" ? "whatsapp" : "web";
  return <Badge variant={variant}>{label}</Badge>;
}

export default function AdminBookingsPage() {
  const { acknowledge, busyId: ackBusyId, refresh: refreshNotifications } = useAdminNotifications();
  const [rows, setRows] = useState<BookingListItem[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<BookingStatus | "">("");
  const [source, setSource] = useState<BookingSource | "">("");
  const [date, setDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.adminBookings({
          limit: 500,
        });
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Failed to load bookings");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.adminBookings({
        q: q || undefined,
        status: status || undefined,
        source: source || undefined,
        booking_date: date || undefined,
        limit: 500,
      });
      setRows(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load bookings");
    } finally {
      setLoading(false);
    }
  }
  async function accept(id: string) {
    setBusyId(id);
    try {
      await acknowledge(id);
      await load();
      await refreshNotifications();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Accept failed");
    } finally {
      setBusyId(null);
    }
  }

  async function cancel(id: string) {
    setBusyId(id);
    try {
      await api.cancelBooking(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Cancel failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-ink">Bookings</h1>
        <p className="mt-1 text-muted-foreground">All channels — web, voice, and WhatsApp.</p>
      </div>
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="font-display text-lg">Filters</CardTitle>
          <CardDescription>Search and narrow the list</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name or phone"
          className="max-w-xs"
        />
        <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="max-w-[11rem]" />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as BookingStatus | "")}
          className="h-10 rounded-lg border border-input bg-background px-3 text-sm"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="confirmed">Confirmed</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select
          value={source}
          onChange={(e) => setSource(e.target.value as BookingSource | "")}
          className="h-10 rounded-lg border border-input bg-background px-3 text-sm"
        >
          <option value="">All sources</option>
          <option value="dashboard">Web</option>
          <option value="voice">Voice</option>
          <option value="whatsapp">WhatsApp</option>
        </select>
        <Button onClick={() => void load()}>Apply</Button>
        </CardContent>
      </Card>
      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!loading && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">No bookings match these filters.</p>
      )}
      <div className="overflow-x-auto rounded-2xl border border-border bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b bg-foam/80 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            <tr>
              <th className="px-3 py-2">Customer</th>
              <th className="px-3 py-2">Vehicle</th>
              <th className="px-3 py-2">Service</th>
              <th className="px-3 py-2">When</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const needsReview = !row.admin_acknowledged_at && row.status !== "cancelled";
              return (
              <tr
                key={row.id}
                className={cn("border-b last:border-0", needsReview && "bg-amber-50/80")}
              >
                <td className="px-3 py-2">
                  <div className="font-medium">{row.customer_name ?? "—"}</div>
                  <div className="text-xs text-muted-foreground">{row.customer_phone}</div>
                </td>
                <td className="px-3 py-2">{row.vehicle_label ?? "—"}</td>
                <td className="px-3 py-2">{row.service_name ?? "—"}</td>
                <td className="px-3 py-2">
                  {row.booking_date} {String(row.booking_time).slice(0, 5)}
                </td>
                <td className="px-3 py-2 capitalize">{row.status}</td>
                <td className="px-3 py-2">
                  <SourceBadge source={row.source} />
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-2">
                    {needsReview && (
                      <Button
                        size="sm"
                        disabled={busyId === row.id || ackBusyId === row.id}
                        onClick={() => void accept(row.id)}
                      >
                        Accept
                      </Button>
                    )}
                    {row.status !== "cancelled" && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busyId === row.id}
                        onClick={() => void cancel(row.id)}
                      >
                        Cancel
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
