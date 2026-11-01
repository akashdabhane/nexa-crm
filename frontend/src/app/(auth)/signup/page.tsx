import type { Metadata } from "next";

import { SignupForm } from "@/features/auth/signup-form";

export const metadata: Metadata = {
  title: "Sign up",
  description:
    "Create your NexaCRM account to manage contacts, leads and deals on a drag-and-drop sales pipeline with a built-in AI assistant.",
  alternates: { canonical: "/signup" },
};

export default function SignupPage() {
  return <SignupForm />;
}
