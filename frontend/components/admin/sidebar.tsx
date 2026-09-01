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

const NAV = [
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
    label: "AI Channels",
    items: [
      { href: "/admin/calls", label: "Voice Calls", icon: Mic },
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
    <aside className="flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="border-b border-sidebar-border px-5 py-6">
        <Link href="/" className="font-display text-xl font-bold text-warm-white">
          Sparkle
        </Link>
        <p className="mt-1 text-[10px] font-semibold tracking-[0.15em] text-chrome uppercase">Operations</p>
      </div>
      <nav className="flex flex-1 flex-col gap-5 overflow-y-auto p-4">
        {NAV.map((group) => (
          <div key={group.label}>
            <p className="mb-2 px-3 text-[10px] font-bold tracking-[0.15em] text-chrome/60 uppercase">{group.label}</p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active =
                  "exact" in item && item.exact ? pathname === item.href : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "relative flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm transition",
                      active
                        ? "bg-sidebar-accent font-medium text-aqua"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-warm-white",
                    )}
                  >
                    {active && (
                      <span className="absolute top-1/2 left-0 h-5 w-0.5 -translate-y-1/2 rounded-full bg-aqua" />
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
        <p className="truncate px-3 text-xs text-chrome" title={user?.email ?? undefined}>
          {user?.email ?? "Admin"}
        </p>
        <button
          type="button"
          onClick={onLogout}
          className="mt-2 flex w-full items-center gap-2 rounded-md px-3 py-2.5 text-sm text-sidebar-foreground/70 hover:bg-sidebar-accent/50"
        >
          <LogOut className="size-4" />
          Log out
        </button>
      </div>
    </aside>
  );
}
