"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AdminSidebar } from "@/components/admin/sidebar";
import { AdminAuthProvider, useAdminAuth } from "@/lib/admin-auth";

function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { loading, session, configured } = useAdminAuth();
  const isLogin = pathname === "/admin/login";

  useEffect(() => {
    if (isLogin || loading) return;
    if (!session) {
      router.replace("/admin/login");
    }
  }, [isLogin, loading, session, router]);

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
