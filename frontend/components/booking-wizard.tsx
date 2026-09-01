"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Calendar, Car, CheckCircle2, Clock, Sparkles, User } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import type { Service } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Step = 1 | 2 | 3 | 4 | 5 | 6;

const STEPS = [
  { n: 1, label: "Service", icon: Sparkles },
  { n: 2, label: "Date", icon: Calendar },
  { n: 3, label: "Time", icon: Clock },
  { n: 4, label: "You", icon: User },
  { n: 5, label: "Vehicle", icon: Car },
  { n: 6, label: "Confirm", icon: CheckCircle2 },
] as const;

function todayIso() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

function normalizePhone(raw: string) {
  const digits = raw.replace(/\D/g, "");
  if (!digits) return "";
  return raw.trim().startsWith("+") ? `+${digits}` : `+${digits}`;
}

function formatPrice(value: string | number) {
  const num = typeof value === "number" ? value : Number.parseFloat(String(value));
  if (Number.isNaN(num)) return String(value);
  return new Intl.NumberFormat("en-PK", { style: "currency", currency: "PKR", maximumFractionDigits: 0 }).format(num);
}

function BookingStepper({ step }: { step: Step }) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between gap-1">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const done = step > s.n;
          const active = step === s.n;
          return (
            <div key={s.n} className="flex flex-1 items-center">
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={cn(
                    "flex size-9 items-center justify-center rounded-full border-2 text-xs font-bold transition-all",
                    done && "border-aqua bg-aqua text-ink",
                    active && !done && "border-primary bg-primary text-primary-foreground shadow-md",
                    !done && !active && "border-border bg-white text-muted-foreground",
                  )}
                >
                  {done ? <CheckCircle2 className="size-4" /> : <Icon className="size-4" />}
                </div>
                <span
                  className={cn(
                    "hidden text-[10px] font-semibold uppercase tracking-wide sm:block",
                    active ? "text-ink" : "text-muted-foreground",
                  )}
                >
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    "mx-1 mb-5 h-0.5 flex-1 rounded-full transition-colors",
                    step > s.n ? "bg-aqua" : "bg-border",
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
      <p className="mt-4 text-center text-xs font-medium text-muted-foreground sm:hidden">
        Step {step} of 6 — {STEPS[step - 1].label}
      </p>
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <span className="mb-1.5 block text-sm font-medium text-ink">{children}</span>;
}

