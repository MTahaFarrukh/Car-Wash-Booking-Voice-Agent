import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  tone?: "default" | "aqua" | "amber" | "rose" | "ink";
}) {
  const tones = {
    default: "border-white/5 bg-graphite-elevated",
    aqua: "border-aqua/20 bg-aqua/5",
    amber: "border-amber-500/20 bg-amber-500/5",
    rose: "border-red-500/20 bg-red-500/5",
    ink: "border-white/10 bg-white/5",
  };
  const iconTones = {
    default: "bg-white/5 text-chrome",
    aqua: "bg-aqua/15 text-aqua",
    amber: "bg-amber-500/15 text-amber-400",
    rose: "bg-red-500/15 text-red-400",
    ink: "bg-white/10 text-warm-white",
  };

  return (
    <div className={cn("rounded-lg border p-5 transition hover:border-white/10", tones[tone])}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold tracking-[0.15em] text-chrome uppercase">{label}</p>
          <p className="mt-2 font-display text-3xl font-bold text-warm-white">{value}</p>
        </div>
        {Icon && (
          <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-md", iconTones[tone])}>
            <Icon className="size-4" />
          </div>
        )}
      </div>
    </div>
  );
}
