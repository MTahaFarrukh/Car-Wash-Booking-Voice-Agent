"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ApiError, api } from "@/lib/api";
import type { Service } from "@/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Step = 1 | 2 | 3 | 4 | 5 | 6;

function todayIso() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

function normalizePhone(raw: string) {
  const digits = raw.replace(/\D/g, "");
  if (!digits) return "";
  return raw.trim().startsWith("+") ? `+${digits}` : `+${digits}`;
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
          const todayIso = [
            now.getFullYear(),
            String(now.getMonth() + 1).padStart(2, "0"),
            String(now.getDate()).padStart(2, "0"),
          ].join("-");
          const raw = result.alternatives ?? [];
          const filtered =
            bookingDate === todayIso
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
      <div className="rounded-2xl border border-border bg-white p-8 text-center shadow-sm">
        <p className="font-display text-2xl font-bold text-ink">You&apos;re booked</p>
        <p className="mt-2 text-muted-foreground">
          {selectedService?.name} on {bookingDate} at {bookingTime.slice(0, 5)}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">Confirmation ID: {bookingId}</p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/" className={cn("text-sm font-semibold text-primary hover:underline")}>
            Home
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
    <div className="rounded-2xl border border-border bg-white p-6 shadow-sm md:p-8">
      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        Step {step} of 6
      </p>

      {step === 1 && (
        <section className="mt-4">
          <h2 className="font-display text-2xl font-bold">Choose a service</h2>
          {loadingServices && <p className="mt-4 text-sm text-muted-foreground">Loading services…</p>}
          {serviceError && <p className="mt-4 text-sm text-destructive">{serviceError}</p>}
          {!loadingServices && !serviceError && services.length === 0 && (
            <p className="mt-4 text-sm text-muted-foreground">No active services yet.</p>
          )}
          <div className="mt-4 grid gap-3">
            {services.map((service) => (
              <button
                key={service.id}
                type="button"
                onClick={() => setServiceId(service.id)}
                className={cn(
                  "rounded-xl border px-4 py-3 text-left transition",
                  serviceId === service.id
                    ? "border-aqua bg-secondary"
                    : "border-border hover:border-aqua/50",
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold text-ink">{service.name}</span>
                  <span className="text-sm text-muted-foreground">
                    {service.duration_minutes} min · {String(service.price)}
                  </span>
                </div>
                {service.description && (
                  <p className="mt-1 text-sm text-muted-foreground">{service.description}</p>
                )}
              </button>
            ))}
          </div>
          <div className="mt-6 flex justify-end">
            <Button disabled={!serviceId} onClick={() => setStep(2)}>
              Continue
            </Button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="mt-4">
          <h2 className="font-display text-2xl font-bold">Pick a date</h2>
          <input
            type="date"
            min={todayIso()}
            value={bookingDate}
            onChange={(e) => setBookingDate(e.target.value)}
            className="mt-4 w-full rounded-lg border border-input bg-background px-3 py-2"
          />
          <div className="mt-6 flex justify-between">
            <Button variant="outline" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button disabled={!bookingDate} onClick={() => setStep(3)}>
              Continue
            </Button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section className="mt-4">
          <h2 className="font-display text-2xl font-bold">Available times</h2>
          {slotsLoading && <p className="mt-4 text-sm text-muted-foreground">Checking calendar…</p>}
          {slotsError && <p className="mt-4 text-sm text-destructive">{slotsError}</p>}
          <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-4">
            {slots.map((slot) => {
              const label = slot.slice(0, 5);
              return (
                <button
                  key={slot}
                  type="button"
                  onClick={() => setBookingTime(slot)}
                  className={cn(
                    "rounded-lg border px-2 py-2 text-sm",
                    bookingTime === slot
                      ? "border-aqua bg-secondary font-semibold"
                      : "border-border hover:border-aqua/50",
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>
          {!slotsLoading && slots.length === 0 && !slotsError && (
            <p className="mt-4 text-sm text-muted-foreground">No open slots that day.</p>
          )}
          <div className="mt-6 flex justify-between">
            <Button variant="outline" onClick={() => setStep(2)}>
              Back
            </Button>
            <Button disabled={!bookingTime} onClick={() => setStep(4)}>
              Continue
            </Button>
          </div>
        </section>
      )}

      {step === 4 && (
        <section className="mt-4 space-y-4">
          <h2 className="font-display text-2xl font-bold">Your details</h2>
          <label className="block text-sm">
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-input px-3 py-2"
              placeholder="Your name"
            />
          </label>
          <label className="block text-sm">
            Phone
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="mt-1 w-full rounded-lg border border-input px-3 py-2"
              placeholder="+92…"
            />
          </label>
          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={() => setStep(3)}>
              Back
            </Button>
            <Button
              disabled={name.trim().length < 2 || phone.replace(/\D/g, "").length < 7}
              onClick={() => setStep(5)}
            >
              Continue
            </Button>
          </div>
        </section>
      )}

      {step === 5 && (
        <section className="mt-4 space-y-4">
          <h2 className="font-display text-2xl font-bold">Vehicle</h2>
          <label className="block text-sm">
            Make
            <input
              value={make}
              onChange={(e) => setMake(e.target.value)}
              className="mt-1 w-full rounded-lg border border-input px-3 py-2"
              placeholder="Suzuki"
            />
          </label>
          <label className="block text-sm">
            Model
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="mt-1 w-full rounded-lg border border-input px-3 py-2"
              placeholder="Swift"
            />
          </label>
          <label className="block text-sm">
            Type
            <select
              value={vehicleType}
              onChange={(e) => setVehicleType(e.target.value)}
              className="mt-1 w-full rounded-lg border border-input px-3 py-2"
            >
              <option value="sedan">Sedan</option>
              <option value="hatchback">Hatchback</option>
              <option value="suv">SUV</option>
              <option value="other">Other</option>
            </select>
          </label>
          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={() => setStep(4)}>
              Back
            </Button>
            <Button
              disabled={make.trim().length < 1 || model.trim().length < 1}
              onClick={() => setStep(6)}
            >
              Review
            </Button>
          </div>
        </section>
      )}

      {step === 6 && (
        <section className="mt-4">
          <h2 className="font-display text-2xl font-bold">Confirm booking</h2>
          <ul className="mt-4 space-y-2 rounded-xl bg-foam p-4 text-sm">
            <li>
              <strong>Service:</strong> {selectedService?.name}
            </li>
            <li>
              <strong>When:</strong> {bookingDate} at {bookingTime.slice(0, 5)}
            </li>
            <li>
              <strong>Name:</strong> {name}
            </li>
            <li>
              <strong>Phone:</strong> {normalizePhone(phone)}
            </li>
            <li>
              <strong>Vehicle:</strong> {make} {model} ({vehicleType})
            </li>
          </ul>
          {submitError && <p className="mt-4 text-sm text-destructive">{submitError}</p>}
          <div className="mt-6 flex justify-between">
            <Button variant="outline" onClick={() => setStep(5)} disabled={submitting}>
              Back
            </Button>
            <Button onClick={confirm} disabled={submitting}>
              {submitting ? "Booking…" : "Confirm booking"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
