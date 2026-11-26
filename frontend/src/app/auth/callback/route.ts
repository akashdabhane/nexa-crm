import { NextResponse, type NextRequest } from "next/server";

import { safeRedirectPath } from "@/lib/safe-redirect";
import { createClient } from "@/lib/supabase/server";

/**
 * Target of Supabase email links (sign-up confirmation, password reset).
 * Exchanges the one-time `code` for a session cookie, then redirects.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;
  const code = searchParams.get("code");
  // Only allow paths on this site, to avoid an open redirect.
  const safeNext = safeRedirectPath(searchParams.get("next"));

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(`${origin}${safeNext}`);
  }

  const message = searchParams.get("error_description") ?? "The link is invalid or has expired.";
  return NextResponse.redirect(`${origin}/login?error=${encodeURIComponent(message)}`);
}
