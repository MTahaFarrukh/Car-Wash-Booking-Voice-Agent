"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { BookingListItem, CallLog, WhatsAppActivity } from "@/types";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{label}</p>
      <p className="mt-2 font-display text-3xl font-bold text-ink">{value}</p>
    </div>
  );
}

export default function AdminDashboardPage() {
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [calls, setCalls] = useState<CallLog[]>([]);
  const [wa, setWa] = useState<WhatsAppActivity[]>([]);
  const [customers, setCustomers] = useState(0);
  const [vehicles, setVehicles] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [b, c, w, cust, veh] = await Promise.all([
          api.adminBookings({ limit: 200 }),
          api.adminCallLogs({ limit: 50 }),
          api.adminWhatsAppActivity(50),
          api.listCustomers({ limit: 500 }),
          api.listVehicles(500),
        ]);
        if (cancelled) return;
        setBookings(b);
        setCalls(c);
        setWa(w);
        setCustomers(cust.length);
        setVehicles(veh.length);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const today = new Date().toISOString().slice(0, 10);
  const stats = useMemo(() => {
    const todayBookings = bookings.filter((b) => b.booking_date === today).length;
    const upcoming = bookings.filter((b) => b.booking_date >= today && b.status !== "cancelled").length;
    const pending = bookings.filter((b) => b.status === "pending").length;
    const confirmed = bookings.filter((b) => b.status === "confirmed").length;
    const cancelled = bookings.filter((b) => b.status === "cancelled").length;
    const bySource = {
      voice: bookings.filter((b) => b.source === "voice").length,
      whatsapp: bookings.filter((b) => b.source === "whatsapp").length,
      web: bookings.filter((b) => b.source === "dashboard").length,
    };
    return { todayBookings, upcoming, pending, confirmed, cancelled, bySource };
  }, [bookings, today]);

  if (loading) return <p className="text-sm text-muted-foreground">Loading dashboard…</p>;
  if (error) return <p className="text-sm text-destructive">{error}</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-ink">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Live counts from the Sparkle backend.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Today" value={stats.todayBookings} />
        <Stat label="Upcoming" value={stats.upcoming} />
        <Stat label="Pending" value={stats.pending} />
        <Stat label="Confirmed" value={stats.confirmed} />
        <Stat label="Cancelled" value={stats.cancelled} />
        <Stat label="Customers" value={customers} />
        <Stat label="Vehicles" value={vehicles} />
        <Stat label="Voice calls" value={calls.length} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Stat label="Web bookings" value={stats.bySource.web} />
        <Stat label="Voice bookings" value={stats.bySource.voice} />
        <Stat label="WhatsApp bookings" value={stats.bySource.whatsapp} />
      </div>
      <div className="rounded-xl border border-border bg-white p-4">
        <h2 className="font-semibold text-ink">WhatsApp activity (recent)</h2>
        <p className="mt-1 text-sm text-muted-foreground">{wa.length} processed replies stored</p>
      </div>
    </div>
  );
}
