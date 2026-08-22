import Link from "next/link";
import { CalendarDays, MessageCircle, Mic } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";
import { whatsappBookUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const wa = whatsappBookUrl();

  return (
    <main className="flex-1">
      <section className="relative min-h-[100svh] overflow-hidden bg-ink text-white">
        <div
          aria-hidden
          className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_20%,#1a6b78_0%,transparent_50%),radial-gradient(ellipse_at_80%_10%,#148f82_0%,transparent_45%),linear-gradient(160deg,#072229_0%,#0d4f5b_48%,#0a3a44_100%)]"
        />
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.12] [background-image:radial-gradient(circle_at_1px_1px,white_1px,transparent_0)] [background-size:28px_28px]"
        />
        <SiteHeader />
        <div className="relative z-10 mx-auto flex min-h-[100svh] max-w-6xl flex-col justify-end px-6 pb-16 pt-28 md:justify-center md:px-10 md:pb-24">
          <p className="animate-fade-up font-display text-4xl font-extrabold tracking-tight text-white md:text-6xl lg:text-7xl">
            Sparkle
          </p>
          <h1 className="animate-fade-up-delay mt-4 max-w-xl font-display text-3xl font-semibold leading-tight text-foam md:text-5xl">
            Your Car. Our Care.
          </h1>
          <p className="animate-fade-up-delay mt-4 max-w-md text-base text-white/75 md:text-lg">
            Professional washes on your schedule — book online, talk to our AI, or message us on WhatsApp.
          </p>
          <div className="animate-fade-up-delay mt-8 flex flex-wrap gap-3">
            <Link
              href="/book"
              className={cn(buttonVariants({ size: "lg" }), "bg-aqua text-ink hover:bg-aqua/90")}
            >
              Book Appointment
            </Link>
            <Link
              href="/voice"
              className={cn(
                buttonVariants({ size: "lg", variant: "outline" }),
                "border-white/30 bg-white/5 text-white hover:bg-white/15",
              )}
            >
              Talk to AI
            </Link>
          </div>
        </div>
      </section>

      <section className="bg-foam px-6 py-20 md:px-10">
        <div className="mx-auto max-w-6xl">
          <h2 className="font-display text-3xl font-bold text-ink md:text-4xl">
            How would you like to book?
          </h2>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            Three real channels. One booking system. Your appointment lands in the same calendar either way.
          </p>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            <ChannelCard
              href="/book"
              icon={<CalendarDays className="size-6" />}
              title="Book Online"
              body="Choose your service, date and time yourself."
              cta="Book Appointment"
            />
            <ChannelCard
              href="/voice"
              icon={<Mic className="size-6" />}
              title="Talk to AI"
              body="Speak naturally with our AI booking assistant."
              cta="Start AI Call"
            />
            <ChannelCard
              href={wa === "#" ? "/book" : wa}
              external={wa !== "#"}
              icon={<MessageCircle className="size-6" />}
              title="WhatsApp"
              body="Message our AI assistant on WhatsApp."
              cta="Book on WhatsApp"
            />
          </div>
        </div>
      </section>

      <footer className="border-t border-border bg-white px-6 py-8 text-sm text-muted-foreground md:px-10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <span className="font-display font-semibold text-ink">Sparkle Car Wash</span>
          <div className="flex gap-4">
            <Link href="/admin" className="hover:text-ink">
              Admin
            </Link>
            <Link href="/book" className="hover:text-ink">
              Book
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}

function ChannelCard({
  href,
  icon,
  title,
  body,
  cta,
  external,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  body: string;
  cta: string;
  external?: boolean;
}) {
  const className =
    "group flex flex-col rounded-2xl border border-border bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-aqua/40 hover:shadow-md";
  const content = (
    <>
      <div className="flex size-12 items-center justify-center rounded-xl bg-secondary text-primary">
        {icon}
      </div>
      <h3 className="mt-5 font-display text-xl font-bold text-ink">{title}</h3>
      <p className="mt-2 flex-1 text-sm text-muted-foreground">{body}</p>
      <span className="mt-6 text-sm font-semibold text-primary group-hover:text-aqua">{cta} →</span>
    </>
  );
  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
        {content}
      </a>
    );
  }
  return (
    <Link href={href} className={className}>
      {content}
    </Link>
  );
}
