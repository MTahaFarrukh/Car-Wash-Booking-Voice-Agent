import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  actionHref,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-border px-8 py-16 text-center",
        className,
      )}
    >
      <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-secondary">
        <Icon className="size-5 text-muted-foreground" />
      </div>
      <h3 className="mt-5 font-display text-lg font-semibold text-foreground">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">{description}</p>
      {actionLabel && actionHref && (
        <Link href={actionHref} className={cn(buttonVariants(), "mt-6")}>
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
