import type { Service } from "@/types";
import { cn } from "@/lib/utils";

export function BookingLiveSummary({
  service,
  bookingDate,
  bookingTime,
  name,
  phone,
  make,
  model,
  vehicleType,
  className,
}: {
  service: Service | null;
  bookingDate: string;
  bookingTime: string;
  name: string;
  phone: string;
  make: string;
  model: string;
  vehicleType: string;
  className?: string;
}) {
  const rows = [
    { label: "Service", value: service?.name },
    { label: "Vehicle", value: make && model ? `${make} ${model}` : undefined },
    { label: "Type", value: vehicleType || undefined },
    { label: "Date", value: bookingDate || undefined },
    { label: "Time", value: bookingTime ? bookingTime.slice(0, 5) : undefined },
    { label: "Name", value: name.trim() || undefined },
    { label: "Phone", value: phone.trim() || undefined },
  ];

  return (
    <aside
      className={cn(
        "sparkle-surface hidden rounded-lg p-6 lg:block lg:sticky lg:top-6 lg:h-fit",
        className,
      )}
    >
      <p className="text-[10px] font-semibold tracking-[0.2em] text-chrome uppercase">Your booking</p>
      <p className="mt-1 font-display text-lg font-semibold text-warm-white">Live summary</p>
      <ul className="mt-6 space-y-0">
        {rows.map((row) => (
          <li
            key={row.label}
            className="flex justify-between gap-3 border-b border-white/5 py-3 text-sm last:border-0"
          >
            <span className="text-chrome">{row.label}</span>
            <span className={cn("font-medium text-right", row.value ? "text-warm-white" : "text-chrome/40")}>
              {row.value ?? "—"}
            </span>
          </li>
        ))}
      </ul>
      {service && (
        <p className="mt-4 border-t border-white/5 pt-4 text-right font-display text-lg font-bold text-aqua">
          {new Intl.NumberFormat("en-PK", { style: "currency", currency: "PKR", maximumFractionDigits: 0 }).format(
            Number.parseFloat(String(service.price)) || 0,
          )}
        </p>
      )}
    </aside>
  );
}
