"use client";

import { useEffect, useRef, useState } from "react";
import Vapi from "@vapi-ai/web";
import { Mic, PhoneOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type CallState = "idle" | "connecting" | "active" | "ended" | "error";

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
  const [transcript, setTranscript] = useState<string>("");
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
    setTranscript("");
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
          const who = message.role === "assistant" ? "Assistant" : "You";
          setTranscript(`${who}: ${message.transcript}`);
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
        // Browser calls have no PSTN caller ID — pass phone so Save Booking can succeed.
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
    <div className="mx-auto flex w-full max-w-lg flex-col items-center rounded-3xl border border-border bg-white p-8 text-center shadow-sm">
      <p className="font-display text-2xl font-bold text-ink">AI Booking Assistant</p>
      <p className="mt-2 text-sm text-muted-foreground">
        Speak naturally — bookings still go through Sparkle&apos;s backend tools.
      </p>

      <label className="mt-6 w-full max-w-sm text-left text-sm">
        <span className="text-muted-foreground">Your mobile (with country code)</span>
        <input
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+923001234567"
          disabled={state === "connecting" || state === "active"}
          className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 outline-none focus:border-teal-600 disabled:opacity-60"
        />
      </label>

      {!configured && (
        <p className="mt-6 rounded-xl bg-foam px-4 py-3 text-sm text-muted-foreground">
          Set <code className="text-xs">NEXT_PUBLIC_VAPI_PUBLIC_KEY</code> and{" "}
          <code className="text-xs">NEXT_PUBLIC_VAPI_ASSISTANT_ID</code> in{" "}
          <code className="text-xs">frontend/.env.local</code> (VAPI Dashboard public key — never the
          server API key).
        </p>
      )}

      <div
        className={cn(
          "mt-10 flex size-28 items-center justify-center rounded-full bg-secondary text-primary",
          state === "active" && "animate-pulse-soft bg-aqua/20 text-aqua",
        )}
      >
        <Mic className="size-10" />
      </div>

      <p className="mt-6 font-semibold text-ink">{statusLabel}</p>
      {(state === "active" || state === "connecting") && (
        <p className="mt-2 font-mono text-sm text-muted-foreground">{formatDuration(seconds)}</p>
      )}
      {transcript && <p className="mt-4 max-w-sm text-sm text-muted-foreground">{transcript}</p>}
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
