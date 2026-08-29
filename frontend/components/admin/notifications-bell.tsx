"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { sourceChannelLabel, useAdminNotifications } from "@/lib/admin-notifications";

export function AdminNotificationsBell() {
  const { count, items, loading, error, acknowledge, busyId } = useAdminNotifications();
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        aria-label="Booking notifications"
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-lg border border-border bg-white p-2 text-muted-foreground transition hover:bg-foam"
      >
        <Bell className="size-5" />
        {count > 0 && (
          <span className="absolute -right-1 -top-1 flex size-5 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-border bg-white shadow-lg">
          <div className="border-b px-4 py-3">
            <p className="font-display text-sm font-semibold text-ink">New appointments</p>
            <p className="text-xs text-muted-foreground">
              {loading
                ? "Checking…"
                : error
                  ? "Could not load notifications"
                  : count === 0
                    ? "You're all caught up."
                    : `${count} need review`}
            </p>
            {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
          </div>
          <ul className="max-h-80 overflow-y-auto">
            {items.length === 0 && !loading && (
              <li className="px-4 py-6 text-center text-sm text-muted-foreground">No pending notifications</li>
            )}
            {items.map((item) => (
              <li key={item.id} className="border-b px-4 py-3 last:border-0">
                <p className="text-sm font-medium text-ink">
                  New appointment through {sourceChannelLabel(item.source)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.customer_name ?? "Customer"} · {item.service_name ?? "Service"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.booking_date} {String(item.booking_time).slice(0, 5)}
                </p>
                <div className="mt-2 flex gap-2">
                  <Button
                    size="sm"
                    disabled={busyId === item.id}
                    onClick={() => void acknowledge(item.id)}
                  >
                    Accept
                  </Button>
                  <Link
                    href="/admin/bookings"
                    onClick={() => setOpen(false)}
                    className={buttonVariants({ size: "sm", variant: "outline" })}
                  >
                    View
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function AdminNavNotificationDot({ show, count }: { show: boolean; count?: number }) {
  if (!show) return null;
  if (count != null && count > 0) {
    return (
      <span className="ml-auto flex size-5 shrink-0 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white ring-2 ring-sidebar">
        {count > 9 ? "9+" : count}
      </span>
    );
  }
  return (
    <span
      className={cn("ml-auto size-2.5 shrink-0 rounded-full bg-red-500 ring-2 ring-sidebar")}
      aria-hidden
    />
  );
}
