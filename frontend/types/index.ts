export type BookingStatus =
  | "pending"
  | "confirmed"
  | "completed"
  | "cancelled"
  | "no_show";

export type BookingSource = "voice" | "dashboard" | "whatsapp";

export type CallOutcome =
  | "booking_created"
  | "information_request"
  | "cancelled"
  | "no_booking";

export interface HealthResponse {
  status: string;
  service?: string;
  environment?: string;
}

export interface DbHealthResponse {
  database: "connected" | "disconnected";
  detail?: string;
}

export interface Service {
  id: string;
  name: string;
  description: string | null;
  duration_minutes: number;
  price: string | number;
  active: boolean;
  created_at: string;
}

export interface Customer {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  created_at: string;
  updated_at: string;
}

export interface Vehicle {
  id: string;
  customer_id: string;
  vehicle_type: string;
  make: string;
  model: string;
  registration_number: string | null;
  created_at: string;
}

export interface Booking {
  id: string;
  customer_id: string;
  vehicle_id: string;
  service_id: string;
  booking_date: string;
  booking_time: string;
  status: BookingStatus;
  source: BookingSource;
  notes: string | null;
  admin_acknowledged_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookingListItem extends Booking {
  customer_name?: string | null;
  customer_phone?: string | null;
  vehicle_label?: string | null;
  service_name?: string | null;
}

export interface AvailabilityResult {
  available: boolean;
  requested_time: string | null;
  alternatives: string[];
  message: string | null;
}

export interface CallLog {
  id: string;
  call_id: string;
  provider: string | null;
  customer_id: string | null;
  phone: string | null;
  started_at: string;
  duration_seconds: number | null;
  outcome: CallOutcome;
  booking_id: string | null;
}

export interface WhatsAppActivity {
  id: string;
  message_id: string;
  sender_id: string;
  response_message: string;
  created_at: string;
}

export interface ConnectionStatus {
  name: string;
  connected: boolean;
  detail: string | null;
}

export interface AdminStatus {
  database: ConnectionStatus;
  gemini: ConnectionStatus;
  whatsapp: ConnectionStatus;
  voice: ConnectionStatus;
  environment: string;
}

export interface VoiceProviderStatus {
  active_provider: string;
  voice_provider_setting?: string;
  providers?: Record<string, { configured?: boolean }>;
}
