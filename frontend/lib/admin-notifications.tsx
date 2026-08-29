"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api } from "@/lib/api";
import type { BookingListItem } from "@/types";

type AdminNotificationsContextValue = {
  count: number;
  items: BookingListItem[];
  loading: boolean;
  refresh: () => Promise<void>;
  acknowledge: (bookingId: string) => Promise<void>;
  busyId: string | null;
};

const AdminNotificationsContext = createContext<AdminNotificationsContextValue | null>(null);

const POLL_MS = 20_000;

export function AdminNotificationsProvider({ children }: { children: ReactNode }) {
  const [count, setCount] = useState(0);
  const [items, setItems] = useState<BookingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [countRes, list] = await Promise.all([
        api.adminNotificationCount(),
        api.adminNotifications(),
      ]);
      setCount(countRes.count);
      setItems(list);
    } catch (err) {
      if (!(err instanceof ApiError && (err.status === 401 || err.status === 403))) {
        console.error("admin notifications refresh failed", err);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const acknowledge = useCallback(
    async (bookingId: string) => {
      setBusyId(bookingId);
      try {
        await api.acknowledgeBooking(bookingId);
        await refresh();
      } finally {
        setBusyId(null);
      }
    },
    [refresh],
  );

  const value = useMemo(
    () => ({ count, items, loading, refresh, acknowledge, busyId }),
    [count, items, loading, refresh, acknowledge, busyId],
  );

  return (
    <AdminNotificationsContext.Provider value={value}>{children}</AdminNotificationsContext.Provider>
  );
}

export function useAdminNotifications() {
  const ctx = useContext(AdminNotificationsContext);
  if (!ctx) {
    throw new Error("useAdminNotifications must be used within AdminNotificationsProvider");
  }
  return ctx;
}

export function sourceChannelLabel(source: BookingListItem["source"]) {
  if (source === "dashboard") return "Web";
  if (source === "voice") return "Voice";
  return "WhatsApp";
}
