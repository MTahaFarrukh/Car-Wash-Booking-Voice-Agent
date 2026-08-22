import Link from "next/link";
import { BookingWizard } from "@/components/booking-wizard";

export default function BookPage() {
  return (
    <main className="min-h-screen bg-foam">
      <div className="mx-auto max-w-2xl px-6 py-10">
        <Link href="/" className="font-display text-lg font-bold text-primary">
          ← Sparkle
        </Link>
        <h1 className="mt-6 font-display text-3xl font-bold text-ink md:text-4xl">Book online</h1>
        <p className="mt-2 text-muted-foreground">
          Pick a service and time. Your booking is saved in the same system as voice and WhatsApp.
        </p>
        <div className="mt-8">
          <BookingWizard />
        </div>
      </div>
    </main>
  );
}
