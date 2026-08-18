export enum BookingStatus {
  Pending = "pending",
  Confirmed = "confirmed",
  Completed = "completed",
  Cancelled = "cancelled",
  NoShow = "no_show",
}

export enum BookingSource {
  Voice = "voice",
  Dashboard = "dashboard",
}

export enum CallOutcome {
  BookingCreated = "booking_created",
  BookingRescheduled = "booking_rescheduled",
  BookingCancelled = "booking_cancelled",
  InfoProvided = "info_provided",
  NoAction = "no_action",
  Failed = "failed",
}

export interface HealthResponse {
  status: string;
  service?: string;
  environment?: string;
}

export interface DbHealthResponse {
  database: "connected" | "disconnected";
  detail?: string;
}
