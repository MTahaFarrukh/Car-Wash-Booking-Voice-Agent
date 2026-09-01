"use client";

import { useEffect, useRef, useState } from "react";
import Vapi from "@vapi-ai/web";
import { Mic, PhoneOff, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

  useEffect(() => {
    if (state !== "active" && state !== "connecting") return;
    const id = window.setInterval(() => setSeconds((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, [state]);

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
      setError("Microphone permission was denied. Allow the mic to talk to the assistant.");
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
              variableValues: {
                customerPhone: phone.trim(),
                phone: phone.trim(),
              },
              metadata: {
                customerPhone: phone.trim(),
              },
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

  const statusLabel =
    state === "connecting"
      ? "Connecting…"
      : state === "active"
        ? speaking
          ? "Assistant speaking…"
          : "Listening…"
        : state === "ended"
          ? "Call ended"
          : state === "error"
            ? "Call failed"
            : "Ready when you are";

  return (
    <div className="glass-card mx-auto flex w-full max-w-lg flex-col items-center rounded-3xl p-8 text-center">
      <div className="flex items-center gap-2 text-aqua">
        <Sparkles className="size-4" />
        <span className="text-xs font-semibold tracking-wide uppercase">AI receptionist</span>
      </div>
      <p className="mt-3 font-display text-2xl font-bold text-ink">Start a voice booking</p>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        Say your service, date, and time — the assistant books through the same backend as the website.
      </p>

      <label className="mt-6 w-full max-w-sm text-left">
        <span className="mb-1.5 block text-sm font-medium text-ink">Your mobile</span>
        <Input
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+923001234567"
          disabled={state === "connecting" || state === "active"}
        />
      </label>

      {!configured && (
        <p className="mt-6 rounded-xl bg-secondary/80 px-4 py-3 text-left text-sm text-muted-foreground">
          Set <code className="text-xs">NEXT_PUBLIC_VAPI_PUBLIC_KEY</code> and{" "}
          <code className="text-xs">NEXT_PUBLIC_VAPI_ASSISTANT_ID</code> in{" "}
          <code className="text-xs">frontend/.env.local</code>.
        </p>
      )}

      <div className="relative mt-10 flex size-32 items-center justify-center">
        {(state === "active" || state === "connecting") && (
          <>
            <span className="voice-ring absolute inset-0 rounded-full border-2 border-aqua/40" />
            <span className="voice-ring absolute inset-2 rounded-full border border-aqua/25 [animation-delay:0.5s]" />
          </>
        )}
        <div
          className={cn(
            "relative flex size-28 items-center justify-center rounded-full bg-gradient-to-br from-secondary to-white text-primary shadow-inner",
            state === "active" && "from-aqua/25 to-aqua/5 text-aqua",
            speaking && "scale-105 transition-transform",
          )}
        >
          <Mic className={cn("size-10", state === "active" && !speaking && "animate-pulse-soft")} />
        </div>
      </div>

      <p className="mt-6 font-semibold text-ink">{statusLabel}</p>
      {(state === "active" || state === "connecting") && (
        <p className="mt-2 font-mono text-sm tabular-nums text-muted-foreground">{formatDuration(seconds)}</p>
      )}

      {transcript.length > 0 && (
        <div className="mt-6 max-h-40 w-full max-w-sm space-y-2 overflow-y-auto rounded-2xl border border-border bg-white/80 p-3 text-left">
          {transcript.map((line, i) => (
            <div
              key={`${line.role}-${i}`}
              className={cn(
                "rounded-xl px-3 py-2 text-sm",
                line.role === "assistant"
                  ? "bg-secondary text-ink"
                  : "ml-4 bg-primary/10 text-primary",
              )}
            >
              <span className="text-[10px] font-bold uppercase tracking-wide opacity-60">
                {line.role === "assistant" ? "Sparkle" : "You"}
              </span>
              <p className="mt-0.5">{line.text}</p>
            </div>
          ))}
        </div>
      )}

      {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

      <div className="mt-8 flex gap-3">
        {(state === "idle" || state === "ended" || state === "error") && (
          <Button size="lg" onClick={startCall} disabled={!configured}>
            Start AI Call
          </Button>
        )}
        {(state === "connecting" || state === "active") && (
          <Button size="lg" variant="destructive" onClick={endCall}>
            <PhoneOff className="size-4" />
            End Call
          </Button>
        )}
      </div>
    </div>
  );
}
