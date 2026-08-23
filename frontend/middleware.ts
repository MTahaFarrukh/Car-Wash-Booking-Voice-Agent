import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Lightweight gate: send unauthenticated browser navigations to /admin/login.
 * Session cookies from Supabase are named sb-*-auth-token (project-specific).
 * Full verification still happens client-side + on the FastAPI admin APIs.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!pathname.startsWith("/admin") || pathname === "/admin/login") {
    return NextResponse.next();
  }

  const hasSupabaseCookie = request.cookies
    .getAll()
    .some((c) => c.name.includes("auth-token") || c.name.startsWith("sb-"));

  if (!hasSupabaseCookie) {
    const login = request.nextUrl.clone();
    login.pathname = "/admin/login";
    return NextResponse.redirect(login);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"],
};
