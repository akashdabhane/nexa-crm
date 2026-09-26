import axios, { AxiosError } from "axios";

import { createClient } from "@/lib/supabase/client";

/** Axios instance for the FastAPI backend. Adds the Supabase access token to every request. */
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
  // Serialize arrays as ?tag=a&tag=b, which is what FastAPI expects.
  paramsSerializer: { indexes: null },
});

api.interceptors.request.use(async (config) => {
  const { data } = await createClient().auth.getSession();
  const token = data.session?.access_token;
  if (token) config.headers.Authorization = `Bearer ${token}`;

  // Drop empty filter values so they don't reach the API as "?status=".
  if (config.params) {
    config.params = Object.fromEntries(
      Object.entries(config.params).filter(([, value]) => value !== "" && value !== null && value !== undefined),
    );
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      await createClient().auth.signOut();
      // A full page load (not router.push) so all cached data is dropped.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

type ValidationIssue = { loc: (string | number)[]; msg: string };

/** Turns an API error into a human-readable message for toasts and alerts. */
export function getErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string | ValidationIssue[] } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const { loc, msg } = detail[0];
      return `${String(loc[loc.length - 1])}: ${msg}`;
    }
    if (!error.response) return "Cannot reach the server. Is the backend running?";
  }
  return error instanceof Error ? error.message : fallback;
}
