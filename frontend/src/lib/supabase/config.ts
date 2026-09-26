export const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";

/** False until the Supabase env vars are filled in (see frontend/.env.example). */
export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseKey);
