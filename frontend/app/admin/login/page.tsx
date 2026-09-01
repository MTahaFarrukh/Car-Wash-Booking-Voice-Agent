"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "@/lib/admin-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AdminLoginPage() {
  const router = useRouter();
  const { configured, loading, session, signIn } = useAdminAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && session) {
      router.replace("/admin");
      router.refresh();
    }
  }, [loading, session, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await signIn(email.trim(), password);
      if (result.error) {
        setError(result.error);
        return;
      }
      router.replace("/admin");
      router.refresh();
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="sparkle-hero-bg flex min-h-screen items-center justify-center text-sm text-chrome">
        Checking session…
      </div>
    );
  }

  if (session) {
    return (
      <div className="sparkle-hero-bg flex min-h-screen items-center justify-center text-sm text-chrome">
        Opening dashboard…
      </div>
    );
  }

  return (
    <div className="sparkle-hero-bg flex min-h-screen items-center justify-center px-4 py-12">
      <div className="sparkle-surface w-full max-w-md rounded-lg p-8 md:p-10">
        <Link href="/" className="text-sm font-medium text-aqua hover:underline">
          ← Sparkle
        </Link>
        <p className="mt-8 font-display text-3xl font-bold text-warm-white">Admin</p>
        <p className="mt-2 text-sm text-chrome">Sign in to the operations center.</p>

        {!configured && (
          <p className="mt-4 rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            Set Supabase env vars in <code className="text-xs">frontend/.env.local</code>.
          </p>
        )}

        <form className="mt-8 space-y-4" onSubmit={onSubmit}>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-chrome">Email</span>
            <Input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="border-white/10 bg-black/20 text-warm-white"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-chrome">Password</span>
            <Input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="border-white/10 bg-black/20 text-warm-white"
            />
          </label>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button
            type="submit"
            size="lg"
            className="w-full bg-aqua text-graphite hover:bg-aqua/90"
            disabled={submitting || !configured}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}
