/**
 * Node built-in test for admin redirect rules (redirect-loop regression).
 * Run: node --test lib/admin-route-guard.test.mjs
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";

// Keep in sync with admin-route-guard.ts
function adminRedirectPath(pathname, hasSession) {
  const isAdmin = pathname === "/admin" || pathname.startsWith("/admin/");
  if (!isAdmin) return null;
  const isLogin = pathname === "/admin/login";
  if (!hasSession && !isLogin) return "/admin/login";
  if (hasSession && isLogin) return "/admin";
  return null;
}

describe("adminRedirectPath", () => {
  it("sends unauthenticated /admin to login", () => {
    assert.equal(adminRedirectPath("/admin", false), "/admin/login");
    assert.equal(adminRedirectPath("/admin/bookings", false), "/admin/login");
  });

  it("allows unauthenticated /admin/login", () => {
    assert.equal(adminRedirectPath("/admin/login", false), null);
  });

  it("sends authenticated /admin/login to dashboard (no loop with session)", () => {
    assert.equal(adminRedirectPath("/admin/login", true), "/admin");
  });

  it("allows authenticated /admin and nested routes", () => {
    assert.equal(adminRedirectPath("/admin", true), null);
    assert.equal(adminRedirectPath("/admin/settings", true), null);
  });

  it("ignores public routes", () => {
    assert.equal(adminRedirectPath("/", false), null);
    assert.equal(adminRedirectPath("/book", true), null);
    assert.equal(adminRedirectPath("/voice", false), null);
  });
});
