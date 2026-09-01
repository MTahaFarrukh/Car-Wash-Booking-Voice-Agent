"use client";

import Link from "next/link";
import { CalendarDays, MessageCircle, Mic } from "lucide-react";
import { whatsappBookUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

const CHANNELS = [
  {
    id: "voice",
    href: "/voice",
    icon: Mic,
    tagline: "Just say when.",
    title: "Voice",
    external: false,
    preview: (
      <div className="mt-4 space-y-2 rounded-md border border-white/5 bg-black/25 p-3 text-left text-xs">
        <p className="text-chrome">You</p>
        <p className="text-warm-white/90">Book premium wash tomorrow 5pm</p>
        <p className="mt-2 text-chrome">Sparkle</p>
        <p className="text-aqua">Done. Premium Wash · Tomorrow · 5:00 PM</p>
      </div>
    ),
  },
  {
    id: "whatsapp",
    href: null as string | null,
    icon: MessageCircle,
    tagline: "Text. Confirm. Done.",
    title: "WhatsApp",
    external: true,
    preview: (
      <div className="mt-4 space-y-2 rounded-md border border-white/5 bg-black/25 p-3 text-left text-xs">
        <p className="text-chrome">You · 12:41</p>
        <p className="rounded-md bg-emerald-900/40 px-2 py-1 text-warm-white/90">Need a wash Friday 10am</p>
        <p className="text-chrome">Sparkle · 12:41</p>
        <p className="rounded-md bg-white/5 px-2 py-1 text-warm-white/90">Booked ✓ Basic Wash · Fri 10:00</p>
      </div>
    ),
  },
  {
    id: "web",
    href: "/book",
    icon: CalendarDays,
    tagline: "Prefer clicking?",
    title: "Web",
    external: false,
    preview: (
      <div className="mt-4 rounded-md border border-white/5 bg-black/25 p-3 text-left text-xs">
        <div className="flex justify-between text-chrome">
          <span>Service</span>
          <span className="text-warm-white">Premium Wash</span>
        </div>
        <div className="mt-2 flex justify-between text-chrome">
          <span>Slot</span>
          <span className="text-aqua">Tomorrow · 5:00 PM</span>
        </div>
      </div>
    ),
  },
];

export function ChannelShowcase() {
  const wa = whatsappBookUrl();

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {CHANNELS.map((ch) => {
        const Icon = ch.icon;
        const href = ch.id === "whatsapp" ? (wa === "#" ? "/book" : wa) : ch.href!;
        const cardClass = cn(
          "group sparkle-surface block rounded-lg p-6 transition-all duration-300",
          "hover:border-aqua/20 hover:shadow-[var(--glow-aqua)]",
        );
        const inner = (
          <>
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-md border border-white/10 bg-white/5">
                <Icon className="size-4 text-aqua" />
              </div>
              <div>
                <p className="text-[10px] font-semibold tracking-[0.15em] text-chrome uppercase">{ch.tagline}</p>
                <h3 className="font-display text-lg font-semibold text-warm-white">{ch.title}</h3>
              </div>
            </div>
            {ch.preview}
            <span className="mt-5 inline-flex text-xs font-medium text-aqua opacity-0 transition-opacity group-hover:opacity-100">
              Open channel →
            </span>
          </>
        );

        if (ch.external && wa !== "#") {
          return (
            <a key={ch.id} href={href} target="_blank" rel="noopener noreferrer" className={cardClass}>
              {inner}
            </a>
          );
        }
        return (
          <Link key={ch.id} href={href} className={cardClass}>
            {inner}
          </Link>
        );
      })}
    </div>
  );
}
