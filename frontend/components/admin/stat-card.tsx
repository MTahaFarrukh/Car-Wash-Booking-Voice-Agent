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
    default: "from-white to-foam text-ink",
    aqua: "from-aqua/10 to-white text-primary",
    amber: "from-amber-50 to-white text-amber-950",
    rose: "from-rose-50 to-white text-rose-950",
    ink: "from-ink/5 to-white text-ink",
  };
  const iconTones = {
    default: "bg-secondary text-primary",
    aqua: "bg-aqua/20 text-primary",
    amber: "bg-amber-100 text-amber-800",
    rose: "bg-rose-100 text-rose-800",
    ink: "bg-ink/10 text-ink",
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br p-5 shadow-sm transition hover:shadow-md",
        tones[tone],
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{label}</p>
          <p className="mt-2 font-display text-3xl font-bold">{value}</p>
        </div>
        {Icon && (
          <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-xl", iconTones[tone])}>
            <Icon className="size-5" />
          </div>
        )}
      </div>
    </div>
  );
}
