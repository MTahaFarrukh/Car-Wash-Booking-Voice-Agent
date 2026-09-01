"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CalendarCheck,
  CalendarClock,
  DollarSign,
  MessageSquare,
  Mic,
  Monitor,
} from "lucide-react";
import { ApiError, api } from "@/lib/api";
import type { BookingListItem, CallLog, WhatsAppActivity } from "@/types";
import { StatCard } from "@/components/admin/stat-card";
import { buildActivityFeed, LiveActivityFeed } from "@/components/sparkle/live-activity-feed";
import { StatSkeleton } from "@/components/sparkle/skeleton";

export default function AdminDashboardPage() {
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [calls, setCalls] = useState<CallLog[]>([]);
  const [wa, setWa] = useState<WhatsAppActivity[]>([]);
  const [customers, setCustomers] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [b, c, w, cust] = await Promise.all([
          api.adminBookings({ limit: 500 }),
          api.adminCallLogs({ limit: 50 }),
          api.adminWhatsAppActivity(50),
          api.listCustomers({ limit: 500 }),
        ]);
        if (cancelled) return;
        setBookings(b);
        setCalls(c);
        setWa(w);
        setCustomers(cust.length);
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
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  })();

  const stats = useMemo(() => {
    const todayBookings = bookings.filter((b) => b.booking_date === today).length;
    const upcoming = bookings.filter((b) => b.booking_date >= today && b.status !== "cancelled").length;
    const bySource = {
      voice: bookings.filter((b) => b.source === "voice").length,
      whatsapp: bookings.filter((b) => b.source === "whatsapp").length,
      web: bookings.filter((b) => b.source === "dashboard").length,
    };
    const activeCount = bookings.filter((b) => b.status !== "cancelled").length;
    const activity = buildActivityFeed(bookings, calls, wa);
    return { todayBookings, upcoming, bySource, activity, activeCount };
  }, [bookings, calls, wa, today]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <StatSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }
  if (error) return <p className="text-sm text-destructive">{error}</p>;

  return (
    <div className="space-y-8">
      <div>
        <p className="text-[10px] font-semibold tracking-[0.2em] text-aqua uppercase">Overview</p>
        <h1 className="mt-2 font-display text-3xl font-bold text-warm-white">Dashboard</h1>
        <p className="mt-1 text-chrome">{customers} customers · {bookings.length} total bookings</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Today" value={stats.todayBookings} icon={CalendarClock} tone="aqua" />
        <StatCard label="Upcoming" value={stats.upcoming} icon={CalendarCheck} />
        <StatCard label="Voice bookings" value={stats.bySource.voice} icon={Mic} tone="aqua" />
        <StatCard label="Active bookings" value={stats.activeCount} icon={DollarSign} tone="ink" />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Web" value={stats.bySource.web} icon={Monitor} />
        <StatCard label="WhatsApp" value={stats.bySource.whatsapp} icon={MessageSquare} tone="aqua" />
        <StatCard label="Voice calls" value={calls.length} icon={Mic} />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="sparkle-surface rounded-lg p-6 lg:col-span-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-semibold tracking-[0.2em] text-chrome uppercase">Sparkle Live</p>
              <h2 className="mt-1 font-display text-lg font-semibold text-warm-white">Activity feed</h2>
            </div>
            <span className="flex items-center gap-1.5 text-[10px] text-aqua">
              <span className="size-1.5 rounded-full bg-aqua animate-pulse-soft" />
              Live
            </span>
          </div>
          <div className="mt-6">
            <LiveActivityFeed items={stats.activity} />
          </div>
        </div>

        <div className="sparkle-surface rounded-lg p-6 lg:col-span-2">
          <p className="text-[10px] font-semibold tracking-[0.2em] text-chrome uppercase">Channels</p>
          <h2 className="mt-1 font-display text-lg font-semibold text-warm-white">Distribution</h2>
          <div className="mt-6 space-y-4">
            {[
              { label: "Voice", value: stats.bySource.voice, pct: bookings.length ? (stats.bySource.voice / bookings.length) * 100 : 0, color: "bg-aqua" },
              { label: "WhatsApp", value: stats.bySource.whatsapp, pct: bookings.length ? (stats.bySource.whatsapp / bookings.length) * 100 : 0, color: "bg-emerald-500" },
              { label: "Web", value: stats.bySource.web, pct: bookings.length ? (stats.bySource.web / bookings.length) * 100 : 0, color: "bg-sky-500" },
            ].map((ch) => (
              <div key={ch.label}>
                <div className="flex justify-between text-sm">
                  <span className="text-chrome">{ch.label}</span>
                  <span className="font-medium text-warm-white">{ch.value}</span>
                </div>
                <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/5">
                  <div className={`h-full ${ch.color} transition-all duration-700`} style={{ width: `${ch.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
