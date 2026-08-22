"use client";

import { usePathname } from "next/navigation";
import { AdminSidebar } from "@/components/admin/sidebar";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen bg-foam">
      <AdminSidebar pathname={pathname} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-border bg-white px-6 py-4">
          <p className="text-sm text-muted-foreground">Sparkle Car Wash · Admin</p>
        </header>
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </div>
    </div>
  );
}
