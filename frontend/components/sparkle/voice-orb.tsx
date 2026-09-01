"use client";

import { Mic } from "lucide-react";
import { cn } from "@/lib/utils";
import { VoiceWaveform } from "./voice-waveform";

export type VoiceOrbState = "idle" | "connecting" | "listening" | "thinking" | "speaking" | "completed";

const STATE_LABEL: Record<VoiceOrbState, string> = {
  idle: "Ready",
  connecting: "Connecting",
  listening: "Listening",
  thinking: "Processing",
  speaking: "Speaking",
  completed: "Complete",
};

export function VoiceOrb({
  state = "idle",
  className,
  size = "lg",
}: {
  state?: VoiceOrbState;
  className?: string;
  size?: "md" | "lg";
}) {
  const active = state === "listening" || state === "speaking" || state === "connecting";
  const speaking = state === "speaking";
  const dim = size === "md" ? "size-24" : "size-32";

  return (
    <div className={cn("flex flex-col items-center gap-4", className)}>
      <div className={cn("relative flex items-center justify-center", dim)}>
        {active && (
          <>
            <span className="voice-ring absolute inset-0 rounded-full border border-aqua/30" />
            <span className="voice-ring absolute inset-2 rounded-full border border-aqua/15 [animation-delay:0.6s]" />
          </>
        )}
        <div
          className={cn(
            "relative flex size-[85%] items-center justify-center rounded-full border transition-all duration-500",
            "border-white/10 bg-gradient-to-b from-graphite-elevated to-graphite",
            active && "animate-orb-breathe border-aqua/40",
            speaking && "border-aqua/60",
          )}
        >
          <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle_at_30%_20%,rgba(46,196,182,0.15),transparent_60%)]" />
          <Mic
            className={cn(
              "relative size-8 text-chrome transition-colors",
              active && "text-aqua",
              speaking && "scale-110",
            )}
          />
        </div>
      </div>
      <div className="text-center">
        <p className="text-[10px] font-semibold tracking-[0.2em] text-chrome uppercase">
          {STATE_LABEL[state]}
        </p>
        <VoiceWaveform active={active} bars={16} className="mt-2 h-6" />
      </div>
    </div>
  );
}
