import { AlertTriangle } from "lucide-react";

import { Logo } from "@/components/layout/logo";
import { isSupabaseConfigured } from "@/lib/supabase/config";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="flex flex-col gap-6 p-6 md:p-10">
        <Logo />
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-sm space-y-4">
            {!isSupabaseConfigured && (
              <div className="flex gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                <p>
                  Supabase is not configured. Copy <code>frontend/.env.example</code> to{" "}
                  <code>frontend/.env.local</code> and add your project URL and publishable key.
                </p>
              </div>
            )}
            {children}
          </div>
        </div>
      </div>
      <div className="relative hidden overflow-hidden bg-primary lg:flex lg:flex-col lg:justify-end lg:p-12">
        <div className="absolute -top-24 -right-24 size-96 rounded-full bg-white/10" />
        <div className="absolute top-1/3 -left-16 size-64 rounded-full bg-white/5" />
        <blockquote className="relative space-y-3 text-primary-foreground">
          <p className="text-2xl font-semibold leading-snug">
            Every contact, lead and deal in one place — so your team always knows what to do next.
          </p>
          <footer className="text-sm text-primary-foreground/70">NexaCRM · Sales pipeline management</footer>
        </blockquote>
      </div>
    </div>
  );
}
