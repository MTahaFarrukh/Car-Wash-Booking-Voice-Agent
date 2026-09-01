"use client";

import { useEffect, useState } from "react";
import { CalendarClock } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useAdminNotifications } from "@/lib/admin-notifications";
import type { BookingListItem, BookingSource, BookingStatus } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/sparkle/empty-state";
import { TableSkeleton } from "@/components/sparkle/skeleton";
import { cn } from "@/lib/utils";

function SourceBadge({ source }: { source: BookingSource }) {
  const label = source === "dashboard" ? "Web" : source === "voice" ? "Voice" : "WhatsApp";
  const variant = source === "voice" ? "voice" : source === "whatsapp" ? "whatsapp" : "web";
  return <Badge variant={variant}>{label}</Badge>;
}

function StatusBadge({ status }: { status: BookingStatus }) {
  const map: Record<BookingStatus, "pending" | "confirmed" | "completed" | "cancelled"> = {
    pending: "pending",
    confirmed: "confirmed",
    completed: "completed",
    cancelled: "cancelled",
    no_show: "cancelled",
  };
  return <Badge variant={map[status]}>{status.replace("_", " ")}</Badge>;
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
    void loadInitial();
  }, []);

  async function loadInitial() {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.adminBookings({ limit: 500 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load bookings");
    } finally {
      setLoading(false);
    }
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(
        await api.adminBookings({
          q: q || undefined,
          status: status || undefined,
          source: source || undefined,
          booking_date: date || undefined,
          limit: 500,
        }),
      );
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
        <p className="text-[10px] font-semibold tracking-[0.2em] text-aqua uppercase">Operations</p>
        <h1 className="mt-2 font-display text-3xl font-bold text-warm-white">Bookings</h1>
        <p className="mt-1 text-chrome">All channels — voice, WhatsApp, and web.</p>
      </div>

      <div className="sparkle-surface rounded-lg p-4 md:p-5">
        <div className="flex flex-wrap gap-2">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name or phone"
            className="max-w-xs border-white/10 bg-black/20 text-warm-white"
          />
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="max-w-[11rem] border-white/10 bg-black/20 text-warm-white"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as BookingStatus | "")}
            className="h-10 rounded-md border border-white/10 bg-black/20 px-3 text-sm text-warm-white"
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
            className="h-10 rounded-md border border-white/10 bg-black/20 px-3 text-sm text-warm-white"
          >
            <option value="">All channels</option>
            <option value="dashboard">Web</option>
            <option value="voice">Voice</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
          <Button onClick={() => void load()} className="bg-aqua text-graphite hover:bg-aqua/90">
            Apply
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <TableSkeleton rows={6} />}

      {!loading && rows.length === 0 && (
        <EmptyState
          icon={CalendarClock}
          title="No bookings yet"
          description="When customers book via voice, WhatsApp, or web, they'll appear here."
          actionLabel="View dashboard"
          actionHref="/admin"
        />
      )}

      {!loading && rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-white/5">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/5 bg-white/[0.02] text-[10px] font-semibold tracking-[0.15em] text-chrome uppercase">
              <tr>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Vehicle</th>
                <th className="px-4 py-3">Service</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Channel</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const needsReview = !row.admin_acknowledged_at && row.status !== "cancelled";
                return (
                  <tr
                    key={row.id}
                    className={cn(
                      "border-b border-white/5 transition hover:bg-white/[0.02]",
                      needsReview && "bg-aqua/[0.04]",
                    )}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-warm-white">{row.customer_name ?? "—"}</div>
                      <div className="text-xs text-chrome">{row.customer_phone}</div>
                    </td>
                    <td className="px-4 py-3 text-chrome">{row.vehicle_label ?? "—"}</td>
                    <td className="px-4 py-3 text-warm-white">{row.service_name ?? "—"}</td>
                    <td className="px-4 py-3 text-chrome">{row.booking_date}</td>
                    <td className="px-4 py-3 font-mono text-xs text-chrome">
                      {String(row.booking_time).slice(0, 5)}
                    </td>
                    <td className="px-4 py-3">
                      <SourceBadge source={row.source} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        {needsReview && (
                          <Button
                            size="sm"
                            disabled={busyId === row.id || ackBusyId === row.id}
                            onClick={() => void accept(row.id)}
                            className="bg-aqua text-graphite hover:bg-aqua/90"
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
                            className="border-white/10 text-chrome hover:bg-white/5"
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
      )}
    </div>
  );
}
