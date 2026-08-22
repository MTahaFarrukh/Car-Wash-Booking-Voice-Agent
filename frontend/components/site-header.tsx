import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function SiteHeader({ className }: { className?: string }) {
  return (
    <header
      className={cn(
        "absolute inset-x-0 top-0 z-20 flex items-center justify-between px-6 py-5 md:px-10",
        className,
      )}
    >
      <Link href="/" className="font-display text-xl font-extrabold tracking-tight text-white md:text-2xl">
        Sparkle
      </Link>
      <nav className="flex items-center gap-2">
        <Link
          href="/book"
          className={cn(buttonVariants({ variant: "ghost" }), "text-white/90 hover:bg-white/10 hover:text-white")}
        >
          Book
        </Link>
        <Link
          href="/voice"
          className={cn(
            buttonVariants({ variant: "ghost" }),
            "hidden text-white/90 hover:bg-white/10 hover:text-white sm:inline-flex",
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
