import { createBrowserClient } from "@supabase/ssr";

import { supabaseKey, supabaseUrl } from "./config";

/** Supabase client for Client Components (returns a singleton in the browser). */
export function createClient() {
  return createBrowserClient(supabaseUrl, supabaseKey);
}
