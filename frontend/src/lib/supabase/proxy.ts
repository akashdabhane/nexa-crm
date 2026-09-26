import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import { isSupabaseConfigured, supabaseKey, supabaseUrl } from "./config";

const PUBLIC_PATHS = ["/login", "/signup", "/forgot-password", "/auth"];
const AUTH_PAGES = ["/login", "/signup", "/forgot-password"];

const matches = (pathname: string, paths: string[]) =>
  paths.some((path) => pathname === path || pathname.startsWith(`${path}/`));

/**
 * Refreshes the Supabase session cookie and performs optimistic redirects:
 * signed-out users go to /login, signed-in users skip the auth pages.
 * Real authorization happens in FastAPI, which verifies the JWT on every call.
 */
export async function updateSession(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!isSupabaseConfigured) {
    // Let the login page explain what is missing instead of crashing.
    return matches(pathname, PUBLIC_PATHS)
      ? NextResponse.next()
      : NextResponse.redirect(new URL("/login", request.url));
  }

  let response = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });

  // getClaims() validates the JWT (refreshing it first when it has expired).
  const { data } = await supabase.auth.getClaims();
  const isSignedIn = Boolean(data?.claims);

  if (!isSignedIn && !matches(pathname, PUBLIC_PATHS)) {
    const url = new URL("/login", request.url);
    if (pathname !== "/") url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isSignedIn && (pathname === "/" || matches(pathname, AUTH_PAGES))) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return response;
}
