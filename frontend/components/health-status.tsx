"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DbHealthResponse, HealthResponse } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type StatusState = "loading" | "ok" | "error";

interface StatusItem {
  label: string;
  state: StatusState;
  message: string;
}

function StatusIndicator({ state }: { state: StatusState }) {
  const colors = {
    loading: "bg-muted-foreground/40 animate-pulse",
    ok: "bg-emerald-500",
    error: "bg-red-500",
  };

  return (
    <span
      className={`inline-block size-2.5 shrink-0 rounded-full ${colors[state]}`}
      aria-hidden="true"
    />
  );
}

export function HealthStatus() {
  const [statuses, setStatuses] = useState<StatusItem[]>([
    { label: "Backend API", state: "loading", message: "Checking..." },
    { label: "Database", state: "loading", message: "Checking..." },
  ]);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    setStatuses([
      { label: "Backend API", state: "loading", message: "Checking..." },
      { label: "Database", state: "loading", message: "Checking..." },
    ]);

    const next: StatusItem[] = [];

    try {
      const response = await fetch(`${API_URL}/health`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = (await response.json()) as HealthResponse;
      next.push({
        label: "Backend API",
        state: "ok",
        message: data.service ?? data.status,
      });
    } catch (error) {
      next.push({
        label: "Backend API",
        state: "error",
        message: error instanceof Error ? error.message : "Unreachable",
      });
    }

    try {
      const response = await fetch(`${API_URL}/health/db`);
      const data = (await response.json()) as DbHealthResponse;

      if (data.database === "connected") {
        next.push({
          label: "Database",
          state: "ok",
          message: "Connected",
        });
      } else {
        next.push({
          label: "Database",
          state: "error",
          message: data.detail ?? "Disconnected",
        });
      }
    } catch (error) {
      next.push({
        label: "Database",
        state: "error",
        message: error instanceof Error ? error.message : "Unreachable",
      });
    }

    setStatuses(next);
    setLastChecked(new Date().toLocaleTimeString());
  }, []);

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>System Status</CardTitle>
        <CardDescription>
          Live connectivity check against the FastAPI backend
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {statuses.map((item) => (
          <div
            key={item.label}
            className="flex items-center justify-between rounded-lg border px-3 py-2.5"
          >
            <div className="flex items-center gap-2.5">
              <StatusIndicator state={item.state} />
              <span className="font-medium">{item.label}</span>
            </div>
            <span className="max-w-[55%] truncate text-right text-xs text-muted-foreground">
              {item.message}
            </span>
          </div>
        ))}
      </CardContent>
      <CardFooter className="justify-between">
        <span className="text-xs text-muted-foreground">
          {lastChecked ? `Last checked ${lastChecked}` : "Checking..."}
        </span>
        <Button variant="outline" size="sm" onClick={() => void checkHealth()}>
          Refresh
        </Button>
      </CardFooter>
    </Card>
  );
}
