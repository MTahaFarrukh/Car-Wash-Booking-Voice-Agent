import { PublicShell } from "@/components/public-shell";
import { BookingWizard } from "@/components/booking-wizard";

export default function BookPage() {
  return (
    <PublicShell
      eyebrow="Online booking"
      title="Book your wash"
      description="Choose a service, pick a time, and confirm — same calendar as voice and WhatsApp."
    >
      <BookingWizard />
    </PublicShell>
  );
}
