"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AdminSidebar } from "@/components/admin/sidebar";
import { AdminAuthProvider, useAdminAuth } from "@/lib/admin-auth";
import { ApiError, api } from "@/lib/api";

type Probe =
  | { token: string; status: "ok" }
  | { token: string; status: "forbidden" | "error"; message: string };

function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { loading, session, configured, signOut } = useAdminAuth();
  const isLogin = pathname === "/admin/login";
  const token = session?.access_token ?? null;
  const [probe, setProbe] = useState<Probe | null>(null);

  const authz =
    !token ? "idle" : probe?.token === token ? probe.status : "checking";
  const authzMessage =
    probe && probe.token === token && probe.status !== "ok" ? probe.message : null;

  useEffect(() => {
    if (isLogin || loading) return;
    if (!session) {
      router.replace("/admin/login");
    }
  }, [isLogin, loading, session, router]);

  useEffect(() => {
    if (isLogin || loading || !token) return;

    let cancelled = false;

    api
      .adminMe()
      .then(() => {
        if (!cancelled) setProbe({ token, status: "ok" });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/admin/login");
          return;
        }
        if (err instanceof ApiError && err.status === 403) {
          setProbe({
            token,
            status: "forbidden",
            message: err.message || "This account is not authorized for admin access.",
          });
          return;
        }
        setProbe({
          token,
          status: "error",
          message: err instanceof Error ? err.message : "Could not verify admin access.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [isLogin, loading, token, router]);

  if (isLogin) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-foam text-sm text-muted-foreground">
        Restoring admin session…
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-foam text-sm text-muted-foreground">
        Redirecting to login…
      </div>
    );
  }

  if (authz === "idle" || authz === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-foam text-sm text-muted-foreground">
        Verifying admin access…
      </div>
    );
  }

  if (authz === "forbidden" || authz === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-foam px-4 text-center">
        <p className="text-sm font-medium text-foreground">
          {authz === "forbidden" ? "Not an admin" : "Admin verification failed"}
        </p>
        <p className="max-w-md text-sm text-muted-foreground">
          {authzMessage ?? "You are signed in, but this account cannot use the admin dashboard."}
        </p>
        <button
          type="button"
          className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
          onClick={async () => {
            await signOut();
            router.replace("/admin/login");
            router.refresh();
          }}
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-foam">
      <AdminSidebar pathname={pathname} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-border bg-white px-6 py-4">
          <p className="text-sm text-muted-foreground">Sparkle Car Wash · Admin</p>
          {!configured && (
            <p className="mt-1 text-xs text-amber-700">Supabase env vars missing — login will not work.</p>
          )}
        </header>
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </div>
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminShell>{children}</AdminShell>
    </AdminAuthProvider>
  );
}
