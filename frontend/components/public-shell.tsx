import { SiteHeader } from "@/components/site-header";
import { cn } from "@/lib/utils";

export function PublicShell({
  children,
  className,
  eyebrow,
  title,
  description,
  centered = false,
}: {
  children: React.ReactNode;
  className?: string;
  eyebrow?: string;
  title: string;
  description?: string;
  centered?: boolean;
}) {
  return (
    <div className={cn("page-mesh-bg min-h-screen", className)}>
      <div className="relative overflow-hidden border-b border-border/60 bg-white/70 backdrop-blur-md">
        <div
          aria-hidden
          className="absolute inset-0 bg-[linear-gradient(135deg,rgba(31,184,168,0.08)_0%,transparent_45%,rgba(13,79,91,0.06)_100%)]"
        />
        <SiteHeader variant="light" />
        <div
          className={cn(
            "relative mx-auto max-w-3xl px-6 pb-10 pt-24 md:px-10",
            centered && "text-center",
          )}
        >
          {eyebrow && (
            <p className="text-xs font-semibold tracking-[0.2em] text-aqua uppercase">{eyebrow}</p>
          )}
          <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">{title}</h1>
          {description && (
            <p
              className={cn(
                "mt-3 max-w-xl text-muted-foreground md:text-lg",
                centered && "mx-auto",
              )}
            >
              {description}
            </p>
          )}
        </div>
      </div>
      <div className="mx-auto max-w-3xl px-6 py-10 md:px-10">{children}</div>
    </div>
  );
}
