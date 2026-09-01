import type { BookingListItem, CallLog, WhatsAppActivity } from "@/types";
import { cn } from "@/lib/utils";

export type ActivityItem = {
  id: string;
  time: string;
  message: string;
  channel?: "voice" | "whatsapp" | "web";
};

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "—";
  }
}

export function buildActivityFeed(
  bookings: BookingListItem[],
  calls: CallLog[],
  whatsapp: WhatsAppActivity[],
): ActivityItem[] {
  const items: ActivityItem[] = [];

  for (const b of bookings.slice(0, 15)) {
    const ch = b.source === "dashboard" ? "web" : b.source;
    items.push({
      id: `b-${b.id}`,
      time: b.created_at,
      message: `${ch === "voice" ? "Voice AI" : ch === "whatsapp" ? "WhatsApp" : "Web"} booking — ${b.customer_name ?? "Customer"} · ${b.service_name ?? "Service"}`,
      channel: ch,
    });
  }

  for (const c of calls.slice(0, 8)) {
    if (c.outcome === "booking_created") {
      items.push({
        id: `c-${c.id}`,
        time: c.started_at,
        message: `Voice call completed — booking created`,
        channel: "voice",
      });
    }
  }

  for (const w of whatsapp.slice(0, 5)) {
    items.push({
      id: `w-${w.id}`,
      time: w.created_at,
      message: `WhatsApp reply sent`,
      channel: "whatsapp",
    });
  }

  return items
    .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
    .slice(0, 12);
}

export function LiveActivityFeed({ items }: { items: ActivityItem[] }) {
  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-chrome">No activity yet — bookings will appear here live.</p>;
  }

  return (
    <ul className="divide-y divide-white/5">
      {items.map((item, i) => (
        <li
          key={item.id}
          className={cn("flex gap-4 py-3 animate-fade-in", i > 0 && "opacity-90")}
          style={{ animationDelay: `${i * 40}ms` }}
        >
          <span className="shrink-0 font-mono text-xs tabular-nums text-chrome">{formatTime(item.time)}</span>
          <span className="text-sm text-warm-white/90">{item.message}</span>
        </li>
      ))}
    </ul>
  );
}
