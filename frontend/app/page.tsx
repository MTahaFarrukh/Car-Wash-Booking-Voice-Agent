import Link from "next/link";
import { HeroVoiceDemo } from "@/components/sparkle/hero-voice-demo";
import { ChannelShowcase } from "@/components/sparkle/channel-showcase";
import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function HomePage() {
  return (
    <main className="flex-1 sparkle-dark">
      {/* ── Cinematic hero ── */}
      <section className="sparkle-hero-bg relative min-h-[100svh] overflow-hidden">
        <div className="sparkle-grid-fine absolute inset-0 opacity-30" aria-hidden />
        <div
          aria-hidden
          className="absolute right-0 top-1/4 h-[500px] w-[500px] -translate-y-1/2 rounded-full bg-aqua/5 blur-[120px]"
        />
        <SiteHeader />

        <div className="relative z-10 mx-auto grid min-h-[100svh] max-w-7xl items-center gap-12 px-6 pb-20 pt-28 lg:grid-cols-[1fr_1fr] lg:gap-16 lg:px-10 lg:pb-24 lg:pt-32">
          <div className="max-w-xl">
            <p className="animate-fade-up text-[11px] font-semibold tracking-[0.25em] text-aqua uppercase">
              AI-powered car care
            </p>
            <h1 className="animate-fade-up-delay mt-5 font-display text-4xl font-bold leading-[1.05] text-warm-white md:text-5xl lg:text-6xl">
              Your Car Wash.
              <br />
              <span className="text-chrome">Booked by AI.</span>
            </h1>
            <p className="animate-fade-up-delay mt-6 max-w-md text-base leading-relaxed text-chrome md:text-lg">
              Book through voice, WhatsApp, or the web — Sparkle handles the rest.
            </p>
            <div className="animate-fade-up-delay-2 mt-10 flex flex-wrap gap-3">
              <Link
                href="/book"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "bg-aqua px-8 text-graphite hover:bg-aqua/90",
                )}
              >
                Book a Wash
              </Link>
              <Link
                href="/voice"
                className={cn(
                  buttonVariants({ size: "lg", variant: "outline" }),
                  "border-white/15 bg-transparent text-warm-white hover:bg-white/5",
                )}
              >
                Talk to Sparkle AI
              </Link>
            </div>
          </div>

          <div className="animate-fade-up-delay-2 flex justify-center lg:justify-end">
            <HeroVoiceDemo />
          </div>
        </div>

        <div className="sparkle-chrome-line absolute bottom-0 left-0 right-0" />
      </section>

      {/* ── Channels ── */}
      <section className="relative px-6 py-24 md:px-10">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold tracking-[0.25em] text-aqua uppercase">One engine</p>
            <h2 className="mt-3 font-display text-3xl font-bold text-warm-white md:text-4xl">
              Three ways in. One calendar out.
            </h2>
            <p className="mt-4 text-chrome">
              Voice, WhatsApp, and web bookings all flow into the same Sparkle operations system.
            </p>
          </div>
          <div className="mt-14">
            <ChannelShowcase />
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-white/5 px-6 py-10 md:px-10">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 text-sm text-chrome">
          <span className="font-display font-semibold text-warm-white">Sparkle</span>
          <div className="flex gap-6">
            <Link href="/book" className="transition hover:text-aqua">
              Book
            </Link>
            <Link href="/voice" className="transition hover:text-aqua">
              Voice
            </Link>
            <Link href="/admin" className="transition hover:text-aqua">
              Admin
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
