import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

/** Browser Supabase client (anon key only — never service role). */
export const supabaseConfigured = Boolean(url && anonKey);

/**
 * Cookie-backed browser client so Next.js middleware/proxy can see the session.
 * Do not use a localStorage-only client here — that causes /admin ↔ /admin/login loops.
 */
export const supabase: SupabaseClient = createBrowserClient(
  url || "https://placeholder.supabase.co",
  anonKey || "placeholder-anon-key",
);

export async function getAccessToken(): Promise<string | null> {
  if (!supabaseConfigured) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
