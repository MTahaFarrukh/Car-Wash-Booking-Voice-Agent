import { PublicShell } from "@/components/public-shell";
import { VapiCallPanel } from "@/components/vapi-call";

export default function VoicePage() {
  return (
    <PublicShell
      eyebrow="Voice AI"
      title="Talk to Sparkle"
      description="Speak naturally with our AI assistant — bookings land in the same system as web and WhatsApp."
      centered
    >
      <VapiCallPanel />
    </PublicShell>
  );
}
