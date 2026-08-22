import Link from "next/link";
import { VapiCallPanel } from "@/components/vapi-call";

export default function VoicePage() {
  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#eef7f8_0%,#f4f8f9_40%,#ffffff_100%)]">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <Link href="/" className="font-display text-lg font-bold text-primary">
          ← Sparkle
        </Link>
        <h1 className="mt-6 text-center font-display text-3xl font-bold text-ink md:text-4xl">
          Talk to AI
        </h1>
        <p className="mx-auto mt-2 max-w-lg text-center text-muted-foreground">
          Browser voice call powered by VAPI — tools hit the same Sparkle backend as phone and WhatsApp.
        </p>
        <div className="mt-10">
          <VapiCallPanel />
        </div>
      </div>
    </main>
  );
}
