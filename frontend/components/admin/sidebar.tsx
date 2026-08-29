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
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/bookings", label: "Bookings", icon: CalendarClock },
  { href: "/admin/customers", label: "Customers", icon: Users },
  { href: "/admin/vehicles", label: "Vehicles", icon: Car },
  { href: "/admin/services", label: "Services", icon: Sparkles },
  { href: "/admin/availability", label: "Availability", icon: Wrench },
  { href: "/admin/calls", label: "Calls", icon: Mic },
  { href: "/admin/whatsapp", label: "WhatsApp", icon: MessageSquare },
  { href: "/admin/settings", label: "Settings", icon: Settings },
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
    <aside className="flex w-60 shrink-0 flex-col bg-sidebar text-sidebar-foreground">
      <div className="border-b border-sidebar-border px-5 py-5">
        <Link href="/" className="font-display text-lg font-bold">
          Sparkle Admin
        </Link>
        <p className="mt-1 text-xs text-sidebar-foreground/60">Operations</p>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {NAV.map((item) => {
          const active =
            item.href === "/admin" ? pathname === "/admin" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition",
                active
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-accent/70",
              )}
            >
              <Icon className="size-4" />
              {item.label}
              {item.href === "/admin/bookings" && (
                <AdminNavNotificationDot show={count > 0} count={count} />
              )}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-sidebar-border p-3">
        <p className="truncate px-3 text-xs text-sidebar-foreground/70" title={user?.email ?? undefined}>
          {user?.email ?? "Admin"}
        </p>
        <button
          type="button"
          onClick={onLogout}
          className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-sidebar-foreground/80 transition hover:bg-sidebar-accent/70"
        >
          <LogOut className="size-4" />
          Log out
        </button>
      </div>
    </aside>
  );
}
