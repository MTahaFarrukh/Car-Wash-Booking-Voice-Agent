import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function SiteHeader({
  className,
  variant = "dark",
}: {
  className?: string;
  variant?: "dark" | "light";
}) {
  const isDark = variant === "dark";

  return (
    <header
      className={cn(
        "absolute inset-x-0 top-0 z-30 flex items-center justify-between px-6 py-5 md:px-10",
        className,
      )}
    >
      <Link
        href="/"
        className={cn(
          "font-display text-lg font-bold tracking-tight md:text-xl",
          isDark ? "text-warm-white" : "text-ink",
        )}
      >
        Sparkle
      </Link>
      <nav className="flex items-center gap-1 sm:gap-2">
        <Link
          href="/book"
          className={cn(
            buttonVariants({ variant: "ghost", size: "sm" }),
            isDark ? "text-chrome hover:bg-white/5 hover:text-warm-white" : "",
          )}
        >
          Book
        </Link>
        <Link
          href="/voice"
          className={cn(
            buttonVariants({ variant: "ghost", size: "sm" }),
            "hidden sm:inline-flex",
            isDark ? "text-chrome hover:bg-white/5 hover:text-warm-white" : "",
          )}
        >
          Voice AI
        </Link>
        <Link
          href="/voice"
          className={cn(
            buttonVariants({ size: "sm" }),
            "border border-aqua/30 bg-aqua/10 text-aqua hover:bg-aqua hover:text-graphite",
          )}
        >
          Talk to Sparkle
        </Link>
      </nav>
    </header>
  );
}
