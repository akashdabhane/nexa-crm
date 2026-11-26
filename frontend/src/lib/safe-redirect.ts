/**
 * A `?next=` redirect target, but only if it's a path on this site.
 *
 * Anything else ("https://evil.com", "//evil.com", "/\evil.com", which browsers read as
 * "//evil.com") falls back, so a crafted login link can't send someone off-site after they sign in.
 */
export function safeRedirectPath(value: string | null | undefined, fallback = "/dashboard"): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return fallback;
  return value;
}
