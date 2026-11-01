import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/features/auth/login-form";

export const metadata: Metadata = {
  title: "Log in",
  description: "Log in to NexaCRM to manage your contacts, leads, deals, tasks and sales pipeline.",
  alternates: { canonical: "/login" },
};

export default function LoginPage() {
  // LoginForm reads ?next= and ?error= via useSearchParams, which needs a Suspense boundary.
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