export function BookingWizard() {
  const [step, setStep] = useState<Step>(1);
  const [services, setServices] = useState<Service[]>([]);
  const [loadingServices, setLoadingServices] = useState(true);
  const [serviceError, setServiceError] = useState<string | null>(null);

  const [serviceId, setServiceId] = useState("");
  const [bookingDate, setBookingDate] = useState(todayIso());
  const [slots, setSlots] = useState<string[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [slotsError, setSlotsError] = useState<string | null>(null);
  const [bookingTime, setBookingTime] = useState("");

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [vehicleType, setVehicleType] = useState("sedan");

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [bookingId, setBookingId] = useState<string | null>(null);

  const selectedService = useMemo(
    () => services.find((s) => s.id === serviceId) ?? null,
    [services, serviceId],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingServices(true);
      setServiceError(null);
      try {
        const rows = await api.listServices(true);
        if (!cancelled) setServices(rows);
      } catch (err) {
        if (!cancelled) {
          setServiceError(err instanceof ApiError ? err.detail : "Could not load services");
        }
      } finally {
        if (!cancelled) setLoadingServices(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (step !== 3 || !serviceId || !bookingDate) return;
    let cancelled = false;
    (async () => {
      setSlotsLoading(true);
      setSlotsError(null);
      setBookingTime("");
      try {
        const result = await api.getAvailability(bookingDate, serviceId);
        if (!cancelled) {
          const now = new Date();
          const todayStr = [
            now.getFullYear(),
            String(now.getMonth() + 1).padStart(2, "0"),
            String(now.getDate()).padStart(2, "0"),
          ].join("-");
          const raw = result.alternatives ?? [];
          const filtered =
            bookingDate === todayStr
              ? raw.filter((slot) => {
                  const [hh, mm] = slot.split(":").map(Number);
                  if (Number.isNaN(hh) || Number.isNaN(mm)) return true;
                  const slotDate = new Date(
                    now.getFullYear(),
                    now.getMonth(),
                    now.getDate(),
                    hh,
                    mm,
                    0,
                    0,
                  );
                  return slotDate.getTime() > now.getTime();
                })
              : raw;
          setSlots(filtered);
          if (!result.available || filtered.length === 0) {
            setSlotsError(
              filtered.length === 0
                ? result.message || "No available slots left for this date"
                : result.message || "No available slots for this date",
            );
          }
        }
      } catch (err) {
        if (!cancelled) {
          setSlots([]);
          setSlotsError(err instanceof ApiError ? err.detail : "Could not load slots");
        }
      } finally {
        if (!cancelled) setSlotsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step, serviceId, bookingDate]);

  async function confirm() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const normalized = normalizePhone(phone);
      let customerId: string;
      const existing = await api.listCustomers({ phone: normalized, limit: 1 });
      if (existing[0]) {
        customerId = existing[0].id;
        if (existing[0].name !== name.trim()) {
          await api.updateCustomer(customerId, { name: name.trim() });
        }
      } else {
        const created = await api.createCustomer({ name: name.trim(), phone: normalized });
        customerId = created.id;
      }
      const vehicle = await api.createVehicle(customerId, {
        make: make.trim(),
        model: model.trim(),
        vehicle_type: vehicleType,
      });
      const booking = await api.createBooking({
        customer_id: customerId,
        vehicle_id: vehicle.id,
        service_id: serviceId,
        booking_date: bookingDate,
        booking_time: bookingTime.length === 5 ? `${bookingTime}:00` : bookingTime,
        source: "dashboard",
        notes: "Booked via website",
      });
      setBookingId(booking.id);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.detail : "Booking failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (bookingId) {
    return (
      <div className="glass-card animate-fade-up rounded-3xl p-10 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-aqua/20 text-aqua">
          <CheckCircle2 className="size-9" />
        </div>
        <p className="mt-6 font-display text-3xl font-bold text-ink">You&apos;re all set!</p>
        <p className="mt-2 text-muted-foreground">
          {selectedService?.name} · {bookingDate} at {bookingTime.slice(0, 5)}
        </p>
        <Badge variant="aqua" className="mt-4">
          Confirmed
        </Badge>
        <p className="mt-4 text-xs text-muted-foreground">Ref {bookingId.slice(0, 8)}…</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/" className={buttonVariants({ variant: "outline", size: "lg" })}>
            Back home
          </Link>
          <Button
            onClick={() => {
              setBookingId(null);
              setStep(1);
            }}
          >
            Book another
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card animate-fade-up rounded-3xl p-6 md:p-8">
      <BookingStepper step={step} />

      {step === 1 && (
        <section className="animate-fade-up">
          <h2 className="font-display text-2xl font-bold text-ink">Choose your service</h2>
          <p className="mt-1 text-sm text-muted-foreground">Tap a package to continue.</p>
          {loadingServices && <p className="mt-6 text-sm text-muted-foreground">Loading services…</p>}
          {serviceError && <p className="mt-6 text-sm text-destructive">{serviceError}</p>}
          {!loadingServices && !serviceError && services.length === 0 && (
            <p className="mt-6 text-sm text-muted-foreground">No active services yet.</p>
          )}
          <div className="mt-6 grid gap-3">
            {services.map((service) => (
              <button
                key={service.id}
                type="button"
                onClick={() => setServiceId(service.id)}
                className={cn(
                  "group rounded-2xl border p-4 text-left transition-all",
                  serviceId === service.id
                    ? "border-aqua bg-gradient-to-r from-aqua/10 to-secondary shadow-sm ring-2 ring-aqua/30"
                    : "border-border bg-white hover:border-aqua/40 hover:shadow-sm",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="font-display text-lg font-bold text-ink">{service.name}</span>
                    {service.description && (
                      <p className="mt-1 text-sm text-muted-foreground">{service.description}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <Badge variant={serviceId === service.id ? "aqua" : "secondary"}>
                      {formatPrice(service.price)}
                    </Badge>
                    <p className="mt-1 text-xs text-muted-foreground">{service.duration_minutes} min</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
          <div className="mt-8 flex justify-end">
            <Button size="lg" disabled={!serviceId} onClick={() => setStep(2)}>
              Continue
            </Button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="animate-fade-up">
          <h2 className="font-display text-2xl font-bold text-ink">Pick a date</h2>
          <p className="mt-1 text-sm text-muted-foreground">When would you like to visit?</p>
          <div className="mt-6">
            <FieldLabel>Appointment date</FieldLabel>
            <Input type="date" min={todayIso()} value={bookingDate} onChange={(e) => setBookingDate(e.target.value)} />
          </div>
          <div className="mt-8 flex justify-between">
            <Button variant="outline" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button size="lg" disabled={!bookingDate} onClick={() => setStep(3)}>
              Continue
            </Button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section className="animate-fade-up">
          <h2 className="font-display text-2xl font-bold text-ink">Choose a time</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Available slots for <span className="font-medium text-ink">{bookingDate}</span>
          </p>
          {slotsLoading && <p className="mt-6 text-sm text-muted-foreground">Checking calendar…</p>}
          {slotsError && <p className="mt-6 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{slotsError}</p>}
          <div className="mt-6 grid grid-cols-3 gap-2 sm:grid-cols-4">
            {slots.map((slot) => {
              const label = slot.slice(0, 5);
              return (
                <button
                  key={slot}
                  type="button"
                  onClick={() => setBookingTime(slot)}
                  className={cn(
                    "rounded-xl border px-2 py-2.5 text-sm font-medium transition-all",
                    bookingTime === slot
                      ? "border-aqua bg-aqua/15 text-primary shadow-sm"
                      : "border-border bg-white hover:border-aqua/50",
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>
          {!slotsLoading && slots.length === 0 && !slotsError && (
            <p className="mt-6 text-sm text-muted-foreground">No open slots that day — try another date.</p>
          )}
          <div className="mt-8 flex justify-between">
            <Button variant="outline" onClick={() => setStep(2)}>
              Back
            </Button>
            <Button size="lg" disabled={!bookingTime} onClick={() => setStep(4)}>
              Continue
            </Button>
          </div>
        </section>
      )}

      {step === 4 && (
        <section className="animate-fade-up space-y-4">
          <h2 className="font-display text-2xl font-bold text-ink">Your details</h2>
          <p className="text-sm text-muted-foreground">We&apos;ll use this to confirm your appointment.</p>
          <div className="mt-4 space-y-4">
            <label className="block">
              <FieldLabel>Name</FieldLabel>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
            </label>
            <label className="block">
              <FieldLabel>Mobile number</FieldLabel>
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+92 300 1234567" type="tel" />
            </label>
          </div>
          <div className="flex justify-between pt-4">
            <Button variant="outline" onClick={() => setStep(3)}>
              Back
            </Button>
            <Button
              size="lg"
              disabled={name.trim().length < 2 || phone.replace(/\D/g, "").length < 7}
              onClick={() => setStep(5)}
            >
              Continue
            </Button>
          </div>
        </section>
      )}

      {step === 5 && (
        <section className="animate-fade-up space-y-4">
          <h2 className="font-display text-2xl font-bold text-ink">Your vehicle</h2>
          <p className="text-sm text-muted-foreground">So we can prep the right bay for you.</p>
          <div className="mt-4 space-y-4">
            <label className="block">
              <FieldLabel>Make</FieldLabel>
              <Input value={make} onChange={(e) => setMake(e.target.value)} placeholder="Suzuki" />
            </label>
            <label className="block">
              <FieldLabel>Model</FieldLabel>
              <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Swift" />
            </label>
            <label className="block">
              <FieldLabel>Type</FieldLabel>
              <select
                value={vehicleType}
                onChange={(e) => setVehicleType(e.target.value)}
                className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30"
              >
                <option value="sedan">Sedan</option>
                <option value="hatchback">Hatchback</option>
                <option value="suv">SUV</option>
                <option value="other">Other</option>
              </select>
            </label>
          </div>
          <div className="flex justify-between pt-4">
            <Button variant="outline" onClick={() => setStep(4)}>
              Back
            </Button>
            <Button
              size="lg"
              disabled={make.trim().length < 1 || model.trim().length < 1}
              onClick={() => setStep(6)}
            >
              Review
            </Button>
          </div>
        </section>
      )}

      {step === 6 && (
        <section className="animate-fade-up">
          <h2 className="font-display text-2xl font-bold text-ink">Confirm booking</h2>
          <p className="mt-1 text-sm text-muted-foreground">Double-check everything looks right.</p>
          <ul className="mt-6 divide-y divide-border overflow-hidden rounded-2xl border border-border bg-white">
            {[
              ["Service", selectedService?.name],
              ["When", `${bookingDate} at ${bookingTime.slice(0, 5)}`],
              ["Name", name],
              ["Phone", normalizePhone(phone)],
              ["Vehicle", `${make} ${model} (${vehicleType})`],
            ].map(([k, v]) => (
              <li key={k} className="flex justify-between gap-4 px-4 py-3 text-sm">
                <span className="text-muted-foreground">{k}</span>
                <span className="font-medium text-ink">{v}</span>
              </li>
            ))}
          </ul>
          {submitError && <p className="mt-4 text-sm text-destructive">{submitError}</p>}
          <div className="mt-8 flex justify-between">
            <Button variant="outline" onClick={() => setStep(5)} disabled={submitting}>
              Back
            </Button>
            <Button size="lg" onClick={confirm} disabled={submitting}>
              {submitting ? "Booking…" : "Confirm booking"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
