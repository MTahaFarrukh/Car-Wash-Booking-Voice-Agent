"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Vapi from "@vapi-ai/web";
import { PhoneOff } from "lucide-react";
import { VoiceOrb, type VoiceOrbState } from "@/components/sparkle/voice-orb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { extractVoiceBookingHints } from "@/lib/voice-booking-hints";
import { cn } from "@/lib/utils";

type CallState = "idle" | "connecting" | "active" | "ended" | "error";
type TranscriptLine = { role: "user" | "assistant"; text: string };

function formatDuration(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

function mapOrbState(state: CallState, speaking: boolean): VoiceOrbState {
  if (state === "connecting") return "connecting";
  if (state === "active" && speaking) return "speaking";
  if (state === "active") return "listening";
  if (state === "ended") return "completed";
  return "idle";
}

function HintRow({ label, value, visible }: { label: string; value?: string; visible: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center justify-between border-b border-white/5 py-3 last:border-0 transition-all duration-500",
        visible ? "opacity-100" : "opacity-30",
      )}
    >
      <span className="text-xs text-chrome">{label}</span>
      <span className={cn("text-sm font-medium", value ? "text-warm-white" : "text-chrome/50")}>
        {value ?? "—"}
      </span>
    </div>
  );
}

export function VapiCallPanel() {
  const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY?.trim() ?? "";
  const assistantId = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID?.trim() ?? "";
  const configured = Boolean(publicKey && assistantId);

  const vapiRef = useRef<Vapi | null>(null);
  const [state, setState] = useState<CallState>("idle");
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [seconds, setSeconds] = useState(0);
  const [phone, setPhone] = useState("");
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  const hints = useMemo(() => extractVoiceBookingHints(transcript), [transcript]);
  const orbState = mapOrbState(state, speaking);

  useEffect(() => {
    if (state !== "active" && state !== "connecting") return;
    const id = window.setInterval(() => setSeconds((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, [state]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  useEffect(() => {
    return () => {
      try {
        vapiRef.current?.stop();
      } catch {
        /* ignore */
      }
    };
  }, []);

  async function startCall() {
    setError(null);
    setTranscript([]);
    setSeconds(0);
    if (!configured) {
      setError("VAPI public key or assistant ID is not configured in the frontend env.");
      setState("error");
      return;
    }

    try {
      const permission = await navigator.mediaDevices.getUserMedia({ audio: true });
      permission.getTracks().forEach((t) => t.stop());
    } catch {
      setError("Microphone permission was denied.");
      setState("error");
      return;
    }

    setState("connecting");
    try {
      const vapi = new Vapi(publicKey);
      vapiRef.current = vapi;

      vapi.on("call-start", () => setState("active"));
      vapi.on("call-end", () => setState("ended"));
      vapi.on("speech-start", () => setSpeaking(true));
      vapi.on("speech-end", () => setSpeaking(false));
      vapi.on("message", (message: { type?: string; role?: string; transcript?: string; transcriptType?: string }) => {
        if (message?.type === "transcript" && message.transcriptType === "final" && message.transcript) {
          const role = message.role === "assistant" ? "assistant" : "user";
          setTranscript((prev) => [...prev, { role, text: message.transcript! }]);
        }
      });
      vapi.on("error", (err: unknown) => {
        const msg =
          err && typeof err === "object" && "message" in err
            ? String((err as { message: unknown }).message)
            : "Could not connect the voice call.";
        setError(msg);
        setState("error");
      });

      await vapi.start(assistantId, {
        ...(phone.trim()
          ? {
              variableValues: { customerPhone: phone.trim(), phone: phone.trim() },
              metadata: { customerPhone: phone.trim() },
            }
          : {}),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the VAPI call.");
      setState("error");
    }
  }

  function endCall() {
    try {
      vapiRef.current?.stop();
    } catch {
      /* ignore */
    }
    setState("ended");
    setSpeaking(false);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      {/* Main call surface */}
      <div className="sparkle-surface rounded-lg p-6 md:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold tracking-[0.2em] text-aqua uppercase">Sparkle Voice</p>
            <p className="mt-1 font-display text-xl font-semibold text-warm-white">AI Booking Assistant</p>
          </div>
          {(state === "active" || state === "connecting") && (
            <span className="font-mono text-sm tabular-nums text-chrome">{formatDuration(seconds)}</span>
          )}
        </div>

        <div className="mt-10 flex justify-center">
          <VoiceOrb state={orbState} size="lg" />
        </div>

        <label className="mt-8 block max-w-sm">
          <span className="mb-1.5 block text-xs font-medium text-chrome">Mobile (for booking confirmation)</span>
          <Input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+923001234567"
            disabled={state === "connecting" || state === "active"}
            className="border-white/10 bg-black/20 text-warm-white placeholder:text-chrome/50"
          />
        </label>

        {!configured && (
          <p className="mt-4 text-sm text-chrome">
            Configure <code className="text-aqua">NEXT_PUBLIC_VAPI_PUBLIC_KEY</code> and assistant ID in{" "}
            <code className="text-aqua">.env.local</code>.
          </p>
        )}

        {transcript.length > 0 && (
          <div className="mt-8 max-h-52 space-y-2 overflow-y-auto rounded-md border border-white/5 bg-black/20 p-4">
            {transcript.map((line, i) => (
              <div
                key={`${line.role}-${i}`}
                className={cn(
                  "animate-slide-in rounded-md px-3 py-2 text-sm",
                  line.role === "assistant" ? "bg-white/5 text-warm-white" : "ml-4 text-aqua",
                )}
              >
                <span className="text-[10px] font-bold tracking-wide text-chrome uppercase">
                  {line.role === "assistant" ? "Sparkle" : "You"}
                </span>
                <p className="mt-0.5">{line.text}</p>
              </div>
            ))}
            <div ref={transcriptEndRef} />
          </div>
        )}

        {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

        <div className="mt-8 flex flex-wrap gap-3">
          {(state === "idle" || state === "ended" || state === "error") && (
            <Button
              size="lg"
              onClick={startCall}
              disabled={!configured}
              className="bg-aqua text-graphite hover:bg-aqua/90"
            >
              Start call
            </Button>
          )}
          {(state === "connecting" || state === "active") && (
            <Button size="lg" variant="destructive" onClick={endCall}>
              <PhoneOff className="size-4" />
              End call
            </Button>
          )}
        </div>
      </div>

      {/* Booking details panel */}
      <div className="sparkle-surface h-fit rounded-lg p-6 lg:sticky lg:top-6">
        <p className="text-[10px] font-semibold tracking-[0.2em] text-chrome uppercase">Booking details</p>
        <p className="mt-1 font-display text-lg font-semibold text-warm-white">Live extraction</p>
        <p className="mt-2 text-xs text-chrome">Fields appear as Sparkle understands your conversation.</p>

        <div className="mt-6">
          <HintRow label="Customer" value={phone.trim() || hints.customer} visible={Boolean(phone || hints.customer)} />
          <HintRow label="Vehicle" value={hints.vehicle} visible={Boolean(hints.vehicle)} />
          <HintRow label="Service" value={hints.service} visible={Boolean(hints.service)} />
          <HintRow label="Date" value={hints.date} visible={Boolean(hints.date)} />
          <HintRow label="Time" value={hints.time} visible={Boolean(hints.time)} />
          <HintRow label="Status" value={hints.status} visible={Boolean(hints.status)} />
        </div>

        {state === "idle" && transcript.length === 0 && (
          <p className="mt-6 text-xs leading-relaxed text-chrome">
            Try: &ldquo;Hey Sparkle, book a premium wash for my Suzuki Swift tomorrow at 5.&rdquo;
          </p>
        )}
      </div>
    </div>
  );
}
