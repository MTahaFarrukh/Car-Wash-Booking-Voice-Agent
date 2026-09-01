import { SiteHeader } from "@/components/site-header";
import { cn } from "@/lib/utils";

export function PublicShell({
  children,
  eyebrow,
  title,
  description,
  centered = false,
  dark = true,
}: {
  children: React.ReactNode;
  eyebrow?: string;
  title: string;
  description?: string;
  centered?: boolean;
  dark?: boolean;
}) {
  return (
    <div className={cn("min-h-screen", dark ? "sparkle-dark sparkle-hero-bg" : "bg-background")}>
      <div className="relative overflow-hidden border-b border-white/5">
        {dark && <div className="sparkle-grid-fine absolute inset-0 opacity-20" aria-hidden />}
        <SiteHeader variant={dark ? "dark" : "light"} />
        <div
          className={cn(
            "relative mx-auto max-w-6xl px-6 pb-12 pt-28 md:px-10 md:pb-16",
            centered && "text-center",
          )}
        >
          {eyebrow && (
            <p className="text-[11px] font-semibold tracking-[0.25em] text-aqua uppercase">{eyebrow}</p>
          )}
          <h1 className="mt-3 font-display text-3xl font-bold tracking-tight text-warm-white md:text-4xl lg:text-5xl">
            {title}
          </h1>
          {description && (
            <p
              className={cn(
                "mt-4 max-w-xl text-chrome md:text-lg",
                centered && "mx-auto",
                dark ? "text-chrome" : "text-muted-foreground",
              )}
            >
              {description}
            </p>
          )}
        </div>
        <div className="sparkle-chrome-line" />
      </div>
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">{children}</div>
    </div>
  );
}
