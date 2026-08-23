/**
 * Centralized FastAPI client for Sparkle Car Wash.
 * Components must use this module instead of calling fetch directly.
 */

import type {
  AdminStatus,
  AvailabilityResult,
  Booking,
  BookingListItem,
  BookingSource,
  BookingStatus,
  CallLog,
  CallOutcome,
  Customer,
  DbHealthResponse,
  HealthResponse,
  Service,
  Vehicle,
  VoiceProviderStatus,
  WhatsAppActivity,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function formatDetail(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "Request failed";
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (detail != null) return JSON.stringify(detail);
  return "Request failed";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { getAccessToken } = await import("@/lib/supabase");
  const token = await getAccessToken();

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(0, "Network error — is the backend running?");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const detail = formatDetail(data);
    if (response.status === 401 && typeof window !== "undefined") {
      const path = window.location.pathname;
      if (path.startsWith("/admin") && path !== "/admin/login") {
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- api client is not a Client Component
        window.location.href = "/admin/login";
      }
    }
    if (response.status === 409) {
      throw new ApiError(
        409,
        detail.includes("slot") || detail.toLowerCase().includes("unavailable")
          ? "That time is no longer available. Please choose another time."
          : detail,
      );
    }
    throw new ApiError(response.status, detail || `HTTP ${response.status}`);
  }

  return data as T;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const out = search.toString();
  return out ? `?${out}` : "";
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  healthDb: () => request<DbHealthResponse>("/health/db"),

  listServices: (activeOnly = true) =>
    request<Service[]>(`/api/services${qs({ active_only: activeOnly })}`),

  getAvailability: (bookingDate: string, serviceId: string, requestedTime?: string) =>
    request<AvailabilityResult>(
      `/api/availability${qs({
        booking_date: bookingDate,
        service_id: serviceId,
        requested_time: requestedTime,
      })}`,
    ),

  createCustomer: (body: { name: string; phone: string; email?: string | null }) =>
    request<Customer>("/api/customers", { method: "POST", body: JSON.stringify(body) }),

  listCustomers: (params?: { q?: string; phone?: string; limit?: number }) =>
    request<Customer[]>(`/api/customers${qs(params ?? {})}`),

  getCustomer: (id: string) => request<Customer>(`/api/customers/${id}`),

  updateCustomer: (id: string, body: Partial<{ name: string; phone: string; email: string | null }>) =>
    request<Customer>(`/api/customers/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  createVehicle: (
    customerId: string,
    body: { make: string; model: string; vehicle_type: string; registration_number?: string | null },
  ) =>
    request<Vehicle>(`/api/customers/${customerId}/vehicles`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listCustomerVehicles: (customerId: string) =>
    request<Vehicle[]>(`/api/customers/${customerId}/vehicles`),

  listVehicles: (limit = 100) => request<Vehicle[]>(`/api/vehicles${qs({ limit })}`),

  getVehicle: (id: string) => request<Vehicle>(`/api/vehicles/${id}`),

  createBooking: (body: {
    customer_id: string;
    vehicle_id: string;
    service_id: string;
    booking_date: string;
    booking_time: string;
    source?: BookingSource;
    notes?: string | null;
  }) =>
    request<Booking>("/api/bookings", {
      method: "POST",
      body: JSON.stringify({ source: "dashboard", ...body }),
    }),

  listBookings: (params?: {
    booking_date?: string;
    status?: BookingStatus;
    customer_id?: string;
    source?: BookingSource;
  }) => request<Booking[]>(`/api/bookings${qs(params ?? {})}`),

  getBooking: (id: string) => request<Booking>(`/api/bookings/${id}`),

  updateBooking: (
    id: string,
    body: Partial<{
      booking_date: string;
      booking_time: string;
      status: BookingStatus;
      notes: string | null;
    }>,
  ) => request<Booking>(`/api/bookings/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  cancelBooking: (id: string) =>
    request<Booking>(`/api/bookings/${id}`, { method: "DELETE" }),

  adminBookings: (params?: {
    booking_date?: string;
    status?: BookingStatus;
    source?: BookingSource;
    q?: string;
    limit?: number;
  }) => request<BookingListItem[]>(`/api/admin/bookings${qs(params ?? {})}`),

  adminCallLogs: (params?: { outcome?: CallOutcome; provider?: string; limit?: number }) =>
    request<CallLog[]>(`/api/admin/call-logs${qs(params ?? {})}`),

  adminWhatsAppActivity: (limit = 50) =>
    request<WhatsAppActivity[]>(`/api/admin/whatsapp/activity${qs({ limit })}`),

  adminStatus: () => request<AdminStatus>("/api/admin/status"),

  adminMe: () =>
    request<{ id: string; email: string; role: string; auth_user_id: string }>("/api/admin/me"),

  voiceProviderStatus: () => request<VoiceProviderStatus>("/api/voice/provider"),
};

export function whatsappBookUrl(): string {
  const raw = (process.env.NEXT_PUBLIC_WHATSAPP_NUMBER ?? "").replace(/\D/g, "");
  if (!raw) return "#";
  const text = encodeURIComponent("Hi Sparkle, I'd like to book a car wash.");
  return `https://wa.me/${raw}?text=${text}`;
}

export { API_URL };
