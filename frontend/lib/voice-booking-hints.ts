/** Heuristic extraction of booking fields from voice transcript (display only). */

export type VoiceBookingHints = {
  service?: string;
  vehicle?: string;
  date?: string;
  time?: string;
  customer?: string;
  status?: string;
};

export function extractVoiceBookingHints(
  lines: { role: string; text: string }[],
): VoiceBookingHints {
  const all = lines.map((l) => l.text).join(" ");
  const user = lines
    .filter((l) => l.role === "user")
    .map((l) => l.text)
    .join(" ");
  const assistant = lines
    .filter((l) => l.role === "assistant")
    .map((l) => l.text)
    .join(" ");
  const combined = `${user} ${assistant}`.toLowerCase();

  const hints: VoiceBookingHints = {};

  if (/premium/i.test(combined)) hints.service = "Premium Wash";
  else if (/basic/i.test(combined)) hints.service = "Basic Wash";
  else if (/interior|detail/i.test(combined)) hints.service = "Interior Detail";
  else if (/wash/i.test(combined)) hints.service = "Car Wash";

  const vehicleMatch = combined.match(
    /\b(suzuki|honda|toyota|bmw|mercedes|audi|swift|city|civic|corolla)\b/gi,
  );
  if (vehicleMatch) {
    hints.vehicle = vehicleMatch
      .slice(0, 2)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");
  }

  if (/tomorrow/i.test(combined)) hints.date = "Tomorrow";
  else if (/today/i.test(combined)) hints.date = "Today";

  const timeMatch = combined.match(/\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b/i);
  if (timeMatch) {
    let h = Number.parseInt(timeMatch[1], 10);
    const m = timeMatch[2] ? Number.parseInt(timeMatch[2], 10) : 0;
    const ampm = timeMatch[3]?.toLowerCase();
    if (ampm === "pm" && h < 12) h += 12;
    if (ampm === "am" && h === 12) h = 0;
    hints.time = `${h % 12 || 12}:${m.toString().padStart(2, "0")} ${h >= 12 ? "PM" : "AM"}`;
  }

  if (/booked|confirmed|all set|you're set/i.test(assistant)) hints.status = "Confirmed";

  return hints;
}
