import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function SiteHeader({ className, variant = "dark" }: { className?: string; variant?: "dark" | "light" }) {
  const isLight = variant === "light";

  return (
    <header
      className={cn(
        "absolute inset-x-0 top-0 z-20 flex items-center justify-between px-6 py-5 md:px-10",
        className,
      )}
    >
      <Link
        href="/"
        className={cn(
          "font-display text-xl font-extrabold tracking-tight md:text-2xl",
          isLight ? "text-ink" : "text-white",
        )}
      >
        Sparkle
      </Link>
      <nav className="flex items-center gap-2">
        <Link
          href="/book"
          className={cn(
            buttonVariants({ variant: "ghost" }),
            isLight
              ? "text-muted-foreground hover:bg-secondary hover:text-ink"
              : "text-white/90 hover:bg-white/10 hover:text-white",
          )}
        >
          Book
        </Link>
        <Link
          href="/voice"
          className={cn(
            buttonVariants({ variant: "ghost" }),
            "hidden sm:inline-flex",
            isLight
              ? "text-muted-foreground hover:bg-secondary hover:text-ink"
              : "text-white/90 hover:bg-white/10 hover:text-white",
          )}
        >
          Voice AI
        </Link>
        <Link
          href="/book"
          className={cn(buttonVariants(), "bg-aqua text-ink hover:bg-aqua/90")}
        >
          Book Appointment
        </Link>
      </nav>
    </header>
  );
}
