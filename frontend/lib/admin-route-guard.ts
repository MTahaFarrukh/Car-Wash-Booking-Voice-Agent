/**
 * Pure redirect rules for admin auth (middleware + client).
 * Kept separate so the redirect loop regression can be unit-tested without Next.
 */

export function adminRedirectPath(
  pathname: string,
  hasSession: boolean,
): "/admin/login" | "/admin" | null {
  const isAdmin = pathname === "/admin" || pathname.startsWith("/admin/");
  if (!isAdmin) return null;

  const isLogin = pathname === "/admin/login";

  if (!hasSession && !isLogin) return "/admin/login";
  if (hasSession && isLogin) return "/admin";
  return null;
}
