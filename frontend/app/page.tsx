import Link from "next/link";
import { ArrowRight, CalendarCheck, Check, Clock3, MessageCircle, Mic2, ShieldCheck, Sparkles, WandSparkles } from "lucide-react";
import { HeroVoiceDemo } from "@/components/sparkle/hero-voice-demo";
import { ChannelShowcase } from "@/components/sparkle/channel-showcase";
import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const services = [
  { number: "01", name: "Essential Wash", detail: "A meticulous exterior reset for everyday driving." },
  { number: "02", name: "Premium Detail", detail: "Inside and out, finished with careful attention to every surface." },
  { number: "03", name: "Signature Finish", detail: "Our complete treatment for a deeper, longer-lasting shine." },
];

const steps = [
  { icon: Mic2, title: "Tell us what you need", copy: "Speak, text, or tap. Natural requests work perfectly." },
  { icon: WandSparkles, title: "Sparkle handles the details", copy: "The AI finds your service, vehicle, date, and best available time." },
  { icon: CalendarCheck, title: "Your wash is confirmed", copy: "Everything lands in one calendar, ready for the team." },
];

export default function HomePage() {
  return (
    <main className="flex-1 overflow-hidden sparkle-dark">
      <section className="sparkle-hero-bg relative min-h-[760px] overflow-hidden lg:min-h-[820px]">
        <div className="sparkle-grid-fine absolute inset-0 opacity-30" aria-hidden />
        <div className="hero-reflection" aria-hidden />
        <SiteHeader />
        <div className="relative z-10 mx-auto grid min-h-[760px] max-w-7xl items-center gap-14 px-6 pb-24 pt-28 lg:min-h-[820px] lg:grid-cols-[0.9fr_1.1fr] lg:gap-20 lg:px-10 lg:pb-24 lg:pt-32">
          <div className="max-w-xl">
            <div className="animate-fade-up inline-flex items-center gap-2 border border-aqua/20 bg-aqua/[0.06] px-3 py-2 text-[10px] font-semibold tracking-[0.2em] text-aqua uppercase"><span className="size-1.5 rounded-full bg-aqua shadow-[0_0_12px_rgba(46,196,182,.8)]" />AI concierge · Always available</div>
            <h1 className="animate-fade-up-delay mt-7 font-display text-[clamp(2.75rem,6vw,5.5rem)] font-bold leading-[0.98] text-warm-white">Your Car Wash.<br /><span className="text-chrome">Booked by AI.</span></h1>
            <p className="animate-fade-up-delay mt-7 max-w-lg text-base leading-7 text-chrome md:text-lg">The effortless way to book exceptional car care. Just call, message, or book online—Sparkle handles the rest.</p>
            <div className="animate-fade-up-delay-2 mt-10 flex flex-col gap-3 sm:flex-row">
              <Link href="/book" className={cn(buttonVariants({ size: "lg" }), "group h-12 bg-aqua px-7 text-graphite hover:bg-[#58d7cb]")}>Book a Wash <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" /></Link>
              <Link href="/voice" className={cn(buttonVariants({ size: "lg", variant: "outline" }), "h-12 border-white/15 bg-white/[0.02] px-7 text-warm-white hover:bg-white/[0.07]")}><Mic2 className="size-4 text-aqua" /> Talk to Sparkle AI</Link>
            </div>
            <div className="animate-fade-up-delay-2 mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-chrome"><span className="flex items-center gap-2"><Check className="size-3.5 text-aqua" /> No app required</span><span className="flex items-center gap-2"><Check className="size-3.5 text-aqua" /> Instant confirmation</span></div>
          </div>
          <div className="animate-fade-up-delay-2 relative flex justify-center lg:justify-end"><div className="absolute inset-1/4 rounded-full bg-aqua/10 blur-[100px]" aria-hidden /><HeroVoiceDemo /></div>
        </div>
        <div className="sparkle-chrome-line absolute bottom-0 left-0 right-0" />
      </section>

      <section className="relative px-6 py-24 md:px-10 lg:py-32"><div className="mx-auto max-w-7xl"><SectionIntro eyebrow="One intelligent calendar" title="Book the way you already communicate." copy="Voice, WhatsApp, and web all connect to the same live booking system—so every appointment stays accurate." /><div className="mt-14"><ChannelShowcase /></div></div></section>

      <section className="border-y border-white/[0.06] bg-white/[0.018] px-6 py-24 md:px-10 lg:py-32"><div className="mx-auto max-w-7xl"><SectionIntro eyebrow="Quietly intelligent" title="From request to confirmed in moments." copy="Sparkle turns a natural conversation into a complete appointment without the back-and-forth." /><div className="mt-16 grid gap-px overflow-hidden border border-white/[0.07] bg-white/[0.07] md:grid-cols-3">{steps.map((step, index) => { const Icon = step.icon; return <article key={step.title} className="group relative bg-graphite px-7 py-10 transition-colors hover:bg-graphite-elevated md:px-9 md:py-12"><span className="absolute right-6 top-5 font-mono text-xs text-white/20">0{index + 1}</span><div className="flex size-11 items-center justify-center border border-aqua/20 bg-aqua/[0.07] text-aqua"><Icon className="size-5" /></div><h3 className="mt-8 text-xl font-semibold text-warm-white">{step.title}</h3><p className="mt-3 max-w-xs text-sm leading-6 text-chrome">{step.copy}</p></article>; })}</div></div></section>

      <section className="px-6 py-24 md:px-10 lg:py-32"><div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[0.78fr_1.22fr] lg:items-end"><div><SectionIntro eyebrow="Car care, considered" title="The right level of care for every drive." copy="Clear packages, thoughtful service, and no confusing add-ons. Choose in seconds or let the AI guide you." /><Link href="/book" className="group mt-8 inline-flex items-center gap-2 text-sm font-semibold text-aqua">Explore live availability <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" /></Link></div><div className="divide-y divide-white/[0.08] border-y border-white/[0.08]">{services.map((service) => <Link href="/book" key={service.name} className="group grid gap-4 py-7 transition-colors hover:bg-white/[0.025] sm:grid-cols-[48px_1fr_auto] sm:items-center sm:px-4"><span className="font-mono text-xs text-aqua/70">{service.number}</span><div><h3 className="text-lg font-semibold text-warm-white">{service.name}</h3><p className="mt-1 text-sm text-chrome">{service.detail}</p></div><ArrowRight className="hidden size-5 text-white/25 transition-all group-hover:translate-x-1 group-hover:text-aqua sm:block" /></Link>)}</div></div></section>

      <section className="px-6 pb-24 md:px-10 lg:pb-32"><div className="mx-auto grid max-w-7xl overflow-hidden border border-white/[0.08] bg-[#0c1114] lg:grid-cols-2"><div className="relative min-h-[420px] overflow-hidden p-8 sm:p-12"><div className="sparkle-grid-fine absolute inset-0 opacity-30" aria-hidden /><div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(46,196,182,.13),transparent_52%)]" aria-hidden /><div className="relative flex h-full flex-col items-center justify-center text-center"><div className="voice-preview-orb"><Mic2 className="size-8 text-aqua" /></div><div className="mt-8 flex items-end gap-1" aria-hidden>{[10,18,28,14,34,22,12,26,18,8].map((h, i) => <span key={i} className="waveform-bar w-1 rounded-full bg-aqua" style={{ height: h, animationDelay: `${i * 70}ms` }} />)}</div><p className="mt-7 text-xs font-semibold tracking-[0.22em] text-aqua uppercase">Listening</p><p className="mt-3 max-w-sm text-sm leading-6 text-chrome">“Book my usual wash tomorrow afternoon.”</p></div></div><div className="border-t border-white/[0.08] p-8 sm:p-12 lg:border-l lg:border-t-0"><p className="text-[11px] font-semibold tracking-[0.24em] text-aqua uppercase">Voice-first experience</p><h2 className="mt-4 text-3xl font-bold text-warm-white md:text-4xl">A concierge that listens.</h2><p className="mt-5 max-w-lg leading-7 text-chrome">Speak naturally. Sparkle understands the service, vehicle, day, and time—then checks availability and confirms the booking in the same conversation.</p><div className="mt-9 grid gap-4 sm:grid-cols-2"><Feature icon={Clock3} text="Available around the clock" /><Feature icon={ShieldCheck} text="Confirms every detail" /><Feature icon={MessageCircle} text="Works across channels" /><Feature icon={Sparkles} text="Natural, human experience" /></div><Link href="/voice" className={cn(buttonVariants({ size: "lg" }), "mt-10 bg-aqua text-graphite hover:bg-[#58d7cb]")}>Try Sparkle Voice <ArrowRight className="size-4" /></Link></div></div></section>

      <section className="px-6 pb-24 md:px-10 lg:pb-32"><div className="mx-auto max-w-7xl border-t border-white/[0.08] pt-20 text-center"><p className="text-[11px] font-semibold tracking-[0.25em] text-aqua uppercase">Ready when you are</p><h2 className="mx-auto mt-4 max-w-3xl text-4xl font-bold leading-tight text-warm-white md:text-6xl">A cleaner car is one conversation away.</h2><p className="mx-auto mt-5 max-w-xl leading-7 text-chrome">Choose your wash online or let Sparkle AI arrange everything for you.</p><div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row"><Link href="/book" className={cn(buttonVariants({ size: "lg" }), "h-12 bg-aqua px-8 text-graphite hover:bg-[#58d7cb]")}>Book a Wash</Link><Link href="/voice" className={cn(buttonVariants({ size: "lg", variant: "outline" }), "h-12 border-white/15 bg-transparent px-8 text-warm-white hover:bg-white/[0.06]")}>Talk to Sparkle AI</Link></div></div></section>

      <footer className="border-t border-white/[0.06] px-6 py-8 md:px-10"><div className="mx-auto flex max-w-7xl flex-col gap-5 text-sm text-chrome sm:flex-row sm:items-center sm:justify-between"><div><span className="font-display font-semibold text-warm-white">Sparkle</span><span className="ml-3 text-xs text-white/35">AI-powered car care</span></div><div className="flex gap-6"><Link href="/book" className="transition hover:text-aqua">Book</Link><Link href="/voice" className="transition hover:text-aqua">Voice</Link><Link href="/admin" className="transition hover:text-aqua">Admin</Link></div></div></footer>
    </main>
  );
}

function SectionIntro({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) { return <div className="max-w-2xl"><p className="text-[11px] font-semibold tracking-[0.25em] text-aqua uppercase">{eyebrow}</p><h2 className="mt-4 text-3xl font-bold leading-tight text-warm-white md:text-5xl">{title}</h2><p className="mt-5 max-w-xl leading-7 text-chrome">{copy}</p></div>; }
function Feature({ icon: Icon, text }: { icon: typeof Clock3; text: string }) { return <div className="flex items-center gap-3 text-sm text-warm-white"><span className="flex size-8 items-center justify-center border border-white/10 bg-white/[0.03] text-aqua"><Icon className="size-4" /></span>{text}</div>; }
