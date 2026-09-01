"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CalendarCheck,
  CalendarClock,
  Car,
  Clock,
  MessageSquare,
  Mic,
  Monitor,
  Users,
  XCircle,
} from "lucide-react";
import { ApiError, api } from "@/lib/api";
import type { BookingListItem, CallLog, WhatsAppActivity } from "@/types";
import { StatCard } from "@/components/admin/stat-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

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
          api.adminBookings({ limit: 500 }),
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

  const today = (() => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  })();

  const stats = useMemo(() => {
    const todayBookings = bookings.filter((b) => b.booking_date === today).length;
    const upcoming = bookings.filter((b) => b.booking_date >= today && b.status !== "cancelled").length;
    const pending = bookings.filter((b) => b.status === "pending").length;
    const confirmed = bookings.filter((b) => b.status === "confirmed").length;
    const cancelled = bookings.filter((b) => b.status === "cancelled").length;
    const needsReview = bookings.filter((b) => !b.admin_acknowledged_at && b.status !== "cancelled").length;
    const bySource = {
      voice: bookings.filter((b) => b.source === "voice").length,
      whatsapp: bookings.filter((b) => b.source === "whatsapp").length,
      web: bookings.filter((b) => b.source === "dashboard").length,
    };
    const recent = bookings.slice(0, 5);
    return { todayBookings, upcoming, pending, confirmed, cancelled, needsReview, bySource, recent };
  }, [bookings, today]);

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading dashboard…</p>
      </div>
    );
  }
  if (error) return <p className="text-sm text-destructive">{error}</p>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-ink">Dashboard</h1>
        <p className="mt-1 text-muted-foreground">Operations overview across web, voice, and WhatsApp.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Today" value={stats.todayBookings} icon={CalendarClock} tone="aqua" />
        <StatCard label="Upcoming" value={stats.upcoming} icon={CalendarCheck} />
        <StatCard label="Needs review" value={stats.needsReview} icon={Clock} tone="amber" />
        <StatCard label="Voice calls" value={calls.length} icon={Mic} tone="ink" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Pending" value={stats.pending} icon={Clock} tone="amber" />
        <StatCard label="Confirmed" value={stats.confirmed} icon={CalendarCheck} tone="aqua" />
        <StatCard label="Customers" value={customers} icon={Users} />
        <StatCard label="Vehicles" value={vehicles} icon={Car} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="shadow-sm lg:col-span-2">
          <CardHeader>
            <CardTitle className="font-display text-lg">Recent bookings</CardTitle>
            <CardDescription>Newest appointments across all channels</CardDescription>
          </CardHeader>
          <CardContent>
            {stats.recent.length === 0 ? (
              <p className="text-sm text-muted-foreground">No bookings yet.</p>
            ) : (
              <ul className="divide-y divide-border">
                {stats.recent.map((b) => (
                  <li key={b.id} className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0 last:pb-0">
                    <div>
                      <p className="font-medium text-ink">{b.customer_name ?? "Customer"}</p>
                      <p className="text-xs text-muted-foreground">
                        {b.service_name} · {b.booking_date} {String(b.booking_time).slice(0, 5)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          b.source === "voice" ? "voice" : b.source === "whatsapp" ? "whatsapp" : "web"
                        }
                      >
                        {b.source === "dashboard" ? "Web" : b.source}
                      </Badge>
                      {!b.admin_acknowledged_at && b.status !== "cancelled" && (
                        <Badge variant="pending">New</Badge>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="font-display text-lg">By channel</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Monitor className="size-4" /> Web
                </span>
                <span className="font-display text-xl font-bold">{stats.bySource.web}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Mic className="size-4" /> Voice
                </span>
                <span className="font-display text-xl font-bold">{stats.bySource.voice}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <MessageSquare className="size-4" /> WhatsApp
                </span>
                <span className="font-display text-xl font-bold">{stats.bySource.whatsapp}</span>
              </div>
              {stats.cancelled > 0 && (
                <div className="flex items-center justify-between border-t border-border pt-3">
                  <span className="flex items-center gap-2 text-sm text-muted-foreground">
                    <XCircle className="size-4" /> Cancelled
                  </span>
                  <span className="font-display text-xl font-bold text-rose-700">{stats.cancelled}</span>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="font-display text-lg">WhatsApp</CardTitle>
              <CardDescription>{wa.length} processed replies</CardDescription>
            </CardHeader>
          </Card>
        </div>
      </div>
    </div>
  );
}
