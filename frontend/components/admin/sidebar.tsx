"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CalendarClock,
  Car,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Mic,
  Settings,
  Sparkles,
  Users,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAdminAuth } from "@/lib/admin-auth";
import { useAdminNotifications } from "@/lib/admin-notifications";
import { AdminNavNotificationDot } from "@/components/admin/notifications-bell";

const NAV_GROUPS = [
  {
    label: "Overview",
    items: [{ href: "/admin", label: "Dashboard", icon: LayoutDashboard, exact: true }],
  },
  {
    label: "Operations",
    items: [
      { href: "/admin/bookings", label: "Bookings", icon: CalendarClock },
      { href: "/admin/customers", label: "Customers", icon: Users },
      { href: "/admin/vehicles", label: "Vehicles", icon: Car },
      { href: "/admin/services", label: "Services", icon: Sparkles },
      { href: "/admin/availability", label: "Availability", icon: Wrench },
    ],
  },
  {
    label: "Channels",
    items: [
      { href: "/admin/calls", label: "Calls", icon: Mic },
      { href: "/admin/whatsapp", label: "WhatsApp", icon: MessageSquare },
    ],
  },
  {
    label: "System",
    items: [{ href: "/admin/settings", label: "Settings", icon: Settings }],
  },
];

export function AdminSidebar({ pathname }: { pathname: string }) {
  const { user, signOut } = useAdminAuth();
  const { count } = useAdminNotifications();
  const router = useRouter();

  async function onLogout() {
    await signOut();
    router.replace("/admin/login");
    router.refresh();
  }

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="border-b border-sidebar-border px-5 py-6">
        <Link href="/" className="font-display text-xl font-bold text-white">
          Sparkle
        </Link>
        <p className="mt-1 text-xs text-sidebar-foreground/60">Admin console</p>
      </div>
      <nav className="flex flex-1 flex-col gap-6 overflow-y-auto p-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p className="mb-2 px-3 text-[10px] font-bold tracking-[0.15em] text-sidebar-foreground/45 uppercase">
              {group.label}
            </p>
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active =
                  "exact" in item && item.exact
                    ? pathname === item.href
                    : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "relative flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition",
                      active
                        ? "bg-sidebar-accent font-medium text-sidebar-primary"
                        : "text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                    )}
                  >
                    {active && (
                      <span className="absolute top-1/2 left-0 h-6 w-1 -translate-y-1/2 rounded-r-full bg-sidebar-primary" />
                    )}
                    <Icon className="size-4 shrink-0" />
                    {item.label}
                    {item.href === "/admin/bookings" && (
                      <AdminNavNotificationDot show={count > 0} count={count} />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-sidebar-border p-4">
        <p className="truncate px-3 text-xs text-sidebar-foreground/60" title={user?.email ?? undefined}>
          {user?.email ?? "Admin"}
        </p>
        <button
          type="button"
          onClick={onLogout}
          className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground/75 transition hover:bg-sidebar-accent/60"
        >
          <LogOut className="size-4" />
          Log out
        </button>
      </div>
    </aside>
  );
}
