"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { VoiceOrb } from "./voice-orb";
import { VoiceWaveform } from "./voice-waveform";

const DEMO_LINES = [
  { delay: 800, text: '"Hey Sparkle, book me a premium wash tomorrow at 5."' },
];

const DEMO_FIELDS = [
  { key: "service", label: "Service", value: "Premium Wash", delay: 2200 },
  { key: "date", label: "Date", value: "Tomorrow", delay: 2800 },
  { key: "time", label: "Time", value: "5:00 PM", delay: 3400 },
  { key: "status", label: "Status", value: "Confirmed", delay: 4000 },
];

export function HeroVoiceDemo() {
  const [phase, setPhase] = useState(0);
  const [visibleFields, setVisibleFields] = useState<string[]>([]);

  useEffect(() => {
    const timers: number[] = [];
    DEMO_FIELDS.forEach((f) => {
      timers.push(
        window.setTimeout(() => {
          setVisibleFields((prev) => [...prev, f.key]);
        }, f.delay),
      );
    });
    timers.push(window.setTimeout(() => setPhase(1), 600));
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="relative w-full max-w-md">
      <div className="sparkle-surface relative overflow-hidden rounded-lg p-6">
        <div className="sparkle-grid-fine absolute inset-0 opacity-40" aria-hidden />
        <div className="relative">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold tracking-[0.2em] text-aqua uppercase">Voice AI</span>
            <span className="flex items-center gap-1.5 text-[10px] text-chrome">
              <span className="size-1.5 rounded-full bg-aqua animate-pulse-soft" />
              Live
            </span>
          </div>

          <div className="mt-6 flex justify-center">
            <VoiceOrb state={phase >= 1 ? "speaking" : "listening"} size="md" />
          </div>

          <div className="mt-4 rounded-md border border-white/5 bg-black/20 px-4 py-3">
            <p className="text-sm text-chrome italic">{DEMO_LINES[0].text}</p>
            <VoiceWaveform active className="mt-3" bars={20} />
          </div>

          <div className="mt-5 space-y-2">
            {DEMO_FIELDS.map((field) => (
              <div
                key={field.key}
                className={cn(
                  "flex items-center justify-between rounded-md border border-white/5 px-3 py-2 transition-all duration-500",
                  visibleFields.includes(field.key)
                    ? "translate-x-0 opacity-100"
                    : "translate-x-2 opacity-0",
                )}
              >
                <span className="text-xs text-chrome">{field.label}</span>
                <span className="flex items-center gap-2 text-sm font-medium text-warm-white">
                  {field.value}
                  {field.key === "status" && visibleFields.includes("status") && (
                    <Check className="size-3.5 text-aqua" />
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-4 -z-10 rounded-2xl bg-aqua/5 blur-3xl"
      />
    </div>
  );
}
