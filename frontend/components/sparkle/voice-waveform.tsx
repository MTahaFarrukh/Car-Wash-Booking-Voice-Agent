"use client";

import { cn } from "@/lib/utils";

export function VoiceWaveform({
  active = false,
  bars = 24,
  className,
}: {
  active?: boolean;
  bars?: number;
  className?: string;
}) {
  return (
    <div className={cn("flex h-8 items-end justify-center gap-[3px]", className)} aria-hidden>
      {Array.from({ length: bars }).map((_, i) => (
        <span
          key={i}
          className={cn(
            "w-[3px] rounded-full bg-aqua/80 transition-all duration-300",
            active ? "waveform-bar" : "h-1 opacity-40",
          )}
          style={active ? { animationDelay: `${(i % 8) * 0.08}s`, height: `${12 + (i % 5) * 4}px` } : undefined}
        />
      ))}
    </div>
  );
}
